"""Reading the edit register. There is no write endpoint, on purpose: rows are
added by the flush listener in services/edit_register.py and never changed."""
from fastapi import APIRouter, HTTPException

from services.ai_share import ai_share
from services.edit_register import RACM_TABLES, TRACKED, history

router = APIRouter()

_READABLE = set(RACM_TABLES) | set(TRACKED)


@router.get("/history/{entity}/{entity_id}")
async def record_history(entity: str, entity_id: str):
    """Who proposed and who decided, for one record, oldest first."""
    if entity not in _READABLE:
        raise HTTPException(status_code=404, detail=f"No history is kept for '{entity}'")
    return await history(entity, entity_id)


@router.get("/engagements/{engagement_id}/ai-share")
async def engagement_ai_share(engagement_id: str):
    """How much of this audit file IA Wingman proposed and what people did with
    it — from the records themselves, and from the register since it started."""
    return await ai_share(engagement_id)
