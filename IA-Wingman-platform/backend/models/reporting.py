"""Reporting phase — models.

Greenfield. A Finding is the report-ready, 5C-structured version of a fieldwork
observation (Condition, Criteria, Cause, Effect/Consequence, Corrective action)
plus a rating. A separate review agent challenges that rating so the human sees
a second opinion before signing. AuditReport is the assembled deliverable.
"""
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.sql import func

from database import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    source_observation_id = Column(String(36), nullable=True)  # fieldwork observation it came from
    racm_test_id = Column(String(36), nullable=True)  # RACM test it was promoted from (traceability)
    title = Column(String(500), nullable=False)
    # The 5 C's
    condition = Column(Text, nullable=True)       # what was found
    criteria = Column(Text, nullable=True)         # the norm / what was expected
    cause = Column(Text, nullable=True)            # why it happened
    effect = Column(Text, nullable=True)           # consequence / risk
    recommendation = Column(Text, nullable=True)   # corrective action
    rating = Column(String(20), nullable=True)     # high | medium | low
    rating_rationale = Column(Text, nullable=True)
    rating_challenge = Column(Text, nullable=True)  # JSON: {agrees, suggested_rating, rationale}
    # Explainability annex — persists ONLY the optional AI-sharpened answers + timestamp.
    # The deterministic scaffold is rebuilt fresh on every GET, so it never goes stale.
    # JSON: {"answers": {"1": "...", ...}, "sharpened_at": "iso", "based_on_updated_at": "iso"}
    explainability = Column(Text, nullable=True)
    # Grounded validator — persists ONLY the opt-in AI judge verdicts (per-claim
    # found/quote/confidence). The deterministic pre-screen is rebuilt on every GET.
    # JSON: {"claims": [...], "judged_at": "iso", "based_on_sig": "sha1"}
    validation = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")  # draft | drafting | ready | failed
    drafter_run_id = Column(String(36), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BoardReport(Base):
    """Portfolio-/board-level narrative. Single latest row (append-only, we read
    the most recent). The aggregates are always recomputed deterministically; only
    the optional AI-drafted executive summary is persisted here."""
    __tablename__ = "board_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    overall_opinion = Column(String(40), nullable=True)   # satisfactory | needs_improvement | unsatisfactory
    exec_summary = Column(Text, nullable=True)
    key_messages = Column(Text, nullable=True)            # JSON list of strings
    status = Column(String(20), nullable=False, default="draft")  # draft | drafting | ready | failed
    generated_by = Column(String(20), nullable=True)      # ai | deterministic
    # sha1 of the salient aggregates at draft time — lets the page flag the AI
    # summary as stale when the portfolio data has moved on since it was written.
    based_on_sig = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    overall_opinion = Column(String(40), nullable=True)   # satisfactory | needs_improvement | unsatisfactory
    exec_summary = Column(Text, nullable=True)
    conclusion = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")  # draft | drafting | ready | failed
    drafter_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
