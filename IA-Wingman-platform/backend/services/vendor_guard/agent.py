"""Vendor Guard fieldwork agent.

Opt-in AI: assess selected vendor documents against the applicable curated
frameworks, then deterministically build a RAG scorecard + gap register, an
optional AI memo, and optional Critical/High gap proposals into the RACM spine.
Mirrors services/governance_assessor.py (AgentRun lifecycle, propose-never-decide,
idempotent proposal replacement, wrap_untrusted fencing).
"""

import json

from sqlalchemy import select

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.planning import UploadedDocument
from services.risk_proposals import ProposedRisk, write as write_proposals
from services.prompt_safety import wrap_untrusted, safe_label

from services.retrieval import retrieve
from .assessors import applicable_specialists, assess_specialist, SPECIALISTS
from .scorecard import compute_rag_scorecard, gap_register, overall_rag

AGENT_TYPE = "vendor_guard"
PROVENANCE_SOURCE = "vendor_guard"

# Only material gaps become spine proposals.
_RATING_BY_SEVERITY = {"Critical": "high", "High": "high", "Medium": "medium", "Low": "low", "Info": "low"}
_PROPOSE_SEVERITIES = {"Critical", "High"}
# Spent on the passages that answer the frameworks being assessed rather than on
# the front of each file — see services/retrieval.py.
_DOC_BUDGET = 24_000


async def _load_docs_fenced(engagement_id: str, document_ids: list[str], query: str = ""):
    """The selected (or all ready) vendor documents, reduced to the passages that
    bear on the frameworks this assessment covers — see services/retrieval.py."""
    async with AsyncSessionLocal() as db:
        q = select(UploadedDocument).where(
            UploadedDocument.engagement_id == engagement_id,
            UploadedDocument.upload_status == "ready",
        )
        docs = (await db.execute(q)).scalars().all()
    if document_ids:
        wanted = set(document_ids)
        docs = [d for d in docs if d.id in wanted]
    found = retrieve(
        ((d.id, d.original_filename, d.extracted_text) for d in docs),
        query, budget_chars=_DOC_BUDGET,
    )
    if not found.block:
        return "", found.coverage
    return wrap_untrusted(found.block, "uploaded vendor documents"), found.coverage


async def _write_risk_proposals(engagement_id: str, run_id: str, findings: list) -> int:
    """Turn Critical/High gaps into proposed risks. The filter is the judgement:
    a low-severity gap in a vendor assessment is not matrix material."""
    proposals = []
    for f in findings:
        if f.status != "Gap" or f.severity not in _PROPOSE_SEVERITIES:
            continue
        description = (f.evidence or "").strip()
        if f.recommendation:
            description = f"{description}\n\nRecommendation: {f.recommendation.strip()}"
        proposals.append(ProposedRisk(
            title=f"{f.framework} {f.control_id}: {f.control_name}".strip(),
            description=description,
            category=f.framework,
            inherent_rating=_RATING_BY_SEVERITY.get(f.severity, "medium"),
            confidence="medium",
            source_ref=f"{f.framework} {f.control_id}",
            rationale=f.evidence,
        ))
    return await write_proposals(engagement_id, run_id, PROVENANCE_SOURCE, proposals)



async def run_vendor_guard(
    run_id: str, engagement_id: str, vendor_name: str = "",
    is_ai_system: bool = False, is_dutch_government: bool = False,
    document_ids: list[str] | None = None,
    draft_memo: bool = False, propose_to_spine: bool = False,
) -> None:
    """Background task: specialist assessments -> scorecard -> memo -> spine proposals."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if not run:
            return
        run.status = "running"
        await db.commit()

    try:
        # Which specialists apply decides what to look for, so they are resolved
        # before the documents are read rather than after.
        specialists_for_query = applicable_specialists(is_ai_system, is_dutch_government)
        query = " ".join(
            f"{SPECIALISTS[k]['label']} " + " ".join(SPECIALISTS[k]["frameworks"])
            for k in specialists_for_query if k in SPECIALISTS
        ) or (vendor_name or "third party outsourcing control security")
        docs_fenced, coverage = await _load_docs_fenced(engagement_id, document_ids or [], query)
        if coverage.documents == 0:
            result = {"error_kind": "no_documents",
                      "message": "No ready vendor documents selected. Upload evidence and select at least one."}
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                if run:
                    run.raw_output = json.dumps(result)
                    run.input_summary = "No vendor documents selected"
                    run.status = "complete"
                    await db.commit()
            return

        specialists = applicable_specialists(is_ai_system, is_dutch_government)
        findings = []
        for key in specialists:
            findings += await assess_specialist(key, docs_fenced)

        scorecard = compute_rag_scorecard(findings)
        result = {
            "vendor_name": vendor_name,
            "is_ai_system": is_ai_system,
            "is_dutch_government": is_dutch_government,
            "specialists": [SPECIALISTS[k]["label"] for k in specialists],
            "documents_assessed": coverage.documents,
            "document_coverage": coverage.as_dict(),
            "scorecard": scorecard,
            "overall_rag": overall_rag(scorecard),
            "gap_register": gap_register(findings),
            "total_findings": len(findings),
        }

        if draft_memo and findings:
            try:
                from .memo import draft_memo as _draft
                result["memo"] = await _draft(vendor_name, findings, scorecard)
            except Exception:  # noqa: BLE001 — memo is best-effort
                result["memo"] = None

        proposed = 0
        if propose_to_spine:
            proposed = await _write_risk_proposals(engagement_id, run_id, findings)
        result["proposed_risk_count"] = proposed

        summary = (f"{vendor_name or 'vendor'} · {coverage.sentence()} · {len(specialists)} specialists · "
                   f"{len(findings)} findings · {result['overall_rag']}"
                   + (f" · {proposed} gaps proposed" if propose_to_spine else ""))

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.raw_output = json.dumps(result)
                run.input_summary = summary
                run.status = "complete"
                await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.raw_output = json.dumps({"error": str(exc)[:500]})
                await db.commit()
