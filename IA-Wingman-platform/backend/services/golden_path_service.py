"""Golden-path showcase — fills ONE engagement end-to-end with realistic,
hand-authored content so a demo shows every phase with real data: Topic
Intelligence → Frameworks → Scope → ANL → Kick-off → BRA → Resource plan →
Work Program → DRL → Fieldwork observations → 5C findings → Audit report, plus
an interview guide and an analysed companion session.

No AI is called — the content is fixed, privacy-safe and merk-neutral. Runs on
every startup but is idempotent: it seeds only if the golden engagement has no
Topic Intelligence yet.
"""
import json
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import (
    TopicIntelligence, ApplicableFramework, RegRequirement, ScopeObjectives,
    ScopeItem, KeyAuditQuestion, ProcessNotes, AuditNotificationLetter,
    KickoffAgenda, BackgroundRiskAssessment, ResourcePlan, WorkProgram, DRLDocument,
    FieldworkObservation,
)
from models.reporting import Finding, AuditReport
from services import scope_sources
from models.interview import InterviewGuide, InterviewSession

GOLDEN_NAME = "Customer Due Diligence Onboarding Review"


def _j(x):
    return json.dumps(x)


# Plain-language "what is this topic" primer for the golden engagement, so the
# Topic Intelligence primer block ("What is this topic?") is populated in the demo.
_GOLDEN_TOPIC_PRIMER = (
    "Customer Due Diligence (CDD) at onboarding is how a bank checks who a new customer is "
    "before opening a relationship. It covers verifying the customer's identity, establishing "
    "who ultimately owns or controls a legal-entity customer (the beneficial owner), and "
    "classifying the customer's money-laundering risk so that higher-risk customers receive "
    "enhanced checks. In the EU this is driven by anti-money-laundering law (the AML directives "
    "and national AML acts) and by supervisory expectations (for example from DNB and the EBA). "
    "It matters because weak onboarding controls are a common way criminals enter the financial "
    "system, and supervisors increasingly hold institutions accountable for the quality — not just "
    "the existence — of these controls, including keeping them current through periodic "
    "re-screening after onboarding."
)


# Full, demo-ready work-program rows — every column populated, test approach as
# ordered steps and a priority, matching the CDD spine. Used by both the fresh
# seed and the backfill that heals older databases with minimal rows.
_GOLDEN_WP_ROWS = [
    {"id": "wp_1", "ref": "WP1", "process": "Identity verification",
     "activity": "Test a sample of new onboardings for complete, verified identity evidence.",
     "risk_description": "Incomplete identity verification at onboarding.",
     "control_objective": "Verify that every new customer's identity is verified with complete evidence before the relationship is opened.",
     "test_steps": [
         "Obtain the population of onboardings for the period under review",
         "Select a risk-based sample of 25 files",
         "Inspect each file for complete, verified identity evidence",
         "Record exceptions and conclude on operating effectiveness"],
     "priority": "high", "responsibility": "IA team", "status": "complete"},
    {"id": "wp_2", "ref": "WP2", "process": "Beneficial ownership",
     "activity": "Inspect UBO evidence for a sample of legal-entity customers.",
     "risk_description": "Beneficial ownership not established or evidenced.",
     "control_objective": "Verify that beneficial owners of legal-entity customers are identified and evidenced.",
     "test_steps": [
         "Obtain the population of legal-entity onboardings",
         "Select a sample of 15 entity files",
         "Inspect UBO identification and supporting evidence against the standard",
         "Record exceptions and conclude"],
     "priority": "high", "responsibility": "IA team", "status": "complete"},
    {"id": "wp_3", "ref": "WP3", "process": "Risk classification",
     "activity": "Re-perform risk classification and confirm EDD triggers.",
     "risk_description": "Customer risk rating applied inconsistently, weakening EDD triggers.",
     "control_objective": "Verify that customer risk classification is applied consistently and triggers enhanced due diligence.",
     "test_steps": [
         "Obtain the population of classified customers",
         "Re-perform the risk classification on a sample of 20 customers",
         "Confirm that enhanced due-diligence triggers fired where required",
         "Record exceptions and conclude"],
     "priority": "medium", "responsibility": "IA team", "status": "complete"},
    {"id": "wp_4", "ref": "WP4", "process": "Ongoing due diligence",
     "activity": "Confirm whether periodic re-screening is scheduled and performed.",
     "risk_description": "Risk-profile drift and status changes undetected after onboarding.",
     "control_objective": "Verify that periodic re-screening after onboarding is scheduled and performed.",
     "test_steps": [
         "Inquire whether a periodic re-screening control exists and is scheduled",
         "Inspect evidence of re-screening runs for the period",
         "Confirm coverage against the customer population",
         "Conclude on the design and existence of the control"],
     "priority": "high", "responsibility": "IA team", "status": "complete"},
]


async def seed_golden_path():
    async with AsyncSessionLocal() as db:
        # first(), not scalar_one_or_none(): a duplicate golden engagement must
        # never crash startup — just fill the first match.
        eng = (await db.execute(select(Engagement).where(Engagement.name == GOLDEN_NAME))).scalars().first()
        if not eng:
            return
        eid = eng.id
        exists = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == eid))).scalars().first()
        if exists:
            return  # idempotent

        if not eng.lead_auditor:
            eng.lead_auditor = "Lead auditor (to confirm)"

        # ── Topic Intelligence (agreed) ──────────────────────────────────────
        db.add(TopicIntelligence(
            id=str(uuid4()), engagement_id=eid, status="agreed", memo_accepted=True, progress_pct=100,
            regulatory_summary="Customer due diligence (CDD) at onboarding is governed by AML/CFT law and supervisory guidance. Institutions must identify and verify customers before establishing a business relationship, apply a risk-based approach, and perform enhanced due diligence for higher-risk relationships.",
            lens1_summary="Regulatory lens: AML directives and national AML acts require identification, verification and beneficial-ownership checks before onboarding, with a documented risk-based approach.",
            lens1_sources=_j([{"title": "EU AML Directive (consolidated)", "url": "https://eur-lex.europa.eu", "confidence": "high"}]),
            lens2_summary="Supervisory lens: recent supervisory reviews emphasise ongoing monitoring, timely re-screening and quality of beneficial-ownership evidence.",
            lens2_sources=_j([{"title": "Supervisory thematic review on CDD", "url": "https://example-supervisor.eu"}]),
            lens3_summary="Society lens: rising public and media scrutiny of onboarding fraud and identity misuse raises reputational materiality.",
            lens3_sources=_j([{"title": "Sector incident coverage", "url": "https://example-news.eu", "materiality_signal": "elevated"}]),
            key_risk_areas=_j([
                {"title": "Identity verification completeness", "rationale": "Incomplete or unverified identity evidence at onboarding.", "basis": "AMLD identification requirements", "source": "Regulatory lens", "confidence": "high"},
                {"title": "Beneficial ownership transparency", "rationale": "UBO not established or evidenced for legal-entity customers.", "basis": "AMLD UBO provisions", "source": "Regulatory lens", "confidence": "high"},
                {"title": "Risk-based classification", "rationale": "Customer risk rating not consistently applied, weakening EDD triggers.", "basis": "Risk-based approach", "source": "Supervisory lens", "confidence": "medium"},
                {"title": "Ongoing monitoring & re-screening", "rationale": "No periodic re-screening after onboarding.", "basis": "Ongoing due diligence", "source": "Supervisory lens", "confidence": "high"},
            ]),
            excluded_areas=_j([{"title": "Transaction monitoring tuning", "rationale": "Covered by a separate dedicated audit; out of scope here."}]),
            conclusion="Focus scope on onboarding identity verification, UBO evidence, risk classification and the absence of periodic re-screening.",
            topic_primer=_GOLDEN_TOPIC_PRIMER,
        ))

        # ── Frameworks + requirements (agreed) ───────────────────────────────
        for code, name, rat, prov, primary in [
            ("AMLD", "Anti-Money-Laundering Directive", "Core CDD obligations at onboarding.", "Identification & verification before business relationship", True),
            ("AML-Act", "National AML Act", "Local transposition of CDD and UBO duties.", "Beneficial ownership identification", False),
            ("FATF-R10", "FATF Recommendation 10", "International CDD standard.", "Customer due diligence measures", False),
        ]:
            db.add(ApplicableFramework(
                id=str(uuid4()), engagement_id=eid, framework_code=code, framework_name=name,
                applicability_rationale=rat, specific_provision=prov, confidence="high",
                jurisdiction="EU", is_primary=primary, is_accepted=True, source="ai_suggested",
            ))
        db.add(RegRequirement(
            id=str(uuid4()), engagement_id=eid, status="agreed",
            items=_j([
                {"code": "AMLD-Art.13", "requirement": "Identify and verify the customer before onboarding.", "is_included": True},
                {"code": "AMLD-UBO", "requirement": "Identify and evidence beneficial owners.", "is_included": True},
                {"code": "AMLD-RBA", "requirement": "Apply a documented risk-based classification.", "is_included": True},
                {"code": "AMLD-Ongoing", "requirement": "Perform ongoing due diligence and re-screening.", "is_included": True},
            ]),
        ))

        # ── Supervisory guidance (soft law — sibling of Laws & Regulations) ───
        for code, name, issuer, gtype, rat, primary in [
            ("EBA-GL-2021-02", "EBA Guidelines on ML/TF risk factors (EBA/GL/2021/02)", "EBA", "Guideline",
             "Sets supervisory expectations for applying a risk-based approach to customer due diligence.", True),
            ("DNB-GP-CDD", "DNB good practices — Customer Due Diligence at onboarding", "DNB", "Good practice",
             "Illustrates DNB's expectations for identity verification and UBO evidencing at intake.", False),
        ]:
            db.add(ApplicableFramework(
                id=str(uuid4()), engagement_id=eid, framework_code=code, framework_name=name,
                applicability_rationale=rat, specific_provision=gtype, confidence="high",
                jurisdiction="EU" if issuer == "EBA" else "NL", category="guidance",
                is_primary=primary, is_accepted=True, source="guidance_analysed",
            ))

        # ── Scope & objectives (all accepted) ────────────────────────────────
        scope = ScopeObjectives(
            id=str(uuid4()), engagement_id=eid, status="agreed",
            overall_objective="Assess the design and operating effectiveness of customer due diligence controls at onboarding.",
            scope_period="FY2026 H1", scope_entity="GRP",
        )
        db.add(scope)
        for i, (t, desc) in enumerate([
            ("in_scope", "Identity verification controls for new individual customers"),
            ("in_scope", "Beneficial-ownership identification for legal-entity customers"),
            ("in_scope", "Customer risk classification and EDD triggering"),
            ("in_scope", "Periodic re-screening after onboarding"),
            ("out_of_scope", "Transaction monitoring rule tuning (separate audit)"),
        ]):
            db.add(ScopeItem(id=str(uuid4()), scope_id=scope.id, item_type=t, description=desc,
                             is_accepted=True, sort_order=i,
                             **scope_sources.stamp(scope_sources.MANUAL)))
        for i, (q, basis) in enumerate([
            ("Are identity verification controls operating effectively for all new customers?", "AMLD-Art.13"),
            ("Is beneficial ownership established and evidenced for legal-entity customers?", "AMLD-UBO"),
            ("Is the risk-based classification applied consistently and does it trigger EDD?", "AMLD-RBA"),
            ("Is periodic re-screening performed after onboarding?", "AMLD-Ongoing"),
        ]):
            db.add(KeyAuditQuestion(id=str(uuid4()), scope_id=scope.id, question_text=q,
                                    regulatory_basis=basis, is_accepted=True, sort_order=i,
                                    **scope_sources.stamp(scope_sources.MANUAL)))

        # ── Process understanding (agreed) ───────────────────────────────────
        db.add(ProcessNotes(
            id=str(uuid4()), engagement_id=eid, status="agreed",
            notes="Onboarding runs through the digital intake flow with manual review for higher-risk cases.",
            process_items=_j([
                {"id": "p1", "name": "Digital intake & identity capture", "is_included": True},
                {"id": "p2", "name": "Beneficial-ownership review", "is_included": True},
                {"id": "p3", "name": "Risk classification & EDD routing", "is_included": True},
            ]),
            preliminary_observations=_j([
                {"text": "No scheduled re-screening control after onboarding.", "source": "Process walkthrough"},
                {"text": "UBO evidence stored inconsistently across cases.", "source": "Process walkthrough"},
            ]),
        ))

        # ── ANL (approved) ───────────────────────────────────────────────────
        db.add(AuditNotificationLetter(
            id=str(uuid4()), engagement_id=eid, status="approved", head_ia_status="approved",
            background="Customer due diligence at onboarding is a key AML control and a supervisory focus area.",
            objectives="To assess the design and operating effectiveness of CDD controls at onboarding.",
            scope_description="Identity verification, beneficial ownership, risk classification and re-screening for new customers in FY2026 H1.",
            out_of_scope="Transaction monitoring rule tuning is covered by a separate audit.",
            approach="Walkthroughs, control testing on a sample of onboardings, and evidence inspection.",
            timing_fieldwork_start="2026-03-02", timing_fieldwork_end="2026-03-27",
            timing_draft_report="2026-04-10", timing_mgmt_response="2026-04-24", timing_final_report="2026-05-01",
            responsibility="Provide onboarding case files, policy documents and system access.",
        ))

        # ── Kick-off (draft ready) ───────────────────────────────────────────
        db.add(KickoffAgenda(
            id=str(uuid4()), engagement_id=eid, status="draft_ready",
            meeting_date="2026-02-24", attendees="Audit sponsor, Onboarding lead, Compliance",
            notes_welcome="Confirm objectives and scope of the CDD onboarding review.",
            notes_context="Audit is in the annual plan due to AML materiality and supervisory focus.",
            notes_scope="Identity, UBO, risk classification, re-screening.",
            notes_next_steps="Share document request list; confirm fieldwork dates.",
        ))

        # ── BRA (draft ready, risks accepted) ────────────────────────────────
        db.add(BackgroundRiskAssessment(
            id=str(uuid4()), engagement_id=eid, status="draft_ready",
            section_strategy="Growth in digital onboarding increases inherent AML risk.",
            section_risk_tolerance="Low tolerance for AML control failures.",
            section_governance="First-line onboarding ops; second-line compliance monitoring.",
            section_frameworks="AMLD, national AML Act, FATF R.10.",
            risk_items=_j([
                {"ref": "R1", "description": "Incomplete identity verification", "process": "Digital intake", "risk_statement": "Customers onboarded without complete verified identity.", "inherent_risk": "High", "controls": "Automated ID checks", "residual_risk": "Medium", "is_accepted": True},
                {"ref": "R2", "description": "UBO not evidenced", "process": "UBO review", "risk_statement": "Beneficial owners not established for entities.", "inherent_risk": "High", "controls": "Manual UBO review", "residual_risk": "Medium", "is_accepted": True},
                {"ref": "R3", "description": "No periodic re-screening", "process": "Ongoing DD", "risk_statement": "Risk drift undetected after onboarding.", "inherent_risk": "High", "controls": "None scheduled", "residual_risk": "High", "is_accepted": True},
            ]),
        ))

        # ── Resource plan (all confirmed) ────────────────────────────────────
        db.add(ResourcePlan(
            id=str(uuid4()), engagement_id=eid, hours_budget=180,
            planned_fieldwork_start="2026-03-02", planned_fieldwork_end="2026-03-27", planned_report_date="2026-05-01",
            milestones=_j([{"name": "Kick-off", "date": "2026-02-24", "done": True},
                           {"name": "Fieldwork", "date": "2026-03-02", "done": True},
                           {"name": "Draft report", "date": "2026-04-10", "done": False}]),
            dates_confirmed=True, hours_confirmed=True, team_confirmed=True, head_ia_acknowledged=True,
        ))

        # ── Work program (signed off → fieldwork unlocked) ───────────────────
        db.add(WorkProgram(
            id=str(uuid4()), engagement_id=eid, status="signed_off",
            rows=_j(_GOLDEN_WP_ROWS),
        ))

        # ── DRL ──────────────────────────────────────────────────────────────
        db.add(DRLDocument(
            id=str(uuid4()), engagement_id=eid,
            generated_at=None,
            items=_j([
                {"id": "D1", "document": "CDD / onboarding policy and procedures", "description": "Current policy and procedure documents.", "regulatory_basis": "AMLD-Art.13", "requested_from": "Compliance", "category": "Policy", "status": "requested"},
                {"id": "D2", "document": "Sample of 25 onboarding case files (FY2026 H1)", "description": "Case files for control testing.", "regulatory_basis": "AMLD-RBA", "requested_from": "Onboarding ops", "category": "Evidence", "status": "requested"},
                {"id": "D3", "document": "Customer risk-classification methodology", "description": "Methodology and thresholds.", "regulatory_basis": "AMLD-RBA", "requested_from": "Compliance", "category": "Methodology", "status": "requested"},
                {"id": "D4", "document": "Re-screening schedule and evidence", "description": "Evidence of periodic re-screening, if any.", "regulatory_basis": "AMLD-Ongoing", "requested_from": "Onboarding ops", "category": "Evidence", "status": "requested"},
            ]),
        ))

        # ── Fieldwork observations (findings) ────────────────────────────────
        obs_specs = [
            ("No periodic re-screening after onboarding", "AMLD ongoing due-diligence duty",
             "Customers are not re-screened on a periodic basis after onboarding.", "No scheduled control exists.",
             "Risk profile drift and sanctions/PEP status changes go undetected."),
            ("Inconsistent beneficial-ownership evidence", "AMLD UBO provisions",
             "UBO evidence was missing or inconsistent in 4 of 15 legal-entity files.", "No standard UBO evidence checklist.",
             "Entities may be onboarded without verified beneficial owners."),
        ]
        obs_ids = []
        for i, (title, crit, cond, cause, risk) in enumerate(obs_specs):
            oid = str(uuid4())
            obs_ids.append(oid)
            db.add(FieldworkObservation(
                id=oid, engagement_id=eid, obs_type="finding", title=title, source="Work Program",
                criteria=crit, detailed_observation=cond, root_cause=cause, risk=risk,
                is_ai_generated=False, sort_order=i,
            ))
        db.add(FieldworkObservation(
            id=str(uuid4()), engagement_id=eid, obs_type="good_practice",
            title="Automated identity verification well embedded", source="Work Program",
            detailed_observation="Automated ID verification performed reliably across the sample.", sort_order=2,
        ))

        # ── 5C findings (ready, with rating challenge) ───────────────────────
        db.add(Finding(
            id=str(uuid4()), engagement_id=eid, source_observation_id=obs_ids[0],
            title="Absence of periodic customer re-screening",
            condition="Customers are not re-screened after onboarding; there is no scheduled control.",
            criteria="AML law requires ongoing due diligence, including periodic re-screening on a risk basis.",
            cause="No control was designed for post-onboarding re-screening.",
            effect="Changes in sanctions/PEP status or risk profile go undetected, increasing AML exposure.",
            recommendation="Design and implement a risk-based periodic re-screening control with defined frequency and evidence.",
            rating="high", rating_rationale="High inherent AML risk with no mitigating control.",
            rating_challenge=_j({"agrees": True, "suggested_rating": "high", "rationale": "Absence of any control on a high inherent risk supports a high rating."}),
            status="ready", sort_order=0,
        ))
        db.add(Finding(
            id=str(uuid4()), engagement_id=eid, source_observation_id=obs_ids[1],
            title="Inconsistent beneficial-ownership evidence",
            condition="UBO evidence was missing or inconsistent in 4 of 15 legal-entity onboarding files.",
            criteria="Beneficial owners must be identified and evidenced before onboarding.",
            cause="No standard UBO evidence checklist or quality control.",
            effect="Legal-entity customers may be onboarded without verified beneficial ownership.",
            recommendation="Introduce a mandatory UBO evidence checklist with a second-line quality check.",
            rating="medium", rating_rationale="Partial control failure on a sample; not systemic.",
            rating_challenge=_j({"agrees": False, "suggested_rating": "high", "rationale": "27% failure rate on a core AML control may warrant a high rating; reviewer suggests reconsidering."}),
            status="ready", sort_order=1,
        ))

        # ── Audit report (ready) ─────────────────────────────────────────────
        db.add(AuditReport(
            id=str(uuid4()), engagement_id=eid, overall_opinion="needs_improvement",
            exec_summary="Customer due diligence at onboarding is largely effective for identity verification, but two control gaps require attention: the absence of periodic re-screening (high) and inconsistent beneficial-ownership evidence (medium). Automated identity verification is well embedded.",
            conclusion="With the recommended re-screening control and a UBO evidence checklist, residual AML risk at onboarding would return to an acceptable level.",
            status="ready",
        ))

        # ── Interview guide (ready) ──────────────────────────────────────────
        db.add(InterviewGuide(
            id=str(uuid4()), engagement_id=eid, status="ready",
            personas=_j([
                {"persona": "sponsor", "role_label": "Audit sponsor / senior management",
                 "goal": "Understand strategic risk appetite and known onboarding issues.",
                 "opening": "Thanks for making time — I'd like to understand how you see onboarding risk.",
                 "questions": [
                     {"text": "What are your main concerns about onboarding risk?", "follow_ups": ["Any known incidents?", "How is risk appetite set?"], "traceability": {"type": "risk", "ref": "Risk-based classification"}},
                     {"text": "How is CDD performance reported to you?", "follow_ups": ["What metrics?"], "traceability": {"type": "framework", "ref": "AMLD-RBA"}},
                 ]},
                {"persona": "process_owner", "role_label": "Onboarding process owner (first line)",
                 "goal": "Walk through the onboarding controls and exceptions.",
                 "opening": "Could you walk me through what happens when a new customer applies?",
                 "questions": [
                     {"text": "Walk me through identity verification for a new customer.", "follow_ups": ["What happens on a failed check?", "Who reviews exceptions?"], "traceability": {"type": "risk", "ref": "Identity verification completeness"}},
                     {"text": "How is beneficial ownership evidenced for entities?", "follow_ups": ["Where is evidence stored?"], "traceability": {"type": "risk", "ref": "Beneficial ownership transparency"}},
                     {"text": "Is there any re-screening after onboarding?", "follow_ups": ["What frequency?", "Any evidence?"], "traceability": {"type": "risk", "ref": "Ongoing monitoring & re-screening"}},
                 ]},
                {"persona": "second_line", "role_label": "Compliance (second line)",
                 "goal": "Understand monitoring and control design assurance.",
                 "opening": "I'd like to understand how second line monitors onboarding quality.",
                 "questions": [
                     {"text": "How do you monitor onboarding CDD quality?", "follow_ups": ["Sampling approach?"], "traceability": {"type": "framework", "ref": "AMLD-Ongoing"}},
                 ]},
                {"persona": "operator", "role_label": "Onboarding operator (first line)",
                 "goal": "Understand day-to-day practice and workarounds.",
                 "opening": "Tell me about a typical onboarding from your side.",
                 "questions": [
                     {"text": "What do you do when UBO information is unclear?", "follow_ups": ["Any workarounds?"], "traceability": {"type": "risk", "ref": "Beneficial ownership transparency"}},
                 ]},
            ]),
            coverage=_j({"summary": "The guide covers all four key risk areas.",
                         "covered": ["Identity verification completeness", "Beneficial ownership transparency", "Risk-based classification", "Ongoing monitoring & re-screening"],
                         "gaps": []}),
        ))

        # ── Interview companion session (analysed) ───────────────────────────
        db.add(InterviewSession(
            id=str(uuid4()), engagement_id=eid, persona="process_owner",
            label="Process owner — onboarding", status="ready",
            notes="The process owner explained that identity checks are automated, UBO is reviewed manually and stored in case notes, and there is no scheduled re-screening after onboarding.",
            analysis=_j({
                "summary": "Onboarding relies on automated identity checks and manual UBO review; there is no periodic re-screening control.",
                "follow_ups": ["How are high-risk customers re-assessed over time?", "Where exactly is UBO evidence retained?"],
                "observations": [
                    {"text": "UBO evidence retention is inconsistent.", "confidence": "medium"},
                    {"text": "No post-onboarding re-screening exists.", "confidence": "high"},
                ],
                "control_gaps": [
                    {"text": "Possible gap: no ongoing due-diligence trigger after onboarding.", "verify": "Check for a scheduled re-screening control and its evidence."},
                ],
                "minutes": [
                    "Identity verification is automated and reliable.",
                    "Beneficial ownership is reviewed manually and stored in case notes.",
                    "No periodic re-screening is scheduled after onboarding.",
                ],
            }),
        ))

        await db.commit()


async def backfill_golden_demo_content():
    """Self-heal older databases whose golden engagement predates later demo content:
    the work program seeded with minimal rows (no control objective, test steps, id,
    priority) and the Topic Intelligence without a plain-language primer. Idempotent:
    each part only rewrites when its enriched content is absent; sign-off is preserved."""
    async with AsyncSessionLocal() as db:
        eng = (await db.execute(
            select(Engagement).where(Engagement.name == GOLDEN_NAME)
        )).scalars().first()
        if not eng:
            return

        wp = (await db.execute(
            select(WorkProgram).where(WorkProgram.engagement_id == eng.id)
        )).scalars().first()
        if wp:
            try:
                rows = json.loads(wp.rows) if wp.rows else []
            except (json.JSONDecodeError, TypeError):
                rows = []
            if not (rows and all(r.get("test_steps") and r.get("id") for r in rows)):
                wp.rows = _j(_GOLDEN_WP_ROWS)

        ti = (await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == eng.id)
        )).scalars().first()
        if ti and not (ti.topic_primer or "").strip():
            ti.topic_primer = _GOLDEN_TOPIC_PRIMER

        await db.commit()


# Backwards-compatible alias (older wiring imported this name).
backfill_golden_work_program = backfill_golden_demo_content
