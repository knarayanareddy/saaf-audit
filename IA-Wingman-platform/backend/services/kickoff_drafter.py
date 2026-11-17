"""Kick-off Agenda Drafter — generates prepared notes for each agenda section."""
import json

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from services.auditee_context import load as load_auditee_context
from models.agent_run import AgentRun
from models.planning import KickoffAgenda, TopicIntelligence, ScopeObjectives, ScopeItem, ApplicableFramework
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


async def run_kickoff_drafter(agenda_id: str, run_id: str, engagement_id: str):
    """Generates kick-off meeting preparation notes. Owns its own DB sessions."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        agenda = await db.get(KickoffAgenda, agenda_id)
        run.status = "running"
        await db.commit()

        ctx = await load_auditee_context(db, engagement_id)

    in_scope, out_scope = ctx.in_scope, ctx.out_of_scope
    frameworks = ctx.frameworks
    ti_summary = ctx.ti_summary
    ti_key_risks = ctx.ti_key_risks
    interview_prework = ctx.ia_prework
    sponsor_questions = ctx.sponsor_questions

    user_prompt = f"""Prepare structured notes for a kick-off meeting for this the organisation internal audit.

ENGAGEMENT: {eng.name} ({eng.entity}, {eng.audit_type})
AUDIT CODE: {eng.audit_code or 'TBD'}
SCOPE PERIOD: {eng.scope_period or 'TBD'}
LEAD AUDITOR: {eng.lead_auditor or 'TBD'}

REGULATORY CONTEXT:
{ti_summary[:800] if ti_summary else 'Not yet completed.'}

KEY RISK AREAS:
{chr(10).join(f'- {r.get("title","")}' for r in ti_key_risks) or 'See regulatory context.'}

SCOPE:
In scope: {', '.join(in_scope) or 'TBD'}
Out of scope: {', '.join(out_scope) or 'TBD'}

APPLICABLE FRAMEWORKS:
{', '.join(frameworks) or 'TBD'}

IA PRE-WORK STILL TO DO (tasks Topic Intelligence proposed for the audit team; none of them is done yet, so do not describe them as completed):
{chr(10).join(f'- {p}' for p in interview_prework) or 'None proposed.'}

QUESTIONS THE TOPIC MEMO PROPOSES FOR THE SPONSOR (the auditor ticked these):
{chr(10).join(f'- {q}' for q in sponsor_questions) or 'None.'}

Prepare concise, specific talking points for each agenda section of the kick-off meeting.
These are notes FOR the internal audit team to use DURING the meeting — not minutes.

WRITE LIKE A COPY-WRITER. Every "notes_*" value MUST be scannable, never one dense paragraph:
- Start with ONE short lead sentence.
- Then 3-5 bullet lines, each on its OWN line, each starting with "- ".
- Separate the lines with newline characters (\n) inside the JSON string.
- Keep each bullet short, concrete and specific. No walls of text.

Produce ONLY a JSON object with these exact keys:
{{
  "audit_purpose": "2-3 sentences in plain language: what this audit is FOR and what it aims to achieve — the 'why'. This is one of the first things a kick-off must settle.",
  "questions_for_auditor": ["5-8 specific questions the IA team should ask the auditor/sponsor at kick-off to clarify intent, expectations, scope boundaries, key risks, constraints and success criteria. Start with the sponsor questions listed above, worded as given, then add your own up to 8 in total"],
  "notes_welcome": "Opening script: confirm attendees, state purpose, confirm confidentiality if needed.",
  "notes_context": "Key points about why this audit is in the 2026 plan, budget hours, audit objective in plain language.",
  "notes_documentation": "List the specific documents and info the IA team has already gathered. Reference specific reports, previous audit findings, supervisory letters, ICS results that are relevant.",
  "notes_missing": "What specific documents or information are still needed from the auditee? Be specific — e.g. 'Q4 2025 AML exception report', 'process flow for EDD onboarding'.",
  "notes_scope": "Summary of in-scope subjects and why. Mention how fraud risk triangle is considered. Note how ESG relates to this audit. Confirm if budget (hours) is realistic given scope.",
  "notes_risks": "Key inherent risks for this audit area. Note control environment expectations. Specify detection risk considerations.",
  "notes_team": "Team composition, role assignments, independence considerations, key dates for planning milestones.",
  "notes_other": "Data analysis opportunities (if any). IT tools to be used. Any confidentiality or access restrictions to flag.",
  "notes_aob": "Open questions to raise with auditee.",
  "notes_next_steps": "Specific action items with owners. Confirm next coordination meeting date."
}}

Be specific and practical — these notes should actually prepare the team for the meeting."""

    try:
        result = await run_agent_to_json(BASE_SYSTEM_PROMPT, user_prompt, max_tokens=4000)

        async with AsyncSessionLocal() as db:
            agenda = await db.get(KickoffAgenda, agenda_id)
            run = await db.get(AgentRun, run_id)

            for field in ("notes_welcome", "notes_context", "notes_documentation", "notes_missing",
                          "notes_scope", "notes_risks", "notes_team", "notes_other", "notes_aob", "notes_next_steps"):
                setattr(agenda, field, result.get(field, ""))

            agenda.audit_purpose = result.get("audit_purpose", "")
            agenda.questions_for_auditor = json.dumps(result.get("questions_for_auditor", []))

            agenda.status = "draft_ready"
            run.status = "complete"
            run.raw_output = json.dumps(result)
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            agenda = await db.get(KickoffAgenda, agenda_id)
            run = await db.get(AgentRun, run_id)
            agenda.status = "not_started"
            run.status = "failed"
            run.raw_output = f"Error: {exc}"
            await db.commit()
