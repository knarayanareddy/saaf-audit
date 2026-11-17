"""The edit register: who proposed each auditable value, and who decided about it.

An audit file built with AI has to answer one question about every line in it:
did a person decide this, or did a model write it and a person let it stand? The
activity log tells a story per event in a sentence. This tells it per field, with
the value before and after, so the answer is a row rather than a recollection.

**Append-only.** Nothing in the application updates or deletes a row here, and
there is deliberately no endpoint that could. A register that can be edited is
a register of the last edit.

**Honest about identity.** Until the platform has real sign-in (phase 3), a
human actor is the initials the person typed at the login screen. They are
recorded with `actor_verified = False`, and the UI says so, rather than the
register presenting a typed-in name as an authenticated one.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text

from database import Base


class FieldEdit(Base):
    __tablename__ = "field_edits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Every new table carries this from day one; it
    # becomes NOT NULL when tenants exist.
    tenant_id = Column(String(36), nullable=True)
    engagement_id = Column(String(36), nullable=True, index=True)
    entity = Column(String(60), nullable=False)        # table name, e.g. racm_risks
    entity_id = Column(String(36), nullable=False)
    field = Column(String(60), nullable=False)         # a column, or "*" for the whole record
    before = Column(Text, nullable=True)               # JSON
    after = Column(Text, nullable=True)                # JSON
    actor_kind = Column(String(10), nullable=False)    # ai | human
    actor = Column(String(100), nullable=False)        # initials, or the agent's name
    actor_verified = Column(Boolean, nullable=False, default=False)
    decision = Column(String(20), nullable=False)      # proposed | created | modified | accepted | rejected
    # The run that produced an AI proposal. Through the ledger (agent_calls.run_id)
    # it names the model, the prompt version and what the proposal cost.
    run_id = Column(String(80), nullable=True)
    # Python's clock, to the microsecond — not the database's `now()`, which on
    # SQLite has whole seconds: a proposal and its rejection a moment later came
    # back in random order, and a history that can show "rejected" before
    # "proposed" is not a history.
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


Index("ix_field_edits_entity", FieldEdit.entity, FieldEdit.entity_id)
