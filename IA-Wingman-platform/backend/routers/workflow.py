from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.workflow_service import method_map, engagement_workflow

router = APIRouter()


@router.get("/workflow/method")
async def workflow_method():
    """The audit lifecycle as a graph — phases, stages, gates and where the
    auditor decides. No engagement and no database: the method overview."""
    return method_map()


@router.get("/workflow/{engagement_id}")
async def workflow_for_engagement(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """The same graph with this engagement's live state. Deterministic and
    read-only — it never queues copilot work, so it is safe to poll."""
    wf = await engagement_workflow(engagement_id, db)
    if wf is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return wf
