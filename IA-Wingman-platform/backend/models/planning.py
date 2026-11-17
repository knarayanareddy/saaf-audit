from uuid import uuid4
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from database import Base


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)
    upload_status = Column(String(50), nullable=False, default="processing")  # processing | ready | failed
    # JSON list of prompt-injection heuristic flags found in extracted_text.
    # Informational only ("possibly suspicious — verify"); never blocks the document.
    injection_flags = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())


class TopicIntelligence(Base):
    __tablename__ = "topic_intelligence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, default="not_started")
    # not_started | agents_pending | review | agreed
    progress_pct = Column(Integer, default=0)

    # Assembled from agent outputs — all human-editable
    regulatory_summary = Column(Text, nullable=True)
    internal_framework_summary = Column(Text, nullable=True)
    external_developments = Column(Text, nullable=True)
    key_risk_areas = Column(Text, nullable=True)       # JSON: [{title, rationale, basis, source, confidence}]
    excluded_areas = Column(Text, nullable=True)       # JSON: [{title, rationale}]
    conclusion = Column(Text, nullable=True)
    interview_agenda = Column(Text, nullable=True)     # JSON: {sponsor:[], sme:[], ia_prework:[]}
    topic_primer = Column(Text, nullable=True)         # plain-language "what is this topic" explainer
    # What the auditor added to the scan's starting context, kept as the record
    # of what this scan actually ran with — not as a setting for the next one.
    extra_context = Column(Text, nullable=True)

    memo_accepted = Column(Boolean, default=False)
    memo_accepted_at = Column(DateTime, nullable=True)
    regulatory_run_id = Column(String(36), nullable=True)
    policy_run_id = Column(String(36), nullable=True)
    interview_run_id = Column(String(36), nullable=True)
    search_results = Column(Text, nullable=True)   # JSON: [{title, url, content, angle}] from Tavily
    search_queries = Column(Text, nullable=True)   # JSON: [{query_text, angle, primary_domain}]

    # ── Topic Intelligence v2 — 4-lens architecture ────────────────────────
    lens1_summary = Column(Text, nullable=True)   # Normative & Regulatory — 150-200 word synthesis
    lens1_sources = Column(Text, nullable=True)   # JSON: [{title, url, date, confidence}]
    lens1_run_id  = Column(String(36), nullable=True)
    lens2_summary = Column(Text, nullable=True)   # Supervisory & Enforcement
    lens2_sources = Column(Text, nullable=True)   # JSON: [{title, url, date}]
    lens2_run_id  = Column(String(36), nullable=True)
    lens3_summary = Column(Text, nullable=True)   # Society / Trends / Incidents
    lens3_sources = Column(Text, nullable=True)   # JSON: [{title, url, date, materiality_signal}]
    lens3_run_id  = Column(String(36), nullable=True)
    lens4_notes   = Column(Text, nullable=True)   # Internal context — manual input
    lens4_state   = Column(String(20), nullable=True)  # 'rich' | 'partial' | 'empty'

    # ── Orchestrator Agent — synthesis of the 3 lenses into a scoping proposal ──
    proposed_frameworks = Column(Text, nullable=True)
    # JSON: [{id, framework_code, framework_name, applicability_rationale, jurisdiction, is_primary, confidence, included}]
    synthesis_failed = Column(Boolean, nullable=False, default=False)
    # JSON: {checks: [{claim, verdict, finding, source_url}], searches_used, searches_allowed, queries, errors}.
    # The verification round's result; null when it did not run.
    verification = Column(Text, nullable=True)


class ScopeObjectives(Base):
    __tablename__ = "scope_objectives"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, default="not_started")
    progress_pct = Column(Integer, default=0)
    overall_objective = Column(Text, nullable=True)
    scope_period = Column(String(100), nullable=True)
    scope_entity = Column(String(20), nullable=True)


class ScopeItem(Base):
    __tablename__ = "scope_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scope_id = Column(String(36), nullable=False, index=True)
    item_type = Column(String(20), nullable=False)     # in_scope | out_of_scope
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    # One of services/scope_sources.SOURCES. 20 characters was too few for the
    # names already being written, which SQLite accepted and Postgres will not.
    source = Column(String(40), nullable=False, default="manual")
    source_ref = Column(String(64), nullable=True)   # the upstream row, when it has an id
    is_accepted = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)


class KeyAuditQuestion(Base):
    __tablename__ = "key_audit_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scope_id = Column(String(36), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    regulatory_basis = Column(String(500), nullable=True)
    source = Column(String(40), nullable=False, default="manual")
    source_ref = Column(String(64), nullable=True)
    is_accepted = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)


class ApplicableFramework(Base):
    __tablename__ = "applicable_frameworks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    framework_code = Column(String(50), nullable=False)
    framework_name = Column(String(255), nullable=False)
    applicability_rationale = Column(Text, nullable=True)
    specific_provision = Column(Text, nullable=True)          # e.g. "Art. 3 WWFT — identification before business relationship"
    source_url = Column(String(500), nullable=True)           # official URL of regulation
    confidence = Column(String(20), nullable=True, default="medium")  # high | medium | low
    jurisdiction = Column(String(20), nullable=True)          # NL | UK | BE | ES | EU | International
    category = Column(String(20), nullable=True, default="law")  # law | guidance (supervisory guidance)
    is_primary = Column(Boolean, default=False)
    is_accepted = Column(Boolean, default=False)
    source = Column(String(30), nullable=False, default="manual")  # ai_suggested | manual | auto_analysed


class ProcessNotes(Base):
    __tablename__ = "process_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    notes = Column(Text, nullable=True)
    # Phase 2 — 4-state agent flow (all nullable — safe migration)
    status = Column(String(30), nullable=True, default="not_started")
    # not_started | reasoning | reasoning_ready | generating | draft_ready | agreed
    reasoning = Column(Text, nullable=True)           # AI's step-by-step reasoning (editable)
    process_items = Column(Text, nullable=True)       # JSON: [{id, name, desc, source, confidence, activities:[...], is_included}]
    preliminary_observations = Column(Text, nullable=True)  # JSON: [{text, source}]
    analyser_run_id = Column(String(36), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BackgroundRiskAssessment(Base):
    __tablename__ = "background_risk_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="not_started")
    # not_started | drafting | draft_ready

    # 4 mandatory background sections (matching the organisation BRA template)
    section_strategy = Column(Text, nullable=True)    # Org strategies, objectives, risks for this area
    section_risk_tolerance = Column(Text, nullable=True)  # Risk tolerance established for this activity
    section_governance = Column(Text, nullable=True)  # Governance, risk management and control processes
    section_frameworks = Column(Text, nullable=True)  # Applicable frameworks, guidance, criteria

    # Risk items stored as JSON: [{ref, link_to_anl, description, process, risk_statement, inherent_risk, controls, residual_risk, is_accepted}]
    risk_items = Column(Text, nullable=True)

    drafter_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KickoffAgenda(Base):
    __tablename__ = "kickoff_agendas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="not_started")
    # not_started | drafting | draft_ready

    meeting_date = Column(String(30), nullable=True)
    attendees = Column(Text, nullable=True)

    # Agenda sections — all human-editable, AI-seeded
    notes_welcome = Column(Text, nullable=True)      # Welcome, confirm objectives
    notes_context = Column(Text, nullable=True)       # Audit info, objective, budget
    notes_documentation = Column(Text, nullable=True) # Available docs: prev audits, controls, risk assessments
    notes_missing = Column(Text, nullable=True)       # Missing documentation needed
    notes_scope = Column(Text, nullable=True)         # Scope subjects, fraud risk, ESG, budget check
    notes_risks = Column(Text, nullable=True)         # Inherent/control/detection risk
    notes_team = Column(Text, nullable=True)          # Team composition, independence, planning
    notes_other = Column(Text, nullable=True)         # IT tools, data analysis, confidentiality
    notes_aob = Column(Text, nullable=True)           # Any other business
    notes_next_steps = Column(Text, nullable=True)    # Actions, responsibilities, next meeting

    # The first questions of any internal audit: what is the audit for, and what to ask the auditor.
    audit_purpose = Column(Text, nullable=True)           # plain-language purpose/aim of this audit
    questions_for_auditor = Column(Text, nullable=True)   # JSON list of kick-off questions for the auditor

    drafter_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditNotificationLetter(Base):
    __tablename__ = "audit_notification_letters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)

    # ANL sections — all human-editable, AI-seeded
    background = Column(Text, nullable=True)        # Why this audit is in the plan
    objectives = Column(Text, nullable=True)        # What we aim to assess
    scope_description = Column(Text, nullable=True) # In-scope items (derived from Scope module)
    out_of_scope = Column(Text, nullable=True)       # Out-of-scope with rationale
    approach = Column(Text, nullable=True)           # Methodology steps
    timing_fieldwork_start = Column(String(30), nullable=True)
    timing_fieldwork_end = Column(String(30), nullable=True)
    timing_draft_report = Column(String(30), nullable=True)   # auto: 2 weeks after fieldwork end
    timing_mgmt_response = Column(String(30), nullable=True)  # auto: 2 weeks after draft
    timing_final_report = Column(String(30), nullable=True)   # auto: 1 week after mgmt response
    responsibility = Column(Text, nullable=True)    # What auditee must provide

    # Workflow status
    # not_started | drafting | draft_ready | review_pending | reviewed | head_ia_review | approved | sent
    status = Column(String(30), nullable=False, default="not_started")

    # AI review comments — JSON: [{id, section, comment, severity, is_accepted}]
    # severity: "must_fix" | "suggestion"
    review_comments = Column(Text, nullable=True)
    review_run_id = Column(String(36), nullable=True)

    # Head IA sign-off
    head_ia_status = Column(String(20), nullable=False, default="pending")  # pending | approved
    head_ia_approved_at = Column(DateTime, nullable=True)

    drafter_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ── Phase 3 models ────────────────────────────────────────────────────────────

class RegRequirement(Base):
    """Regulatory Requirements — extracts specific control obligations from accepted frameworks."""
    __tablename__ = "reg_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="not_started")
    # not_started | analysing | draft_ready | agreed
    items = Column(Text, nullable=True)
    # JSON: [{id, framework_code, framework_name, provision, what_it_requires,
    #         control_objective, test_approach, is_included}]
    analyser_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ResourcePlan(Base):
    """Resource Planning — hours, milestones, team confirmation."""
    __tablename__ = "resource_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    hours_budget = Column(Integer, nullable=True)
    planned_fieldwork_start = Column(String(20), nullable=True)
    planned_fieldwork_end = Column(String(20), nullable=True)
    planned_report_date = Column(String(20), nullable=True)
    milestones = Column(Text, nullable=True)  # JSON: [{name, date, done}]
    dates_confirmed = Column(Boolean, default=False)
    hours_confirmed = Column(Boolean, default=False)
    team_confirmed = Column(Boolean, default=False)
    head_ia_acknowledged = Column(Boolean, default=False)
    ai_timeline = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WorkProgram(Base):
    """Work Program — planning matrix, Head IA sign-off unlocks Fieldwork."""
    __tablename__ = "work_programs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="draft")
    # draft | generating | ready | signed_off
    rows = Column(Text, nullable=True)
    # JSON: [{id, process, activity, risk_description, control_objective,
    #         test_approach, responsibility, status}]
    signed_off_at = Column(DateTime, nullable=True)
    generator_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DRLDocument(Base):
    """Document Request List — documents requested from the auditee."""
    __tablename__ = "drl_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, unique=True, index=True)
    items = Column(Text, nullable=True)
    # JSON: [{id, document, description, regulatory_basis, requested_from,
    #         category, status, deadline?, validation?}]
    # status: not_requested | requested | received | not_needed
    # deadline: ISO date "YYYY-MM-DD" (optional); overdue is DERIVED, never stored
    # validation: last PBC document-validation result for this item (optional)
    generated_at = Column(DateTime, nullable=True)
    # PBC assistant ("Isabelle") artifacts — modelled, never sent (JSON strings).
    distribution_email = Column(Text, nullable=True)   # {subject, body, contact, drafted_at}
    reminder_log = Column(Text, nullable=True)          # {messages:[...], activity_log, drafted_at}
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FieldworkObservation(Base):
    """Fieldwork observation — a finding, recommendation, good practice, or improvement."""
    __tablename__ = "fieldwork_observations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    obs_type = Column(String(30), nullable=False, default="finding")
    # finding | recommendation | good_practice | improvement
    title = Column(String(500), nullable=False)
    source = Column(String(100), nullable=True)  # e.g. "Process Understanding", "Work Program", "Manual"
    criteria = Column(Text, nullable=True)        # The norm / what was expected
    detailed_observation = Column(Text, nullable=True)  # What was found
    root_cause = Column(Text, nullable=True)
    risk = Column(Text, nullable=True)            # Risk consequence
    linked_wp_row_id = Column(String(36), nullable=True)
    is_ai_generated = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
