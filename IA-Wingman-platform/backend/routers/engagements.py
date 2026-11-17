import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from services.progress_service import planning_progress
from schemas import EngagementCreate, EngagementUpdate

router = APIRouter()


def serialize(e: Engagement) -> dict:
    return {
        "id": e.id,
        "audit_code": e.audit_code,
        "name": e.name,
        "entity": e.entity,
        "audit_type": e.audit_type,
        "summary": e.summary,
        "status": e.status,
        "lead_auditor": e.lead_auditor,
        "team_members": json.loads(e.team_members or "[]"),
        "planning_date": e.planning_date,
        "start_date": e.start_date,
        "end_date": e.end_date,
        "draft_report_date": e.draft_report_date,
        "final_report_date": e.final_report_date,
        "scope_period": e.scope_period,
        "jurisdictions": json.loads(e.jurisdictions) if e.jurisdictions else [],
        "copilot_autonomy_paused": bool(e.copilot_autonomy_paused),
    }


@router.get("/engagements")
async def list_engagements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Engagement).order_by(Engagement.entity, Engagement.name))
    return [serialize(e) for e in result.scalars().all()]


@router.get("/engagements/stats")
async def engagement_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Engagement))
    engagements = result.scalars().all()
    active_statuses = {"in_planning", "in_fieldwork", "in_reporting"}
    return {
        "total": len(engagements),
        "active": sum(1 for e in engagements if e.status in active_statuses),
        "in_planning": sum(1 for e in engagements if e.status == "in_planning"),
        "in_fieldwork": sum(1 for e in engagements if e.status == "in_fieldwork"),
        "in_reporting": sum(1 for e in engagements if e.status == "in_reporting"),
        "closed": sum(1 for e in engagements if e.status == "closed"),
        "to_be_scheduled": sum(1 for e in engagements if e.status == "to_be_scheduled"),
    }


@router.get("/engagements/{engagement_id}")
async def get_engagement(engagement_id: str, db: AsyncSession = Depends(get_db)):
    e = await db.get(Engagement, engagement_id)
    if not e:
        raise HTTPException(status_code=404, detail="Engagement not found")
    data = serialize(e)
    data["planning_progress"] = await planning_progress(engagement_id, db)
    return data


@router.post("/engagements", status_code=201)
async def create_engagement(payload: EngagementCreate, db: AsyncSession = Depends(get_db)):
    e = Engagement(
        id=str(uuid4()),
        audit_code=payload.audit_code,
        name=payload.name,
        entity=payload.entity,
        audit_type=payload.audit_type,
        summary=payload.summary,
        status=payload.status,
        lead_auditor=payload.lead_auditor,
        team_members=json.dumps(payload.team_members),
        planning_date=payload.planning_date,
        start_date=payload.start_date,
        end_date=payload.end_date,
        draft_report_date=payload.draft_report_date,
        final_report_date=payload.final_report_date,
        scope_period=payload.scope_period,
    )
    db.add(e)
    await db.commit()
    return serialize(e)


@router.patch("/engagements/{engagement_id}")
async def update_engagement(engagement_id: str, payload: EngagementUpdate, db: AsyncSession = Depends(get_db)):
    e = await db.get(Engagement, engagement_id)
    if not e:
        raise HTTPException(status_code=404, detail="Engagement not found")
    data = payload.model_dump(exclude_unset=True)
    if "team_members" in data and data["team_members"] is not None:
        data["team_members"] = json.dumps(data["team_members"])
    if "jurisdictions" in data and data["jurisdictions"] is not None:
        data["jurisdictions"] = json.dumps(data["jurisdictions"])
    for key, value in data.items():
        setattr(e, key, value)
    await db.commit()
    return serialize(e)


@router.delete("/engagements/{engagement_id}", status_code=204)
async def delete_engagement(engagement_id: str, db: AsyncSession = Depends(get_db)):
    e = await db.get(Engagement, engagement_id)
    if not e:
        raise HTTPException(status_code=404, detail="Engagement not found")
    await db.delete(e)
    await db.commit()
