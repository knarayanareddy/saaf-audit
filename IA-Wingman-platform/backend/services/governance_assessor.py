"""Governance-Document Assessor — a fieldwork agent that checks whether the
governance in place (uploaded policy/charter documents + the control environment
already in the RACM) covers the requirements of the applicable laws and
supervisory guidance, and proposes the coverage gaps as risks in the RACM spine.

Deterministic-first & propose-never-decide:
  - The AI does ONE thing — judge, per requirement, whether it is covered /
    partial / a gap, with evidence and confidence.
  - The mapping from "gap/partial" to a RACM risk proposal is deterministic
    Python. Proposals are written with origin='ai', accepted=False and full
    provenance, so they surface in the spine as "AI proposed" awaiting the
    auditor's acceptance — nothing is decided automatically.

Opt-in & budget-safe: the run is a background task started only from an explicit
button; on failure the run is marked failed and nothing is written. Untrusted
document text is fenced with wrap_untrusted before it reaches the model.
"""
import asyncio
import json
import logging

from sqlalchemy import select

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.engagement import Engagement
from models.planning import ApplicableFramework, UploadedDocument
from models.racm import RacmControl
from services.risk_proposals import ProposedRisk, write as write_proposals
from services.agent_contract import run_agent
from services.agent_schemas import GovernanceAssessment
from services.retrieval import retrieve, verify_citation
from services.agent_ledger import agent_context
from services.prompt_safety import wrap_untrusted, safe_label

logger = logging.getLogger("ia.wingman")

AGENT_TYPE = "governance_assessor"
PROVENANCE_SOURCE = "governance_assessor"

# The prompt's document budget, spent on the passages that answer the frameworks
# being assessed rather than on the opening pages of each file. Roughly six times
# the old per-document clip, and it now buys relevant text instead of cover
# pages — see services/retrieval.py.
_DOC_BUDGET = 24_000

SYSTEM_PROMPT = (
    "You are an expert internal-audit governance assessor. You judge whether an organisation's "
    "governance — its policy and charter documents plus the controls already in place — covers the "
    "requirements set by the applicable laws and supervisory guidance. You are precise and evidence-led: "
    "you cite what covers a requirement, and you never invent coverage that is not shown. You classify "
    "each requirement as covered, partial or gap. You propose, you never decide — the auditor confirms."
)

_GAP_DEFAULT_RATING = {"gap": "high", "partial": "medium"}


async def _load_context(engagement_id: str):
    """Gather the accepted frameworks, uploaded governance docs and current RACM
    controls that the assessment reasons over. Returns plain dicts/strings."""
    async with AsyncSessionLocal() as db:
        frameworks = (await db.execute(
            select(ApplicableFramework).where(
                ApplicableFramework.engagement_id == engagement_id,
                ApplicableFramework.is_accepted == True,  # noqa: E712
            )
        )).scalars().all()
        docs = (await db.execute(
            select(UploadedDocument).where(
                UploadedDocument.engagement_id == engagement_id,
                UploadedDocument.upload_status == "ready",
            )
        )).scalars().all()
        control_rows = (await db.execute(
            select(RacmControl).where(RacmControl.engagement_id == engagement_id)
        )).scalars().all()

    fw = [{
        "ref": f.framework_code, "name": f.framework_name, "category": f.category or "law",
        "provision": f.specific_provision, "rationale": f.applicability_rationale,
    } for f in frameworks]
    control_env = [{
        "title": c.title, "description": c.description, "design": c.design_conclusion,
    } for c in control_rows]
    # What this run is looking for, in the documents' own words: the frameworks
    # and provisions being assessed, plus the controls already claimed. Building
    # the query from the requirements is the whole point — it is what makes the
    # passage about Art. 13 on page thirty reachable at all.
    query = " ".join(
        " ".join(str(v) for v in (f.get("ref"), f.get("name"), f.get("provision"), f.get("rationale")) if v)
        for f in fw
    ) + " " + " ".join(f"{c['title']} {c['description'] or ''}" for c in control_env)

    found = retrieve(
        ((d.id, d.original_filename, d.extracted_text) for d in docs),
        query, budget_chars=_DOC_BUDGET,
    )
    doc_text = wrap_untrusted(found.block, "uploaded governance documents") if found.block else ""
    return fw, doc_text, control_env, found


#: One framework per call. At ten frameworks in one call the answer ran to ~6,500
#: output tokens, and that is where it broke down: both runs at the old 4,000
#: ceiling truncated, and with room to finish it still needed a correction round
#: most times — once the model drifted out of JSON into `<parameter name=...>`
#: markup mid-answer and the run failed outright. None of that is a prompt
#: problem; it is what asking for a very long structured answer costs. Split up,
#: each call produces a few hundred tokens and has nothing to drift out of.
#:
#: The passages are retrieved once and handed to every call, so a [P#] means the
#: same passage in every item the auditor reads. That is what makes the split
#: safe; it also means the document block is paid for once per framework, which
#: is the price of this and is measured in the commit that introduced it.
_MAX_PARALLEL = 4
#: Generous on purpose. At 2,500 the split "worked" and quietly assessed four of
#: ten frameworks: the six it dropped were the broad supervisory guides — the ECB
#: SSM guide alone carries thirteen expectations, so one framework is thirteen
#: requirements and several thousand tokens of answer. A ceiling that decides
#: which frameworks get assessed is the worst kind of limit, because the result
#: still reads like an assessment. Unused ceiling costs nothing; tokens are billed
#: as produced.
_PER_FRAMEWORK_CEILING = 8_000


async def _assess_one(f: dict, doc_text: str, control_env: list) -> tuple[list, object, str]:
    """One framework. Returns (items, meta, error) — never raises."""
    try:
        outcome = await run_agent(
            SYSTEM_PROMPT,
            _build_user_blocks([f], doc_text, control_env),
            GovernanceAssessment,
            max_tokens=_PER_FRAMEWORK_CEILING,
            description=("Return one coverage item per requirement of the framework given, "
                         "with the evidence for each."),
        )
    except Exception as exc:  # noqa: BLE001
        # Reported, never guessed: a framework whose assessment failed is named in
        # the result rather than left out of it, because an assessment missing a
        # framework silently reads as a framework with nothing to say about it.
        logger.warning("Governance assessment failed for framework %s: %s",
                       f.get("ref"), exc)
        return [], None, f"{f.get('ref') or f.get('name')}: {type(exc).__name__}"

    items = outcome.dump()["items"]
    for item in items:
        # The model was given one framework, so it has no reason to say which —
        # and every reason not to be trusted if it does. Stamped here from the
        # row that was actually sent.
        item["framework_ref"] = f.get("ref")
        item["framework_name"] = f.get("name")
    return items, outcome.meta, ""


def _combined_meta(metas: list) -> dict:
    """One receipt for an assessment that is now several calls.

    The panel shows `result.run`, which used to be the single call's own figures.
    Ten calls with one of their receipts on screen would show a tenth of the bill,
    so the tokens and the cost are summed, and the duration is what the auditor
    actually waited (see _wall_clock_ms).
    """
    if not metas:
        return {}
    priced = [m.cost_usd for m in metas if m.cost_usd is not None]
    return {
        "model": metas[0].model,
        "tier": metas[0].tier,
        "calls": len(metas),
        "duration_ms": _wall_clock_ms(metas),
        "input_tokens": sum(m.input_tokens for m in metas),
        "output_tokens": sum(m.output_tokens for m in metas),
        "cached_tokens": sum(m.cached_tokens for m in metas),
        "cache_write_tokens": sum(m.cache_write_tokens for m in metas),
        "thinking_tokens": sum(m.thinking_tokens for m in metas),
        "reasoned": any(m.reasoned for m in metas),
        # None, not 0, when a model in the set has no price configured: an
        # unpriced call costs an unknown amount, and the panel says so in words.
        "cost_usd": sum(priced) if len(priced) == len(metas) else None,
        "repaired": any(m.repaired for m in metas),
        "schema": metas[0].schema,
    }


def _cost_line(metas: list) -> str:
    """What the whole assessment cost, now that it is several calls.

    `AgentMeta.sentence()` describes one call. Ten of them side by side would let
    the receipt show a tenth of the bill, which is the failure mode this ledger
    exists to prevent.
    """
    from services.model_tiers import format_cost

    if not metas:
        return "no call completed"
    priced = [m.cost_usd for m in metas if m.cost_usd is not None]
    total = format_cost(sum(priced)) if len(priced) == len(metas) else (
        format_cost(sum(priced)) + f" (+{len(metas) - len(priced)} unpriced)")
    cached = sum(m.cached_tokens for m in metas)
    return (f"{len(metas)} calls · {_wall_clock_ms(metas) / 1000:.1f}s · "
            f"{sum(m.input_tokens for m in metas):,} in"
            + (f" (+{cached:,} from cache)" if cached else "")
            + f" / {sum(m.output_tokens for m in metas):,} out · {total}")


def _wall_clock_ms(metas: list) -> int:
    """How long the auditor waited: the first call, which runs alone to write the
    cache, then the slowest of the rest, which run together. Not the slowest of
    all — that described the fan-out before the first call was made to go first."""
    if not metas:
        return 0
    rest = [m.duration_ms for m in metas[1:]]
    return metas[0].duration_ms + (max(rest) if rest else 0)


def _summarise(items: list, fw_count: int, failed: list) -> str:
    """The overall sentence, composed rather than written.

    Counted from the items themselves, so it cannot disagree with the list under
    it — which a model-written summary of a ten-part assessment could, and now
    could not even see.
    """
    tally = {k: sum(1 for i in items if (i.get("coverage") or "") == k)
             for k in ("covered", "partial", "gap")}
    parts = [f"{len(items)} requirement{'s' if len(items) != 1 else ''} assessed across "
             f"{fw_count - len(failed)} of {fw_count} frameworks",
             f"{tally['covered']} covered, {tally['partial']} partial, {tally['gap']} gap"]
    if failed:
        parts.append(f"{len(failed)} framework{'s' if len(failed) != 1 else ''} could not be "
                     f"assessed ({', '.join(failed)})")
    return ". ".join(parts) + "."


def _build_user_blocks(fw, doc_text, control_env) -> list[dict]:
    """The prompt as two blocks: what every framework call shares, then the framework.

    Order is the whole point. The shared part — the control environment, the
    retrieved passages and the rules — is identical for every framework, so it
    goes first and is marked for caching; only the framework differs, so it goes
    last. When the framework came first, as it used to, every call's prefix was
    different from its first line and no byte of the passages could ever be read
    from cache: measured at roughly 38% of what an assessment cost, paid again
    for every framework.
    """
    fw_lines = "\n".join(
        f"- [{f['category']}] {f['ref']} — {f['name']}"
        + (f" · provision: {f['provision']}" if f.get("provision") else "")
        + (f" · why applicable: {f['rationale']}" if f.get("rationale") else "")
        for f in fw
    ) or "(no accepted frameworks on file)"
    ctrl_lines = "\n".join(
        f"- {c['title']}: {c['description'] or ''} (design: {c['design'] or 'not assessed'})"
        for c in control_env
    ) or "(no controls recorded in the RACM yet)"
    doc_section = (
        f"\nUPLOADED GOVERNANCE DOCUMENTS:\n{doc_text}\n"
        if doc_text else
        "\n(No governance documents uploaded — assess coverage from the control environment only.)\n"
    )
    shared = f"""Assess whether the governance in place covers the applicable requirements of the
framework given at the end of this message.

CONTROL ENVIRONMENT (from the RACM):
{ctrl_lines}
{doc_section}
For each requirement you assess, decide coverage = "covered", "partial" or "gap", based ONLY on the
documents and controls above. When coverage is "partial" or "gap", propose a risk describing what is
not adequately governed.

Return your assessment in the JSON format this request requires. Its fields describe what each one must
contain.

Rules:
- Assess at most THREE requirements of that framework: the ones that carry the risk for THIS
  audit. Not every expectation the document contains — a broad supervisory guide has dozens, and a
  matrix of dozens per framework is one no auditor can work through. Do not invent requirements
  beyond the framework given.
- Mark "covered" only when a named document or control clearly addresses it.
- You are reading SELECTED PASSAGES, not whole documents. Never call a requirement a "gap" purely
  because it does not appear in them: say that it is not visible in the passages you were given,
  and lower your confidence instead.
- In "evidence", cite the passage you relied on by its [P#] id, or name the control. An assessment
  of "covered" with no [P#] and no named control is not evidence and will be read as unsupported.
- Set "proposed_risk" to null for "covered" items.
- Keep titles short and specific; ratings reflect inherent risk of the gap.
"""
    specific = f"""THE FRAMEWORK TO ASSESS:
{fw_lines}
"""
    return [
        {"type": "text", "text": shared, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": specific},
    ]


async def _write_proposals(engagement_id: str, run_id: str, items: list) -> int:
    """Turn partial/gap items into proposed risks. The filter is the judgement:
    a requirement the documents cover is not a gap and is not proposed."""
    proposals = []
    for item in items:
        coverage = (item.get("coverage") or "").lower()
        if coverage not in ("partial", "gap"):
            continue
        pr = item.get("proposed_risk") or {}
        title = (pr.get("title") or item.get("requirement") or "").strip()
        if not title:
            continue
        proposals.append(ProposedRisk(
            title=title,
            description=pr.get("description"),
            category=pr.get("category"),
            inherent_rating=(pr.get("inherent_rating") or _GAP_DEFAULT_RATING.get(coverage) or "medium"),
            confidence=item.get("confidence"),
            source_ref=item.get("framework_ref"),
            rationale=item.get("evidence"),
        ))
    return await write_proposals(engagement_id, run_id, PROVENANCE_SOURCE, proposals)



async def run_governance_assessment(run_id: str, engagement_id: str) -> None:
    """Background task: assess coverage, then write gap proposals into the RACM."""
    with agent_context(engagement_id=engagement_id, agent="governance_assessor", run_id=run_id):
        await _run_governance_assessment(run_id, engagement_id)


async def _run_governance_assessment(run_id: str, engagement_id: str) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if not run:
            return
        run.status = "running"
        await db.commit()

    try:
        fw, doc_text, control_env, found = await _load_context(engagement_id)
        coverage = found.coverage

        # One call per framework, a few at a time. Bounded because ten at once is
        # a burst of requests for one button press, and a 429 retried three times
        # is slower than not causing it.
        gate = asyncio.Semaphore(_MAX_PARALLEL)

        async def one(f):
            async with gate:
                return await _assess_one(f, doc_text, control_env)

        # The first framework runs alone so that it writes the shared passages to
        # the cache; the rest then run in parallel and read them. Started all at
        # once, the first four calls would each miss a cache none of them had
        # finished writing. One call's latency, against the passages being paid
        # for in full once instead of once per framework.
        assessments = [await one(fw[0])] if fw else []
        assessments += await asyncio.gather(*(one(f) for f in fw[1:]))

        items, metas, failed = [], [], []
        for got, meta, error in assessments:
            items.extend(got)
            if meta is not None:
                metas.append(meta)
            if error:
                failed.append(error)

        if fw and not items:
            # Every framework failed. That is a failed run, not an assessment
            # that found nothing.
            raise RuntimeError("No framework could be assessed: " + "; ".join(failed))

        result = {"items": items, "summary": _summarise(items, len(fw), failed),
                  "frameworks_not_assessed": failed,
                  "run": _combined_meta(metas),
                  "calls": [m.as_dict() for m in metas]}
        # Resolve every [P#] the model cited back to a real passage. An id it
        # invented must not read as provenance — the same rule grounded_validator
        # applies to quotes, applied here to citations.
        for item in items:
            if isinstance(item, dict):
                item["citations"] = verify_citation(str(item.get("evidence") or ""), found.by_cid)
        proposed = await _write_proposals(engagement_id, run_id, items)
        result["proposed_risk_count"] = proposed
        result["documents_assessed"] = coverage.documents
        result["document_coverage"] = coverage.as_dict()

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.raw_output = json.dumps(result)
                run.input_summary = (f"{len(fw)} frameworks · {coverage.sentence()} · "
                                     f"{proposed} gaps proposed · {_cost_line(metas)}")
                run.status = "complete"
                await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.raw_output = json.dumps({"error": str(exc)[:500]})
                await db.commit()
