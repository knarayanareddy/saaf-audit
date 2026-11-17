"""Generic QA Reviewer — an agent that checks the other agents' output.

Loads an engagement artifact, critiques it against an audit-quality rubric
(completeness, evidential support/provenance, regulatory accuracy, internal
consistency), and returns must-fix / suggestion comments for the human to
triage. Generalises the ANL review pattern to any planning artifact.
"""
import json
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from services.work_program_view import rows_for as _wp_rows
from models.engagement import Engagement
from models.ai_analysis import AiAnalysis
from models.planning import (
    TopicIntelligence, ScopeObjectives, ScopeItem, KeyAuditQuestion, ApplicableFramework,
    AuditNotificationLetter, BackgroundRiskAssessment, KickoffAgenda, WorkProgram,
    FieldworkObservation,
)
from models.racm import RacmTest, RacmEvidence
from models.reporting import Finding, AuditReport
from services.ai_service import BASE_SYSTEM_PROMPT
from services.agent_contract import run_agent
from services.agent_schemas import PeerReview, QaReview
from services.activity_service import log_activity
from services.orchestrator import compute_engagement_pack
from services import coverage_service, orchestrator_agent


# ── AI Peer Reviewer — GIAS-based peer-review checklist ──────────────────────
# Rubric derived from the internal-audit peer-review standard (GIAS Principles 13/14/15).
# White-label: no organisation-specific references; GIAS standard references kept.
PEER_REVIEW_CRITERIA = [
    {"nr": 1, "gias": "13.5", "title": "Kick-off / audit team communication held",
     "req": "The nature, complexity and timing of the engagement and the resources to achieve its objectives are documented."},
    {"nr": 2, "gias": "13.1", "title": "Communication with the auditee on objectives, scope and timing",
     "req": "Objectives, scope and timing are communicated to management (e.g. scoping/opening meeting or notification)."},
    {"nr": 3, "gias": "13.1/13.3/13.4", "title": "Audit Notification Letter (ANL) in place and approved",
     "req": "The ANL clearly communicates objectives, scope and timing and is reviewed and approved by the audit manager."},
    {"nr": 4, "gias": "13.2", "title": "Engagement risk assessment in place",
     "req": "An understanding of the activity under review is developed to assess relevant risks, following the IA risk-assessment template."},
    {"nr": 5, "gias": "13.6", "title": "Good-quality work program in place and approved",
     "req": "The work program links to the scope (ANL) and the risk assessment, identifies criteria, tasks, methods and assignees, and is approved before fieldwork."},
    {"nr": 6, "gias": "14.1/14.2/14.6", "title": "Execution of the work program with sufficient evidence",
     "req": "Information gathered is relevant, reliable and sufficient; evidence links to work-program steps and the work is reperformable."},
    {"nr": 7, "gias": "14.2/14.3/14.5", "title": "Findings and conclusion developed against criteria",
     "req": "Information is analysed against the engagement criteria; the conclusion summarises significance relative to objectives."},
    {"nr": 8, "gias": "14.3/14.4", "title": "Root cause analysis incl. discussion with management",
     "req": "Root causes are identified in collaboration with management; recommendations or action plans are considered."},
    # The only criterion with no artifact anywhere in this platform: a closing
    # meeting happens in a room, and nothing here records that it did. Rating it
    # "nc" would blame the auditor for what the tool never tracked, so it is
    # rated "na" and left out of the score instead — see score_peer_review.
    {"nr": 9, "gias": "14.3/14.4", "title": "Closing meeting / communication of findings",
     "req": "Findings and recommendations are discussed with the management authorised to act on them.",
     "platform_evidence": False},
    {"nr": 10, "gias": "14.6", "title": "Workpaper review evidence",
     "req": "Engagement documentation is reviewed for accuracy, relevance and completeness, and approved."},
    {"nr": 11, "gias": "IA requirement", "title": "Challenge session held",
     "req": "A challenge session is held with IA leadership and the audit team to discuss the risk level of findings."},
    {"nr": 12, "gias": "15.1", "title": "Final report approved before issue and distributed",
     "req": "The final communication is accurate, objective, clear, concise, constructive, complete and timely, and reviewed/approved before issue."},
]

# gc/pc/nc score; "na" (not assessable from this platform) is excluded from the
# maximum entirely rather than scored as zero — see score_peer_review.
_RATING_SCORE = {"gc": 2, "pc": 1, "nc": 0}  # weight 2 per criterion → max 24

# The peer review can be run for one audit phase or the whole engagement. The GIAS
# domain of each criterion decides its phase: 13.x = planning, 14.x = fieldwork,
# 15.x = reporting.
PEER_REVIEW_PHASES = ("total", "planning", "fieldwork", "reporting")
_PHASE_BY_NR = {
    1: "planning", 2: "planning", 3: "planning", 4: "planning", 5: "planning",
    6: "fieldwork", 7: "fieldwork", 8: "fieldwork", 9: "fieldwork", 10: "fieldwork", 11: "fieldwork",
    12: "reporting",
}


def criteria_for_phase(phase: str) -> list[dict]:
    """The subset of criteria for a phase; 'total' (or unknown) = all 12."""
    if phase == "total" or phase not in PEER_REVIEW_PHASES:
        return PEER_REVIEW_CRITERIA
    return [c for c in PEER_REVIEW_CRITERIA if _PHASE_BY_NR.get(c["nr"]) == phase]


def score_peer_review(criteria: list[dict]) -> dict:
    """Deterministic scoring of the GIAS criteria passed in — no model math trusted.
    gc=2, pc=1, nc=0; max = 2 per criterion. Returns totals + derived comments.
    The max is based on the criteria supplied so a phase-scoped run scores correctly.

    A criterion rated "na" — one this platform holds no record of at all — is left
    OUT of the maximum rather than counted as zero. Scoring an audit down for
    something the tool never tracked would make the percentage a statement about
    the tool rather than about the audit. It still produces a comment, because
    "we cannot see this" is exactly what a peer reviewer needs to be told."""
    scored = [c for c in criteria if (c.get("rating") or "nc").lower() != "na"]
    not_assessable = [c for c in criteria if (c.get("rating") or "nc").lower() == "na"]
    max_score = 2 * len(scored)
    total = 0
    comments = []
    for c in scored:
        rating = (c.get("rating") or "nc").lower()
        total += _RATING_SCORE.get(rating, 0)
        if rating == "nc":
            comments.append({"section": c.get("title", ""), "severity": "must_fix",
                             "comment": c.get("comment") or "Not compliant / not evidenced."})
        elif rating == "pc":
            comments.append({"section": c.get("title", ""), "severity": "suggestion",
                             "comment": c.get("comment") or "Partially compliant — strengthen evidence."})
    for c in not_assessable:
        comments.append({"section": c.get("title", ""), "severity": "info",
                         "comment": c.get("comment")
                         or "This platform holds no record of it — verify outside the tool."})
    pct = round(100 * total / max_score) if max_score else 0
    quality = "good" if pct >= 75 else "adequate" if pct >= 50 else "needs_work"
    return {"total_score": total, "max_score": max_score, "percentage": pct,
            "overall_quality": quality, "comments": comments,
            "not_assessable": len(not_assessable)}


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


REVIEW_SYSTEM = BASE_SYSTEM_PROMPT + """

REVIEW ROLE:
You are a senior internal-audit quality reviewer. Critique the artifact below and identify specific,
actionable issues the auditor must address. Assess against:
1. COMPLETENESS — are the required elements present and specific (not generic)?
2. EVIDENTIAL SUPPORT / PROVENANCE — is each claim backed by a cited source (document, regulation, or
   marked as model knowledge)? Flag unsupported or vague assertions.
3. REGULATORY ACCURACY — are frameworks/articles correctly applied to this entity and audit type?
4. INTERNAL CONSISTENCY — do the parts align (scope vs objectives vs risks)?
Be constructive and precise. Do not manufacture trivial comments.

SEVERITY — the distinction the auditor acts on, so keep it sharp:
- must_fix: the conclusion could be wrong, or could not be defended, unless this is addressed —
  a contradiction between a result and its conclusion, a conclusion drawn from work not performed,
  a sample or population that cannot support the conclusion, a control objective the tests do not
  address, or evidence that is missing for a claim the conclusion rests on.
- suggestion: everything that would make a sound artifact better — more detail, a further
  reference, a check of a citation you are not certain is wrong, a scope extension, wording.
A sound artifact can have no must_fix at all; say so and rate it "good". A reference you merely
want verified is a suggestion; one you know is wrong is a must_fix.
"""

ARTIFACT_LABELS = {
    "topic_intelligence": "Topic Intelligence memo",
    "scope": "Scope & Objectives",
    "frameworks": "Applicable frameworks",
    "peer_review": "AI Peer Review (GIAS)",
    "coherence": "Engagement coherence",
}


async def _load_artifact(engagement_id: str, artifact: str, db) -> tuple[str, str] | None:
    """Return (label, content_text) for review, or None when there is nothing to review."""
    if artifact == "topic_intelligence":
        ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
        if not ti or ti.status in (None, "not_started", "agents_pending"):
            return None
        risks = _loads(ti.key_risk_areas, [])
        parts = [
            f"REGULATORY SUMMARY:\n{ti.regulatory_summary or ti.lens1_summary or '(none)'}",
            f"SUPERVISORY / EXTERNAL:\n{ti.lens2_summary or ti.external_developments or '(none)'}",
            f"INTERNAL FRAMEWORK:\n{ti.internal_framework_summary or '(none)'}",
            "KEY RISK AREAS:\n" + ("\n".join(f"- {r.get('title','')}: {r.get('rationale','')} (basis: {r.get('basis','n/a')})" for r in risks) or "(none)"),
            f"CONCLUSION:\n{ti.conclusion or '(none)'}",
        ]
        return ARTIFACT_LABELS[artifact], "\n\n".join(parts)

    if artifact == "scope":
        scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))).scalar_one_or_none()
        if not scope:
            return None
        items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
        qs = (await db.execute(select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars().all()
        if not items and not qs:
            return None
        parts = [
            "IN/OUT OF SCOPE ITEMS:\n" + "\n".join(f"- [{i.item_type}] {i.description}" for i in items),
            "KEY AUDIT QUESTIONS:\n" + "\n".join(f"- {q.question_text}" for q in qs),
        ]
        return ARTIFACT_LABELS[artifact], "\n\n".join(parts)

    if artifact == "frameworks":
        fws = (await db.execute(select(ApplicableFramework).where(ApplicableFramework.engagement_id == engagement_id))).scalars().all()
        if not fws:
            return None
        return ARTIFACT_LABELS[artifact], "\n".join(f"- {f.framework_code}: {f.framework_name} — {f.applicability_rationale or '(no rationale)'}" for f in fws)

    return None


def qa_review_prompt(eng_name: str, entity: str, audit_type: str, label: str, content: str) -> str:
    """The QA review prompt from plain values — shared with the eval suite, so a
    planted defect is looked for by exactly the prompt the reviewer sends."""
    return f"""Review this internal-audit artifact for engagement "{eng_name}" ({entity}, {audit_type}).

=== {label.upper()} ===
{content}

Return the review in the JSON format this request requires.
Rate by what you find, not by a quota: there is no expected number of comments, and a sound
artifact may have no must_fix. Max 10 comments."""


async def review_artifact(eng_name: str, entity: str, audit_type: str, label: str, content: str) -> dict:
    """One QA review, typed. Shared with the eval suite, so the score is for this exact call."""
    result = await run_agent(REVIEW_SYSTEM, qa_review_prompt(eng_name, entity, audit_type, label, content),
                             QaReview, max_tokens=3000)
    return result.data.model_dump()


async def run_quality_review(analysis_id: str, engagement_id: str, artifact: str, phase: str = "total"):
    """Owns its own sessions. Loads the artifact, runs the review, stores the result."""
    if artifact == "peer_review":
        return await _run_peer_review(analysis_id, engagement_id, phase)
    if artifact == "coherence":
        return await _run_coherence_check(analysis_id, engagement_id)

    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        loaded = await _load_artifact(engagement_id, artifact, db)

    if loaded is None:
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "no_data"
            a.result = json.dumps({"summary": "Nothing to review yet — generate this artifact first."})
            await db.commit()
        return

    label, content = loaded

    try:
        # Validated, so the "adequate when the model said something else"
        # fallbacks that sat here are gone: a reply without a verdict is a
        # failed review, not an adequate one.
        result = await review_artifact(eng.name, eng.entity, eng.audit_type, label, content)
        comments = result["comments"]
        for c in comments:
            c["id"] = str(uuid4())[:8]
            c["is_accepted"] = False
            c["is_dismissed"] = False
        payload = {
            "overall_quality": result["overall_quality"],
            "summary": result["summary"],
            "comments": comments,
        }
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "ready"
            a.result = json.dumps(payload)
            await db.commit()
        must = sum(1 for c in comments if c.get("severity") == "must_fix")
        await log_activity(
            engagement_id, "qa_review", "review_ready",
            summary=f"QA Reviewer critiqued the {label} — {must} must-fix, {len(comments) - must} suggestion(s)",
            confidence=None,
        )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "failed"
            a.result = json.dumps({"summary": f"Review failed: {exc}"})
            await db.commit()


# ── AI Peer Reviewer run path ────────────────────────────────────────────────
PEER_REVIEW_SYSTEM = BASE_SYSTEM_PROMPT + """

PEER-REVIEW ROLE:
You are an independent internal-audit peer reviewer assessing an engagement against the GIAS
peer-review checklist. Rate each criterion strictly on the evidence provided. Be objective and
specific. Where an artifact is not yet produced, rate it 'nc' and state 'not evidenced' — never
invent evidence. You PROPOSE ratings; a human peer reviewer confirms them.
"""


# ── The evidence pack ────────────────────────────────────────────────────────
# A peer reviewer reads the file. This builder used to report only whether an
# artifact existed and how many rows it had, so the model was rating audit
# QUALITY from row counts — and eight of the twelve criteria (work program
# through final report) had no evidence in the prompt at all, which made them
# "nc" no matter how good the file was.
#
# It now passes what the file actually says, grouped by the criterion each block
# serves, and every cap it applies says so out loud: a peer review that silently
# saw half the findings is worth less than one that admits it saw half.

_PACK_MAX_ROWS = 25    # rows per block before the pack states what it left out
_PACK_FIELD_CHARS = 700


def _clip(value, limit: int = _PACK_FIELD_CHARS) -> str:
    """One field, capped — and honest about it."""
    if value is None:
        return "(empty)"
    text = " ".join(str(value).split())
    if not text:
        return "(empty)"
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\u2026 [truncated here; {len(text)} characters in full]"


def _rows(items: list[str], cap: int = _PACK_MAX_ROWS) -> str:
    """A block's rows, with an explicit note when not all of them fit."""
    if not items:
        return "  (none recorded)"
    shown = items[:cap]
    out = "\n".join(f"  {r}" for r in shown)
    if len(items) > len(shown):
        out += (f"\n  [{len(items) - len(shown)} further row(s) not included in this review \u2014 "
                f"showing {len(shown)} of {len(items)}]")
    return out


async def _peer_review_blocks(engagement_id: str, db) -> dict[int, str]:
    """One evidence block per criterion number. A block that comes back
    "(none recorded)" is real evidence of "not evidenced"; a criterion this
    platform does not track at all never gets a block and is handled by the
    criteria table's platform_evidence flag instead."""
    blocks: dict[int, str] = {}

    # ── 1 · Kick-off ─────────────────────────────────────────────────────────
    ko = (await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))).scalar_one_or_none()
    if ko:
        blocks[1] = (
            f"Status: {ko.status or 'draft'}\n"
            f"Meeting date: {ko.meeting_date or '(not set)'}\n"
            f"Attendees: {_clip(ko.attendees, 300)}\n"
            f"Audit purpose as documented: {_clip(ko.audit_purpose)}\n"
            f"Context / activity under review: {_clip(ko.notes_context)}\n"
            f"Scope discussed: {_clip(ko.notes_scope)}\n"
            f"Risks discussed: {_clip(ko.notes_risks)}\n"
            f"Team and resourcing discussed: {_clip(ko.notes_team)}\n"
            f"Timing / next steps: {_clip(ko.notes_next_steps)}"
        )
    else:
        blocks[1] = "(no kick-off agenda recorded)"

    # ── 2 & 3 · Communication with the auditee, and the ANL ──────────────────
    anl = (await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))).scalar_one_or_none()
    if anl:
        review_comments = _loads(anl.review_comments, [])
        anl_text = (
            f"Status: {anl.status or 'draft'}\n"
            f"Head of IA approval: {anl.head_ia_status or 'not recorded'}"
            f"{' on ' + str(anl.head_ia_approved_at) if anl.head_ia_approved_at else ''}\n"
            f"Background: {_clip(anl.background)}\n"
            f"Objectives: {_clip(anl.objectives)}\n"
            f"Scope: {_clip(anl.scope_description)}\n"
            f"Explicitly out of scope: {_clip(anl.out_of_scope)}\n"
            f"Approach: {_clip(anl.approach)}\n"
            f"Timing \u2014 fieldwork {anl.timing_fieldwork_start or '?'} to {anl.timing_fieldwork_end or '?'}, "
            f"draft report {anl.timing_draft_report or '?'}, management response {anl.timing_mgmt_response or '?'}, "
            f"final report {anl.timing_final_report or '?'}\n"
            f"Responsibility paragraph: {_clip(anl.responsibility, 300)}\n"
            f"AI review comments raised on this letter: {len(review_comments)}"
        )
    else:
        anl_text = "(no audit notification letter recorded)"
    blocks[3] = anl_text
    blocks[2] = (
        "The objectives, scope and timing communicated to management are carried by the "
        "notification letter and the kick-off, both reproduced in their own blocks.\n"
        f"Notification letter: {'present' if anl else 'not present'}. "
        f"Kick-off agenda: {'present' if ko else 'not present'}."
    )

    # ── 4 · Engagement risk assessment ───────────────────────────────────────
    bra = (await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))).scalar_one_or_none()
    if bra:
        risks = _loads(bra.risk_items, [])
        accepted = [r for r in risks if r.get("is_accepted")]
        rows = [
            f"- [{r.get('ref', '?')}] {_clip(r.get('description'), 260)} "
            f"(inherent {r.get('inherent_risk', '?')}, residual {r.get('residual_risk', '?')}, "
            f"{'accepted by the auditor' if r.get('is_accepted') else 'not yet accepted'})"
            for r in risks
        ]
        blocks[4] = (
            f"Status: {bra.status or 'draft'}\n"
            f"Risk items: {len(risks)} recorded, {len(accepted)} accepted by the auditor\n"
            f"Strategy section: {_clip(bra.section_strategy)}\n"
            f"Risk tolerance section: {_clip(bra.section_risk_tolerance)}\n"
            f"Governance section: {_clip(bra.section_governance)}\n"
            f"Risks:\n{_rows(rows)}"
        )
    else:
        blocks[4] = "(no background risk assessment recorded)"

    # ── 5 · Work program ─────────────────────────────────────────────────────
    wp = (await db.execute(select(WorkProgram).where(WorkProgram.engagement_id == engagement_id))).scalar_one_or_none()
    if wp:
        wp_rows = await _wp_rows(engagement_id, db)
        rows = [
            f"- {r.get('process', '?')} / {r.get('activity', '?')}: "
            f"risk \u00ab{_clip(r.get('risk_description'), 200)}\u00bb; "
            f"control objective \u00ab{_clip(r.get('control_objective'), 200)}\u00bb; "
            f"{len(r.get('test_steps') or [])} test step(s); priority {r.get('priority', '?')}; "
            f"assigned to {r.get('responsibility', '(unassigned)')}"
            for r in wp_rows
        ]
        blocks[5] = (
            f"Status: {wp.status or 'draft'}\n"
            f"Signed off: {'yes, on ' + str(wp.signed_off_at) if wp.signed_off_at else 'NOT signed off'}\n"
            f"Rows: {len(wp_rows)}\n{_rows(rows)}"
        )
    else:
        blocks[5] = "(no work program recorded)"

    # ── 6 · Execution of the work program, and the evidence behind it ────────
    tests = (await db.execute(select(RacmTest).where(RacmTest.engagement_id == engagement_id))).scalars().all()
    evidence = (await db.execute(select(RacmEvidence).where(RacmEvidence.engagement_id == engagement_id))).scalars().all()
    ev_by_test: dict[str, list] = {}
    for e in evidence:
        ev_by_test.setdefault(e.test_id or "", []).append(e)
    obs = (await db.execute(select(FieldworkObservation).where(FieldworkObservation.engagement_id == engagement_id))).scalars().all()
    test_rows = []
    for t in tests:
        evs = ev_by_test.get(t.id, [])
        linked = sum(1 for e in evs if e.source_document_id)
        kinds = ", ".join(sorted({e.kind for e in evs if e.kind})) or "no evidence attached"
        test_rows.append(
            f"- [{t.ref or '?'}] {_clip(t.title, 200)} \u2014 method {t.method or 'not stated'}, "
            f"sample {t.sample_size if t.sample_size is not None else 'not stated'}, "
            f"exceptions {t.exceptions_count if t.exceptions_count is not None else 'not stated'}, "
            f"result {t.result or 'pending'}; evidence: {len(evs)} item(s) ({kinds}), "
            f"{linked} linked to a source document; conclusion: {_clip(t.conclusion, 240)}"
        )
    obs_rows = [
        f"- [{o.obs_type or 'observation'}] {_clip(o.title, 180)} \u2014 criteria: {_clip(o.criteria, 180)}; "
        f"{'linked to a work-program step' if o.linked_wp_row_id else 'NOT linked to a work-program step'}"
        for o in obs
    ]
    blocks[6] = (
        f"Control tests recorded: {len(tests)}; evidence items recorded: {len(evidence)} "
        f"({sum(1 for e in evidence if e.source_document_id)} of them linked to a source document)\n"
        f"Tests:\n{_rows(test_rows)}\n"
        f"Fieldwork observations: {len(obs)}\n{_rows(obs_rows)}"
    )

    # ── 7 & 8 · Findings, conclusions and root cause ─────────────────────────
    findings = (await db.execute(select(Finding).where(Finding.engagement_id == engagement_id))).scalars().all()
    finding_rows = [
        f"- \u00ab{_clip(f.title, 160)}\u00bb [{f.status or 'draft'}] rated {f.rating or 'unrated'}\n"
        f"    condition: {_clip(f.condition, 300)}\n"
        f"    criteria:  {_clip(f.criteria, 300)}\n"
        f"    effect:    {_clip(f.effect, 300)}\n"
        f"    rating rationale: {_clip(f.rating_rationale, 240)}\n"
        f"    {'linked to RACM test ' + f.racm_test_id if f.racm_test_id else 'not linked to a RACM test'}"
        f"{'; grounding validation present' if f.validation else ''}"
        for f in findings
    ]
    blocks[7] = f"Findings recorded: {len(findings)}\n{_rows(finding_rows, cap=12)}"

    cause_rows = [
        f"- \u00ab{_clip(f.title, 160)}\u00bb\n"
        f"    cause:          {_clip(f.cause, 300)}\n"
        f"    recommendation: {_clip(f.recommendation, 300)}"
        for f in findings
    ]
    stated = sum(1 for f in findings if (f.cause or "").strip())
    blocks[8] = (
        f"{stated} of {len(findings)} finding(s) state a cause.\n{_rows(cause_rows, cap=12)}\n"
        "NOTE: whether the root cause was discussed WITH MANAGEMENT is not recorded anywhere in this "
        "platform. Do not infer that it happened; say it must be verified outside the tool."
    )

    # ── 10 · Workpaper review evidence ───────────────────────────────────────
    analyses = (await db.execute(
        select(AiAnalysis).where(AiAnalysis.engagement_id == engagement_id, AiAnalysis.kind == "quality_review")
    )).scalars().all()
    reviewed = sorted({a.artifact for a in analyses if a.status == "ready"})
    accepted_findings = sum(1 for f in findings if (f.status or "") in ("confirmed", "accepted"))
    blocks[10] = (
        f"AI quality reviews run on: {', '.join(reviewed) if reviewed else 'nothing'}\n"
        f"Findings moved past draft by the auditor: {accepted_findings} of {len(findings)}\n"
        f"Work program signed off: {'yes' if (wp and wp.signed_off_at) else 'no'}\n"
        f"Notification letter approved by the Head of IA: {anl.head_ia_status if anl else 'no letter'}\n"
        "NOTE: a per-workpaper human reviewer sign-off is not recorded in this platform. Rate what the "
        "signals above evidence, and name what a reviewer must still check outside the tool."
    )

    # ── 11 · Challenge of the finding ratings ────────────────────────────────
    challenged = [f for f in findings if f.rating_challenge]
    challenge_rows = []
    for f in challenged:
        ch = _loads(f.rating_challenge, {})
        challenge_rows.append(
            f"- \u00ab{_clip(f.title, 160)}\u00bb rated {f.rating or '?'}: challenger "
            f"{'agreed' if ch.get('agrees') else 'disagreed, suggesting ' + str(ch.get('suggested_rating', '?'))} "
            f"\u2014 {_clip(ch.get('rationale'), 240)}"
        )
    blocks[11] = (
        f"Ratings challenged by the independent rating agent: {len(challenged)} of {len(findings)}\n"
        f"{_rows(challenge_rows, cap=12)}\n"
        "NOTE: this is the platform's AI rating challenge. Whether a challenge SESSION with IA leadership "
        "was held is not recorded here; do not infer it."
    )

    # ── 12 · Final report ────────────────────────────────────────────────────
    report = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
    if report:
        blocks[12] = (
            f"Status: {report.status or 'draft'}\n"
            f"Overall opinion: {_clip(report.overall_opinion)}\n"
            f"Executive summary: {_clip(report.exec_summary)}\n"
            f"Conclusion: {_clip(report.conclusion)}"
        )
    else:
        blocks[12] = "(no audit report recorded)"

    return blocks


async def _load_peer_review_context(engagement_id: str, db, nrs: list[int] | None = None) -> str:
    """The evidence pack, limited to the criteria actually being rated \u2014 a
    planning-phase review should not pay for the fieldwork evidence it will
    never look at. Supporting context (scope, frameworks, topic intelligence)
    is always included: every criterion is judged relative to what this audit
    set out to do."""
    blocks = await _peer_review_blocks(engagement_id, db)

    ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
    scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))).scalar_one_or_none()
    scope_text = "(no scope recorded)"
    if scope:
        items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
        qs = (await db.execute(select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars().all()
        in_rows = [f"- [in scope] {_clip(i.description, 200)}" for i in items if i.item_type == "in_scope"]
        out_rows = [f"- [out of scope] {_clip(i.description, 200)}" for i in items if i.item_type != "in_scope"]
        q_rows = [f"- {_clip(q.question_text, 200)}" for q in qs]
        scope_text = (
            f"Overall objective: {_clip(scope.overall_objective)}\n"
            f"Period: {scope.scope_period or '(not set)'} \u00b7 Entity: {scope.scope_entity or '(not set)'}\n"
            f"{_rows(in_rows + out_rows)}\n"
            f"Key audit questions ({len(qs)}):\n{_rows(q_rows)}"
        )

    fws = (await db.execute(select(ApplicableFramework).where(ApplicableFramework.engagement_id == engagement_id))).scalars().all()
    fw_rows = [
        f"- [{f.category or 'law'}] {f.framework_code or '?'} \u2014 {_clip(f.framework_name, 160)}"
        f"{' \u00b7 ' + _clip(f.specific_provision, 160) if f.specific_provision else ''}"
        f"{' (accepted)' if f.is_accepted else ' (not accepted)'}"
        for f in fws
    ]

    parts = [
        "=== SUPPORTING CONTEXT (applies to every criterion) ===",
        f"TOPIC INTELLIGENCE: {ti.status if ti else 'not started'}"
        + (f"\nConclusion: {_clip(ti.conclusion)}" if ti and ti.conclusion else ""),
        f"SCOPE & OBJECTIVES:\n{scope_text}",
        f"APPLICABLE FRAMEWORKS ({len(fws)}):\n{_rows(fw_rows)}",
    ]
    wanted = nrs if nrs else sorted(blocks)
    for nr in wanted:
        if nr in blocks:
            title = next((c["title"] for c in PEER_REVIEW_CRITERIA if c["nr"] == nr), str(nr))
            parts.append(f"=== EVIDENCE FOR CRITERION {nr} \u2014 {title.upper()} ===\n{blocks[nr]}")
    return "\n\n".join(parts)


async def _run_peer_review(analysis_id: str, engagement_id: str, phase: str = "total"):
    scoped = criteria_for_phase(phase)
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        context = await _load_peer_review_context(engagement_id, db, [c["nr"] for c in scoped])

    phase_label = {"planning": "Planning", "fieldwork": "Fieldwork",
                   "reporting": "Reporting"}.get(phase, "the full engagement")
    nrs = [c["nr"] for c in scoped]
    criteria_list = "\n".join(
        f'{c["nr"]}. [{c["gias"]}] {c["title"]} — {c["req"]}'
        + ("  [NO PLATFORM RECORD — rate \"na\"]" if c.get("platform_evidence") is False else "")
        for c in scoped
    )
    prompt = f"""Perform an independent PEER REVIEW of this internal-audit engagement against the GIAS peer-review checklist, focusing on {phase_label}.

ENGAGEMENT: {eng.name} ({eng.entity}, {eng.audit_type})

THE AUDIT FILE. Read this as the file itself — each block is the evidence for one criterion:

{context}

Rate EACH criterion below as:
- "gc" generally compliant (>75% of the step is good quality)
- "pc" partially compliant (25-75%)
- "nc" not compliant / not evidenced (<25%)
- "na" not assessable from this platform — ONLY for criteria marked [NO PLATFORM RECORD]

HOW TO RATE:
- Judge a criterion from ITS OWN evidence block plus the supporting context, and nothing else.
- Judge the QUALITY of what the block contains, not the fact that it exists. A work program with
  twenty vague rows is worse than one with eight specific, risk-linked ones.
- An empty block ("none recorded") means the work is not evidenced: that is "nc", and it is a real
  finding about this audit.
- Where a block carries a NOTE about something the platform does not record, never infer that it
  happened. Rate what is evidenced and say in the comment what a human reviewer must check outside
  the tool.
- Where a block says rows were not included, do not read the missing rows as absent work.
- "evidence" must name or quote the specific thing in the block that drove your rating. Never a
  general statement, never an artifact count.

CRITERIA:
{criteria_list}

Return your review in the JSON format this request requires, with exactly {len(scoped)} criteria entries —
one for each criterion number: {nrs}."""

    try:
        reviewed = await run_agent(
            PEER_REVIEW_SYSTEM, prompt, PeerReview, max_tokens=4000,
            description="Return one rating per GIAS criterion, plus the reviewer's summary.",
        )
        # Validated: every entry has an integer nr and one of the four ratings,
        # so the "is this digit-shaped?" filter that used to drop malformed rows
        # in silence is no longer needed — and can no longer hide a lost rating.
        result = reviewed.dump()
        by_nr = {c["nr"]: c for c in result["criteria"]}
        merged = []
        for c in scoped:
            m = by_nr.get(c["nr"], {})
            # A criterion this platform cannot evidence falls back to "na", not to
            # "nc" — the same reason score_peer_review leaves it out of the max.
            fallback = "na" if c.get("platform_evidence") is False else "nc"
            rating = (m.get("rating") or fallback).lower()
            if rating not in ("gc", "pc", "nc", "na"):
                rating = fallback
            # "na" is reserved for criteria that genuinely have no record here; a
            # model reaching for it elsewhere would quietly erase a real gap.
            if rating == "na" and c.get("platform_evidence") is not False:
                rating = "nc"
            merged.append({
                "nr": c["nr"], "title": c["title"], "gias": c["gias"],
                "rating": rating, "platform_evidence": c.get("platform_evidence", True),
                "comment": m.get("comment") or "", "evidence": m.get("evidence") or "",
            })
        scored = score_peer_review(merged)
        for cm in scored["comments"]:
            cm.setdefault("id", str(uuid4())[:8])
            cm.setdefault("is_accepted", False)
            cm.setdefault("is_dismissed", False)
        payload = {
            "phase": phase if phase in PEER_REVIEW_PHASES else "total",
            "overall_quality": scored["overall_quality"],
            "summary": result["summary"],
            "run": reviewed.meta.as_dict(),
            "total_score": scored["total_score"], "max_score": scored["max_score"],
            "percentage": scored["percentage"], "criteria": merged,
            "not_assessable": scored.get("not_assessable", 0),
            "comments": scored["comments"],
        }
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "ready"
            a.result = json.dumps(payload)
            await db.commit()
        await log_activity(
            engagement_id, "peer_review", "review_ready",
            summary=f"AI Peer Review ({phase_label}) — {scored['total_score']}/{scored['max_score']} ({scored['percentage']}%)",
            confidence=None,
        )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "failed"
            a.result = json.dumps({"summary": f"Peer review failed: {exc}"})
            await db.commit()


# ── Engagement coherence run path (Part 2b of the Orchestrator Agent plan) ──
# Opt-in, click-only — see orchestrator_agent.explain_coherence's own
# docstring for why it raises rather than fails open (the try/except below is
# what turns that raise into status="failed", exactly like every artifact
# above). Candidates come from coverage_service.select_coherence_candidates
# (2a); this turns the model's verified observations into the same
# {overall_quality, summary, comments:[...]} shape every other review
# artifact uses, plus two internal bookkeeping fields (based_on_sig,
# cited_refs) the frontend ignores — only routers/review.py's staleness check
# and coverage_service's check 10 read those back.

async def _run_coherence_check(analysis_id: str, engagement_id: str):
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        pack = await compute_engagement_pack(engagement_id, db)
        candidates = await coverage_service.select_coherence_candidates(engagement_id, db)

    if not candidates:
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "no_data"
            a.result = json.dumps({
                "summary": "No coherence candidates to check yet — nothing stood out across "
                           "Topic Intelligence, RACM scoping and Findings.",
            })
            await db.commit()
        return

    try:
        observations = await orchestrator_agent.explain_coherence(eng, pack["summary"], candidates)

        comments = []
        refs_for_sig: list[tuple[str, object]] = []
        async with AsyncSessionLocal() as db:
            for obs in observations:
                c = obs["candidate"]
                if c["kind"] == "ti_racm_gap":
                    section, severity = "Topic Intelligence vs. RACM scoping", "suggestion"
                    refs = [("ti_risk_area", c["ti_risk_area"])] + [
                        ("racm_risk", r) for r in c["near_miss_racm_risks"]
                    ]
                else:
                    section, severity = "Findings consistency", "must_fix"
                    refs = []
                    for f in c["findings"]:
                        row = await db.get(Finding, f["id"])
                        if row is not None:
                            refs.append(("finding", row))
                if not refs:
                    continue  # a cited artifact vanished between selection and now — drop it
                refs_for_sig += refs
                comments.append({
                    "id": str(uuid4())[:8], "section": section, "severity": severity,
                    "comment": f'{obs["explanation"]} — "{obs["side_a"]["quote"]}" vs. "{obs["side_b"]["quote"]}"',
                    "is_accepted": False, "is_dismissed": False,
                })

        based_on_sig = coverage_service.coherence_run_signature(refs_for_sig) if refs_for_sig else ""
        cited_refs = [
            {"kind": kind, "id": (obj.get("id") if isinstance(obj, dict) else obj.id)}
            for kind, obj in refs_for_sig
        ]
        must_fix = sum(1 for c in comments if c["severity"] == "must_fix")
        payload = {
            "overall_quality": "needs_work" if must_fix else ("adequate" if comments else "good"),
            "summary": (
                f"{len(comments)} coherence observation(s) confirmed across Topic Intelligence, "
                f"RACM and Findings." if comments else
                "No coherence conflicts confirmed on the candidates checked — Topic Intelligence, "
                "RACM and Findings line up."
            ),
            "comments": comments,
            "based_on_sig": based_on_sig,
            "cited_refs": cited_refs,
        }
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "ready"
            a.result = json.dumps(payload)
            await db.commit()
        await log_activity(
            engagement_id, "qa_review", "review_ready",
            summary=f"Coherence check — {len(comments)} observation(s) confirmed ({must_fix} must-fix)",
            confidence=None,
        )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            a = await db.get(AiAnalysis, analysis_id)
            a.status = "failed"
            a.result = json.dumps({"summary": f"Coherence check failed: {exc}"})
            await db.commit()
