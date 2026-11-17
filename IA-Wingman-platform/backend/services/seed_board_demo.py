"""Board-demo enrichment — gives a few well-matched engagements a little findings +
RACM data so the portfolio Board Report has cross-engagement severity and real
"high risk x weak control" hotspots to show. Deterministic, idempotent, generic
and white-label; it NEVER touches the golden engagement.

Three specific engagements are enriched, each with content that fits its theme:
Cybersecurity (access/change), Fraud Risk (segregation of duties), and Business
Continuity (backup/incident). Each gets 2 findings (1 high, 1 medium) and a
minimal RACM slice: 2 risks (1 high-inherent, 1 medium) and 2 controls (1
deficient on the high risk -> a genuine hotspot, 1 effective on the medium risk).
Idempotent per engagement: enrich only when it has no findings/RACM yet, so
repeated startups never add more.
"""
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.reporting import Finding
from models.racm import RacmRisk, RacmControl

# Each entry: the target engagement name + theme-matched content.
_ENRICH = [
    {
        "engagement": "Cybersecurity Controls Review",
        "high_finding": ("Access rights not reviewed on time",
                         "Periodic user-access reviews were overdue for several in-scope systems.",
                         "Policy requires quarterly access reviews for critical systems.",
                         "No automated reminder or clear ownership for the review cycle.",
                         "Excessive or stale access raises the risk of unauthorised actions."),
        "med_finding": ("Change approvals inconsistently evidenced",
                        "A minority of changes lacked documented approval before deployment.",
                        "The change policy requires documented approval prior to release.",
                        "Manual approval capture is skipped under time pressure.",
                        "Weak change governance can let unauthorised changes through."),
        "high_risk": ("Unauthorised or excessive system access", "IAM"),
        "med_risk": ("Unapproved changes reach production", "Change"),
        "def_control": ("Periodic access-review control", "Reviews run ad hoc; no evidence checklist."),
        "eff_control": ("Change-approval gate", "Approvals enforced in the deployment pipeline."),
    },
    {
        "engagement": "Fraud Risk Management",
        "high_finding": ("Segregation-of-duties conflicts in payments",
                         "Several users could both initiate and approve outgoing payments.",
                         "Payments require segregation between initiation and approval.",
                         "Role design was not reviewed after a reorganisation.",
                         "Conflicting duties enable undetected fraudulent payments."),
        "med_finding": ("Manual journal entries not independently reviewed",
                        "A sample of manual journals lacked independent review evidence.",
                        "Manual journals above a threshold require independent review.",
                        "Review is informal and not consistently recorded.",
                        "Unreviewed manual entries can conceal misstatement or fraud."),
        "high_risk": ("Undetected fraudulent payments", "Fraud"),
        "med_risk": ("Management override of controls", "Fraud"),
        "def_control": ("Payment segregation-of-duties control", "Conflicting roles not fully separated."),
        "eff_control": ("Manual-journal review", "Threshold journals independently reviewed."),
    },
    {
        "engagement": "Business Continuity & Disaster Recovery",
        "high_finding": ("Backup restoration not tested",
                         "Restore tests for critical systems were not performed in the audit period.",
                         "Continuity policy requires periodic restore testing.",
                         "Restore testing is not scheduled after backup changes.",
                         "Untested backups may fail when actually needed."),
        "med_finding": ("Incident post-mortems incomplete",
                        "Major-incident reviews were not consistently documented.",
                        "Major incidents require a documented post-incident review.",
                        "No standard template or owner for post-mortems.",
                        "Recurring root causes go unaddressed."),
        "high_risk": ("Unrecoverable critical system", "BC/DR"),
        "med_risk": ("Recurring incidents from unaddressed root causes", "Incident"),
        "def_control": ("Periodic restore testing", "No scheduled restore tests evidenced."),
        "eff_control": ("Major-incident review process", "Post-mortems run for major incidents."),
    },
]


async def _has_data(db, eng_id) -> bool:
    f = (await db.execute(select(Finding.id).where(Finding.engagement_id == eng_id).limit(1))).first()
    r = (await db.execute(select(RacmRisk.id).where(RacmRisk.engagement_id == eng_id).limit(1))).first()
    return bool(f or r)


async def seed_board_demo():
    async with AsyncSessionLocal() as db:
        changed = False
        for spec in _ENRICH:
            eng = (await db.execute(
                select(Engagement).where(Engagement.name == spec["engagement"])
            )).scalars().first()
            if not eng or await _has_data(db, eng.id):
                continue  # missing or already enriched — idempotent

            def _finding(f, rating, order):
                t, cond, crit, cause, eff = f
                return Finding(id=str(uuid4()), engagement_id=eng.id, title=t, condition=cond,
                               criteria=crit, cause=cause, effect=eff, rating=rating, status="draft",
                               sort_order=order)
            db.add(_finding(spec["high_finding"], "high", 0))
            db.add(_finding(spec["med_finding"], "medium", 1))

            hr = RacmRisk(id=str(uuid4()), engagement_id=eng.id, ref="R1", sort_order=0,
                          origin="human", accepted=True, accepted_by="DA", inherent_rating="high",
                          category=spec["high_risk"][1], title=spec["high_risk"][0])
            mr = RacmRisk(id=str(uuid4()), engagement_id=eng.id, ref="R2", sort_order=1,
                          origin="human", accepted=True, accepted_by="DA", inherent_rating="medium",
                          category=spec["med_risk"][1], title=spec["med_risk"][0])
            db.add(hr)
            db.add(mr)
            db.add(RacmControl(id=str(uuid4()), engagement_id=eng.id, risk_id=hr.id, ref="C1", sort_order=0,
                               origin="human", accepted=True, accepted_by="DA", control_type="detective",
                               design_conclusion="deficient", title=spec["def_control"][0],
                               description=spec["def_control"][1]))
            db.add(RacmControl(id=str(uuid4()), engagement_id=eng.id, risk_id=mr.id, ref="C2", sort_order=1,
                               origin="human", accepted=True, accepted_by="DA", control_type="preventive",
                               design_conclusion="effective", title=spec["eff_control"][0],
                               description=spec["eff_control"][1]))
            changed = True

        if changed:
            await db.commit()
