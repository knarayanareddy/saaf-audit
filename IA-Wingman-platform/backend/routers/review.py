"""QA Reviewer + Coverage endpoints — agents that check the other agents."""
import json
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.ai_analysis import AiAnalysis
from services.review_service import run_quality_review, ARTIFACT_LABELS
from services.coverage_service import compute_coverage, recompute_coherence_signature
from services.agent_ledger import attributed

router = APIRouter()


def _serialize(a: AiAnalysis) -> dict:
    return {
        "kind": a.kind,
        "artifact": a.artifact,
        "status": a.status,
        "result": json.loads(a.result) if a.result else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


async def _get_analysis(db, engagement_id, kind, artifact):
    return (await db.execute(
        select(AiAnalysis).where(
            AiAnalysis.engagement_id == engagement_id,
            AiAnalysis.kind == kind,
            AiAnalysis.artifact == artifact,
        )
    )).scalar_one_or_none()


@router.post("/planning/{engagement_id}/review/{artifact}")
async def run_review(
    engagement_id: str, artifact: str, background_tasks: BackgroundTasks,
    phase: str = "total", db: AsyncSession = Depends(get_db),
):
    if artifact not in ARTIFACT_LABELS:
        raise HTTPException(status_code=422, detail="Unknown artifact")
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")

    a = await _get_analysis(db, engagement_id, "quality_review", artifact)
    if not a:
        a = AiAnalysis(id=str(uuid4()), engagement_id=engagement_id, kind="quality_review", artifact=artifact)
        db.add(a)
    a.status = "running"
    a.result = None
    await db.commit()

    # phase only applies to the peer review; other artifacts ignore it
    background_tasks.add_task(attributed(run_quality_review, engagement_id, "quality_review"),
                              a.id, engagement_id, artifact, phase)
    return {"status": "running", "artifact": artifact}


@router.get("/planning/{engagement_id}/review/{artifact}")
async def get_review(engagement_id: str, artifact: str, db: AsyncSession = Depends(get_db)):
    a = await _get_analysis(db, engagement_id, "quality_review", artifact)
    if not a:
        return {"kind": "quality_review", "artifact": artifact, "status": "not_run", "result": None}
    serialized = _serialize(a)

    # Coherence: recompute-and-compare at read time, never auto-refresh — same
    # pattern as board_report.py's latest_narrative(). ReviewPanel.jsx gets no
    # dedicated staleness UI (out of scope, see the plan), so the signal rides
    # along inside the existing summary text it already renders as-is.
    if artifact == "coherence" and a.status == "ready" and serialized["result"]:
        data = serialized["result"]
        cited_refs = data.get("cited_refs") or []
        current_sig = await recompute_coherence_signature(engagement_id, cited_refs, db)
        stale = bool(cited_refs) and current_sig != data.get("based_on_sig")
        data["stale"] = stale
        if stale:
            data["summary"] = (
                f"⚠ Stale — the underlying data has changed since this check last ran. {data.get('summary', '')}"
            ).strip()

    return serialized


@router.patch("/planning/{engagement_id}/review/{artifact}/comments/{comment_id}")
async def patch_review_comment(
    engagement_id: str, artifact: str, comment_id: str, payload: dict, db: AsyncSession = Depends(get_db),
):
    a = await _get_analysis(db, engagement_id, "quality_review", artifact)
    if not a or not a.result:
        raise HTTPException(status_code=404, detail="Review not found")
    data = json.loads(a.result)
    for c in data.get("comments", []):
        if c.get("id") == comment_id:
            for k in ("is_accepted", "is_dismissed"):
                if k in payload:
                    c[k] = bool(payload[k])
            break
    a.result = json.dumps(data)
    await db.commit()
    return _serialize(a)


@router.get("/planning/{engagement_id}/coverage")
async def get_coverage(engagement_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    return await compute_coverage(engagement_id, db)
