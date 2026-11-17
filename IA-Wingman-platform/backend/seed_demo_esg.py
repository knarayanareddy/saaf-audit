"""Seed realistic demo data for the ESG Risk engagement (English).

Run once: python seed_demo_esg.py
"""
import asyncio
import json
from uuid import uuid4

ESG_ID = "d2387f2d-f922-49b2-ba59-5b242c3420a9"

REGULATORY_SUMMARY = """the organisation NL's ESG Risk audit examines how the bank identifies, assesses and manages its sustainability risks — in particular climate risk (physical and transition risk) and environmental, social and governance (ESG) risks across the lending portfolio and investment policy.

The primary regulation is EBA/GL/2021/02 (ESG Risk Guidelines), which DNB adopted as of 1 January 2022 and which requires banks to integrate ESG risks into their risk management framework, ICAAP and strategy. In addition, the SFDR (Sustainable Finance Disclosure Regulation) and the EU Taxonomy Regulation require transparency on the sustainability characteristics of financial products. The CSRD (Corporate Sustainability Reporting Directive) obliges the organisation NL to provide extensive sustainability reporting from financial year 2025.

In its 2023-2024 thematic review, DNB found that Dutch banks are still making insufficient progress integrating climate risk into stress tests and risk models. the organisation scores relatively strongly on mission alignment, but its formal ESG risk management framework and the data infrastructure for climate scenario analysis warrant particular attention in this audit."""

KEY_RISK_AREAS = json.dumps([
    {
        "title": "Climate risk in the lending portfolio",
        "basis": "EBA/GL/2021/02 §4.3 — identification and assessment of climate-related risks in the loan portfolio",
        "rationale": "the organisation provides many loans to sustainable sectors (renewable energy, bio-agriculture), but is also exposed to transition risk from clients dependent on fossil activities",
        "confidence": "high",
        "source": "regulatory_intelligence"
    },
    {
        "title": "SFDR classification and product governance",
        "basis": "SFDR Art. 8/9 — sustainability characteristics of financial products, Principal Adverse Impacts (PAI)",
        "rationale": "Asset Management is also supervised by AFM/ESMA; correct classification of ESG funds and timely PAI reporting are critical",
        "confidence": "high",
        "source": "regulatory_intelligence"
    },
    {
        "title": "ICAAP integration of climate scenarios",
        "basis": "EBA/GL/2021/02 §6 + EBA ICAAP Guidelines — integration of climate risk into capital planning and stress tests",
        "rationale": "DNB expects climate scenarios (2°C / 4°C) to be embedded in the ICAAP; the maturity of the organisation' climate stress tests is unclear",
        "confidence": "high",
        "source": "regulatory_intelligence"
    },
    {
        "title": "ESG data quality and reporting",
        "basis": "CSRD (2025) + EU Taxonomy Regulation Art. 8 — reporting on sustainable activities and ESG KPIs",
        "rationale": "the organisation already reports extensively on ESG voluntarily, but CSRD obligations go deeper; data collection from borrowers is a known challenge",
        "confidence": "medium",
        "source": "regulatory_intelligence"
    },
    {
        "title": "Governance of ESG risk management",
        "basis": "EBA/GL/2021/02 §3 — governance framework, role of the Supervisory Board and risk committee on ESG matters",
        "rationale": "Formal ESG risk governance (Risk Appetite Statement, escalation paths) warrants verification",
        "confidence": "medium",
        "source": "regulatory_intelligence"
    }
])

EXCLUDED_AREAS = json.dumps([
    {
        "title": "T-IM fund management and AIFMD",
        "rationale": "Falls under a separate supervisory regime (AFM); separate audit planned Q3 2026"
    }
])

CONCLUSION = """Recommended audit scope: ESG risk management at the organisation NL, focusing on (1) climate risk integration in the lending portfolio, (2) SFDR compliance for TB NL products, (3) ICAAP climate scenarios, and (4) CSRD readiness for reporting year 2025. T-IM fund management is out of scope for this audit. Expected audit duration: 120-140 hours."""

INTERNAL_FRAMEWORK_SUMMARY = """Based on the uploaded policy documents, the organisation NL operates an ESG Risk Framework (version 3.1, 2024) aligned with EBA/GL/2021/02. The framework distinguishes physical climate risk (floods, drought) from transition risk (carbon pricing, regulation). The credit assessment procedure includes an ESG scorecard per sector. Points of attention from the documents: the ESG scorecard is not yet fully integrated into the credit approval process for loans below €500k, and the climate scenario analyses in the ICAAP 2024 do not yet use DNB-validated scenarios."""

INTERVIEW_AGENDA = json.dumps({
    "sponsor": [
        "What is the primary driver for the ESG Risk audit in 2026 — DNB expectations, board priorities, or internal monitoring?",
        "How is ESG risk anchored in the Risk Appetite Statement of the organisation NL?",
        "Are there recent findings from DNB contact or internal monitoring that require particular attention?",
        "What is the expected timeline for CSRD implementation and who is ultimately responsible?"
    ],
    "sme": [
        "Walk us through the complete ESG risk management process: from identification to reporting to the Supervisory Board",
        "How does the ESG scorecard work in credit assessment — who completes it, who reviews it, how is it weighted?",
        "Which climate scenarios are used in the ICAAP and how were they selected?",
        "How does the organisation collect ESG data from borrowers — what challenges exist with data quality?",
        "How does SFDR PAI reporting work — which systems, which controls, who signs off?",
        "Were there any exceptions or escalations in the ESG risk assessment process in 2024-2025?"
    ],
    "ia_prework": [
        "Request: ESG Risk Framework version 3.1 + all annexes",
        "Request: ICAAP 2024 — climate scenario chapter",
        "Request: ESG scorecard template and completion instructions",
        "Request: SFDR PAI report 2024 (published on website)",
        "Request: Supervisory Board reporting on ESG risks (last 2 meetings)",
        "Request: Outcomes of DNB correspondence on climate risk 2024-2025",
        "Review: the organisation Annual Report 2025 (ESG chapter)"
    ]
})

APPLICABLE_FRAMEWORKS = json.dumps([
    {
        "framework_code": "EBA_ESG",
        "framework_name": "EBA/GL/2021/02 — ESG Risk Guidelines",
        "applicability_rationale": "Primary guideline for ESG risk management at European banks; adopted by DNB as of 1 Jan 2022. Requires integration of ESG into strategy, governance, ICAAP and reporting.",
        "key_articles": ["§3 — Governance", "§4 — ESG risk identification", "§5 — Monitoring", "§6 — ICAAP integration"],
        "confidence": "high",
        "is_primary": True
    },
    {
        "framework_code": "SFDR",
        "framework_name": "SFDR — Sustainable Finance Disclosure Regulation",
        "applicability_rationale": "Requires transparency on sustainability risks and PAI (Principal Adverse Impacts) in financial products. Art. 8/9 classification applies directly to TB NL products.",
        "key_articles": ["Art. 4 — mandatory PAI reporting", "Art. 8 — funds with ESG characteristics", "Art. 9 — sustainable investment funds"],
        "confidence": "high",
        "is_primary": True
    },
    {
        "framework_code": "EU_TAXONOMY",
        "framework_name": "EU Taxonomy Regulation (2020/852)",
        "applicability_rationale": "Requires the organisation to report what percentage of its activities are 'taxonomy-aligned' (Art. 8). Relevant for the lending portfolio and green bonds.",
        "key_articles": ["Art. 8 — disclosure obligations for financial institutions"],
        "confidence": "high",
        "is_primary": False
    },
    {
        "framework_code": "CSRD",
        "framework_name": "CSRD — Corporate Sustainability Reporting Directive",
        "applicability_rationale": "the organisation NL is subject to CSRD (large public-interest entity, listed bonds). ESRS reporting mandatory from financial year 2025.",
        "key_articles": ["ESRS E1 — climate change", "ESRS S1 — own workforce", "ESRS G1 — governance"],
        "confidence": "medium",
        "is_primary": False
    }
])


async def seed():
    import sys
    sys.path.insert(0, '.')
    from database import AsyncSessionLocal, create_tables, run_migrations
    from models.planning import (
        TopicIntelligence, ScopeObjectives, ScopeItem, KeyAuditQuestion,
        ApplicableFramework, RegRequirement, KickoffAgenda, BackgroundRiskAssessment,
        AuditNotificationLetter
    )
    from models.agent_run import AgentRun
    from sqlalchemy import select, delete as sqla_delete
    from services import scope_sources

    await create_tables()
    await run_migrations()

    async with AsyncSessionLocal() as db:
        # ── Topic Intelligence ──────────────────────────────────────────────
        ti_res = await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == ESG_ID))
        ti = ti_res.scalar_one_or_none()
        if not ti:
            ti = TopicIntelligence(id=str(uuid4()), engagement_id=ESG_ID)
            db.add(ti)

        ti.status = "review"
        ti.regulatory_summary = REGULATORY_SUMMARY
        ti.internal_framework_summary = INTERNAL_FRAMEWORK_SUMMARY
        ti.key_risk_areas = KEY_RISK_AREAS
        ti.excluded_areas = EXCLUDED_AREAS
        ti.conclusion = CONCLUSION
        ti.interview_agenda = INTERVIEW_AGENDA
        ti.memo_accepted = False

        fake_run_id = str(uuid4())
        fake_run = AgentRun(
            id=fake_run_id,
            engagement_id=ESG_ID,
            agent_type="regulatory",
            status="complete",
            input_summary="Regulatory intelligence for ESG Risk (TB NL)",
            raw_output=json.dumps({"applicable_frameworks": json.loads(APPLICABLE_FRAMEWORKS)}),
        )
        db.add(fake_run)
        ti.regulatory_run_id = fake_run_id
        await db.commit()
        print("[OK] Topic Intelligence memo seeded")

        # ── Frameworks & Requirements ─────────────────────────────────────────
        await db.execute(sqla_delete(ApplicableFramework).where(ApplicableFramework.engagement_id == ESG_ID))
        await db.commit()

        fw_ids_by_code = {}
        for fw_data in json.loads(APPLICABLE_FRAMEWORKS):
            fw = ApplicableFramework(
                id=str(uuid4()),
                engagement_id=ESG_ID,
                framework_code=fw_data["framework_code"],
                framework_name=fw_data["framework_name"],
                applicability_rationale=fw_data["applicability_rationale"],
                is_primary=fw_data["is_primary"],
                is_accepted=True,
                confidence="high" if fw_data["confidence"] == "high" else "medium",
                source="ai_suggested",
            )
            db.add(fw)
            fw_ids_by_code[fw_data["framework_code"]] = fw.id
        await db.commit()
        print("[OK] Frameworks seeded (4 confirmed)")

        # Fake-completed AgentRun so opening the merged Frameworks & Requirements page
        # doesn't silently re-trigger a real analysis (which would duplicate the frameworks above).
        fake_fr_run = AgentRun(
            id=str(uuid4()),
            engagement_id=ESG_ID,
            agent_type="framework_requirements",
            status="complete",
            input_summary="Frameworks & requirements for ESG Risk (TB NL)",
            search_progress=json.dumps({"stage": "complete"}),
        )
        db.add(fake_fr_run)

        rr_res = await db.execute(select(RegRequirement).where(RegRequirement.engagement_id == ESG_ID))
        rr = rr_res.scalar_one_or_none()
        if not rr:
            rr = RegRequirement(id=str(uuid4()), engagement_id=ESG_ID)
            db.add(rr)
        rr.status = "agreed"
        rr.items = json.dumps([
            {
                "id": "req_1", "framework_id": fw_ids_by_code["EBA_ESG"], "framework_code": "EBA_ESG",
                "framework_name": "EBA/GL/2021/02 — ESG Risk Guidelines", "provision": "§4.3",
                "what_it_requires": "Banks must identify and assess climate-related physical and transition risks in the lending portfolio.",
                "control_objective": "Verify that climate risk is systematically assessed and documented for each credit exposure via the ESG scorecard.",
                "test_approach": "Walkthrough of the credit assessment procedure + sample of 25 client files", "is_included": True,
            },
            {
                "id": "req_2", "framework_id": fw_ids_by_code["SFDR"], "framework_code": "SFDR",
                "framework_name": "SFDR — Sustainable Finance Disclosure Regulation", "provision": "Art. 4",
                "what_it_requires": "Financial market participants must report on Principal Adverse Impacts (PAI) of investment decisions on sustainability factors.",
                "control_objective": "Verify that the 2024 PAI report is complete, accurate and supported by underlying data.",
                "test_approach": "Document inspection of the PAI report + re-performance of 3 PAI indicator calculations", "is_included": True,
            },
            {
                "id": "req_3", "framework_id": fw_ids_by_code["EBA_ESG"], "framework_code": "EBA_ESG",
                "framework_name": "EBA/GL/2021/02 — ESG Risk Guidelines", "provision": "§6",
                "what_it_requires": "Climate scenarios must be integrated into the ICAAP and capital planning process.",
                "control_objective": "Verify that the ICAAP 2024 climate scenarios are based on DNB-recognised (NGFS) scenarios and are validated by the Supervisory Board.",
                "test_approach": "Document inspection of ICAAP 2024 climate chapter + inquiry with Risk Management", "is_included": True,
            },
            {
                "id": "req_4", "framework_id": fw_ids_by_code["CSRD"], "framework_code": "CSRD",
                "framework_name": "CSRD — Corporate Sustainability Reporting Directive", "provision": "ESRS E1",
                "what_it_requires": "Large public-interest entities must report on climate change mitigation and adaptation from financial year 2025.",
                "control_objective": "Verify that the CSRD implementation project is on track to produce ESRS E1-compliant disclosures for FY2025.",
                "test_approach": "Inquiry with the CSRD project team + inspection of the implementation timeline", "is_included": True,
            },
        ])
        await db.commit()
        print("[OK] Regulatory requirements seeded (4 items, agreed)")

        # ── Scope & Objectives ──────────────────────────────────────────────
        scope_res = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == ESG_ID))
        scope = scope_res.scalar_one_or_none()
        if not scope:
            scope = ScopeObjectives(id=str(uuid4()), engagement_id=ESG_ID, status="in_progress")
            db.add(scope)
            await db.commit()
            await db.refresh(scope)

        # Clear existing scope items/questions to avoid duplicates on re-run
        await db.execute(sqla_delete(ScopeItem).where(ScopeItem.scope_id == scope.id))
        await db.execute(sqla_delete(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))
        await db.commit()

        scope.overall_objective = (
            "The objective of the audit is to assess the adequacy and effectiveness of "
            "the organisation NL's ESG risk management framework, in particular the integration of "
            "climate risk into credit assessments, ICAAP stress tests and SFDR product classification, "
            "in accordance with EBA/GL/2021/02 and DNB expectations."
        )
        scope.scope_period = "Jan 2025 - Dec 2025"
        scope.scope_entity = "GRP"
        await db.commit()

        scope_items_data = [
            ("in_scope", "Climate risk integration in the lending portfolio (ESG scorecard, sectoral risk assessments)", "EBA/GL/2021/02 §4 — climate risk identification in lending"),
            ("in_scope", "SFDR PAI reporting 2024 and internal controls around data collection", "SFDR Art. 4 — PAI disclosure obligations"),
            ("in_scope", "ICAAP climate scenarios: methodology, data sources, validation by the Supervisory Board", "EBA/GL/2021/02 §6 + EBA ICAAP Guidelines — climate stress tests"),
            ("in_scope", "ESG governance: Risk Appetite Statement, escalation procedures, Supervisory Board reporting", "EBA/GL/2021/02 §3 — ESG risk governance"),
            ("in_scope", "CSRD readiness: gap analysis, data processes, implementation timeline", "CSRD (2025) — ESRS reporting TB NL"),
            ("out_of_scope", "T-IM fund management and AIFMD compliance", "Separate audit planned Q3 2026"),
            ("out_of_scope", "Green bond framework", "Part of a separate Capital Markets audit"),
        ]
        for i, (item_type, description, rationale) in enumerate(scope_items_data):
            db.add(ScopeItem(
                id=str(uuid4()), scope_id=scope.id,
                item_type=item_type, description=description,
                rationale=rationale, is_accepted=True, sort_order=i,
                **scope_sources.stamp(scope_sources.MANUAL),
            ))

        questions_data = [
            ("Is the ESG risk management framework demonstrably integrated into the ICAAP and RAS of the organisation NL?", "EBA/GL/2021/02 §3+6"),
            ("Are climate risks consistently and fully considered in credit assessment — including for loans below €500k?", "EBA/GL/2021/02 §4.3"),
            ("Does the SFDR PAI reporting 2024 meet all mandatory indicators and is the underlying data demonstrably reliable?", "SFDR Art. 4 + RTS"),
            ("Are the climate scenarios in the ICAAP 2024 based on DNB-recognised scenarios (NGFS)?", "DNB climate expectations + EBA/GL/2021/02 §6"),
            ("Is the organisation NL adequately and timely prepared for the CSRD reporting obligation for financial year 2025?", "CSRD + ESRS E1/S1/G1"),
        ]
        for i, (q_text, basis) in enumerate(questions_data):
            db.add(KeyAuditQuestion(
                id=str(uuid4()), scope_id=scope.id,
                question_text=q_text, regulatory_basis=basis,
                is_accepted=True, sort_order=i,
                **scope_sources.stamp(scope_sources.MANUAL),
            ))
        await db.commit()
        print("[OK] Scope & Objectives seeded (5 in scope, 2 out, 5 key questions)")

        # ── ANL ─────────────────────────────────────────────────────────────
        anl_res = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == ESG_ID))
        anl = anl_res.scalar_one_or_none()
        if not anl:
            anl = AuditNotificationLetter(id=str(uuid4()), engagement_id=ESG_ID)
            db.add(anl)

        anl.status = "draft_ready"
        anl.background = (
            "the organisation NL is a sustainable bank that places ESG considerations at the heart of its core strategy. "
            "The bank has a growing responsibility to formalise its ESG risk management and to comply with the "
            "increasing regulatory requirements in the field of climate and sustainability. "
            "EBA/GL/2021/02 (ESG Risk Guidelines), which DNB adopted as of 1 January 2022, "
            "requires the organisation to structurally integrate its ESG risks into its risk management framework, "
            "ICAAP and strategy."
        )
        anl.objectives = (
            "The objective of the audit is to independently assess the adequacy and effectiveness "
            "of the organisation NL's ESG risk management framework. Specifically, this concerns the integration "
            "of climate risk into the lending portfolio, SFDR PAI reporting, ICAAP climate scenarios, "
            "ESG governance and CSRD readiness."
        )
        anl.scope_description = (
            "The audit covers the period January 2025 to December 2025 at the organisation NL. "
            "In scope: (1) climate risk integration in credit assessments, (2) SFDR PAI reporting, "
            "(3) ICAAP climate scenarios, (4) ESG governance and (5) CSRD readiness."
        )
        anl.out_of_scope = "T-IM fund management and AIFMD compliance; the green bond programme (separate Capital Markets audit)."
        anl.approach = (
            "The audit is conducted through: document analysis (ESG Risk Framework, ICAAP climate chapter, "
            "SFDR PAI report), interviews with the CRO, Head of Risk Management and ESG specialist, "
            "a walkthrough of the ESG scorecard in the credit assessment process, and a sample of "
            "25 credit files for ESG scoring and climate risk assessment."
        )
        anl.timing_fieldwork_start = "2026-09-15"
        anl.timing_fieldwork_end = "2026-10-10"
        anl.timing_draft_report = "2026-10-15"
        anl.timing_final_report = "2026-11-01"
        anl.responsibility = "Internal Audit team, under responsibility of the Head of Internal Audit."
        await db.commit()
        print("[OK] ANL seeded (status: draft_ready)")

        # ── Kickoff Agenda ──────────────────────────────────────────────────
        ko_res = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == ESG_ID))
        ko = ko_res.scalar_one_or_none()
        if not ko:
            ko = KickoffAgenda(id=str(uuid4()), engagement_id=ESG_ID)
            db.add(ko)

        ko.status = "draft_ready"
        ko.meeting_date = "2026-11-01"
        ko.attendees = "IA team (2), CRO, ESG Risk Manager, ESG Specialist, Compliance Officer"
        ko.notes_welcome = "Opening by the IA team lead. Confirmation of attendees and roles. Explanation of the purpose of the kick-off: alignment on scope, planning and document requests."
        ko.notes_context = "ESG Risk is on the 2026 audit plan due to increasing DNB expectations and the CSRD implementation. Audit period: Jan-Dec 2025. Budget: 130 hours."
        ko.notes_scope = "Discuss scope: 5 in-scope areas (climate risk lending, SFDR PAI, ICAAP scenarios, governance, CSRD). T-IM and green bond framework out of scope. Confirmation by auditee."
        ko.notes_risks = "Inherent risks: rapid regulatory developments (CSRD Level 2), data quality at borrowers, climate model uncertainty. Discuss expected control risks."
        ko.notes_documentation = "Available: ESG Risk Framework v3.1, ICAAP 2024, SFDR PAI report 2024, Supervisory Board reporting Q3 2025. Still to be received: credit file sample."
        ko.notes_next_steps = "DRL to be sent within 5 working days. Fieldwork starts 15 September 2026. Draft report expected 15 October 2026. Closing meeting: 1 November 2026."
        await db.commit()
        print("[OK] Kickoff Agenda seeded")

        # ── BRA ─────────────────────────────────────────────────────────────
        bra_res = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == ESG_ID))
        bra = bra_res.scalar_one_or_none()
        if not bra:
            bra = BackgroundRiskAssessment(id=str(uuid4()), engagement_id=ESG_ID)
            db.add(bra)

        bra.status = "draft_ready"
        bra.section_strategy = (
            "the organisation NL has embedded sustainability in its core strategy. The bank finances "
            "exclusively organisations and projects that contribute to people and the environment. "
            "ESG risk management is therefore not a compliance exercise but a strategic core competency. "
            "Principal strategic risk: if the ESG risk assessment framework falls short, "
            "the organisation could incur both transition risk and reputational damage."
        )
        bra.section_governance = (
            "The Supervisory Board has established a Sustainability Committee that receives quarterly reports on "
            "ESG risks. The CRO is ultimately responsible for the ESG Risk Framework. "
            "An ESG Risk Officer reports directly to the CRO. "
            "Internal control measures include an annual ESG scorecard validation "
            "and quarterly climate risk monitoring per portfolio segment."
        )
        bra.section_frameworks = (
            "Applicable frameworks: EBA/GL/2021/02 (ESG Risk), SFDR, EU Taxonomy, CSRD, "
            "DNB Good Practice ESG risk management (2023), NGFS climate scenarios. "
            "the organisation also voluntarily follows: TCFD framework, UN PRI, Science Based Targets initiative."
        )
        bra.section_risk_tolerance = (
            "the organisation accepts no net-negative ESG impact in its financing portfolio. "
            "Climate risk is considered a material financial risk. "
            "The bank has a target to align its portfolio with 1.5°C scenarios."
        )
        bra.risk_items = json.dumps([
            {
                "ref": "R01", "description": "Climate risk in lending portfolio", "is_accepted": True,
                "process": "Credit assessment", "link_to_anl": "Climate risk integration",
                "risk_statement": "Climate-related physical and transition risks are insufficiently considered in credit assessments, resulting in unexpected credit losses.",
                "controls": "ESG scorecard in credit procedure, sectoral climate risk matrix, annual reassessment requirement",
                "inherent_risk": "High", "residual_risk": "Medium"
            },
            {
                "ref": "R02", "description": "SFDR PAI reporting errors", "is_accepted": True,
                "process": "Sustainability reporting", "link_to_anl": "SFDR PAI reporting",
                "risk_statement": "Incorrect or incomplete PAI indicators lead to misleading SFDR disclosure, regulatory breach and reputational damage.",
                "controls": "Four-eyes principle on PAI calculation, external data checks, Compliance review",
                "inherent_risk": "High", "residual_risk": "Medium"
            },
            {
                "ref": "R03", "description": "ICAAP climate scenarios insufficiently robust", "is_accepted": True,
                "process": "ICAAP / Capital planning", "link_to_anl": "ICAAP climate scenarios",
                "risk_statement": "Climate scenarios in the ICAAP do not align with DNB expectations (NGFS), causing capital calculations to be understated.",
                "controls": "Annual ICAAP review by Supervisory Board, validation by Risk Management",
                "inherent_risk": "High", "residual_risk": "High"
            },
            {
                "ref": "R04", "description": "CSRD implementation delay", "is_accepted": True,
                "process": "Sustainability reporting", "link_to_anl": "CSRD readiness",
                "risk_statement": "the organisation NL is not ready in time for CSRD reporting on financial year 2025, resulting in regulatory breach and reputational damage.",
                "controls": "CSRD project team, external adviser, quarterly progress reporting to Supervisory Board",
                "inherent_risk": "Medium", "residual_risk": "Medium"
            },
            {
                "ref": "R05", "description": "ESG data quality at borrowers", "is_accepted": False,
                "process": "Data collection", "link_to_anl": "SFDR PAI reporting",
                "risk_statement": "Low data quality of ESG information from borrowers undermines the reliability of ESG scores and PAI reporting.",
                "controls": "Mandatory ESG questionnaire at loan origination, data estimation methodology for missing data",
                "inherent_risk": "Medium", "residual_risk": "Medium"
            }
        ])
        await db.commit()
        print("[OK] BRA seeded (5 risk items, 4 accepted)")

    print()
    print("[DONE] Demo data for ESG Risk fully seeded (English)!")
    print(f"       Engagement ID: {ESG_ID}")


if __name__ == "__main__":
    asyncio.run(seed())
