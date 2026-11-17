"""ANL Drafter agent — generates a full Audit Notification Letter draft from planning data."""
import json
from uuid import uuid4
from datetime import datetime, timedelta

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from services.auditee_context import load as load_auditee_context
from models.agent_run import AgentRun
from models.planning import (
    AuditNotificationLetter, TopicIntelligence,
    ScopeObjectives, ScopeItem, ApplicableFramework,
)
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _auto_timing(start_date: str | None, end_date: str | None) -> dict:
    """Calculate suggested ANL timing from engagement dates."""
    timing = {
        "fieldwork_start": start_date or "TBD",
        "fieldwork_end": end_date or "TBD",
        "draft_report": "",
        "mgmt_response": "",
        "final_report": "",
    }
    if end_date:
        try:
            fd_end = datetime.strptime(end_date, "%Y-%m-%d")
            # Standard ANL timing: draft 3 weeks after close of fieldwork, management
            # response 2 weeks after the draft, final report 5 days after that.
            draft = fd_end + timedelta(weeks=3)
            mgmt = draft + timedelta(weeks=2)
            final = mgmt + timedelta(days=5)
            timing["draft_report"] = draft.strftime("%d %B %Y")
            timing["mgmt_response"] = mgmt.strftime("%d %B %Y")
            timing["final_report"] = final.strftime("%d %B %Y")
        except ValueError:
            pass
    return timing


async def run_anl_drafter(anl_id: str, run_id: str, engagement_id: str):
    """Drafts all ANL sections. Owns its own DB sessions."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        run.status = "running"
        await db.commit()

        ctx = await load_auditee_context(db, engagement_id)

    items_in, items_out = ctx.in_scope, ctx.out_of_scope
    frameworks = ctx.frameworks
    ti_summary = ctx.ti_summary
    ti_conclusion = ctx.ti_conclusion
    ti_key_risks = ctx.ti_key_risks

    timing = _auto_timing(eng.start_date, eng.end_date)

    user_prompt = f"""You are drafting a professional Audit Notification Letter (ANL) for the organisation's Internal Audit function.

ENGAGEMENT DETAILS:
- Audit name: {eng.name}
- Audit code: {eng.audit_code or 'To be assigned'}
- Entity: {eng.entity}
- Type: {eng.audit_type}
- Lead auditor: {eng.lead_auditor or 'To be confirmed'}
- Team: {eng.team_members or '[]'}
- Scope period: {eng.scope_period or 'To be confirmed'}

REGULATORY CONTEXT (from Regulatory Intelligence):
{ti_summary or 'Not yet completed — use your knowledge of applicable regulations for this entity and audit type.'}

OVERALL AUDIT OBJECTIVE:
{ctx.overall_objective or 'To be defined.'}

IN-SCOPE AREAS:
{chr(10).join(f'- {s}' for s in items_in) or '(Scope items not yet confirmed — draft based on regulatory context)'}

OUT-OF-SCOPE AREAS:
{chr(10).join(f'- {s}' for s in items_out) or 'To be confirmed.'}

KEY RISK AREAS:
{chr(10).join(f'- {r.get("title","")} — {r.get("rationale","")}' for r in ti_key_risks) or 'See regulatory context above.'}

APPLICABLE FRAMEWORKS:
{chr(10).join(f'- {f}' for f in frameworks) or 'To be confirmed.'}

CONCLUSION / RECOMMENDED SCOPE:
{ti_conclusion or ''}

Write each section of the ANL following the organisation's Internal Audit template format.
Write in clear, professional English using established internal-audit language (IIA/GIAS style).
Each section should be concise and specific.

Produce ONLY a JSON object with these exact keys:
{{
  "background": "2-3 paragraphs: why this audit is in the plan, link to strategic themes, risk context. Reference the applicable regulatory framework; do not invent an organisation mission or name.",
  "objectives": "1-2 sentences: what the audit aims to assess, using IIA language ('To assess the design and operating effectiveness of...')",
  "scope_description": "Bullet-style description of in-scope areas and scope period. Reference specific controls, processes, or regulatory articles where relevant.",
  "out_of_scope": "Brief list of exclusions with rationale for each. If none confirmed, write 'To be confirmed during kick-off meeting.'",
  "approach": "3-5 steps describing the audit methodology: document review, interviews, testing, findings discussion. Reference IIA standards and relevant regulatory requirements.",
  "responsibility": "2-3 sentences: what the auditee must provide — documentation, access, timely responses to findings. Standard the organisation language."
}}

Be specific to {eng.entity} and {eng.audit_type} audit context. Never use generic placeholder text."""

    try:
        result = await run_agent_to_json(BASE_SYSTEM_PROMPT, user_prompt, max_tokens=6000)

        async with AsyncSessionLocal() as db:
            anl = await db.get(AuditNotificationLetter, anl_id)
            run = await db.get(AgentRun, run_id)

            anl.background = result.get("background", "")
            anl.objectives = result.get("objectives", "")
            anl.scope_description = result.get("scope_description", "")
            anl.out_of_scope = result.get("out_of_scope", "")
            anl.approach = result.get("approach", "")
            anl.responsibility = result.get("responsibility", "")

            # Auto-fill timing from engagement dates
            anl.timing_fieldwork_start = timing["fieldwork_start"]
            anl.timing_fieldwork_end = timing["fieldwork_end"]
            anl.timing_draft_report = timing["draft_report"]
            anl.timing_mgmt_response = timing["mgmt_response"]
            anl.timing_final_report = timing["final_report"]

            anl.status = "draft_ready"
            run.status = "complete"
            run.raw_output = json.dumps(result)
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            anl = await db.get(AuditNotificationLetter, anl_id)
            run = await db.get(AgentRun, run_id)
            anl.status = "not_started"
            run.status = "failed"
            run.raw_output = f"Drafter error: {exc}"
            await db.commit()
