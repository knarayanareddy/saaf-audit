"""Audit Memory — endpoints.

Deterministic recall of cross-engagement precedents is free. Adopting a precedent
writes a PROPOSED RACM node (origin='ai', accepted=False) — the auditor confirms.
The AI synthesis is opt-in.
"""
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.racm import RacmRisk, RacmControl
from services.audit_memory import recall as memory_recall, synthesize as memory_synthesize

router = APIRouter()


@router.get("/memory/{engagement_id}/recall")
async def get_recall(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministically recall topic-matched precedents from other engagements."""
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    return await memory_recall(db, engagement_id)


@router.post("/memory/{engagement_id}/adopt")
async def adopt_precedent(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Adopt a risk/control precedent as a PROPOSED node in this engagement's spine."""
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    kind = payload.get("kind")
    title = (payload.get("title") or "").strip()
    if kind not in ("risk", "control") or not title:
        raise HTTPException(status_code=422, detail="kind must be risk|control and title is required")

    provenance = json.dumps({
        "source_type": "audit_memory",
        "source_ref": payload.get("source_ref") or "prior audit",
        "rationale": "Adopted from a prior-audit precedent; confirm relevance and detail.",
    })
    common = dict(id=str(uuid4()), engagement_id=engagement_id, origin="ai", accepted=False,
                  confidence="medium", provenance=provenance, title=title[:500],
                  description=payload.get("description"))
    if kind == "risk":
        node = RacmRisk(**common, category=payload.get("category"),
                        inherent_rating=payload.get("inherent_rating"))
    else:
        node = RacmControl(**common, control_type=payload.get("control_type"),
                           design_conclusion="not_assessed")
    db.add(node)
    await db.commit()
    await db.refresh(node)  # avoid MissingGreenlet on server-side onupdate columns
    return {"adopted": True, "kind": kind, "id": node.id, "title": node.title}


@router.post("/memory/{engagement_id}/synthesize")
async def synthesize_memory(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Opt-in: a short AI note on what prior audits found on this topic."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    result = await memory_recall(db, engagement_id)
    try:
        summary = await memory_synthesize(result, eng)
    except Exception:  # noqa: BLE001
        summary = "The AI summary could not be generated; the recalled precedents above are the source."
    return {"summary": summary}
