from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.sql import func
from database import Base


class AgentActivity(Base):
    """Append-only audit trail of AI activity per engagement.

    Every meaningful AI event — an agent run, a human acceptance, edit, or
    dismissal — is logged here. This is the provenance / defensibility record
    for AI use in the audit: it is never mutated or deleted by the app, which
    keeps it independent of the AgentRun lifecycle (AgentRuns are cleared on
    re-run; activity is not).
    """
    __tablename__ = "agent_activity"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    agent = Column(String(60), nullable=False)          # e.g. regulatory | policy | interview | qa_review | grounding
    action = Column(String(30), nullable=False)         # run | accept | edit | dismiss | error
    summary = Column(Text, nullable=True)               # human-readable one-liner
    sources = Column(Text, nullable=False, default="[]")  # JSON: [{type, ref}]  provenance
    confidence = Column(String(20), nullable=True)      # high | medium | low
    actor = Column(String(100), nullable=True)          # user initials (from client), or "system"
    created_at = Column(DateTime, server_default=func.now())


Index("ix_agent_activity_eng_created", AgentActivity.engagement_id, AgentActivity.created_at)
