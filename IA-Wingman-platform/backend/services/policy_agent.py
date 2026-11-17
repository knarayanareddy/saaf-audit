import json

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.planning import UploadedDocument
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services.prompt_safety import wrap_untrusted
from services.retrieval import retrieve


async def run_policy_agent(run_id: str, engagement_id: str):
    """Policy Scout agent — searches only uploaded documents. Owns its own DB session."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        run.status = "running"
        await db.commit()

        docs_result = await db.execute(
            select(UploadedDocument).where(
                UploadedDocument.engagement_id == engagement_id,
                UploadedDocument.upload_status == "ready",
            )
        )
        docs = docs_result.scalars().all()
        doc_ids = [d.id for d in docs]
        # The Scout's whole job is finding what in the internal framework bears on
        # this audit, so the audit is the query — an 8,000-character clip off the
        # front of each policy was answering a different question.
        found = retrieve(
            ((d.id, d.original_filename, d.extracted_text) for d in docs),
            f"{eng.name} {eng.audit_type} {eng.entity} policy procedure standard control requirement",
            budget_chars=24_000,
        )

    try:
        if not found.block:
            result = {
                "relevant_documents": [],
                "internal_framework_summary": "No internal documents were uploaded for this engagement. "
                "Policy Scout has nothing to analyse. Upload internal policies, frameworks, or guidelines "
                "to ground the audit in the organisation's own materials.",
                "policy_gaps": [],
            }
        else:
            documents_text = found.block
            user_prompt = f"""Run the Policy Scout agent.

Engagement: {eng.name}
Entity: {eng.entity}
Audit type: {eng.audit_type}

Passages selected from the uploaded documents:
{wrap_untrusted(documents_text, "uploaded documents")}

Search these passages for content relevant to the audit topic. Cite the passage id [P#] for every
section you report, and treat what is not shown as unknown rather than absent.
Produce ONLY a JSON object:
{{
  "relevant_documents": [
    {{
      "filename": "...",
      "relevant_sections": ["Section 3.2 - EDD procedures"],
      "summary": "What this document says about the topic",
      "gaps_or_issues_noted": "What seems missing or unclear"
    }}
  ],
  "internal_framework_summary": "Overall summary of the internal framework based on these documents",
  "policy_gaps": ["Gap 1", "Gap 2"]
}}

IMPORTANT: Only use information from the passages provided. Never invent document contents, and
never report a gap on the basis that something is not in the passages — say it was not visible in
what you were shown."""
            result = await run_agent_to_json(BASE_SYSTEM_PROMPT, user_prompt)

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.raw_output = json.dumps(result)
            run.document_ids = json.dumps(doc_ids)
            run.status = "complete"
            run.input_summary = f"Policy scout for {eng.name} ({len(doc_ids)} documents)"
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.status = "failed"
            run.raw_output = f"Error: {exc}"
            await db.commit()
