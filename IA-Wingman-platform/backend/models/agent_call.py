"""One row per call to a model — the spend ledger.

The plan for this was columns on AgentRun and CopilotTask. That would have
captured roughly a third of the spend and quietly implied it was all of it:
most agent calls create neither row. The chat's title suggestions, the proactive
check-in, the coherence check, the QA review and the GIAS peer review (which
writes to AiAnalysis) all spend money without an AgentRun existing anywhere.

So the ledger is its own table, and it is append-only for the same reason
AgentActivity is: it is the record of what was spent and on whose behalf, and a
record that can be rewritten is not one. A run is linked back to its AgentRun or
CopilotTask when it has one, and stands on its own when it does not.

It is written best-effort. A ledger failure must never take down the agent whose
work it was recording — the work is what the auditor is waiting for.
"""
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class AgentCall(Base):
    __tablename__ = "agent_calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Nullable: some calls belong to no engagement (a title suggested before one
    # exists). Those still cost money, so they are still recorded.
    engagement_id = Column(String(36), nullable=True, index=True)
    agent = Column(String(60), nullable=True)      # governance_assessor | peer_review | ...
    schema = Column(String(60), nullable=True)     # the output contract, when there was one
    tier = Column(String(10), nullable=True)       # quick | draft | judge
    model = Column(String(60), nullable=True)

    started_at = Column(DateTime, server_default=func.now())
    duration_ms = Column(Integer, nullable=False, default=0)

    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cached_tokens = Column(Integer, nullable=False, default=0)
    # Tokens written to the prompt cache, billed at 1.25x input. Not recorded
    # before 2026-10-22: rows from before then show NULL here, which means
    # "not measured", not "none were written".
    cache_write_tokens = Column(Integer, nullable=True)
    # Which instructions produced this call: the first 12 characters of the
    # sha256 of the system prompt plus the schema the API was held to. The task
    # template inside the user prompt is NOT part of it — template and data are
    # one string there — so a change to the template alone keeps the version.
    prompt_version = Column(String(16), nullable=True)
    # Whether the model reasoned. thinking_tokens counts only VISIBLE reasoning,
    # and the current models hide theirs by default — so a judge that thought at
    # length shows 0 there. NULL on rows from before this was recorded.
    reasoned = Column(Boolean, nullable=True)
    thinking_tokens = Column(Integer, nullable=False, default=0)
    # Nullable on purpose: a model with no price configured costs an unknown
    # amount, not zero. Summing skips these and the total says how many it skipped.
    cost_usd = Column(Float, nullable=True)

    stop_reason = Column(String(30), nullable=True)
    repaired = Column(Boolean, nullable=False, default=False)
    # How it had to be fixed before it could be used, or null when it did not.
    # `retry` is the typed path handing the model its own validation error; the
    # others are surgery this code performed on prose — a code fence stripped,
    # the braces sliced out of a sentence, a trailing comma deleted. Both were
    # `repaired = True` and nothing more, so an answer the model corrected itself
    # and a string cut into shape by regex read identically in the record.
    repair = Column(String(30), nullable=True)
    ok = Column(Boolean, nullable=False, default=True)
    error = Column(String(200), nullable=True)
    # The module and function the call was made from. Recorded always, because
    # `agent` is filled only when a caller opened `agent_context` — which 19 of
    # the first 20 untyped calls never did, leaving the ledger unable to say
    # whose spend it was recording. An observed fact beside a declared one,
    # never instead of it: a call that names itself keeps its own name.
    caller = Column(String(80), nullable=True)

    # What this call actually read: the coverage sentence and the passage ids, so
    # a run's provenance survives the run itself.
    sources = Column(Text, nullable=True)          # JSON

    run_id = Column(String(36), nullable=True)     # AgentRun, when there is one
    task_id = Column(String(36), nullable=True)    # CopilotTask, when there is one


Index("ix_agent_calls_eng_started", AgentCall.engagement_id, AgentCall.started_at)
