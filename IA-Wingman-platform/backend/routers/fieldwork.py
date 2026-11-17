"""Fieldwork endpoints: Observations (findings, recommendations, good practice, improvements).

How the screen works:
- Fieldwork unlocks when Work Program is signed off
- Observations tab shows findings pre-populated from Process Understanding preliminary observations
- 4 tabs: Findings | Recommendations | Good Practice | Ongoing Improvement
- Each observation: Title | Source badge | Criteria | Detailed observation | Root cause | Risk
- AI badge on AI-generated observations
"""
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.planning import FieldworkObservation, ProcessNotes, WorkProgram

router = APIRouter()

OBS_TYPES = {"finding", "recommendation", "good_practice", "improvement"}


def _serialize(obs: FieldworkObservation) -> dict:
    return {
        "id": obs.id,
        "obs_type": obs.obs_type,
        "title": obs.title,
        "source": obs.source,
        "criteria": obs.criteria,
        "detailed_observation": obs.detailed_observation,
        "root_cause": obs.root_cause,
        "risk": obs.risk,
        "linked_wp_row_id": obs.linked_wp_row_id,
        "is_ai_generated": obs.is_ai_generated,
        "sort_order": obs.sort_order,
    }


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


@router.get("/fieldwork/{engagement_id}/observations")
async def list_observations(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """List all observations grouped by type."""
    result = await db.execute(
        select(FieldworkObservation)
        .where(FieldworkObservation.engagement_id == engagement_id)
        .order_by(FieldworkObservation.sort_order, FieldworkObservation.created_at)
    )
    obs = result.scalars().all()

    # Check if fieldwork is unlocked (work program signed off)
    wp_res = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = wp_res.scalar_one_or_none()
    fieldwork_unlocked = wp is not None and wp.status == "signed_off"

    grouped = {t: [] for t in ["finding", "recommendation", "good_practice", "improvement"]}
    for o in obs:
        if o.obs_type in grouped:
            grouped[o.obs_type].append(_serialize(o))

    return {
        "fieldwork_unlocked": fieldwork_unlocked,
        "total": len(obs),
        "findings": grouped["finding"],
        "recommendations": grouped["recommendation"],
        "good_practices": grouped["good_practice"],
        "improvements": grouped["improvement"],
    }


@router.post("/fieldwork/{engagement_id}/observations/seed-from-planning")
async def seed_from_planning(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Pre-populate observations from Process Understanding preliminary observations."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    pn_res = await db.execute(
        select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id)
    )
    pn = pn_res.scalar_one_or_none()
    prelim = _loads(pn.preliminary_observations if pn else None, [])

    # Skip if already seeded
    existing = await db.execute(
        select(FieldworkObservation).where(
            FieldworkObservation.engagement_id == engagement_id,
            FieldworkObservation.source == "Process Understanding",
        )
    )
    if existing.scalars().first():
        return {"seeded": 0, "message": "Already seeded from Process Understanding"}

    seeded = 0
    for i, obs_data in enumerate(prelim):
        text = obs_data.get("text", "") if isinstance(obs_data, dict) else str(obs_data)
        if not text.strip():
            continue
        db.add(FieldworkObservation(
            id=str(uuid4()),
            engagement_id=engagement_id,
            obs_type="finding",
            title=text[:120],
            source="Process Understanding",
            detailed_observation=text,
            is_ai_generated=True,
            sort_order=i,
        ))
        seeded += 1

    await db.commit()
    return {"seeded": seeded}


@router.post("/fieldwork/{engagement_id}/observations")
async def create_observation(
    engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)
):
    obs_type = payload.get("obs_type", "finding")
    if obs_type not in OBS_TYPES:
        raise HTTPException(status_code=400, detail=f"obs_type must be one of {OBS_TYPES}")
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    # Get current max sort order
    res = await db.execute(
        select(FieldworkObservation)
        .where(FieldworkObservation.engagement_id == engagement_id)
        .order_by(FieldworkObservation.sort_order.desc())
    )
    last = res.scalars().first()
    sort_order = (last.sort_order + 1) if last else 0

    obs = FieldworkObservation(
        id=str(uuid4()),
        engagement_id=engagement_id,
        obs_type=obs_type,
        title=title[:500],
        source=payload.get("source", "Manual"),
        criteria=payload.get("criteria"),
        detailed_observation=payload.get("detailed_observation"),
        root_cause=payload.get("root_cause"),
        risk=payload.get("risk"),
        linked_wp_row_id=payload.get("linked_wp_row_id"),
        is_ai_generated=False,
        sort_order=sort_order,
    )
    db.add(obs)
    await db.commit()
    return _serialize(obs)


@router.patch("/fieldwork/{engagement_id}/observations/{obs_id}")
async def update_observation(
    engagement_id: str, obs_id: str, payload: dict, db: AsyncSession = Depends(get_db)
):
    obs = await db.get(FieldworkObservation, obs_id)
    if not obs or obs.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Observation not found")

    editable = {"title", "obs_type", "source", "criteria", "detailed_observation",
                "root_cause", "risk", "linked_wp_row_id"}
    for key in editable:
        if key in payload:
            val = payload[key]
            if key == "obs_type" and val not in OBS_TYPES:
                continue
            setattr(obs, key, val[:500] if isinstance(val, str) and key == "title" else val)
    await db.commit()
    return _serialize(obs)


@router.delete("/fieldwork/{engagement_id}/observations/{obs_id}")
async def delete_observation(
    engagement_id: str, obs_id: str, db: AsyncSession = Depends(get_db)
):
    obs = await db.get(FieldworkObservation, obs_id)
    if not obs or obs.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Observation not found")
    await db.delete(obs)
    await db.commit()
    return {"ok": True}
