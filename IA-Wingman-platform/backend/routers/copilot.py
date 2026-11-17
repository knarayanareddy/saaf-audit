"""Audit Copilot — chat history, proposal lifecycle, the manual "run this
stage" dispatch, and the autonomous-run task queue (services/copilot_orchestrator.py).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.copilot import CopilotTask
from services import copilot_service, copilot_orchestrator
from services.stage_actions import AUDITOR_STARTED_STAGE_KEYS, STAGE_RUN_ACTIONS

router = APIRouter()


@router.get("/copilot/ready-for-review-counts")
async def get_ready_for_review_counts(db: AsyncSession = Depends(get_db)):
    """{engagement_id: count} of ready_for_review copilot_tasks, across every
    engagement in one query — feeds the Daily Briefing's workload rule without
    an N+1 (one call per engagement) from the frontend."""
    rows = (await db.execute(
        select(CopilotTask.engagement_id, func.count(CopilotTask.id))
        .where(CopilotTask.status == "ready_for_review")
        .group_by(CopilotTask.engagement_id)
    )).all()
    return {eid: count for eid, count in rows}


@router.get("/copilot/{engagement_id}/messages")
async def get_copilot_messages(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Persisted chat history for this engagement's copilot thread — lets the
    panel restore the conversation after a refresh instead of starting empty."""
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    return await copilot_service.list_messages(engagement_id)


class ProposalStatusUpdate(BaseModel):
    status: str


@router.patch("/copilot/proposals/{proposal_id}")
async def update_proposal_status(proposal_id: str, payload: ProposalStatusUpdate):
    """The human accepted or dismissed a proposal — persist that so it survives
    a refresh instead of only living in React state. Executing the proposal's
    actual side effect (creating the engagement, running the stage, ...) is a
    separate call the frontend makes alongside this one."""
    if payload.status not in ("accepted", "dismissed"):
        raise HTTPException(status_code=422, detail="status must be 'accepted' or 'dismissed'")
    result = await copilot_service.set_proposal_status(proposal_id, payload.status)
    if not result:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return result


@router.post("/copilot/{engagement_id}/stages/{stage_key}/run")
async def run_stage(
    engagement_id: str, stage_key: str, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a stage's AI drafting/analysis step — what accepting a
    propose_run_stage chat proposal calls. Goes through copilot_orchestrator's
    run_stage_now rather than calling the STAGE_RUN_ACTIONS handler directly,
    so a manual run gets a CopilotTask (and therefore shows up in Ready for
    Review once done, and is protected against double-firing if auto-fire
    already grabbed the same stage) exactly like an auto-fired one does."""
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    if stage_key in AUDITOR_STARTED_STAGE_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"'{stage_key}' is started by the auditor on its own page, after adding what they know — not from chat.",
        )
    if stage_key not in STAGE_RUN_ACTIONS:
        raise HTTPException(status_code=422, detail=f"Stage '{stage_key}' has no run action")
    return await copilot_orchestrator.run_stage_now(engagement_id, stage_key, background_tasks, triggered_by="chat")


@router.get("/copilot/{engagement_id}/tasks")
async def get_copilot_tasks(
    engagement_id: str, background_tasks: BackgroundTasks, status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """The autonomous-run queue — 'ready_for_review' rows are the batch the
    auditor reviews. Also re-scans for newly-eligible Planning stages, since
    the frontend polls this while the panel is open — a low-friction second
    trigger point alongside the one on every chat turn."""
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not await copilot_service.is_autonomy_paused(engagement_id):
        await copilot_orchestrator.scan_and_queue(engagement_id, background_tasks)
        await copilot_orchestrator.scan_and_queue_items(engagement_id, background_tasks)
    return await copilot_service.list_tasks(engagement_id, status)


class TaskStatusUpdate(BaseModel):
    status: str


@router.patch("/copilot/tasks/{task_id}")
async def update_task_status(task_id: str, payload: TaskStatusUpdate):
    """The auditor acknowledged (or dismissed) a ready-for-review card. This
    only manages the review queue's inbox state — the drafted content itself
    already landed in the stage's own artifact table and is edited there."""
    if payload.status not in ("reviewed", "dismissed"):
        raise HTTPException(status_code=422, detail="status must be 'reviewed' or 'dismissed'")
    result = await copilot_service.set_task_status(task_id, payload.status)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


class AutonomyUpdate(BaseModel):
    paused: bool


@router.patch("/copilot/{engagement_id}/autonomy")
async def update_autonomy(engagement_id: str, payload: AutonomyUpdate):
    """The kill switch — every reactive auto-fire trigger point checks this
    first. Pausing never touches in-flight tasks, it only stops new ones from
    being queued."""
    result = await copilot_service.set_autonomy_paused(engagement_id, payload.paused)
    if not result:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return result
