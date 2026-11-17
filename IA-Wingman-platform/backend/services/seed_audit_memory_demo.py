"""Audit-memory demo enrichment — gives one topic-adjacent prior audit some
findings + RACM data so the golden CDD/AML engagement's Audit Memory recall
surfaces a strong, relevant precedent. Deterministic, idempotent, white-label;
never touches the golden engagement.

'Sanctions Screening Process' (in_reporting) is the natural neighbour of the
golden 'Customer Due Diligence Onboarding Review': both deal with sanctions/PEP
screening and periodic re-screening, so their vocabularies overlap strongly.
"""
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.reporting import Finding
from models.racm import RacmRisk, RacmControl

_TARGET = "Sanctions Screening Process"


async def _has_data(db, eng_id) -> bool:
    f = (await db.execute(select(Finding.id).where(Finding.engagement_id == eng_id).limit(1))).first()
    r = (await db.execute(select(RacmRisk.id).where(RacmRisk.engagement_id == eng_id).limit(1))).first()
    return bool(f or r)


async def seed_audit_memory_demo():
    async with AsyncSessionLocal() as db:
        eng = (await db.execute(
            select(Engagement).where(Engagement.name == _TARGET)
        )).scalars().first()
        if not eng or await _has_data(db, eng.id):
            return  # missing or already enriched — idempotent

        db.add(Finding(
            id=str(uuid4()), engagement_id=eng.id, rating="high", status="draft", sort_order=0,
            title="Sanctions screening alerts not cleared timely",
            condition="A backlog of sanctions and PEP screening alerts remained uncleared beyond the SLA.",
            criteria="Screening alerts must be reviewed and dispositioned within the defined SLA.",
            cause="Insufficient analyst capacity and no escalation for ageing alerts.",
            effect="Potential dealings with sanctioned parties may go undetected.",
        ))
        db.add(Finding(
            id=str(uuid4()), engagement_id=eng.id, rating="medium", status="draft", sort_order=1,
            title="Periodic PEP re-screening not performed",
            condition="Existing customers were not re-screened for PEP or sanctions status changes on a schedule.",
            criteria="Customers must be periodically re-screened for sanctions and PEP status.",
            cause="No scheduled re-screening run after onboarding.",
            effect="Risk-profile and sanctions/PEP status changes go undetected after onboarding.",
        ))

        hr = RacmRisk(id=str(uuid4()), engagement_id=eng.id, ref="R1", sort_order=0,
                      origin="human", accepted=True, accepted_by="DA", inherent_rating="high",
                      category="Sanctions", title="Dealings with sanctioned parties",
                      description="Customers or transactions involving sanctioned parties are not detected.")
        mr = RacmRisk(id=str(uuid4()), engagement_id=eng.id, ref="R2", sort_order=1,
                      origin="human", accepted=True, accepted_by="DA", inherent_rating="medium",
                      category="Screening", title="Outdated PEP status after onboarding",
                      description="PEP status is not refreshed, so enhanced due diligence is not triggered.")
        db.add(hr)
        db.add(mr)
        db.add(RacmControl(id=str(uuid4()), engagement_id=eng.id, risk_id=hr.id, ref="C1", sort_order=0,
                           origin="human", accepted=True, accepted_by="DA", control_type="detective",
                           design_conclusion="deficient", title="Sanctions list screening control",
                           description="Screening against sanctions lists with timely alert clearance."))
        db.add(RacmControl(id=str(uuid4()), engagement_id=eng.id, risk_id=mr.id, ref="C2", sort_order=1,
                           origin="human", accepted=True, accepted_by="DA", control_type="preventive",
                           design_conclusion="effective", title="Periodic PEP re-screening control",
                           description="Scheduled re-screening of existing customers for PEP/sanctions status."))
        await db.commit()
