"""Document Request List (DRL) Generator.

Auto-generates a list of documents to request from the auditee based on:
- the evidence the work program's tests declare they need
- accepted frameworks (what the law requires as evidence)
- accepted scope items (what areas will be audited)
- process understanding (what process documents are needed)

Each row: document needed | regulatory basis | requested from | category | covers

The first input is the new one, and `covers` is what it buys. Measured on one
engagement, 17 tests declared 62 evidence needs against a 19-item DRL: the work
done here is the **reduction**, merging needs across tests into one request an
auditee can act on, addressed to a department that exists. What was missing was
the record of which needs each request settles, so nobody could say whether a
given test had been asked for at all. The model doing the merging is the only
thing that knows, so it is asked while it merges rather than reconstructed
afterwards by comparing words — see services/evidence_needs.py.
"""
import json
import logging

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import (
    ApplicableFramework, ScopeObjectives, ScopeItem,
    ProcessNotes, RegRequirement,
)
from services.agent_contract import AgentContractError, AgentTruncated, run_agent
from services.agent_schemas import DocumentRequestList
from services.ai_service import BASE_SYSTEM_PROMPT

logger = logging.getLogger("ia.wingman")


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


async def generate_drl(engagement_id: str) -> list[dict]:
    """Generate a Document Request List from planning data. Returns list of DRL items."""
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        if not eng:
            return []

        # Accepted frameworks
        fw_res = await db.execute(
            select(ApplicableFramework).where(
                ApplicableFramework.engagement_id == engagement_id,
                ApplicableFramework.is_accepted == True,  # noqa: E712
            )
        )
        frameworks = fw_res.scalars().all()

        # Scope items
        scope_res = await db.execute(
            select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
        )
        scope = scope_res.scalar_one_or_none()
        scope_items = []
        if scope:
            si_res = await db.execute(
                select(ScopeItem).where(
                    ScopeItem.scope_id == scope.id,
                    ScopeItem.is_accepted == True,  # noqa: E712
                    ScopeItem.item_type == "in_scope",
                )
            )
            scope_items = si_res.scalars().all()

        # Process notes
        pn_res = await db.execute(
            select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id)
        )
        pn = pn_res.scalar_one_or_none()
        processes = _loads(pn.process_items if pn else None, [])
        included_processes = [p for p in processes if p.get("is_included") is not False]

        # What the tests say they need, carrying refs so the answer can point back.
        from services.evidence_needs import needs_for
        needs = [n for n in await needs_for(engagement_id, db) if n.requestable]

        # Regulatory requirements
        rr_res = await db.execute(
            select(RegRequirement).where(RegRequirement.engagement_id == engagement_id)
        )
        rr = rr_res.scalar_one_or_none()
        reqs = _loads(rr.items if rr else None, [])
        included_reqs = [r for r in reqs if r.get("is_included") is not False]

    fw_ctx = "\n".join(
        f"- {f.framework_name}" + (f": {f.specific_provision}" if f.specific_provision else "")
        for f in frameworks[:8]
    ) if frameworks else "No frameworks accepted yet."

    scope_ctx = "\n".join(
        f"- {s.description}" for s in scope_items[:8]
    ) if scope_items else "No scope items accepted yet."

    process_ctx = "\n".join(
        f"- {p['name']}: {p.get('description','')[:100]}"
        for p in included_processes[:6]
    ) if included_processes else ""

    req_ctx = "\n".join(
        f"- {r.get('provision','')}: {r.get('test_approach','')[:100]}"
        for r in included_reqs[:6]
    ) if included_reqs else ""

    needs_ctx = "\n".join(
        f"- {n.ref or n.id}: {n.title}"
        + (f" [{n.requested_from}]" if n.requested_from else "")
        + (f" [{n.period}]" if n.period else "")
        for n in needs[:60]
    ) if needs else ""

    prompt = f"""Generate a Document Request List (DRL) for this internal audit.
The DRL lists documents the audit team will request from the auditee before or at the kick-off meeting.

Audit: {eng.name}
Entity: {eng.entity}
Audit type: {eng.audit_type}

ACCEPTED FRAMEWORKS:
{fw_ctx}

IN-SCOPE AREAS:
{scope_ctx}

{f"PROCESSES IN SCOPE:{chr(10)}{process_ctx}" if process_ctx else ""}
{f"CONTROL TEST APPROACHES:{chr(10)}{req_ctx}" if req_ctx else ""}
{f"EVIDENCE THE TESTS NEED — each ref belongs in exactly one request:{chr(10)}{needs_ctx}" if needs_ctx else ""}

Generate a comprehensive document request list.
Return the requests in the JSON format this request requires. Its schema carries each
field's meaning, so what follows is only the judgement it cannot express.

Rules:
- Generate 10-20 items
- covers: the refs from EVIDENCE THE TESTS NEED that this request settles. Merge
  freely — one request may cover several needs across several tests, and that
  merging is the point of this list. Every listed ref belongs in exactly one
  request. Where a need genuinely cannot be asked of the auditee, leave it out
  rather than inventing a request for it. Empty list when no needs are listed
- Be specific: name real document types (not generic "all records")
- Mix categories: policies, procedures, management reports, system exports, evidence files
- Ordered by: Policies first, then Procedures, then Reports/Data, then Evidence
"""
    # Raised from 3,500: twenty requests each naming the needs it covers did
    # not fit, and the run failed outright rather than returning a short list.
    #
    # The second call site the ledger ranked, and it earned the place the same
    # way the first did: asked for a bare JSON array, it came back inside a
    # markdown fence on 3 of 3 measured runs. The fence was stripped before
    # anyone saw it and the row read as clean, so the prompt looked obeyed. What
    # made this one worth doing before the rest is the line underneath: a reply
    # that parsed into anything other than a list returned an empty DRL, and an
    # empty DRL is indistinguishable on screen from an audit that needs no
    # documents.
    try:
        result = await run_agent(BASE_SYSTEM_PROMPT, prompt, DocumentRequestList,
                                 max_tokens=8_000,
                                 description="Return the document requests.")
    except (AgentContractError, AgentTruncated):
        logger.exception("DRL generation failed for %s", engagement_id)
        raise
    items = [item.model_dump() for item in result.data.items]
    for i, item in enumerate(items):
        # Positional, and renumbered on every regenerate — which is why the
        # evidence links are cleared before this runs; see evidence_needs.
        item["id"] = f"drl_{i + 1}"
        item["status"] = "not_requested"
        item["covers"] = [str(r) for r in item["covers"]]
    return items
