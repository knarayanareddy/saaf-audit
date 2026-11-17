"""Document center — endpoint. Lists every generatable document with its
availability. Downloads themselves go through the existing per-artifact export
endpoints (all authenticated)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from services.document_center import list_generated_documents

router = APIRouter()


@router.get("/engagements/{engagement_id}/documents/generated")
async def generated_documents(engagement_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    docs = await list_generated_documents(engagement_id, db)
    available = sum(1 for d in docs if d["available"])
    return {"total": len(docs), "available": available, "documents": docs}
