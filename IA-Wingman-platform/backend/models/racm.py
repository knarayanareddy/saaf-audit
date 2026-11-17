"""RACM spine — the Risk-and-Control Matrix backbone.

The spine is the traceable chain every agent writes into:

    Objective → Risk → Control → Test → Evidence

It is what turns isolated AI output into audit-grade, herleidbare results.
Every node records who proposed it (AI or human), whether a human has accepted
it, and its provenance — so the governance principle "AI proposed · you own"
holds end to end. A separate ScopeDecision log records the governed scope calls
(in/out of scope, materiality, reliance, changes) that shape the spine.

Deterministic and additive: plain tables with bare String foreign keys, matching
the rest of the models. New tables are created by create_all at startup, so no
ALTER migration is needed. No AI runs here.
"""
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime
from sqlalchemy.sql import func

from database import Base


class _NodeMixin:
    """Governance + provenance columns shared by every spine node.

    origin      — 'ai' | 'human': who created the node.
    accepted    — a human has confirmed it (the "you own" flip). AI nodes start
                  False; human-created nodes are owned on creation.
    accepted_by — initials of the confirming human.
    confidence  — 'high' | 'medium' | 'low' (mainly meaningful for AI nodes).
    provenance  — JSON string: {source_type, source_ref, rationale, run_id}.

    SQLAlchemy copies plain Column attributes declared on a mixin onto each
    mapped subclass, so these live once here and apply to all node tables.
    """
    origin = Column(String(10), nullable=False, default="human")
    accepted = Column(Boolean, nullable=False, default=False)
    accepted_by = Column(String(40), nullable=True)
    confidence = Column(String(10), nullable=True)
    provenance = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RacmObjective(Base, _NodeMixin):
    __tablename__ = "racm_objectives"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    ref = Column(String(12), nullable=True)          # display code, e.g. "O1"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)


class RacmRisk(Base, _NodeMixin):
    __tablename__ = "racm_risks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    objective_id = Column(String(36), nullable=True, index=True)   # parent objective
    ref = Column(String(12), nullable=True)          # "R1"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(60), nullable=True)     # e.g. "AML", "Sanctions"
    inherent_rating = Column(String(10), nullable=True)   # high | medium | low


class RacmControl(Base, _NodeMixin):
    __tablename__ = "racm_controls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    risk_id = Column(String(36), nullable=True, index=True)        # parent risk
    ref = Column(String(12), nullable=True)          # "C1"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    control_type = Column(String(20), nullable=True)      # preventive | detective
    frequency = Column(String(40), nullable=True)
    owner = Column(String(120), nullable=True)
    design_conclusion = Column(String(20), nullable=True)  # effective | deficient | not_assessed


class RacmTest(Base, _NodeMixin):
    __tablename__ = "racm_tests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    control_id = Column(String(36), nullable=True, index=True)     # parent control
    ref = Column(String(12), nullable=True)          # "T1"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    method = Column(String(40), nullable=True)       # inspection | reperformance | sampling | full_population | inquiry
    sample_size = Column(Integer, nullable=True)
    exceptions_count = Column(Integer, nullable=True)
    result = Column(String(20), nullable=True)       # pass | fail | exceptions | pending
    conclusion = Column(Text, nullable=True)
    # Carried over from the work program, which is a projection of this spine.
    # `result` is the outcome; `progress` is how far along the work is. A test
    # that has not started has neither, and saying so with one column made
    # "not started" and "found nothing" look alike.
    priority = Column(String(10), nullable=True)     # high | medium | low
    assigned_to = Column(String(120), nullable=True)  # who runs it, not who owns the control
    progress = Column(String(20), nullable=True)     # not_started | in_progress | complete


class RacmEvidence(Base, _NodeMixin):
    __tablename__ = "racm_evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    test_id = Column(String(36), nullable=True, index=True)        # parent test
    ref = Column(String(12), nullable=True)          # "E1"
    kind = Column(String(20), nullable=True)         # document | interview | data | observation
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    source_document_id = Column(String(36), nullable=True)         # link to UploadedDocument
    # A need before it is met, the same row after. Measured on one engagement:
    # 17 tests declared 62 needs, of which 48 are document or data — the other
    # 14 are interviews and observations, which are not things to ask an auditee
    # to send. Only the first kind can become a document request.
    requested_from = Column(String(120), nullable=True)   # the department that holds it
    period = Column(String(120), nullable=True)           # the population or period needed
    drl_item_id = Column(String(36), nullable=True)       # the request that covers this need


class ScopeDecision(Base):
    """Governed scope call: rationale, materiality, sponsor sign-off, change control.

    Not a spine node (no accept flip); it is an append-only decision record that
    documents why the spine looks the way it does.
    """
    __tablename__ = "scope_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    decision_type = Column(String(20), nullable=False, default="in_scope")
    # in_scope | out_of_scope | materiality | reliance | change
    summary = Column(String(500), nullable=False)
    rationale = Column(Text, nullable=True)
    materiality = Column(String(200), nullable=True)
    sponsor = Column(String(120), nullable=True)
    status = Column(String(20), nullable=False, default="proposed")   # proposed | approved | changed
    origin = Column(String(10), nullable=False, default="human")
    provenance = Column(Text, nullable=True)   # JSON: {source_type, source_ref, rationale, run_id}
    linked_objective_id = Column(String(36), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
