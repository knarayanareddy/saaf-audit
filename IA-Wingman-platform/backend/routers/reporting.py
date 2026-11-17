"""Reporting phase — endpoints.

Findings (5C) + audit report. The 5C drafter and the report drafter are opt-in
AI, run as background tasks; everything is a proposal the auditor edits and signs.
Report export goes through the authenticated client like every other document.
"""
import json
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.reporting import Finding, AuditReport
from models.planning import FieldworkObservation
from services.finding_drafter import draft_finding, RATINGS
from services.report_drafter import draft_report
from services.explainability_annex import assemble as assemble_annex, sharpen_finding_annex
from services.grounded_validator import assemble as assemble_validation, judge_finding_task
from services.agent_ledger import attributed

router = APIRouter()


def _loads(raw, default=None):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _finding(f: Finding) -> dict:
    return {
        "id": f.id, "title": f.title, "source_observation_id": f.source_observation_id,
        "condition": f.condition, "criteria": f.criteria, "cause": f.cause,
        "effect": f.effect, "recommendation": f.recommendation,
        "rating": f.rating, "rating_rationale": f.rating_rationale,
        "rating_challenge": _loads(f.rating_challenge), "status": f.status,
        "sort_order": f.sort_order,
    }


def _report(r: AuditReport) -> dict:
    return {
        "overall_opinion": r.overall_opinion, "exec_summary": r.exec_summary,
        "conclusion": r.conclusion, "status": r.status,
    }


# ── Findings ─────────────────────────────────────────────────────────────────────

@router.get("/reporting/{engagement_id}/findings")
async def list_findings(engagement_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id).order_by(Finding.sort_order, Finding.created_at)
    )).scalars().all()
    return [_finding(f) for f in rows]


@router.post("/reporting/{engagement_id}/findings/seed-from-fieldwork")
async def seed_from_fieldwork(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Create findings from fieldwork 'finding' observations (idempotent per source obs)."""
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    obs = (await db.execute(
        select(FieldworkObservation).where(
            FieldworkObservation.engagement_id == engagement_id,
            FieldworkObservation.obs_type == "finding",
        ).order_by(FieldworkObservation.sort_order)
    )).scalars().all()
    existing = (await db.execute(select(Finding).where(Finding.engagement_id == engagement_id))).scalars().all()
    seeded_ids = {f.source_observation_id for f in existing if f.source_observation_id}

    seeded = 0
    base = len(existing)
    for i, o in enumerate(obs):
        if o.id in seeded_ids:
            continue
        db.add(Finding(
            id=str(uuid4()), engagement_id=engagement_id, source_observation_id=o.id,
            title=o.title, condition=o.detailed_observation, criteria=o.criteria,
            cause=o.root_cause, effect=o.risk, sort_order=base + i,
        ))
        seeded += 1
    await db.commit()
    return {"seeded": seeded}


@router.post("/reporting/{engagement_id}/findings")
async def create_finding(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")
    last = (await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id).order_by(Finding.sort_order.desc())
    )).scalars().first()
    f = Finding(
        id=str(uuid4()), engagement_id=engagement_id, title=title[:500],
        condition=payload.get("condition"), criteria=payload.get("criteria"),
        cause=payload.get("cause"), effect=payload.get("effect"),
        recommendation=payload.get("recommendation"), rating=payload.get("rating"),
        sort_order=(last.sort_order + 1) if last else 0,
    )
    db.add(f)
    await db.commit()
    return _finding(f)


@router.patch("/reporting/{engagement_id}/findings/{finding_id}")
async def update_finding(engagement_id: str, finding_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    f = await db.get(Finding, finding_id)
    if not f or f.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    for k in ("title", "condition", "criteria", "cause", "effect", "recommendation", "rating_rationale"):
        if k in payload:
            setattr(f, k, payload[k])
    if "rating" in payload and payload["rating"] in RATINGS:
        f.rating = payload["rating"]
    await db.commit()
    return _finding(f)


@router.delete("/reporting/{engagement_id}/findings/{finding_id}")
async def delete_finding(engagement_id: str, finding_id: str, db: AsyncSession = Depends(get_db)):
    f = await db.get(Finding, finding_id)
    if not f or f.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    await db.delete(f)
    await db.commit()
    return {"deleted": True}


@router.post("/reporting/{engagement_id}/findings/{finding_id}/draft")
async def draft_finding_ai(engagement_id: str, finding_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    f = await db.get(Finding, finding_id)
    if not f or f.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    f.status = "drafting"
    await db.commit()
    background_tasks.add_task(attributed(draft_finding, engagement_id, "findings"), finding_id, engagement_id)
    return {"status": "drafting"}


# ── Explainability annex ───────────────────────────────────────────────────────────

@router.get("/reporting/{engagement_id}/findings/{finding_id}/explainability")
async def get_explainability(engagement_id: str, finding_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministically (re)build the finding's explainability annex from the
    current 5C + RACM spine. Any persisted AI-sharpened answers are overlaid."""
    f = await db.get(Finding, finding_id)
    if not f or f.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return await assemble_annex(db, f)


@router.post("/reporting/{engagement_id}/findings/{finding_id}/explainability/sharpen")
async def sharpen_explainability(engagement_id: str, finding_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Opt-in: rephrase the annex answers with one AI call (no new facts). The
    deterministic scaffold is kept if the call fails."""
    f = await db.get(Finding, finding_id)
    if not f or f.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    background_tasks.add_task(attributed(sharpen_finding_annex, engagement_id, "findings"), finding_id, engagement_id)
    return {"status": "sharpening"}


@router.get("/reporting/{engagement_id}/findings/{finding_id}/validation")
async def get_validation(engagement_id: str, finding_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministic grounded pre-screen of the finding's claims against the source
    (free), with any persisted AI judge verdicts overlaid."""
    f = await db.get(Finding, finding_id)
    if not f or f.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return await assemble_validation(db, f)


@router.post("/reporting/{engagement_id}/findings/{finding_id}/validation/judge")
async def judge_validation(engagement_id: str, finding_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Opt-in: one AI judge call re-reads the source per claim (verbatim-verified).
    The deterministic pre-screen is kept if the call fails."""
    f = await db.get(Finding, finding_id)
    if not f or f.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    background_tasks.add_task(attributed(judge_finding_task, engagement_id, "findings"), finding_id, engagement_id)
    return {"status": "judging"}


# ── Report ───────────────────────────────────────────────────────────────────────

@router.get("/reporting/{engagement_id}/report")
async def get_report(engagement_id: str, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
    if not r:
        return {"status": "not_started", "overall_opinion": None, "exec_summary": None, "conclusion": None}
    return _report(r)


@router.post("/reporting/{engagement_id}/report/draft")
async def draft_report_ai(engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    r = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
    if not r:
        r = AuditReport(id=str(uuid4()), engagement_id=engagement_id)
        db.add(r)
    r.status = "drafting"
    await db.commit()
    background_tasks.add_task(attributed(draft_report, engagement_id, "report_draft"), engagement_id)
    return {"status": "drafting"}


@router.patch("/reporting/{engagement_id}/report")
async def update_report(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
    if not r:
        r = AuditReport(id=str(uuid4()), engagement_id=engagement_id)
        db.add(r)
    for k in ("overall_opinion", "exec_summary", "conclusion"):
        if k in payload:
            setattr(r, k, payload[k])
    await db.commit()
    return _report(r)


@router.get("/reporting/{engagement_id}/report/export-word")
async def export_report_word(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    r = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="No report yet")
    findings = (await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id).order_by(Finding.sort_order)
    )).scalars().all()

    import asyncio
    from functools import partial
    from services.word_export import generate_report_docx
    eng_data = {"name": eng.name, "audit_code": eng.audit_code, "entity": eng.entity}
    report_data = _report(r)
    findings_data = [_finding(f) for f in findings]
    # Assemble the explainability annex for each finding (deterministic; no AI).
    annexes = []
    for f in findings:
        annex = await assemble_annex(db, f)
        annex["title"] = f.title
        annexes.append(annex)
    docx_bytes = await asyncio.get_event_loop().run_in_executor(
        None, partial(generate_report_docx, report_data, findings_data, eng_data, annexes)
    )
    safe = (eng.audit_code or eng.name[:20].replace(" ", "-"))
    filename = f"Audit-Report-{safe}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
