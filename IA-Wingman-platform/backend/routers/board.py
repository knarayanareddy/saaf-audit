"""Board / portfolio report — endpoints.

Deterministic aggregates are free; the AI executive summary is opt-in and runs as
a background task. Export goes through the authenticated client like every other
document.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from organization import ORG
from services.board_report import (
    compute_board, deterministic_summary, latest_narrative, draft_board_narrative_task,
)

router = APIRouter()


@router.get("/board/summary")
async def board_summary(db: AsyncSession = Depends(get_db)):
    """Deterministic portfolio aggregates + a deterministic fallback summary."""
    board = await compute_board(db)
    board["deterministic_summary"] = deterministic_summary(board)
    return board


@router.get("/board/narrative")
async def board_narrative(db: AsyncSession = Depends(get_db)):
    """The latest saved (AI or deterministic) narrative, if any."""
    return await latest_narrative(db) or {"status": "not_started"}


@router.post("/board/narrative/draft")
async def board_narrative_draft(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Opt-in: draft the executive summary with AI (falls back to deterministic)."""
    background_tasks.add_task(draft_board_narrative_task)
    return {"status": "drafting"}


@router.get("/board/export-word")
async def board_export_word(db: AsyncSession = Depends(get_db)):
    import asyncio
    from functools import partial
    from services.word_export import generate_board_docx

    board = await compute_board(db)
    narrative = await latest_narrative(db) or deterministic_summary(board)
    docx_bytes = await asyncio.get_event_loop().run_in_executor(
        None, partial(generate_board_docx, board, narrative, ORG.to_dict())
    )
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="Board-Report.docx"'},
    )
