import json
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.planning import AuditNotificationLetter, TopicIntelligence, ScopeObjectives, ScopeItem, ApplicableFramework
from schemas import ANLPatch
from services.progress_service import anl_progress
from services.agent_ledger import attributed

router = APIRouter()


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def serialize_anl(anl: AuditNotificationLetter) -> dict:
    return {
        "id": anl.id,
        "engagement_id": anl.engagement_id,
        "status": anl.status,
        "background": anl.background,
        "objectives": anl.objectives,
        "scope_description": anl.scope_description,
        "out_of_scope": anl.out_of_scope,
        "approach": anl.approach,
        "timing_fieldwork_start": anl.timing_fieldwork_start,
        "timing_fieldwork_end": anl.timing_fieldwork_end,
        "timing_draft_report": anl.timing_draft_report,
        "timing_mgmt_response": anl.timing_mgmt_response,
        "timing_final_report": anl.timing_final_report,
        "responsibility": anl.responsibility,
        "review_comments": _loads(anl.review_comments, []),
        "head_ia_status": anl.head_ia_status,
        "head_ia_approved_at": anl.head_ia_approved_at.isoformat() if anl.head_ia_approved_at else None,
    }


@router.get("/planning/{engagement_id}/anl")
async def get_anl(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        return {"status": "not_started"}
    return serialize_anl(anl)


@router.patch("/planning/{engagement_id}/anl")
async def update_anl(engagement_id: str, payload: ANLPatch, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        raise HTTPException(status_code=404, detail="ANL not started")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(anl, k, v)
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/anl/draft")
async def draft_anl(engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        anl = AuditNotificationLetter(id=str(uuid4()), engagement_id=engagement_id)
        db.add(anl)

    run = AgentRun(
        id=str(uuid4()), engagement_id=engagement_id,
        agent_type="anl_drafter", status="pending",
    )
    db.add(run)
    anl.drafter_run_id = run.id
    anl.status = "drafting"
    await db.commit()

    background_tasks.add_task(attributed(_run_anl_drafter, engagement_id, "anl", run.id), anl.id, run.id, engagement_id)
    return {"run_id": run.id, "anl_id": anl.id}


@router.post("/planning/{engagement_id}/anl/review")
async def review_anl(engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl or anl.status not in ("draft_ready", "reviewed"):
        raise HTTPException(status_code=400, detail="ANL must be in draft_ready state before review")

    run = AgentRun(
        id=str(uuid4()), engagement_id=engagement_id,
        agent_type="anl_reviewer", status="pending",
    )
    db.add(run)
    anl.review_run_id = run.id
    anl.status = "review_pending"
    await db.commit()

    background_tasks.add_task(attributed(_run_anl_reviewer, engagement_id, "anl", run.id), anl.id, run.id, engagement_id)
    return {"run_id": run.id}


@router.post("/planning/{engagement_id}/anl/accept-reviews")
async def accept_reviews(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Human marks all pending review comments as reviewed and moves ANL to reviewed state."""
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        raise HTTPException(status_code=404, detail="ANL not found")
    anl.status = "reviewed"
    await db.commit()
    return {"ok": True}


@router.patch("/planning/{engagement_id}/anl/review-comments/{comment_id}")
async def update_review_comment(engagement_id: str, comment_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Accept or dismiss an individual AI review comment."""
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        raise HTTPException(status_code=404, detail="ANL not found")
    comments = _loads(anl.review_comments, [])
    for c in comments:
        if c.get("id") == comment_id:
            if "is_accepted" in payload:
                c["is_accepted"] = payload["is_accepted"]
            if "is_dismissed" in payload:
                c["is_dismissed"] = payload["is_dismissed"]
            break
    anl.review_comments = json.dumps(comments)
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/anl/submit-head-ia")
async def submit_for_head_ia(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        raise HTTPException(status_code=404, detail="ANL not found")
    anl.status = "head_ia_review"
    anl.head_ia_status = "in_review"
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/anl/head-ia-approve")
async def head_ia_approve(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        raise HTTPException(status_code=404, detail="ANL not found")
    anl.status = "approved"
    anl.head_ia_status = "approved"
    anl.head_ia_approved_at = datetime.utcnow()
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/anl/mark-sent")
async def mark_sent(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl or anl.status != "approved":
        raise HTTPException(status_code=400, detail="ANL must be approved before marking as sent")
    anl.status = "sent"
    await db.commit()
    return {"ok": True}


@router.get("/planning/{engagement_id}/anl/export-word")
async def export_anl_word(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Download the ANL as a filled the organisation Word document."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl:
        raise HTTPException(status_code=404, detail="ANL not started")

    import json as _json
    from services.word_export import generate_anl_docx
    eng_data = {
        "name": eng.name, "audit_code": eng.audit_code, "entity": eng.entity,
        "lead_auditor": eng.lead_auditor,
        "team_members": _json.loads(eng.team_members or "[]"),
        "scope_period": eng.scope_period,
    }
    anl_data = serialize_anl(anl)
    docx_bytes = await __import__("asyncio").get_event_loop().run_in_executor(
        None, generate_anl_docx, anl_data, eng_data
    )
    filename = f"ANL-{eng.audit_code or eng.name[:20].replace(' ','-')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Background task wrappers ──────────────────────────────────────────────────

async def _run_anl_drafter(anl_id: str, run_id: str, engagement_id: str):
    from services.anl_drafter import run_anl_drafter
    await run_anl_drafter(anl_id, run_id, engagement_id)


async def _run_anl_reviewer(anl_id: str, run_id: str, engagement_id: str):
    from services.anl_review_agent import run_anl_review_agent
    await run_anl_review_agent(anl_id, run_id, engagement_id)
