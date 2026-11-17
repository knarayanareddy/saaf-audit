"""Interview Agent v2 + live Companion — endpoints.

Opt-in and human-in-the-loop. The persona guide and the companion both run as
background tasks; the frontend polls for status. Minutes export goes through the
authenticated client like every other document.
"""
import json
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.interview import InterviewGuide, InterviewSession
from services.interview_v2_service import generate_guide, run_companion
from services.agent_ledger import attributed

router = APIRouter()


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _serialize_guide(g: InterviewGuide) -> dict:
    return {
        "status": g.status,
        "personas": _loads(g.personas, []),
        "coverage": _loads(g.coverage, None),
    }


def _serialize_session(s: InterviewSession) -> dict:
    return {
        "id": s.id,
        "persona": s.persona,
        "label": s.label,
        "notes": s.notes or "",
        "status": s.status,
        "analysis": _loads(s.analysis, None),
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ── Persona guide ───────────────────────────────────────────────────────────────

@router.get("/planning/{engagement_id}/interview/guide")
async def get_guide(engagement_id: str, db: AsyncSession = Depends(get_db)):
    g = (await db.execute(select(InterviewGuide).where(InterviewGuide.engagement_id == engagement_id))).scalar_one_or_none()
    if not g:
        return {"status": "not_started", "personas": [], "coverage": None}
    return _serialize_guide(g)


@router.post("/planning/{engagement_id}/interview/guide")
async def build_guide(engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    g = (await db.execute(select(InterviewGuide).where(InterviewGuide.engagement_id == engagement_id))).scalar_one_or_none()
    if not g:
        g = InterviewGuide(id=str(uuid4()), engagement_id=engagement_id)
        db.add(g)
    g.status = "running"
    await db.commit()
    background_tasks.add_task(attributed(generate_guide, engagement_id, "interview_guide"), g.id, engagement_id)
    return {"status": "running"}


# ── Companion sessions ──────────────────────────────────────────────────────────

@router.get("/planning/{engagement_id}/interview/sessions")
async def list_sessions(engagement_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(InterviewSession).where(InterviewSession.engagement_id == engagement_id).order_by(InterviewSession.created_at)
    )).scalars().all()
    return [_serialize_session(s) for s in rows]


@router.post("/planning/{engagement_id}/interview/sessions")
async def create_session(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    s = InterviewSession(
        id=str(uuid4()),
        engagement_id=engagement_id,
        persona=payload.get("persona"),
        label=payload.get("label"),
        notes=payload.get("notes", ""),
    )
    db.add(s)
    await db.commit()
    return _serialize_session(s)


@router.patch("/planning/{engagement_id}/interview/sessions/{session_id}")
async def update_session(engagement_id: str, session_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    s = await db.get(InterviewSession, session_id)
    if not s or s.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Session not found")
    for k in ("persona", "label", "notes"):
        if k in payload:
            setattr(s, k, payload[k])
    await db.commit()
    return _serialize_session(s)


@router.delete("/planning/{engagement_id}/interview/sessions/{session_id}")
async def delete_session(engagement_id: str, session_id: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(InterviewSession, session_id)
    if not s or s.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(s)
    await db.commit()
    return {"deleted": True}


@router.post("/planning/{engagement_id}/interview/sessions/{session_id}/analyse")
async def analyse_session(engagement_id: str, session_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    s = await db.get(InterviewSession, session_id)
    if not s or s.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Session not found")
    s.status = "analysing"
    await db.commit()
    background_tasks.add_task(attributed(run_companion, engagement_id, "interview_companion"), session_id, engagement_id)
    return {"status": "analysing"}


@router.get("/planning/{engagement_id}/interview/sessions/{session_id}/minutes")
async def export_minutes(engagement_id: str, session_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    s = await db.get(InterviewSession, session_id)
    if not eng or not s or s.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Session not found")

    import asyncio
    from services.word_export import generate_minutes_docx
    eng_data = {"name": eng.name, "audit_code": eng.audit_code, "entity": eng.entity}
    session_data = _serialize_session(s)
    docx_bytes = await asyncio.get_event_loop().run_in_executor(None, generate_minutes_docx, session_data, eng_data)
    safe = (eng.audit_code or eng.name[:20].replace(" ", "-"))
    filename = f"Interview-Minutes-{safe}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
