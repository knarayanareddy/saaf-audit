"""AI Assurance Center — security posture + red-team suite endpoints.

All routes sit behind the global auth dependency. The `live` suite actually
spends AI tokens, so it carries an extra confirm-token and its own rate-limit on
top of auth — the costliest, most abusable endpoint gets the most friction.
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.assurance import AssuranceRun
from services.assurance import red_team_suite as rt
from services.assurance.posture import compute_posture, flagged_documents

router = APIRouter()

LIVE_CONFIRM_TOKEN = "RUN-LIVE"
_LIVE_MIN_INTERVAL = 60.0  # seconds between live runs (cost guard)
_last_live_ts = {"t": 0.0}


class SuiteRunRequest(BaseModel):
    mode: str = "static"          # static | live
    confirm: str | None = None    # required == LIVE_CONFIRM_TOKEN for live


@router.get("/assurance/posture")
async def posture(db: AsyncSession = Depends(get_db)):
    return await compute_posture(db)


@router.get("/assurance/runs")
async def runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AssuranceRun).order_by(AssuranceRun.started_at.desc()).limit(min(limit, 100))
    )).scalars().all()
    out = []
    for r in rows:
        try:
            summ = json.loads(r.summary)
        except (ValueError, TypeError):
            summ = {}
        out.append({
            "id": r.id, "mode": r.mode, "passed": r.passed, "total": r.total,
            "score_pct": summ.get("score_pct"), "headline": summ.get("headline"),
            "started_at": r.started_at.isoformat() if r.started_at else None,
        })
    return {"runs": out}


@router.get("/assurance/runs/{run_id}")
async def run_detail(run_id: str, db: AsyncSession = Depends(get_db)):
    """Full per-payload report for one run — powers the readable drill-down.

    Degrades gracefully for runs saved before the richer fields existed: any
    missing key simply comes back as None/empty and the UI falls back."""
    r = await db.get(AssuranceRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    try:
        summ = json.loads(r.summary)
    except (ValueError, TypeError):
        summ = {}
    try:
        results = json.loads(r.results)
    except (ValueError, TypeError):
        results = []
    # Backfill verdict/label/headline for runs saved before those fields existed,
    # so every historical run renders in the readable report (no DB mutation).
    verdicts, headline = rt.hydrate_report(r.mode, r.passed, r.total, results, summ)
    return {
        "id": r.id, "mode": r.mode, "passed": r.passed, "total": r.total,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "score_pct": summ.get("score_pct"), "headline": headline,
        "verdicts": verdicts, "note": rt._note(r.mode),
        "by_category": summ.get("by_category"), "results": results,
    }


@router.get("/assurance/documents/flags")
async def document_flags(db: AsyncSession = Depends(get_db)):
    docs = await flagged_documents(db)
    return {"total": len(docs), "documents": docs}


@router.post("/assurance/suite/run")
async def run_suite(payload: SuiteRunRequest, db: AsyncSession = Depends(get_db)):
    mode = (payload.mode or "static").lower()
    if mode not in ("static", "live"):
        raise HTTPException(status_code=422, detail="mode must be 'static' or 'live'")

    if mode == "static":
        report = rt.run_static()
    else:
        # Extra friction for the paid path.
        if payload.confirm != LIVE_CONFIRM_TOKEN:
            raise HTTPException(
                status_code=400,
                detail=f"Live red-team consumes AI budget. Resend with confirm='{LIVE_CONFIRM_TOKEN}'.",
            )
        now = time.monotonic()
        if now - _last_live_ts["t"] < _LIVE_MIN_INTERVAL:
            wait = int(_LIVE_MIN_INTERVAL - (now - _last_live_ts["t"]))
            raise HTTPException(status_code=429, detail=f"Live run rate-limited — retry in {wait}s.",
                                headers={"Retry-After": str(wait)})
        _last_live_ts["t"] = now
        report = await rt.run_live()

    run_id = await rt.persist_run(db, report)
    return {"run_id": run_id, **report}
