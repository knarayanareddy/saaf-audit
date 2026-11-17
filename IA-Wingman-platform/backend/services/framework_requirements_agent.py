"""Framework Requirements Agent.

Merges what used to be two separate agents/pages into one auditor-facing step:
  1. Identify applicable regulatory frameworks with specific provisions (article numbers)
  2. Derive control requirements (objective + test approach) from the frameworks just saved

The two steps run sequentially and each commits independently — a failure while
deriving requirements never loses the frameworks already identified and saved in
step 1. `RegRequirement` (one row per engagement) doubles as the phase tracker for
the merged step, same as it did for the old, standalone Regulatory Requirements page.
"""
import json
import logging
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.engagement import Engagement, jurisdictions_or_default
from models.planning import ApplicableFramework, RegRequirement
from services.framework_rows import LAW, replace_rows
from services.agent_contract import AgentContractError, AgentTruncated, run_agent
from services.agent_schemas import Frameworks, Requirements, ScopeContribution
from services.web_search_service import search_regulatory

logger = logging.getLogger("ia_wingman.framework_requirements")

ENTITY_LABELS = {
    "GRP": "the organisation Netherlands (DNB/ECB supervised)",
    "INT": "the organisation UK (PRA/FCA supervised)",
    "RET": "the organisation Belgium (NBB/ECB supervised, FSMA for conduct)",
    "BUS": "the organisation Spain (Banco de España/ECB supervised)",
    "AM": "Asset Management (AIFMD/UCITS)",
}

FRAMEWORKS_SYSTEM = (
    "You are an expert internal audit regulatory analyst for the organisation's Internal Audit function. "
    "You identify applicable regulatory frameworks with SPECIFIC article references and provisions — "
    "not just law names. Always cite exact article numbers. "
    "Always explain what each provision requires in plain audit language."
)

REQUIREMENTS_SYSTEM = (
    "You are an expert internal audit regulatory analyst for the organisation's Internal Audit function. "
    "You extract precise, audit-ready control requirements from regulatory provisions. "
    "Always cite exact article numbers. Always distinguish what the law requires from what the auditor tests. "
    "Write control objectives in the form: 'Verify that [subject] [action] [standard]'."
)

SCOPE_SYSTEM = (
    "You are an expert internal auditor at the organisation. "
    "You derive clear, specific scope items and key audit questions from a list of regulatory frameworks. "
    "Each item must directly reference the regulatory basis."
)


async def _get_or_create_rr(db, engagement_id: str) -> RegRequirement:
    result = await db.execute(select(RegRequirement).where(RegRequirement.engagement_id == engagement_id))
    rr = result.scalar_one_or_none()
    if not rr:
        rr = RegRequirement(id=str(uuid4()), engagement_id=engagement_id)
        db.add(rr)
        await db.flush()
    return rr


def _as_bool(value, default: bool = False) -> bool:
    """Coerce a JSON value to bool, guarding against Claude emitting a quoted
    '"false"' string — plain bool(...) treats any non-empty string as truthy,
    which would silently flip a stringified false into True."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "", "no")
    if value is None:
        return default
    return bool(value)


async def _fail(agent_run_id: str, message: str, engagement_id: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, agent_run_id)
        if run:
            run.status = "failed"
            run.raw_output = message[:2000]
        if engagement_id:
            # Without this, RegRequirement.status (set to "analysing" by the router
            # before this background task started) stays stuck forever on any failure —
            # AgentRun correctly shows "failed" but the Planning Hub tile (which reads
            # RegRequirement.status) would show "Analysing…" permanently.
            rr = await _get_or_create_rr(db, engagement_id)
            rr.status = "not_started"
        await db.commit()


async def _set_stage(agent_run_id: str, stage: str) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, agent_run_id)
        if run:
            run.search_progress = json.dumps({"stage": stage})
            await db.commit()


def frameworks_prompt(name: str, entity: str, audit_type: str, jurisdictions: list[str],
                      search_ctx: str = "") -> str:
    """The step-1 prompt, built from plain values.

    A function of its own so that the eval suite sends exactly what the agent
    sends. An eval that rebuilds the prompt in its own words keeps measuring the
    old prompt after this one changes — and reports a score for an agent that
    no longer exists.
    """
    return f"""Analyse this internal audit engagement and identify the most applicable
regulatory frameworks with SPECIFIC provisions (article numbers, section references).

Audit name: {name}
Entity: {ENTITY_LABELS.get(entity, entity)}
Audit type: {audit_type}
Jurisdictions in scope: {", ".join(jurisdictions)} — prioritise applicable laws & regulations for THESE jurisdictions; set each item's "jurisdiction" to the country it applies to.
{search_ctx}
Return the frameworks in the JSON format this request requires. Its schema carries each
field's meaning, so what follows is only the judgement it cannot express.

Rules:
- Use SPECIFIC provisions (Art. 3 WWFT, §4.17 Wft, Art. 101 PSD2) not just law names
- Adapt to the entity:
  TB NL → Dutch law (WWFT, Wft, DNB circulaires), EU directives
  TB UK → FCA/PRA rules (FCA Consumer Duty, BCOBS, CASS), UK regulations
  TB BE → Belgian law (Wet 2017, Wet 25 april 2014), NBB/FSMA guidance, EU directives
  TB ES → Spanish law (Ley 10/2010, Ley 10/2014), BdE/SEPBLAC guidance, EU directives
  AM  → AIFMD, UCITS, SFDR, ESMA guidelines
"""


async def run_framework_requirements_analysis(agent_run_id: str, engagement_id: str) -> None:
    """Background task: identify applicable frameworks, then derive control requirements from them."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, agent_run_id)
        if not run:
            return
        run.status = "running"
        run.search_progress = json.dumps({"stage": "identifying_frameworks"})
        await db.commit()

    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        if not eng:
            await _fail(agent_run_id, "Engagement not found", engagement_id=engagement_id)
            return
        eng_name, eng_entity, eng_type = eng.name, eng.entity, eng.audit_type
        eng_jurisdictions = jurisdictions_or_default(eng)

    # ── Step 1: identify applicable frameworks ──────────────────────────────
    try:
        search_results = await search_regulatory(eng_name, eng_entity)
        search_ctx = ""
        if search_results:
            lines = "\n".join(
                f"- [{r['title']}]({r['url']})\n  {r['content'][:500]}"
                for r in search_results[:4]
            )
            search_ctx = f"\nRECENT REGULATORY UPDATES (live web search):\n{lines}\n"

        prompt = frameworks_prompt(eng_name, eng_entity, eng_type, eng_jurisdictions, search_ctx)

        # Measured before migrating: this prompt came back inside a markdown
        # fence on 1 of 3 runs, the one below it on 3 of 3, and the scope
        # contribution on 3 of 3 — against prompts that said "no markdown" in
        # those words. None of the twelve failed outright, which is why these
        # three moved after the ones that did: the repair was working, and that
        # was the problem. It worked silently, so nobody knew the regex stripping
        # those fences had become load-bearing.
        result = await run_agent(FRAMEWORKS_SYSTEM, prompt, Frameworks,
                                 max_tokens=3000,
                                 description="Return the applicable frameworks.")
        fw_result = [item.model_dump() for item in result.data.frameworks]

        async with AsyncSessionLocal() as db:
            await replace_rows(db, engagement_id, LAW, fw_result)
            await db.commit()  # durable — a step 2 failure below must not lose this

    except Exception as exc:  # noqa: BLE001
        await _fail(agent_run_id, f"Framework identification failed: {exc}", engagement_id=engagement_id)
        return

    # ── Step 2: derive control requirements from the frameworks just saved ──
    await _set_stage(agent_run_id, "deriving_requirements")

    try:
        # Snapshot the frameworks and close the session before the slow Claude call below —
        # holding a session (and, on SQLite, a write lock from the get-or-create flush) open
        # across a call that took 60-90s in practice risks "database is locked" errors against
        # every other concurrent request (chat panel, other agents, status polling).
        async with AsyncSessionLocal() as db:
            fw_rows = (await db.execute(
                select(ApplicableFramework).where(
                    ApplicableFramework.engagement_id == engagement_id,
                    ApplicableFramework.is_accepted == True,  # noqa: E712
                )
            )).scalars().all()
            fw_snapshot = [
                {"id": f.id, "code": f.framework_code, "name": f.framework_name,
                 "provision": f.specific_provision, "rationale": f.applicability_rationale}
                for f in fw_rows
            ]

        if not fw_snapshot:
            linked_items = []
        else:
            # Reference frameworks by a short positional tag (F1, F2, ...) rather than
            # asking Claude to echo back framework_code verbatim — in practice Claude
            # reformats/re-derives codes (e.g. "LEY_10_2010" -> "Ley10/2010"), which broke
            # code-based matching almost entirely. A plain tag has no "better" spelling to
            # drift towards, so it comes back unchanged and links reliably every time.
            fw_by_ref = {f"F{i + 1}": snap for i, snap in enumerate(fw_snapshot)}
            fw_list = "\n".join(
                f"F{i + 1}. {snap['name']}"
                + (f": {snap['provision']}" if snap["provision"] else "")
                + (f" — {snap['rationale'][:200]}" if snap["rationale"] else "")
                for i, snap in enumerate(fw_snapshot)
            )

            requirements_prompt = f"""Extract specific regulatory control requirements for this internal audit.

Audit: {eng_name}
Entity: {eng_entity}
Audit type: {eng_type}

ACCEPTED FRAMEWORKS:
{fw_list}

For each significant provision in these frameworks, extract a control requirement.
Return the requirements in the JSON format this request requires. Its schema carries each
field's meaning, so what follows is only the judgement it cannot express.

Rules:
- Be specific: cite Art./§/Section numbers
- Adapt to entity jurisdiction (NL=WWFT/DNB, UK=FCA/PRA, BE=NBB, ES=BdE, EU=EBA)
"""
            # `items = req_result if isinstance(req_result, list) else []` stood
            # here: a reply of the wrong shape became an empty requirement list,
            # written as `draft_ready` with nothing in it. A failure now reaches
            # the handler below, which marks the run failed and says why.
            req = await run_agent(REQUIREMENTS_SYSTEM, requirements_prompt, Requirements,
                                  max_tokens=6000,
                                  description="Return the control requirements.")
            items = [item.model_dump() for item in req.data.requirements]

            linked_items = []
            for i, item in enumerate(items):
                matched = fw_by_ref.get(item.get("framework_ref"))
                if not matched:
                    continue  # drop requirements Claude couldn't tie back to a real framework
                linked_items.append({
                    "id": f"req_{i + 1}",
                    "framework_id": matched["id"],
                    "framework_code": matched["code"],
                    "framework_name": matched["name"],
                    "provision": item.get("provision"),
                    "what_it_requires": item.get("what_it_requires"),
                    "control_objective": item.get("control_objective"),
                    "test_approach": item.get("test_approach"),
                    "is_included": _as_bool(item.get("is_included"), default=True),
                })

        async with AsyncSessionLocal() as db:
            rr = await _get_or_create_rr(db, engagement_id)
            rr.status = "draft_ready"
            rr.items = json.dumps(linked_items)
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        await _fail(agent_run_id, f"Requirement extraction failed: {exc}", engagement_id=engagement_id)
        return

    try:
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, agent_run_id)
            if run:
                run.status = "complete"
                run.search_progress = json.dumps({"stage": "complete"})
            await db.commit()
    except Exception:  # noqa: BLE001
        # Both steps' data is already durably committed at this point — only the final
        # status flag failed to write. Log it rather than let the run hang at "running"
        # forever with no trace of why.
        logger.exception("Failed to mark framework_requirements run %s complete", agent_run_id)


async def generate_scope_contribution(engagement_id: str) -> dict:
    """Generate scope items and key questions from the accepted frameworks for this engagement.

    Returns {"scope_items": [...], "key_questions": [...]} — not saved yet; caller stores it.
    """
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        result = await db.execute(
            select(ApplicableFramework).where(
                ApplicableFramework.engagement_id == engagement_id,
                ApplicableFramework.is_accepted == True,  # noqa: E712
            )
        )
        frameworks = result.scalars().all()

    if not frameworks or not eng:
        return {"scope_items": [], "key_questions": []}

    fw_list = "\n".join(
        f"- {f.framework_name}: {f.specific_provision or f.applicability_rationale or ''}"
        for f in frameworks
    )

    user_prompt = f"""Based on the following accepted regulatory frameworks for this internal audit:

Audit: {eng.name}
Entity: {ENTITY_LABELS.get(eng.entity, eng.entity)}

FRAMEWORKS:
{fw_list}

Generate a scope contribution for the Scope & Objectives module.

Return the contribution in the JSON format this request requires. Its schema carries each
field's meaning, so what follows is only the judgement it cannot express.

Rules:
- 3-5 in_scope items derived from the primary framework obligations
- 1-2 out_of_scope items for clearly excluded areas
- 4-6 key audit questions, each referencing a specific provision
- Be specific and audit-ready — not generic
"""

    # The router calls this inside a request, so a failure returns the empty
    # contribution rather than a 500 — but it says so in the log now. The ceiling
    # is 2,000 tokens for an answer of five scope items and six questions; a run
    # that hits it raises AgentTruncated instead of arriving short.
    try:
        result = await run_agent(SCOPE_SYSTEM, user_prompt, ScopeContribution,
                                 max_tokens=2000,
                                 description="Return the scope contribution.")
    except (AgentContractError, AgentTruncated):
        logger.exception("Scope contribution failed for %s", engagement_id)
        return {"scope_items": [], "key_questions": []}
    return {
        "scope_items": [i.model_dump() for i in result.data.scope_items],
        "key_questions": [q.model_dump() for q in result.data.key_questions],
    }
