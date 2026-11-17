import json
import asyncio
import logging
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from services.work_program_view import rows_for as _wp_rows
from models.engagement import Engagement, jurisdictions_or_default
from models.agent_run import AgentRun
from models.planning import TopicIntelligence
from services.regulatory_agent import run_regulatory_agent
from services.policy_agent import run_policy_agent
from services.interview_agent import run_interview_agent
from services.lens_regulatory_agent import run_lens_regulatory_agent
from services.lens_supervisory_agent import run_lens_supervisory_agent
from services.lens_society_agent import run_lens_society_agent
from services.memory_context import recall_for
from services.agent_contract import run_agent
from services.agent_schemas import TopicPrimer
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services.prompt_safety import wrap_untrusted
from services.activity_service import log_activity
from services.orchestrator_agent import synthesize_topic_intelligence
from services.ti_verification import verify as verify_open_points, format_for_prompt as format_verification


_PRIMER_SYSTEM = BASE_SYSTEM_PROMPT + (
    "\n\nYou explain an audit topic to an internal auditor who is new to it. "
    "Be accurate, neutral and concise."
)


def _build_primer_prompt(topic: str, jurisdictions: list[str], lenses: dict[str, str | None],
                         auditor_note: str | None = None, verified: str | None = None) -> str:
    """The primer is written from what the three lenses found, not from memory.

    It used to be asked for before the lenses ran, so it knew nothing of what
    they found (a regulation adopted last July, say) and told a different story
    from the rest of the memo.
    """
    juris = ", ".join(jurisdictions) if jurisdictions else "NL, EU"
    parts = [
        f'Explain the internal-audit topic "{topic}" to an auditor who is new to it.',
        f"Jurisdictions in scope: {juris}. Stay strictly within these jurisdictions: reference only the "
        f"regulators and rules that apply there, plus EU-/international-level law that binds them.",
    ]
    if auditor_note and auditor_note.strip():
        parts.append(wrap_untrusted(auditor_note, "the auditor's note on what this audit covers"))
    for name, text in lenses.items():
        if text and text.strip():
            parts.append(wrap_untrusted(text, f"{name} summary"))
    if verified:
        parts.append(wrap_untrusted(verified, "verification of the statements the summaries left open"))
        parts.append("Where the verification above settles a point, write it as settled (CONFIRMED) or as corrected "
                     "(CORRECTED); where it says NOT SETTLED, keep calling it unconfirmed.")
    parts.append(
        "Use only the summaries above and the plain definition of the topic. State a date or a legal status "
        "only if a summary gives it, and where the summaries call something unconfirmed or disagree, say so "
        "in `rules` instead of choosing. Do not mention the lenses by name. Plain words, no preamble."
    )
    return "\n\n".join(parts)


def format_primer(primer: TopicPrimer) -> str:
    """The typed answer as the scannable text the page already shows."""
    return (f"{primer.lead.strip()}\n\n"
            f"- **In practice:** {primer.in_practice.strip()}\n"
            f"- **Why it matters:** {primer.why_it_matters.strip()}\n"
            f"- **Rules that apply:** {primer.rules.strip()}\n"
            f"- **What to expect in the research:** {primer.what_surfaces.strip()}")


async def _generate_topic_primer(engagement_id: str, lenses: dict[str, str | None] | None = None,
                                 auditor_note: str | None = None, verified: str | None = None) -> str | None:
    """Plain-language 'what is this topic' explainer. Fail-safe: callers ignore errors.

    Typed, so a reply cut off by the token limit raises (AgentTruncated) and is
    never stored; the caller keeps the scan and simply has no primer.
    """
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
    if not eng:
        return None
    prompt = _build_primer_prompt(eng.name, jurisdictions_or_default(eng), lenses or {}, auditor_note, verified)
    outcome = await run_agent(_PRIMER_SYSTEM, prompt, TopicPrimer, max_tokens=1500)
    return format_primer(outcome.data)


def _load_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


# ── Agent Studio — visible orchestration (deterministic, no AI cost) ───────────

# The planning pack is a gated cascade: each stage unlocks the next, and every
# gate is opened by a separate human action. compute_planning_pack derives the
# live state of that cascade from the actual artifacts — never runs an agent
# itself, so it is free and safe to poll.

PACK_STAGES = [
    {"key": "topic_intelligence", "label": "Topic Intelligence", "agent": "4-lens scan", "route": "topic-intelligence", "gate": None},
    {"key": "frameworks", "label": "Frameworks & Requirements", "agent": "Regulatory mapper", "route": "framework-requirements", "gate": "topic_intelligence"},
    {"key": "scope", "label": "Scope & Objectives", "agent": "Scope drafter", "route": "scope-objectives", "gate": "frameworks"},
    {"key": "work_program", "label": "Work Program", "agent": "Test generator", "route": "work-program", "gate": "scope"},
]


async def compute_planning_pack(engagement_id: str, db) -> dict:
    """Live state of the planning cascade. Deterministic; reads artifacts only."""
    from models.planning import (
        TopicIntelligence, ApplicableFramework, ScopeObjectives, ScopeItem, WorkProgram,
    )

    ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
    fws = (await db.execute(select(ApplicableFramework).where(ApplicableFramework.engagement_id == engagement_id))).scalars().all()
    scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))).scalar_one_or_none()
    in_scope = 0
    if scope:
        items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
        in_scope = sum(1 for i in items if i.item_type == "in_scope")
    wp = (await db.execute(select(WorkProgram).where(WorkProgram.engagement_id == engagement_id))).scalar_one_or_none()
    wp_rows = await _wp_rows(engagement_id, db)

    # Raw completeness per stage
    ti_risks = _load_json(ti.key_risk_areas) if ti and ti.key_risk_areas else []
    raw = {
        "topic_intelligence": {
            "running": bool(ti and ti.status in ("agents_pending", "running")),
            "done": bool(ti and (ti.status in ("review", "accepted", "complete") or ti.memo_accepted)),
            "detail": (f"{len(ti_risks)} key risk area(s)" if ti_risks else (ti.status if ti else "not started")),
        },
        "frameworks": {"running": False, "done": bool(fws), "detail": f"{len(fws)} framework(s)" if fws else "none yet"},
        "scope": {"running": False, "done": in_scope > 0, "detail": f"{in_scope} in-scope item(s)" if in_scope else "not defined"},
        "work_program": {"running": False, "done": len(wp_rows) > 0, "detail": f"{len(wp_rows)} test row(s)" if wp_rows else "not generated"},
    }

    stages, prev_done = [], True
    next_gate = None
    for s in PACK_STAGES:
        info = raw[s["key"]]
        gate_open = raw[s["gate"]]["done"] if s["gate"] else True
        if info["running"]:
            status = "in_progress"
        elif info["done"]:
            status = "complete"
        elif gate_open:
            status = "available"
        else:
            status = "locked"
        if status == "available" and next_gate is None:
            next_gate = s["key"]
        stages.append({**s, "status": status, "detail": info["detail"]})
        prev_done = info["done"]

    done = sum(1 for s in stages if s["status"] == "complete")
    return {
        "stages": stages,
        "completed": done,
        "total": len(stages),
        "next_gate": next_gate,
        "summary": (
            f"{done}/{len(stages)} planning stages complete."
            + (f" Next open gate: {next((x['label'] for x in stages if x['key'] == next_gate), '')}." if next_gate else " All gates cleared.")
        ),
    }


# ── Engagement pack — the full lifecycle cascade ────────────────────────────
#
# A superset of the planning-only pack above: same gated-cascade idea, extended
# across Quality, RACM, Fieldwork and Reporting. `gates` is an AND-list of stage
# keys (or "stage_key:attr" for a hard gate on a specific field, e.g. Fieldwork's
# real sign-off gate). `kind` distinguishes the strictly-sequential planning/RACM/
# reporting stages from Quality's cross-cutting checks (always available, never
# block anything downstream — purely advisory) and the Interview Companion
# (an ungated, fieldwork-time activity).

STAGE_GRAPH = [
    {"key": "topic_intelligence", "label": "Topic Intelligence", "agent": "4-lens scan", "route": "topic-intelligence", "base": "planning", "gates": [], "kind": "sequential"},
    {"key": "frameworks", "label": "Frameworks & Requirements", "agent": "Regulatory mapper", "route": "framework-requirements", "base": "planning", "gates": ["topic_intelligence"], "kind": "sequential"},
    {"key": "process_understanding", "label": "Process Understanding", "agent": "Process analyser", "route": "process-understanding", "base": "planning", "gates": ["topic_intelligence"], "kind": "sequential"},
    {"key": "scope", "label": "Scope & Objectives", "agent": "Scope drafter", "route": "scope-objectives", "base": "planning", "gates": ["frameworks"], "kind": "sequential"},
    {"key": "bra", "label": "Background Risk Assessment", "agent": "BRA drafter", "route": "bra", "base": "planning", "gates": ["scope"], "kind": "sequential"},
    {"key": "anl", "label": "Audit Notification Letter", "agent": "ANL drafter", "route": "anl", "base": "planning", "gates": ["scope"], "kind": "sequential"},
    {"key": "kickoff", "label": "Kick-off", "agent": "Kickoff drafter", "route": "kickoff", "base": "planning", "gates": ["scope"], "kind": "sequential"},
    {"key": "resource_plan", "label": "Resource Planning", "agent": "Resource planner", "route": "resource-plan", "base": "planning", "gates": ["scope"], "kind": "sequential"},
    {"key": "interview_guide", "label": "Interview Guide", "agent": "Guide generator", "route": "interview", "base": "planning", "gates": ["scope"], "kind": "sequential"},
    {"key": "work_program", "label": "Work Program", "agent": "Test generator", "route": "work-program", "base": "planning", "gates": ["scope"], "kind": "sequential"},
    {"key": "drl", "label": "Document Request List", "agent": "DRL generator", "route": "drl", "base": "planning", "gates": ["work_program"], "kind": "sequential"},
    {"key": "interview_companion", "label": "Interview Companion", "agent": "Live companion", "route": "interview", "base": "planning", "gates": [], "kind": "always_available"},
    {"key": "quality_coverage", "label": "Coverage check", "agent": "Consistency sweep", "route": "quality", "base": "", "gates": [], "kind": "cross_cutting"},
    {"key": "quality_review", "label": "AI QA review", "agent": "QA reviewer", "route": "quality", "base": "", "gates": [], "kind": "cross_cutting"},
    {"key": "quality_peer_review", "label": "AI peer review (GIAS)", "agent": "Peer reviewer", "route": "quality", "base": "", "gates": [], "kind": "cross_cutting"},
    {"key": "racm_scoping", "label": "RACM scoping", "agent": "Scoping engine", "route": "racm", "base": "", "gates": ["scope", "bra"], "kind": "sequential"},
    {"key": "racm_governance", "label": "Governance assessment", "agent": "Governance assessor", "route": "fieldwork", "base": "", "gates": ["frameworks", "racm_scoping"], "kind": "sequential"},
    {"key": "racm_data_analysis", "label": "Data analysis", "agent": "Data analysis", "route": "fieldwork", "base": "", "gates": ["racm_scoping"], "kind": "sequential"},
    {"key": "racm_evidence_chase", "label": "Evidence chase", "agent": "Evidence chaser", "route": "fieldwork", "base": "", "gates": ["drl"], "kind": "sequential"},
    {"key": "fieldwork", "label": "Fieldwork", "agent": "Observations", "route": "fieldwork", "base": "", "gates": ["work_program:signed_off"], "kind": "sequential"},
    {"key": "findings", "label": "Findings (5C)", "agent": "Finding drafter", "route": "reporting", "base": "", "gates": ["fieldwork"], "kind": "sequential"},
    {"key": "report_draft", "label": "Audit report", "agent": "Report drafter", "route": "reporting", "base": "", "gates": ["findings"], "kind": "sequential"},
]


def _gate_open(gate: str, raw: dict) -> bool:
    """A gate is either a plain stage key (its own 'done' flag) or 'key:attr' for
    a hard gate on a specific field — e.g. Fieldwork's real sign-off gate, which
    must not be satisfied merely by Work Program rows existing."""
    if ":" in gate:
        key, attr = gate.split(":", 1)
        return bool(raw.get(key, {}).get(attr, False))
    return bool(raw.get(gate, {}).get("done", False))


async def compute_engagement_pack(engagement_id: str, db) -> dict:
    """Live state of the full lifecycle cascade — Planning through Reporting.
    Deterministic; reads artifacts only, same idiom as compute_planning_pack."""
    from models.planning import (
        TopicIntelligence, ApplicableFramework, ScopeObjectives, ScopeItem, WorkProgram,
        ProcessNotes, BackgroundRiskAssessment, AuditNotificationLetter, KickoffAgenda,
        ResourcePlan, DRLDocument, FieldworkObservation,
    )
    from models.interview import InterviewGuide, InterviewSession
    from models.racm import RacmObjective, RacmRisk, RacmEvidence
    from models.reporting import Finding, AuditReport
    from models.ai_analysis import AiAnalysis
    from services.governance_assessor import AGENT_TYPE as GOV_AGENT
    from services.data_analysis import AGENT_TYPE as DATA_AGENT
    from services.coverage_service import compute_coverage

    ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
    fws = (await db.execute(select(ApplicableFramework).where(ApplicableFramework.engagement_id == engagement_id))).scalars().all()
    scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))).scalar_one_or_none()
    in_scope = 0
    if scope:
        items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
        in_scope = sum(1 for i in items if i.item_type == "in_scope")
    wp = (await db.execute(select(WorkProgram).where(WorkProgram.engagement_id == engagement_id))).scalar_one_or_none()
    wp_rows = await _wp_rows(engagement_id, db)
    pn = (await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))).scalar_one_or_none()
    bra = (await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))).scalar_one_or_none()
    anl = (await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))).scalar_one_or_none()
    kickoff = (await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))).scalar_one_or_none()
    rp = (await db.execute(select(ResourcePlan).where(ResourcePlan.engagement_id == engagement_id))).scalar_one_or_none()
    guide = (await db.execute(select(InterviewGuide).where(InterviewGuide.engagement_id == engagement_id))).scalar_one_or_none()
    sessions = (await db.execute(select(InterviewSession).where(InterviewSession.engagement_id == engagement_id))).scalars().all()
    drl = (await db.execute(select(DRLDocument).where(DRLDocument.engagement_id == engagement_id))).scalar_one_or_none()
    drl_items = _load_json(drl.items) if drl and drl.items else []
    if not isinstance(drl_items, list):
        drl_items = []
    obs = (await db.execute(select(FieldworkObservation).where(FieldworkObservation.engagement_id == engagement_id))).scalars().all()
    objectives = (await db.execute(select(RacmObjective).where(RacmObjective.engagement_id == engagement_id))).scalars().all()
    risks = (await db.execute(select(RacmRisk).where(RacmRisk.engagement_id == engagement_id))).scalars().all()
    evidence = (await db.execute(select(RacmEvidence).where(RacmEvidence.engagement_id == engagement_id))).scalars().all()
    gov_run = (await db.execute(select(AgentRun).where(
        AgentRun.engagement_id == engagement_id, AgentRun.agent_type == GOV_AGENT, AgentRun.status == "complete",
    ))).scalars().first()
    data_run = (await db.execute(select(AgentRun).where(
        AgentRun.engagement_id == engagement_id, AgentRun.agent_type == DATA_AGENT, AgentRun.status == "complete",
    ))).scalars().first()
    findings = (await db.execute(select(Finding).where(Finding.engagement_id == engagement_id))).scalars().all()
    findings_ready = sum(1 for f in findings if f.status == "ready")
    report = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
    qa_reviews = (await db.execute(select(AiAnalysis).where(
        AiAnalysis.engagement_id == engagement_id, AiAnalysis.kind == "quality_review",
    ))).scalars().all()
    review_done = sum(1 for a in qa_reviews if a.artifact != "peer_review" and a.status == "ready")
    peer_done = any(a.artifact == "peer_review" and a.status == "ready" for a in qa_reviews)
    coverage = await compute_coverage(engagement_id, db)

    ti_risks = _load_json(ti.key_risk_areas) if ti and ti.key_risk_areas else []
    fieldwork_unlocked = bool(wp and wp.status == "signed_off")

    raw = {
        "topic_intelligence": {
            "running": bool(ti and ti.status in ("agents_pending", "running")),
            "done": bool(ti and (ti.status in ("review", "accepted", "complete") or ti.memo_accepted)),
            "detail": (f"{len(ti_risks)} key risk area(s)" if ti_risks else (ti.status if ti else "not started")),
        },
        "frameworks": {"running": False, "done": bool(fws), "detail": f"{len(fws)} framework(s)" if fws else "none yet"},
        "process_understanding": {
            "running": bool(pn and pn.status in ("reasoning", "generating")),
            "done": bool(pn and pn.status in ("draft_ready", "agreed")),
            "detail": (pn.status if pn else "not started"),
        },
        "scope": {"running": False, "done": in_scope > 0, "detail": f"{in_scope} in-scope item(s)" if in_scope else "not defined"},
        "bra": {
            "running": bool(bra and bra.status == "drafting"),
            "done": bool(bra and bra.status == "draft_ready"),
            "detail": (bra.status if bra else "not started"),
        },
        "anl": {
            "running": bool(anl and anl.status == "drafting"),
            "done": bool(anl and anl.status not in (None, "not_started", "drafting")),
            "detail": (anl.status if anl else "not started"),
        },
        "kickoff": {
            "running": bool(kickoff and kickoff.status == "drafting"),
            "done": bool(kickoff and kickoff.status == "draft_ready"),
            "detail": (kickoff.status if kickoff else "not started"),
        },
        "resource_plan": {
            "running": False,
            "done": bool(rp and rp.dates_confirmed and rp.hours_confirmed and rp.team_confirmed),
            "detail": ("confirmed" if rp and rp.dates_confirmed and rp.hours_confirmed and rp.team_confirmed else ("in progress" if rp else "not started")),
        },
        "interview_guide": {
            "running": bool(guide and guide.status == "running"),
            "done": bool(guide and guide.status == "ready"),
            "detail": (guide.status if guide else "not started"),
        },
        "work_program": {
            "running": False, "done": len(wp_rows) > 0,
            "detail": f"{len(wp_rows)} test row(s)" if wp_rows else "not generated",
            "signed_off": fieldwork_unlocked,
        },
        "drl": {"running": False, "done": len(drl_items) > 0, "detail": f"{len(drl_items)} document(s) requested" if drl_items else "not generated"},
        "interview_companion": {
            "running": False, "done": len(sessions) > 0,
            "detail": f"{len(sessions)} session(s) captured" if sessions else "no sessions yet",
        },
        "quality_coverage": {
            "running": False, "done": in_scope > 0 and coverage["gaps"] == 0,
            "detail": coverage["summary"],
        },
        "quality_review": {
            "running": False, "done": review_done > 0,
            "detail": f"{review_done} artefact(s) reviewed" if review_done else "not yet checked",
        },
        "quality_peer_review": {
            "running": False, "done": peer_done,
            "detail": "peer review complete" if peer_done else "not yet run",
        },
        "racm_scoping": {
            "running": False, "done": bool(objectives or risks),
            "detail": f"{len(objectives)} objective(s), {len(risks)} risk(s)" if (objectives or risks) else "not run",
        },
        "racm_governance": {
            "running": False, "done": bool(gov_run),
            "detail": "assessment complete" if gov_run else "not run",
        },
        "racm_data_analysis": {
            "running": False, "done": bool(data_run),
            "detail": "analysis complete" if data_run else "not run",
        },
        "racm_evidence_chase": {
            "running": False, "done": len(evidence) > 0,
            "detail": f"{len(evidence)} evidence item(s) captured" if evidence else "none captured",
        },
        "fieldwork": {
            "running": False, "done": len(obs) > 0,
            "detail": f"{len(obs)} observation(s)" if obs else "not started",
        },
        "findings": {
            "running": False, "done": len(findings) > 0 and findings_ready == len(findings),
            "detail": f"{findings_ready}/{len(findings)} ready" if findings else "no findings yet",
        },
        "report_draft": {
            "running": bool(report and report.status == "drafting"),
            "done": bool(report and report.status == "ready"),
            "detail": (report.status if report else "not started"),
        },
    }

    stages, next_gate = [], None
    for s in STAGE_GRAPH:
        info = raw[s["key"]]
        if s["kind"] != "sequential":
            # Cross-cutting checks and the ungated Interview Companion: never
            # locked, never block anything downstream — purely informational.
            status = "in_progress" if info["running"] else ("complete" if info["done"] else "available")
        else:
            gate_open = all(_gate_open(g, raw) for g in s["gates"])
            if info["running"]:
                status = "in_progress"
            elif info["done"]:
                status = "complete"
            elif gate_open:
                status = "available"
            else:
                status = "locked"
            if status == "available" and next_gate is None:
                next_gate = s["key"]
        stages.append({**s, "status": status, "detail": info["detail"]})

    done = sum(1 for s in stages if s["status"] == "complete")
    return {
        "stages": stages,
        "completed": done,
        "total": len(stages),
        "next_gate": next_gate,
        "summary": (
            f"{done}/{len(stages)} lifecycle stages complete."
            + (f" Next open gate: {next((x['label'] for x in stages if x['key'] == next_gate), '')}." if next_gate else " All gates cleared.")
        ),
    }


async def run_topic_intelligence_pipeline(
    engagement_id, reg_id, pol_id, int_id, urls,
    use_web_search=True, custom_queries=None, manual_keyword=None,
):
    """Owns the whole agent sequence. Each agent opens its own session."""
    await _set_ti_status(engagement_id, "agents_pending")

    # Regulatory + Policy concurrently. return_exceptions so one failing doesn't cancel the other.
    await asyncio.gather(
        run_regulatory_agent(
            reg_id, engagement_id, urls,
            use_web_search=use_web_search,
            custom_queries=custom_queries,
            manual_keyword=manual_keyword or None,
        ),
        run_policy_agent(pol_id, engagement_id),
        return_exceptions=True,
    )

    async with AsyncSessionLocal() as db:
        reg = await db.get(AgentRun, reg_id)
        pol = await db.get(AgentRun, pol_id)
        both_ok = reg.status == "complete" and pol.status == "complete"

    if both_ok:
        await run_interview_agent(int_id, engagement_id)
    else:
        async with AsyncSessionLocal() as db:
            int_run = await db.get(AgentRun, int_id)
            int_run.status = "failed"
            int_run.raw_output = "Skipped - a prerequisite agent (Regulatory or Policy) failed."
            await db.commit()

    await assemble_topic_intelligence_memo(engagement_id, reg_id, pol_id, int_id)


async def _set_ti_status(engagement_id: str, status: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
        )
        ti = result.scalar_one_or_none()
        if ti is None:
            ti = TopicIntelligence(id=str(uuid4()), engagement_id=engagement_id, status=status)
            db.add(ti)
        else:
            ti.status = status
        await db.commit()


async def _store_extra_context(engagement_id: str, extra_context: str | None):
    """Record what the auditor added, so the result can say what it ran on.

    Stored even when empty, because "nothing was added" is itself part of the
    account of how a conclusion came about.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
        )
        ti = result.scalar_one_or_none()
        if ti is None:
            ti = TopicIntelligence(id=str(uuid4()), engagement_id=engagement_id)
            db.add(ti)
        ti.extra_context = (extra_context or "").strip() or None
        await db.commit()


async def assemble_topic_intelligence_memo(engagement_id, reg_id, pol_id, int_id):
    """Merge the three agent outputs into the TopicIntelligence row and synthesize risk areas."""
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        reg = await db.get(AgentRun, reg_id)
        pol = await db.get(AgentRun, pol_id)
        intv = await db.get(AgentRun, int_id)
        # What the organisation has already audited on this topic is a scoping
        # input in its own right: an area a prior audit covered thoroughly last
        # year may be worth excluding, and one where it found something is worth
        # keeping in.
        memory = await recall_for(db, engagement_id, limit=6, kinds=("finding", "scope", "risk"))

    reg_data = _load_json(reg.raw_output) if reg else {}
    pol_data = _load_json(pol.raw_output) if pol else {}
    int_data = _load_json(intv.raw_output) if intv else {}

    # Synthesize key risk areas + excluded areas + conclusion from the two inputs.
    key_risk_areas, excluded_areas, conclusion = [], [], ""
    try:
        synth_prompt = f"""Based on the regulatory and internal findings below, propose scoping decisions
for this internal audit at the organisation.

Engagement: {eng.name} ({eng.entity}, {eng.audit_type})

REGULATORY SUMMARY:
{reg_data.get("regulatory_summary", "")}
Frameworks: {json.dumps(reg_data.get("applicable_frameworks", []))}

INTERNAL FRAMEWORK SUMMARY:
{pol_data.get("internal_framework_summary", "")}
Policy gaps: {json.dumps(pol_data.get("policy_gaps", []))}

{memory.block if not memory.is_empty else 'PRIOR AUDITS: nothing on file matched this topic.'}

Produce ONLY a JSON object:
{{
  "key_risk_areas": [
    {{"title": "...", "rationale": "...", "basis": "WWFT Art. 3", "source": "Regulatory Intelligence", "confidence": "high"}}
  ],
  "excluded_areas": [
    {{"title": "...", "rationale": "why this is out of scope for this engagement"}}
  ],
  "conclusion": "Recommended scope in 2-3 sentences"
}}

Propose 4-6 key risk areas and 1-3 excluded areas. Cite regulatory basis where possible.
Where a prior audit shapes a scoping call — an area already covered, or one where something was
found — name that audit in the rationale so the auditor can weigh it."""
        synth = await run_agent_to_json(BASE_SYSTEM_PROMPT, synth_prompt)
        key_risk_areas = synth.get("key_risk_areas", [])
        excluded_areas = synth.get("excluded_areas", [])
        conclusion = synth.get("conclusion", "")
    except Exception:  # noqa: BLE001
        pass  # Synthesis is best-effort; the agent outputs are still saved below.

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
        )
        ti = result.scalar_one_or_none()
        if ti is None:
            ti = TopicIntelligence(id=str(uuid4()), engagement_id=engagement_id)
            db.add(ti)

        ti.regulatory_summary = reg_data.get("regulatory_summary")
        ti.external_developments = reg_data.get("recent_developments")
        ti.internal_framework_summary = pol_data.get("internal_framework_summary")
        ti.key_risk_areas = json.dumps(key_risk_areas)
        ti.excluded_areas = json.dumps(excluded_areas)
        ti.conclusion = conclusion
        ti.interview_agenda = json.dumps({
            "sponsor": int_data.get("sponsor_questions", []),
            "sme": int_data.get("sme_questions", []),
            "ia_prework": int_data.get("ia_prework", []),
        })
        # Stash frameworks for the cascade step
        ti.regulatory_run_id = reg_id
        ti.policy_run_id = pol_id
        ti.interview_run_id = int_id
        ti.status = "review"
        ti.progress_pct = 60
        await db.commit()


# ── Topic Intelligence v2 — 4-lens pipeline ───────────────────────────────────

async def run_topic_intelligence_v2(
    engagement_id: str,
    lens1_id: str,
    lens2_id: str,
    lens3_id: str,
    urls: list[str] | None = None,
    use_web_search: bool = True,
    manual_keyword: str | None = None,
    extra_context: str | None = None,
):
    """4-lens Topic Intelligence pipeline. Runs Lens 1, 2, 3 concurrently."""
    await _set_ti_status(engagement_id, "agents_pending")
    await _store_extra_context(engagement_id, extra_context)
    await log_activity(
        engagement_id, "topic_intelligence", "run",
        summary="Started 4-lens Topic Intelligence scan (regulatory, supervisory, society lenses)",
        sources=[{"type": "web"}] if use_web_search else [{"type": "model"}],
    )

    await asyncio.gather(
        run_lens_regulatory_agent(lens1_id, engagement_id, urls, use_web_search, manual_keyword, extra_context),
        run_lens_supervisory_agent(lens2_id, engagement_id, urls, use_web_search, manual_keyword, extra_context),
        run_lens_society_agent(lens3_id, engagement_id, use_web_search, manual_keyword, extra_context),
        return_exceptions=True,
    )

    await _finalize_ti_v2(engagement_id, lens1_id, lens2_id, lens3_id)


def _store_lens(ti: TopicIntelligence, lens: int, run_id: str, data: dict) -> list:
    """Put one lens's answer on the memo. Lens 3 carries its materiality signal on its
    first source, which is where the page reads it. Returns the stored sources."""
    sources = list(data.get("sources", []))
    if lens == 3 and data.get("materiality_signal"):
        if sources:
            sources[0] = {**sources[0], "materiality_signal": data["materiality_signal"]}
        else:
            sources = [{"materiality_signal": data["materiality_signal"]}]
    setattr(ti, f"lens{lens}_summary", data.get("summary"))
    setattr(ti, f"lens{lens}_sources", json.dumps(sources))
    setattr(ti, f"lens{lens}_run_id", run_id)
    return sources


async def rerun_lens(engagement_id: str, lens: int, run_id: str):
    """Run one lens again and replace only that lens on the memo.

    The other lenses, the proposal the auditor may have edited, the primer and the
    verification are left alone: they were written from the earlier research, and the
    page says so. A lens that fails keeps its earlier result on the memo; the failed
    run stays on record and the page reads its reason from it.
    """
    async with AsyncSessionLocal() as db:
        ti = (await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
        extra = ti.extra_context if ti else None
    try:
        if lens == 1:
            await run_lens_regulatory_agent(run_id, engagement_id, None, True, None, extra)
        elif lens == 2:
            await run_lens_supervisory_agent(run_id, engagement_id, None, True, None, extra)
        else:
            await run_lens_society_agent(run_id, engagement_id, True, None, extra)
    finally:
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            data = _load_json(run.raw_output) if run else {}
            ti = (await db.execute(
                select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
            ok = bool(run and run.status == "complete" and isinstance(data, dict) and data.get("summary"))
            if ti is not None:
                if ok:
                    _store_lens(ti, lens, run_id, data)
                    for earlier in (await db.execute(select(AgentRun).where(
                            AgentRun.engagement_id == engagement_id, AgentRun.agent_type == f"lens{lens}",
                            AgentRun.status == "failed"))).scalars():
                        earlier.status = "superseded"
                ti.status = "review"
                await db.commit()
        await log_activity(
            engagement_id, "topic_intelligence", "lens_rerun",
            summary=f"Lens {lens} was run again" + ("" if ok else " and failed; the earlier result was kept"),
            sources=[{"type": "web"}],
        )


async def _finalize_ti_v2(engagement_id: str, lens1_id: str, lens2_id: str, lens3_id: str):
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        l1 = await db.get(AgentRun, lens1_id)
        l2 = await db.get(AgentRun, lens2_id)
        l3 = await db.get(AgentRun, lens3_id)

    l1_data = _load_json(l1.raw_output) if l1 else {}
    l2_data = _load_json(l2.raw_output) if l2 else {}
    l3_data = _load_json(l3.raw_output) if l3 else {}
    # _extract_json's truncation-recovery can return a bare list (e.g. when a
    # response gets cut off mid-way through a nested "sources" array) instead
    # of the expected {summary, sources} object — guard every .get() call
    # below (both new and pre-existing) against that shape, rather than crash.
    if not isinstance(l1_data, dict):
        l1_data = {}
    if not isinstance(l2_data, dict):
        l2_data = {}
    if not isinstance(l3_data, dict):
        l3_data = {}

    # Progress signal (UX point 1) — reuses the existing 0 -> 60 -> 100 column,
    # no new ti.status value: a new status string would break
    # compute_planning_pack/compute_engagement_pack's hardcoded
    # `ti.status in ("agents_pending", "running")` classification.
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
        )
        ti = result.scalar_one_or_none()
        if ti is None:
            ti = TopicIntelligence(id=str(uuid4()), engagement_id=engagement_id)
            db.add(ti)
        ti.progress_pct = 50
        auditor_note = ti.extra_context
        await db.commit()

    # The verification round: a few searches on the statements the lenses left open, so the
    # primer and the proposal can write them as settled or still open. Fail-safe, like the primer.
    lens_summaries = {"Normative & regulatory": l1_data.get("summary"),
                      "Supervisory & enforcement": l2_data.get("summary"),
                      "Society, trends & incidents": l3_data.get("summary")}
    verification = await verify_open_points(eng.name, lens_summaries) if eng else None
    verified_text = format_verification(verification)

    # Plain-language topic primer ("the angle"), written from what the lenses
    # found so it tells the same story as the rest of the memo. Fail-safe — never
    # blocks finalisation; a truncated reply raises and is simply not stored.
    primer = None
    try:
        primer = await _generate_topic_primer(
            engagement_id,
            {"Normative & regulatory": l1_data.get("summary"),
             "Supervisory & enforcement": l2_data.get("summary"),
             "Society, trends & incidents": l3_data.get("summary")},
            auditor_note,
            verified_text,
        )
    except Exception:  # noqa: BLE001
        logging.getLogger("ia.wingman").exception("Topic primer failed for %s — the scan keeps going without it", engagement_id)
        primer = None

    # Best-effort synthesis into a scoping proposal — same fail-open shape as
    # the primer call above. Only attempted if at least one lens produced a
    # summary, and only if the engagement row is still there.
    synthesis = None
    has_any_output = bool(eng) and bool(
        l1_data.get("summary") or l2_data.get("summary") or l3_data.get("summary")
    )
    if has_any_output:
        try:
            synthesis = await synthesize_topic_intelligence(
                eng,
                l1_data.get("summary"), l2_data.get("summary"), l3_data.get("summary"),
                l3_data.get("materiality_signal"),
                verified_text,
            )
        except Exception:  # noqa: BLE001
            synthesis = None

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
        )
        ti = result.scalar_one_or_none()
        if ti is None:
            ti = TopicIntelligence(id=str(uuid4()), engagement_id=engagement_id)
            db.add(ti)

        ti.verification = json.dumps(verification) if verification else None
        _store_lens(ti, 1, lens1_id, l1_data)
        _store_lens(ti, 2, lens2_id, l2_data)
        l3_sources = _store_lens(ti, 3, lens3_id, l3_data)
        if primer:
            ti.topic_primer = primer

        if synthesis is not None:
            ti.key_risk_areas = json.dumps(synthesis["key_risk_areas"])
            ti.excluded_areas = json.dumps(synthesis["excluded_areas"])
            ti.interview_agenda = json.dumps(synthesis["interview_agenda"])
            ti.conclusion = synthesis["conclusion"]
            ti.proposed_frameworks = json.dumps(synthesis["proposed_frameworks"])
            ti.synthesis_failed = False
            ti.progress_pct = 60
        else:
            ti.synthesis_failed = True

        ti.status = "review"
        await db.commit()

    n_sources = len(l1_data.get("sources", [])) + len(l2_data.get("sources", [])) + len(l3_sources)
    await log_activity(
        engagement_id, "topic_intelligence", "review_ready",
        summary=f"Topic Intelligence scan complete — {n_sources} source(s) across 3 lenses, ready for review",
        sources=[{"type": "web"}] if n_sources else [{"type": "model"}],
    )
