import json

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.agent_run import AgentRun
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT


def _load_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


async def run_interview_agent(run_id: str, engagement_id: str):
    """Interview Guide agent — runs after Regulatory + Policy. Owns its own DB session."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        run.status = "running"
        await db.commit()

        # Pull the two prerequisite agent outputs
        result = await db.execute(
            select(AgentRun).where(
                AgentRun.engagement_id == engagement_id,
                AgentRun.agent_type.in_(["regulatory", "policy"]),
            )
        )
        prereqs = result.scalars().all()

    reg_data, pol_data = {}, {}
    for r in prereqs:
        if r.agent_type == "regulatory":
            reg_data = _load_json(r.raw_output)
        elif r.agent_type == "policy":
            pol_data = _load_json(r.raw_output)

    try:
        frameworks = ", ".join(
            f.get("framework_name", "") for f in reg_data.get("applicable_frameworks", [])
        )
        policy_gaps = "; ".join(pol_data.get("policy_gaps", [])) or "None identified"
        internal_summary = pol_data.get("internal_framework_summary", "No internal documents provided.")
        no_docs_note = (
            "No internal documents were uploaded — focus interview questions on regulatory requirements "
            "and request internal process documentation."
            if not pol_data.get("relevant_documents")
            else ""
        )

        user_prompt = f"""You are generating a structured interview guide for an internal audit at the organisation.

Engagement: {eng.name}
Entity: {eng.entity}
Audit type: {eng.audit_type}

REGULATORY INTELLIGENCE FINDINGS:
{reg_data.get("regulatory_summary", "")}
Applicable frameworks: {frameworks}
Supervisory focus: {reg_data.get("supervisory_focus", "")}

INTERNAL FRAMEWORK FINDINGS:
{internal_summary}
Policy gaps identified: {policy_gaps}
{no_docs_note}

Generate structured interview questions following the organisation's kick-off meeting structure.
Produce ONLY a JSON object:
{{
  "sponsor_questions": ["..."],
  "sme_questions": ["..."],
  "ia_prework": ["..."]
}}

Guidelines:
- Sponsor questions (5-7): strategic and governance-focused (why this audit, risk appetite, known issues)
- SME questions (8-12): operational and process-focused (walk me through X, how is Y handled, exceptions)
- IA pre-work (5-8): specific, actionable preparation tasks
- Reference specific regulations by name where relevant
- Where internal policy gaps exist, add questions to probe them"""

        result = await run_agent_to_json(BASE_SYSTEM_PROMPT, user_prompt)

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.raw_output = json.dumps(result)
            run.status = "complete"
            run.input_summary = f"Interview guide for {eng.name}"
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.status = "failed"
            run.raw_output = f"Error: {exc}"
            await db.commit()
