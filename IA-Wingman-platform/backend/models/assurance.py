from uuid import uuid4
from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class AssuranceRun(Base):
    """Append-only record of an AI Assurance red-team suite run.

    `static` runs are deterministic (no AI) and prove the injection-isolation
    plumbing is in place. `live` runs actually exercise the model against curated
    payloads (opt-in, costs tokens). Kept as history so the posture dashboard can
    show the last result and trend without re-running.
    """
    __tablename__ = "assurance_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mode = Column(String(20), nullable=False)             # static | live
    started_at = Column(DateTime, server_default=func.now())
    passed = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=False, default="{}")  # JSON roll-up (by_category, score_pct)
    results = Column(Text, nullable=False, default="[]")  # JSON full per-test results
