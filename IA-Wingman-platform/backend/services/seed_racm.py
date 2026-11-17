"""Golden-path RACM spine — fills the showcase engagement's Risk-and-Control
Matrix so the spine view renders with real, coherent data on a fresh demo.

The chain is derived from the same CDD-onboarding content the golden path already
seeds (identity verification, beneficial ownership, risk classification,
re-screening), so the whole app stays consistent. It deliberately mixes accepted
human/cascaded nodes with a few AI-proposed-but-unaccepted nodes to demonstrate
the governance principle "AI proposed · you own".

No AI is called. Runs on every startup but is idempotent: it seeds only if the
golden engagement has no RACM objectives yet.
"""
import json
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.racm import (
    RacmObjective, RacmRisk, RacmControl, RacmTest, RacmEvidence, ScopeDecision,
)
from services.golden_path_service import GOLDEN_NAME


def _prov(source_type, source_ref, rationale=None, run_id=None):
    return json.dumps({"source_type": source_type, "source_ref": source_ref,
                       "rationale": rationale, "run_id": run_id})


async def seed_racm():
    async with AsyncSessionLocal() as db:
        # first(), not scalar_one_or_none(): a duplicate golden engagement must
        # never crash startup — just seed against the first match.
        eng = (await db.execute(
            select(Engagement).where(Engagement.name == GOLDEN_NAME)
        )).scalars().first()
        if not eng:
            return
        eid = eng.id
        exists = (await db.execute(
            select(RacmObjective.id).where(RacmObjective.engagement_id == eid).limit(1)
        )).first()
        if exists:
            await _ensure_demo_finding(db, eid)  # backfill on already-seeded DBs
            return  # idempotent

        def add(model, **kw):
            obj = model(id=str(uuid4()), engagement_id=eid, **kw)
            db.add(obj)
            return obj

        # ── Objectives ───────────────────────────────────────────────────────
        o1 = add(RacmObjective, ref="O1", sort_order=0, origin="human", accepted=True,
                 accepted_by="DA",
                 title="CDD controls at onboarding operate effectively",
                 description="New customers are correctly identified, verified and risk-classified before a business relationship starts.",
                 provenance=_prov("scope_objective", "Overall objective"))
        o2 = add(RacmObjective, ref="O2", sort_order=1, origin="human", accepted=True,
                 accepted_by="DA",
                 title="Ongoing due diligence keeps customer risk current",
                 description="Customer risk and screening status stay up to date after onboarding.",
                 provenance=_prov("scope_objective", "Overall objective"))

        # ── Risks ────────────────────────────────────────────────────────────
        r1 = add(RacmRisk, ref="R1", sort_order=0, objective_id=o1.id, category="KYC",
                 inherent_rating="high", origin="human", accepted=True, accepted_by="DA",
                 confidence="high",
                 title="Incomplete identity verification",
                 description="Customers onboarded without complete, verified identity evidence.",
                 provenance=_prov("bra", "R1"))
        r2 = add(RacmRisk, ref="R2", sort_order=1, objective_id=o1.id, category="UBO",
                 inherent_rating="high", origin="human", accepted=True, accepted_by="DA",
                 confidence="high",
                 title="Beneficial ownership not evidenced",
                 description="Beneficial owners of legal-entity customers not established or evidenced.",
                 provenance=_prov("bra", "R2"))
        r3 = add(RacmRisk, ref="R3", sort_order=2, objective_id=o1.id, category="RBA",
                 inherent_rating="medium", origin="human", accepted=True, accepted_by="DA",
                 confidence="medium",
                 title="Inconsistent risk classification",
                 description="Customer risk rating not applied consistently, weakening EDD triggers.",
                 provenance=_prov("topic_intelligence", "Supervisory lens"))
        # AI-proposed, not yet accepted — demonstrates the "you own" flip.
        r4 = add(RacmRisk, ref="R4", sort_order=3, objective_id=o2.id, category="Ongoing DD",
                 inherent_rating="high", origin="ai", accepted=False, confidence="high",
                 title="No periodic re-screening after onboarding",
                 description="Risk-profile drift and sanctions/PEP status changes go undetected after onboarding.",
                 provenance=_prov("topic_intelligence", "Supervisory lens",
                                  rationale="Ongoing due-diligence duty with no scheduled control detected in process notes."))

        # ── Controls ─────────────────────────────────────────────────────────
        c1 = add(RacmControl, ref="C1", sort_order=0, risk_id=r1.id, control_type="preventive",
                 frequency="Per onboarding", owner="Onboarding ops",
                 design_conclusion="effective", origin="human", accepted=True, accepted_by="DA",
                 confidence="high",
                 title="Automated identity verification",
                 description="Automated ID document and identity checks run before the relationship is opened.",
                 provenance=_prov("process_notes", "Digital intake & identity capture"))
        c2 = add(RacmControl, ref="C2", sort_order=1, risk_id=r2.id, control_type="detective",
                 frequency="Per onboarding", owner="Onboarding ops",
                 design_conclusion="deficient", origin="human", accepted=True, accepted_by="DA",
                 confidence="medium",
                 title="Manual beneficial-ownership review",
                 description="UBO reviewed manually; no standard evidence checklist, evidence stored inconsistently.",
                 provenance=_prov("process_notes", "Beneficial-ownership review"))
        c3 = add(RacmControl, ref="C3", sort_order=2, risk_id=r3.id, control_type="preventive",
                 frequency="Per onboarding", owner="Compliance",
                 design_conclusion="not_assessed", origin="human", accepted=True, accepted_by="DA",
                 title="Customer risk-classification methodology",
                 description="Risk classification applied at intake to trigger enhanced due diligence.",
                 provenance=_prov("process_notes", "Risk classification & EDD routing"))
        # AI-proposed control that captures the gap: none is scheduled today.
        c4 = add(RacmControl, ref="C4", sort_order=3, risk_id=r4.id, control_type="detective",
                 frequency="Not scheduled", owner="Onboarding ops",
                 design_conclusion="deficient", origin="ai", accepted=False, confidence="high",
                 title="Periodic re-screening control",
                 description="No scheduled post-onboarding re-screening control currently exists.",
                 provenance=_prov("process_notes", "Preliminary observations",
                                  rationale="Process walkthrough noted no scheduled re-screening control."))

        # ── Tests ────────────────────────────────────────────────────────────
        t1 = add(RacmTest, ref="T1", sort_order=0, control_id=c1.id, method="sampling",
                 sample_size=25, exceptions_count=0, result="pass",
                 origin="human", accepted=True, accepted_by="DA",
                 title="Identity evidence on a sample of onboardings",
                 description="Test a sample of new onboardings for complete verified identity evidence.",
                 conclusion="No exceptions in 25 sampled files; control operating effectively.",
                 provenance=_prov("work_program", "WP1"))
        t2 = add(RacmTest, ref="T2", sort_order=1, control_id=c2.id, method="sampling",
                 sample_size=15, exceptions_count=4, result="exceptions",
                 origin="human", accepted=True, accepted_by="DA",
                 title="UBO evidence inspection",
                 description="Inspect UBO evidence for a sample of legal-entity customers.",
                 conclusion="UBO evidence missing or inconsistent in 4 of 15 files (27%).",
                 provenance=_prov("work_program", "WP2"))
        # AI-proposed test, still pending.
        t3 = add(RacmTest, ref="T3", sort_order=2, control_id=c3.id, method="reperformance",
                 result="pending", origin="ai", accepted=False, confidence="medium",
                 title="Re-perform risk classification",
                 description="Re-perform risk classification on a sample and confirm EDD triggers fire.",
                 provenance=_prov("work_program", "WP3",
                                  rationale="Methodology present but operating effectiveness not yet assessed."))
        t4 = add(RacmTest, ref="T4", sort_order=3, control_id=c4.id, method="inquiry",
                 sample_size=0, exceptions_count=1, result="fail",
                 origin="human", accepted=True, accepted_by="DA",
                 title="Confirm re-screening is scheduled and performed",
                 description="Confirm whether periodic re-screening is scheduled and evidenced.",
                 conclusion="No scheduled re-screening control found — design gap confirmed.",
                 provenance=_prov("work_program", "WP4"))

        # ── Evidence ─────────────────────────────────────────────────────────
        add(RacmEvidence, ref="E1", sort_order=0, test_id=t1.id, kind="document",
            origin="human", accepted=True, accepted_by="DA",
            title="Onboarding case-file sample (25 files)",
            description="Sampled FY2026 H1 onboarding case files with identity evidence.",
            provenance=_prov("drl", "D2"))
        add(RacmEvidence, ref="E2", sort_order=1, test_id=t2.id, kind="document",
            origin="human", accepted=True, accepted_by="DA",
            title="UBO evidence review workpaper",
            description="Workpaper recording UBO evidence per entity file; 4 exceptions.",
            provenance=_prov("drl", "D2"))
        add(RacmEvidence, ref="E3", sort_order=2, test_id=t4.id, kind="interview",
            origin="human", accepted=True, accepted_by="DA",
            title="Process-owner interview — no re-screening",
            description="Process owner confirmed there is no scheduled re-screening after onboarding.",
            provenance=_prov("interview", "Process owner — onboarding"))

        # ── Scope decisions (governance log) ─────────────────────────────────
        add(ScopeDecision, sort_order=0, decision_type="in_scope", status="approved",
            origin="human", linked_objective_id=o1.id, sponsor="Audit sponsor",
            summary="Identity verification, beneficial ownership, risk classification and re-screening are in scope.",
            rationale="Core CDD controls with high AML materiality and supervisory focus.")
        add(ScopeDecision, sort_order=1, decision_type="out_of_scope", status="approved",
            origin="human", sponsor="Audit sponsor",
            summary="Transaction monitoring rule tuning is out of scope.",
            rationale="Covered by a separate dedicated audit; excluded to avoid overlap.")
        add(ScopeDecision, sort_order=2, decision_type="materiality", status="approved",
            origin="human", sponsor="Audit sponsor",
            summary="Low tolerance for AML control failures at onboarding.",
            materiality="Any systemic CDD control failure is treated as material.")
        add(ScopeDecision, sort_order=3, decision_type="reliance", status="proposed",
            origin="ai",
            summary="Consider relying on second-line compliance monitoring for ongoing screening quality.",
            rationale="Second line performs periodic monitoring; reliance could reduce substantive testing if evidenced.")

        await db.commit()
        await _ensure_demo_finding(db, eid)


async def _ensure_demo_finding(db, eid: str):
    """Deterministically promote the golden UBO test (T2) to a 5C finding so the
    reporting demo has one finding with a full O→R→C→T→E grounding trail. No AI;
    idempotent (one finding per test)."""
    from models.reporting import Finding

    t2 = (await db.execute(
        select(RacmTest).where(RacmTest.engagement_id == eid, RacmTest.ref == "T2")
    )).scalars().first()
    if not t2:
        return
    if (await db.execute(select(Finding.id).where(Finding.racm_test_id == t2.id))).first():
        return  # already promoted

    control = await db.get(RacmControl, t2.control_id) if t2.control_id else None
    risk = await db.get(RacmRisk, control.risk_id) if control and control.risk_id else None
    objective = await db.get(RacmObjective, risk.objective_id) if risk and risk.objective_id else None

    norm = []
    if control:
        norm.append(f"Control '{control.title}' is expected to operate effectively.")
    if risk:
        norm.append(f"It must mitigate the risk '{risk.title}'.")
    if objective:
        norm.append(f"This supports the objective '{objective.title}'.")

    ex = t2.exceptions_count or 0
    last = (await db.execute(
        select(Finding).where(Finding.engagement_id == eid).order_by(Finding.sort_order.desc())
    )).scalars().first()
    db.add(Finding(
        id=str(uuid4()), engagement_id=eid, racm_test_id=t2.id,
        title=(f"Control-testing exceptions — {control.title}" if control else "Control-testing exceptions")[:500],
        condition=t2.conclusion or f"Testing '{t2.title}' found {ex} exception(s) in {t2.sample_size or 0} item(s).",
        criteria=" ".join(norm) or "The control is expected to operate effectively.",
        cause="No standard evidence checklist for beneficial-ownership review.",
        effect=(risk.description or risk.title) if risk else "The control weakness may go undetected.",
        recommendation="Introduce a standard UBO evidence checklist and second-line review.",
        rating=(risk.inherent_rating if risk and risk.inherent_rating in ("high", "medium", "low") else "medium"),
        rating_rationale=f"Proposed from inherent risk rating and {ex} testing exception(s).",
        status="draft",
        sort_order=(last.sort_order + 1) if last else 0,
    ))
    await db.commit()
