"""Process Understanding Agent — 2-step flow.

Step 1 (run_process_analysis):
    Reads uploaded docs + engagement context → generates AI reasoning (Steps 1-3 + conclusion).
    Stores in ProcessNotes.reasoning, sets status = 'reasoning_ready'.

Step 2 (generate_process_proposals, triggered after human approves reasoning):
    Turns the approved reasoning into structured process items with activities.
    Stores in ProcessNotes.process_items + preliminary_observations, sets status = 'draft_ready'.
"""
import json
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.planning import ProcessNotes, UploadedDocument
from models.engagement import Engagement
from services.ai_service import run_agent_to_json
from services.retrieval import retrieve
from services.prompt_safety import wrap_untrusted, safe_label

ENTITY_LABELS = {
    "GRP": "the organisation Netherlands (DNB/ECB supervised)",
    "INT": "the organisation UK (PRA/FCA supervised)",
    "RET": "the organisation Belgium (NBB/ECB supervised)",
    "BUS": "the organisation Spain (Banco de España/ECB supervised)",
    "AM": "Asset Management (AIFMD/UCITS)",
}

REASONING_SYSTEM = (
    "You are an expert internal audit process analyst for the organisation's Internal Audit function. "
    "You analyse audit scope and available documents to map the in-scope business processes "
    "with clear step-by-step reasoning. Be specific, cite document sections when available, "
    "and explain WHY each process is in scope with reference to the regulatory or operational basis."
)

PROPOSALS_SYSTEM = (
    "You are an expert internal auditor at the organisation. "
    "You generate structured process maps with specific activities from approved reasoning. "
    "Each process must have a name, description, source (from_docs or best_practice), "
    "confidence (high/medium/low), and 2-4 specific activities."
)


async def _get_document_context(engagement_id: str, query: str = "") -> str:
    """The uploaded documents, reduced to the passages that bear on the processes
    under review — see services/retrieval.py. A 3,000-character clip off the top
    of a process manual was, reliably, its title page."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UploadedDocument).where(
                UploadedDocument.engagement_id == engagement_id,
                UploadedDocument.upload_status == "ready",
            )
        )
        docs = result.scalars().all()

    if not docs:
        return ""

    found = retrieve(
        ((d.id, d.original_filename, d.extracted_text) for d in docs),
        query, budget_chars=18_000,
    )
    if not found.block:
        return ""
    return wrap_untrusted(found.block, "uploaded documents")


async def run_process_analysis(pn_id: str, engagement_id: str) -> None:
    """Background task: Step 1 — generate AI reasoning about in-scope processes."""
    async with AsyncSessionLocal() as db:
        pn = await db.get(ProcessNotes, pn_id)
        if not pn:
            return
        pn.status = "reasoning"
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            eng = await db.get(Engagement, engagement_id)
            if not eng:
                raise ValueError("Engagement not found")
            eng_name = eng.name
            eng_entity = eng.entity
            eng_type = eng.audit_type

        # The audit itself is the query: its name and type are what decides which
        # part of a process manual matters here.
        doc_context = await _get_document_context(
            engagement_id, f"{eng_name} {eng_type} process procedure control responsibility")
        doc_section = (
            f"\nUPLOADED DOCUMENTS:\n{doc_context}\n"
            if doc_context else
            "\n(No documents uploaded — reasoning based on audit scope knowledge only.)\n"
        )

        user_prompt = f"""Analyse this internal audit engagement and produce structured reasoning
about which business processes should be in scope.

Audit: {eng_name}
Entity: {ENTITY_LABELS.get(eng_entity, eng_entity)}
Audit type: {eng_type}
{doc_section}
Return ONLY a valid JSON object (no explanation, no markdown):
{{
  "step1_understanding": "2-3 sentences explaining what this audit examines and why",
  "step2_sources": [
    {{
      "filename": "document name or 'audit knowledge'",
      "relevance": "What relevant content this source contains"
    }}
  ],
  "step3_proposed_processes": [
    {{
      "name": "Process name",
      "rationale": "Why this process is in scope — cite document section or regulatory basis",
      "source": "from_docs or best_practice",
      "confidence": "high or medium or low"
    }}
  ],
  "step3_excluded": [
    {{
      "name": "Process name",
      "reason": "Why excluded from scope"
    }}
  ],
  "conclusion": "1-2 sentence summary of the proposed process scope"
}}

Rules:
- Propose 4-7 in-scope processes — the most relevant for this specific audit
- Mark source='from_docs' only for processes explicitly mentioned in the passages shown, and cite
  the passage id [P#] in the rationale
- The passages are a selection, not the whole documents: a process that does not appear in them is
  unknown to you, not excluded
- Mark source='best_practice' for processes derived from audit type knowledge
- confidence='high' if directly evidenced, 'medium' if likely, 'low' if uncertain
- If no documents: all sources are 'best_practice'
"""

        result = await run_agent_to_json(
            system_prompt=REASONING_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=3000,
        )

        if not isinstance(result, dict):
            raise ValueError(f"Expected JSON object, got: {type(result)}")

        async with AsyncSessionLocal() as db:
            pn = await db.get(ProcessNotes, pn_id)
            if pn:
                pn.reasoning = json.dumps(result)
                pn.status = "reasoning_ready"
                await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            pn = await db.get(ProcessNotes, pn_id)
            if pn:
                pn.status = "not_started"
                pn.reasoning = json.dumps({"error": str(exc)[:500]})
                await db.commit()


async def generate_process_proposals(pn_id: str, engagement_id: str, approved_reasoning: str) -> None:
    """Background task: Step 2 — generate structured proposals from approved reasoning."""
    async with AsyncSessionLocal() as db:
        pn = await db.get(ProcessNotes, pn_id)
        if not pn:
            return
        pn.status = "generating"
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            eng = await db.get(Engagement, engagement_id)
            eng_name = eng.name if eng else "Unknown"
            eng_entity = eng.entity if eng else "GRP"

        user_prompt = f"""Based on the following approved reasoning for an internal audit,
generate structured process items with specific activities.

Audit: {eng_name}
Entity: {ENTITY_LABELS.get(eng_entity, eng_entity)}

APPROVED REASONING:
{approved_reasoning}

Return ONLY a valid JSON object (no explanation, no markdown):
{{
  "processes": [
    {{
      "id": "generate a short UUID here",
      "name": "Process name",
      "description": "1-2 sentence description of what this process covers",
      "source": "from_docs or best_practice",
      "confidence": "high or medium or low",
      "is_included": true,
      "activities": [
        {{
          "id": "short UUID",
          "name": "Activity name",
          "description": "What happens in this activity"
        }}
      ]
    }}
  ],
  "preliminary_observations": [
    {{
      "text": "A preliminary observation or risk identified from the process review",
      "source": "from_docs or from_knowledge"
    }}
  ]
}}

Rules:
- Include all processes from the approved reasoning's step3_proposed_processes
- Each process: 2-4 specific, actionable activities (not vague steps)
- preliminary_observations: 2-4 observations grounded in the documents or audit knowledge
- Use short UUIDs (8 chars) for ids
"""

        result = await run_agent_to_json(
            system_prompt=PROPOSALS_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=4000,
        )

        if not isinstance(result, dict):
            raise ValueError(f"Expected JSON object, got: {type(result)}")

        async with AsyncSessionLocal() as db:
            pn = await db.get(ProcessNotes, pn_id)
            if pn:
                pn.process_items = json.dumps(result.get("processes", []))
                pn.preliminary_observations = json.dumps(result.get("preliminary_observations", []))
                pn.status = "draft_ready"
                await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            pn = await db.get(ProcessNotes, pn_id)
            if pn:
                pn.status = "reasoning_ready"  # fall back so user can re-approve
                await db.commit()
