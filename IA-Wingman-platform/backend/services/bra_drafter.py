"""Background Risk Assessment Drafter — fills the 4 background sections and suggests risk items."""
import json

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.planning import BackgroundRiskAssessment, TopicIntelligence, ScopeObjectives, ScopeItem, ApplicableFramework
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services.memory_context import recall_for


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


async def run_bra_drafter(bra_id: str, run_id: str, engagement_id: str):
    """Drafts the Background Risk Assessment. Owns its own DB sessions."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        bra = await db.get(BackgroundRiskAssessment, bra_id)
        run.status = "running"
        await db.commit()

        ti_res = await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))
        ti = ti_res.scalar_one_or_none()

        scope_res = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))
        scope = scope_res.scalar_one_or_none()

        in_scope = []
        if scope:
            items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
            in_scope = [(i.description, i.rationale) for i in items if i.item_type == "in_scope" and i.is_accepted]

        fw_res = await db.execute(
            select(ApplicableFramework).where(
                ApplicableFramework.engagement_id == engagement_id,
                ApplicableFramework.is_accepted == True,  # noqa: E712
            )
        )
        frameworks = [(f.framework_name, f.applicability_rationale or "") for f in fw_res.scalars().all()]

        # This prompt has always asked for "what we know from prior audits" and
        # for "audit findings from related reviews", and has never been given
        # anything to answer with. Whatever came back was invented.
        memory = await recall_for(db, engagement_id, limit=6, kinds=("finding", "risk", "scope"))

    ti_summary = ti.regulatory_summary if ti else ""
    ti_key_risks = _loads(ti.key_risk_areas if ti else None, [])
    ti_developments = ti.external_developments if ti else ""
    int_framework = ti.internal_framework_summary if ti else ""
    ti_conclusion = ti.conclusion if ti else ""

    user_prompt = f"""Complete the Background Risk Assessment template for this the organisation internal audit.

ENGAGEMENT: {eng.name} ({eng.entity}, {eng.audit_type})
SCOPE PERIOD: {eng.scope_period or 'TBD'}
OVERALL OBJECTIVE: {scope.overall_objective if scope else 'TBD'}

REGULATORY CONTEXT (from Topic Intelligence):
{ti_summary[:1000] if ti_summary else 'Not completed.'}

RECENT DEVELOPMENTS: {ti_developments[:400] if ti_developments else ''}

INTERNAL FRAMEWORK: {int_framework[:400] if int_framework else 'Not available.'}

IN-SCOPE AREAS:
{chr(10).join(f'- {desc} (basis: {rat or "TBD"})' for desc, rat in in_scope) or 'TBD'}

APPLICABLE FRAMEWORKS:
{chr(10).join(f'- {name}: {rat}' for name, rat in frameworks[:8]) or 'TBD'}

KEY RISK AREAS FROM TOPIC INTELLIGENCE:
{chr(10).join(f'- {r.get("title","")}: {r.get("rationale","")}' for r in ti_key_risks) or 'See regulatory context.'}

{memory.block if not memory.is_empty else 'PRIOR AUDITS: nothing on file matched this topic. Say so rather than inventing a history.'}

Produce ONLY a JSON object with these exact keys:

{{
  "section_strategy": "2-3 paragraphs covering: (1) what this audit area does and its strategic importance to the organisation, (2) main objectives and risks for this area based on regulatory context, (3) what we know from prior audits/risk assessments. Reference specific the organisation strategy elements and the regulatory environment.",

  "section_risk_tolerance": "1-2 paragraphs: what risk tolerance level has management established for this audit area (e.g. low tolerance for regulatory non-compliance, moderate for operational efficiency). Reference DNB/PRA/NBB/BdE supervisory expectations if relevant. Indicate where residual risks may exceed appetite.",

  "section_governance": "2-3 paragraphs covering: (1) who owns and oversees this area (governance structure), (2) what management reports, controls and monitoring exist, (3) any relevant ICS/RCSA results, walkthrough observations, or audit findings from related reviews. Note outstanding audit issues if any.",

  "section_frameworks": "Structured list of applicable laws, regulations, internal policies and guidelines. For each, note what specifically it requires of the organisation and how compliance is measured. Group by: primary regulation, supervisory guidance, internal policy.",

  "risk_items": [
    {{
      "ref": "R1",
      "link_to_anl": "Scope area from ANL this risk relates to",
      "description": "Brief risk area title",
      "process": "Process or sub-process and control objective",
      "risk_statement": "The likelihood of <undesirable event> due to <cause> resulting in <impact>",
      "inherent_risk": "High",
      "controls": "Key existing controls designed to reduce this risk",
      "residual_risk": "Medium",
      "is_accepted": false
    }}
  ]
}}

For risk_items: propose 4-7 risks covering the key risk areas identified. Use the exact risk statement format from the the organisation template. Inherent and residual risk must be 'High', 'Medium', or 'Low'. Be realistic — AML risks at a bank usually have High inherent risk."""

    try:
        result = await run_agent_to_json(BASE_SYSTEM_PROMPT, user_prompt, max_tokens=6000)

        async with AsyncSessionLocal() as db:
            bra = await db.get(BackgroundRiskAssessment, bra_id)
            run = await db.get(AgentRun, run_id)

            bra.section_strategy = result.get("section_strategy", "")
            bra.section_risk_tolerance = result.get("section_risk_tolerance", "")
            bra.section_governance = result.get("section_governance", "")
            bra.section_frameworks = result.get("section_frameworks", "")
            bra.risk_items = json.dumps(result.get("risk_items", []))
            bra.status = "draft_ready"
            run.status = "complete"
            # The run says what it was told, not only what it produced: an
            # assessment shaped by a prior audit should show that on its face.
            run.input_summary = (f"{len(in_scope)} in-scope area(s) · "
                                 f"{len(frameworks)} framework(s) · {memory.sentence()}")
            run.raw_output = json.dumps(result)
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            bra = await db.get(BackgroundRiskAssessment, bra_id)
            run = await db.get(AgentRun, run_id)
            bra.status = "not_started"
            run.status = "failed"
            run.raw_output = f"Error: {exc}"
            await db.commit()
