"""ANL Review agent — critiques a draft ANL for quality, completeness, and consistency."""
import json
from uuid import uuid4

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.engagement import Engagement
from models.planning import AuditNotificationLetter, TopicIntelligence
from sqlalchemy import select
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


REVIEW_SYSTEM = BASE_SYSTEM_PROMPT + """

REVIEW ROLE:
You are acting as a senior internal audit quality reviewer for the organisation. Your job is to review
a draft Audit Notification Letter (ANL) and identify specific issues the lead auditor must address
before the letter is approved by the Head of Internal Audit.

Be constructive, specific, and professional. Reference the relevant section and the exact issue.
Distinguish between must-fix issues (missing information, factual errors, regulatory inconsistencies)
and improvement suggestions (clarity, completeness, tone).
"""


async def run_anl_review_agent(anl_id: str, run_id: str, engagement_id: str):
    """Critiques the draft ANL. Owns its own DB sessions."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        anl = await db.get(AuditNotificationLetter, anl_id)
        run.status = "running"
        await db.commit()

        ti_res = await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))
        ti = ti_res.scalar_one_or_none()

    ti_summary = ti.regulatory_summary if ti else "(not available)"
    ti_key_risks = _loads(ti.key_risk_areas if ti else None, [])
    risk_titles = [r.get("title", "") for r in ti_key_risks]

    user_prompt = f"""Review the following draft Audit Notification Letter for the internal audit engagement:

ENGAGEMENT: {eng.name} | Entity: {eng.entity} | Type: {eng.audit_type}

=== DRAFT ANL ===

BACKGROUND:
{anl.background or '(empty — not drafted)'}

OBJECTIVES:
{anl.objectives or '(empty — not drafted)'}

SCOPE:
{anl.scope_description or '(empty — not drafted)'}

OUT OF SCOPE:
{anl.out_of_scope or '(empty — not drafted)'}

APPROACH:
{anl.approach or '(empty — not drafted)'}

TIMING:
Fieldwork: {anl.timing_fieldwork_start} to {anl.timing_fieldwork_end}
Draft report by: {anl.timing_draft_report or 'TBD'}
Management response by: {anl.timing_mgmt_response or 'TBD'}
Final report by: {anl.timing_final_report or 'TBD'}

RESPONSIBILITY:
{anl.responsibility or '(empty — not drafted)'}

=== REGULATORY CONTEXT ===
Key regulatory summary: {ti_summary[:1000] if ti_summary else 'Not available'}
Key risk areas identified: {', '.join(risk_titles) or 'Not available'}

=== REVIEW CRITERIA ===
Check each section against these criteria:
1. BACKGROUND: Does it clearly explain WHY this audit is in the plan? Does it link to strategic themes or regulatory requirements? Is it specific to the organisation's context?
2. OBJECTIVES: Is it clear and measurable? Does it use proper IIA assurance language? Is it consistent with the regulatory context?
3. SCOPE: Are all key risk areas from the regulatory analysis covered? Is the scope period mentioned? Are specific controls or processes named?
4. OUT OF SCOPE: Is there a rationale for each exclusion? Are major topics that a reader might expect to see audited explained?
5. APPROACH: Are the methodology steps logical and complete? Is the IIA framework referenced? Are specific regulatory requirements mentioned in the approach?
6. TIMING: Are all dates filled in? Is the timeline realistic?
7. RESPONSIBILITY: Is it clear what the auditee must provide? Is the tone appropriate?

Produce ONLY a JSON object with this structure:
{{
  "overall_quality": "good|adequate|needs_work",
  "summary": "2-3 sentence overall assessment for the lead auditor",
  "comments": [
    {{
      "id": "c1",
      "section": "background|objectives|scope|out_of_scope|approach|timing|responsibility",
      "severity": "must_fix|suggestion",
      "comment": "Specific, actionable comment explaining the issue and how to fix it",
      "is_accepted": false,
      "is_dismissed": false
    }}
  ]
}}

Only include comments where there is a genuine issue. Do not manufacture minor stylistic comments.
A well-written ANL may have 2-4 must_fix and 2-3 suggestions. Maximum 10 comments total."""

    try:
        result = await run_agent_to_json(REVIEW_SYSTEM, user_prompt, max_tokens=3000)
        comments = result.get("comments", [])
        for c in comments:
            c.setdefault("id", str(uuid4())[:8])
            c.setdefault("is_accepted", False)
            c.setdefault("is_dismissed", False)

        async with AsyncSessionLocal() as db:
            anl = await db.get(AuditNotificationLetter, anl_id)
            run = await db.get(AgentRun, run_id)
            anl.review_comments = json.dumps(comments)
            anl.status = "reviewed" if not comments else "draft_ready"  # stays draft_ready if there are comments
            # Actually: always set to reviewed state so human sees the comments
            anl.status = "reviewed"
            run.status = "complete"
            run.raw_output = json.dumps(result)
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            anl = await db.get(AuditNotificationLetter, anl_id)
            run = await db.get(AgentRun, run_id)
            anl.status = "draft_ready"  # revert to draft_ready so user can retry
            run.status = "failed"
            run.raw_output = f"Review error: {exc}"
            await db.commit()
