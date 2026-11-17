"""Audit Copilot — persistence for the chat that guides an auditor through an
engagement. Additive: today's chat is stateless server-side (history lives only
in React state and is lost on refresh); these tables let it survive that.

One session per engagement (the "one continuous conversation" the copilot's
autonomy and review-queue mechanisms will hang off in later phases).
"""
from uuid import uuid4
from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CopilotMessage(Base):
    __tablename__ = "copilot_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False, default="")
    # JSON: [{tool, input, proposal_id}] — proposal_id links each tool_use back
    # to its CopilotProposal row; the row's own status is the live source of
    # truth (this snapshot is written once and never updated in place).
    tool_calls = Column(Text, nullable=True)
    # A copilot-initiated check-in (M10's maybe_ask_proactive_question), not a
    # reply to the auditor's own message. Deliberately its own column rather
    # than a tool_calls marker — a proactive question has no proposal_id and
    # would otherwise misrender as a broken ActionCard on the frontend.
    is_proactive = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())


class CopilotProposal(Base):
    """A persisted version of an ActionCard — makes a Tier-B proposal survive
    closing the chat panel or refreshing the page, instead of only living in
    React state. status is the live source of truth for that proposal."""
    __tablename__ = "copilot_proposals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), nullable=False, index=True)
    tool_name = Column(String(60), nullable=False)
    input = Column(Text, nullable=False, default="{}")  # JSON
    status = Column(String(20), nullable=False, default="pending")  # pending | accepted | dismissed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CopilotTask(Base):
    """An autonomously (or chat-)triggered stage run — the working-state/queue
    the auditor's 'ready for review' batch is read from. Wraps a call into
    services/stage_actions.py:STAGE_RUN_ACTIONS; the drafted content itself
    lands in that stage's own artifact table as usual, this row only tracks
    that the run happened and whether it's been looked at yet."""
    __tablename__ = "copilot_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    # A STAGE_GRAPH key for stage-level tasks. For item-level tasks (see item_id)
    # this holds a short, constant item-type label ("finding", "interview_session")
    # instead — never a per-item synthetic key, to avoid overloading what every
    # other reader of this column already assumes it means.
    stage_key = Column(String(40), nullable=False)
    # Set only for item-level tasks — the Finding/InterviewSession id this task
    # is about. NULL for ordinary per-engagement stage tasks.
    item_id = Column(String(36), nullable=True)
    # queued | running | ready_for_review | reviewed | dismissed | failed
    status = Column(String(20), nullable=False, default="queued")
    triggered_by = Column(String(10), nullable=False, default="auto")  # auto | chat
    # Set when copilot_preflight downgraded this task from auto-fire to a
    # confirm-first review card (e.g. a source document has an injection-scan flag).
    flagged = Column(Boolean, nullable=False, default=False)
    error = Column(Text, nullable=True)
    # One-sentence "why this now" from the Orchestrator Agent's advise_stage_order
    # (stage-level tasks) or advise_item_order (item-level tasks, item_id set).
    # Set only for auto-fired batches of 2+ candidates that the advisor actually
    # reordered; None for manual runs and single-candidate/fail-open batches.
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
