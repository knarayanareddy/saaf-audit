from uuid import uuid4
from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    agent_type = Column(String(50), nullable=False)  # regulatory | policy | interview
    status = Column(String(50), nullable=False, default="pending")  # pending | running | waiting | complete | failed
    input_summary = Column(Text, nullable=True)
    raw_output = Column(Text, nullable=True)
    accepted_output = Column(Text, nullable=True)
    human_edits_made = Column(Boolean, default=False)
    document_ids = Column(Text, nullable=False, default="[]")  # JSON string
    created_at = Column(DateTime, server_default=func.now())
    accepted_at = Column(DateTime, nullable=True)
    # Regulatory Intelligence — live search progress (JSON) and query plan
    search_progress = Column(Text, nullable=True)   # {stage, queries:[{text,angle,status,results}], results_found}
    search_queries = Column(Text, nullable=True)    # [{query_text, angle, primary_domain, description}]
