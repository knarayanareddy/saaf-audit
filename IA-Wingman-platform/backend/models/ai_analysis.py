from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.sql import func
from database import Base


class AiAnalysis(Base):
    """Stored output of a cross-cutting AI analysis of an engagement artifact —
    a QA/quality review or a grounding (source-support) check. One current row
    per (engagement, kind, artifact); re-running replaces it.
    """
    __tablename__ = "ai_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    kind = Column(String(30), nullable=False)      # quality_review | grounding
    artifact = Column(String(40), nullable=False)  # topic_intelligence | scope | frameworks | anl | ...
    status = Column(String(20), nullable=False, default="running")  # running | ready | failed | no_data
    result = Column(Text, nullable=True)           # JSON
    created_at = Column(DateTime, server_default=func.now())


Index("ix_ai_analyses_lookup", AiAnalysis.engagement_id, AiAnalysis.kind, AiAnalysis.artifact)
