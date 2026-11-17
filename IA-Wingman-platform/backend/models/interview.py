"""Interview Agent v2 + live Companion — models.

Additive to the existing TI interview-guide cascade (which stays untouched).
- InterviewGuide: a persona-structured guide (sponsor / process owner / second
  line / first line) with per-question follow-ups and traceability (which risk
  area or framework each question probes) plus a coverage check.
- InterviewSession: a live companion session. The auditor pastes (anonymised)
  answers; the agent proposes follow-ups, observations and candidate control
  gaps, and drafts minutes. Human-in-the-loop and privacy-first: no names.
"""
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func

from database import Base


class InterviewGuide(Base):
    __tablename__ = "interview_guides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="not_started")  # not_started | running | ready | no_data | failed
    personas = Column(Text, nullable=True)   # JSON: [{persona, role_label, goal, opening, questions:[{text, follow_ups:[], traceability:{type,ref}}]}]
    coverage = Column(Text, nullable=True)   # JSON: {summary, covered:[], gaps:[]}
    generator_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    persona = Column(String(40), nullable=True)          # which persona this session covers
    label = Column(String(200), nullable=True)           # auditor's own label, e.g. "Process owner — payments"
    notes = Column(Text, nullable=True)                  # pasted, anonymised answers (raw)
    status = Column(String(30), nullable=False, default="draft")  # draft | analysing | ready | failed
    analysis = Column(Text, nullable=True)               # JSON: {summary, follow_ups:[], observations:[], control_gaps:[], minutes:[]}
    companion_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
