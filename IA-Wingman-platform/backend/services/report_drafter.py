"""Report drafter — assembles an executive summary, overall opinion and
conclusion from the engagement's findings. Human-in-the-loop: the auditor edits
and signs. Grounded strictly in the accepted findings, never invents issues.
"""
import json

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.reporting import Finding, AuditReport
from services.model_tiers import JUDGE
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services.activity_service import log_activity

OPINIONS = ("satisfactory", "needs_improvement", "unsatisfactory")

REPORT_SYSTEM = BASE_SYSTEM_PROMPT + """

REPORT-DRAFTER ROLE:
You draft the executive summary and conclusion of an internal-audit report from the list of findings provided.
Be balanced and evidence-based: reflect the actual severity mix, do not inflate or downplay. The overall
opinion must follow from the findings. Neutral, professional tone. Do not introduce findings that are not in
the list. The auditor edits and signs off — you propose.
"""


async def draft_report(engagement_id: str):
    """Assemble exec summary + opinion + conclusion from findings. Owns sessions."""
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        findings = (await db.execute(
            select(Finding).where(Finding.engagement_id == engagement_id).order_by(Finding.sort_order)
        )).scalars().all()
        items = [
            {"title": f.title, "rating": f.rating or "medium", "effect": f.effect or "", "recommendation": f.recommendation or ""}
            for f in findings
        ]

    if not items:
        async with AsyncSessionLocal() as db:
            r = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
            if r:
                r.status = "ready"
                r.exec_summary = "No findings recorded yet — add and draft findings first."
                await db.commit()
        return

    counts = {lvl: sum(1 for i in items if i["rating"] == lvl) for lvl in ("high", "medium", "low")}
    findings_txt = "\n".join(f"- [{i['rating'].upper()}] {i['title']} — effect: {i['effect']}" for i in items)

    prompt = f"""Draft the executive summary and conclusion for the internal-audit report of "{eng.name}" ({eng.entity}, {eng.audit_type}).

FINDINGS ({counts['high']} high, {counts['medium']} medium, {counts['low']} low):
{findings_txt}

Return ONLY a JSON object:
{{
  "overall_opinion": "satisfactory|needs_improvement|unsatisfactory",
  "exec_summary": "3-5 sentence executive summary reflecting the severity mix",
  "conclusion": "2-3 sentence balanced conclusion"
}}
The opinion must follow from the findings: any high finding generally precludes 'satisfactory'."""

    try:
        # The overall audit opinion is the one sentence the board reads. Nobody
        # downstream re-derives it, which is the definition of the judge tier.
        result = await run_agent_to_json(REPORT_SYSTEM, prompt, max_tokens=1500, tier=JUDGE)
        opinion = result.get("overall_opinion") if isinstance(result, dict) else None
        if opinion not in OPINIONS:
            opinion = "needs_improvement" if counts["high"] or counts["medium"] else "satisfactory"
        async with AsyncSessionLocal() as db:
            r = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
            if r:
                r.overall_opinion = opinion
                r.exec_summary = result.get("exec_summary", "") if isinstance(result, dict) else ""
                r.conclusion = result.get("conclusion", "") if isinstance(result, dict) else ""
                r.status = "ready"
                await db.commit()
        await log_activity(
            engagement_id, "report_drafter", "report_ready",
            summary=f"Drafted audit report — opinion '{opinion}', {len(items)} finding(s)",
            confidence=None,
        )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            r = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
            if r:
                r.status = "failed"
                r.exec_summary = f"Report draft failed: {exc}"
                await db.commit()
