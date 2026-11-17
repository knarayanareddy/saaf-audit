"""Tests for the shared auditee context (services/auditee_context.py).

    venv/Scripts/python.exe -m tests.test_auditee_context

One rule carries this module, and it was implicit in two places before it was
explicit in one:

    Only what the auditor accepted may reach the auditee.

The notification letter and the kick-off agenda both told the auditee what the
audit covers. Both filtered on `is_accepted`, neither said why, and nothing
would have failed if one copy had quietly dropped the filter — the letter would
simply have announced a scope nobody had agreed to.
"""
import asyncio
import sys
from uuid import uuid4

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import ApplicableFramework, ScopeItem, ScopeObjectives
from services.auditee_context import load

failures: list[str] = []
ENGAGEMENT = "test-auditee-context"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean(db):
    for model in (ApplicableFramework, ScopeItem, ScopeObjectives, Engagement):
        from sqlalchemy import select
        if model is ScopeItem:
            scopes = (await db.execute(
                select(ScopeObjectives).where(ScopeObjectives.engagement_id == ENGAGEMENT)
            )).scalars().all()
            for sc in scopes:
                for it in (await db.execute(
                    select(ScopeItem).where(ScopeItem.scope_id == sc.id)
                )).scalars().all():
                    await db.delete(it)
            continue
        col = model.id if model is Engagement else model.engagement_id
        target = ENGAGEMENT
        for row in (await db.execute(select(model).where(col == target))).scalars().all():
            await db.delete(row)
    await db.commit()


async def run() -> None:
    async with AsyncSessionLocal() as db:
        await _clean(db)

        db.add(Engagement(id=ENGAGEMENT, name="Customer Due Diligence", entity="GRP",
                          audit_type="operational", status="in_planning"))
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=ENGAGEMENT,
                                overall_objective="Assess CDD at onboarding.")
        db.add(scope)
        await db.flush()

        db.add_all([
            ScopeItem(id=str(uuid4()), scope_id=scope.id, item_type="in_scope",
                      description="Onboarding of new corporate clients", is_accepted=True),
            ScopeItem(id=str(uuid4()), scope_id=scope.id, item_type="in_scope",
                      description="Periodic review of existing clients", is_accepted=False),
            ScopeItem(id=str(uuid4()), scope_id=scope.id, item_type="out_of_scope",
                      description="Sanctions screening", is_accepted=True),
            ScopeItem(id=str(uuid4()), scope_id=scope.id, item_type="out_of_scope",
                      description="Transaction monitoring", is_accepted=False),
        ])
        db.add_all([
            ApplicableFramework(id=str(uuid4()), engagement_id=ENGAGEMENT, framework_code="Wwft",
                                framework_name="Wwft", category="law", is_accepted=True,
                                source="auto_analysed"),
            ApplicableFramework(id=str(uuid4()), engagement_id=ENGAGEMENT, framework_code="DRAFT",
                                framework_name="Proposal nobody accepted", category="law",
                                is_accepted=False, source="auto_analysed"),
        ])
        await db.commit()

        ctx = await load(db, ENGAGEMENT)

        print("\nonly what the auditor accepted reaches the auditee:")
        check(ctx.in_scope == ["Onboarding of new corporate clients"],
              "an unaccepted in-scope item stays out of the letter")
        check(ctx.out_of_scope == ["Sanctions screening"],
              "an unaccepted out-of-scope item stays out too")
        check(ctx.frameworks == ["Wwft"], "an unaccepted framework is not announced")

        print("\nthe rest of the pack:")
        check(ctx.engagement.name == "Customer Due Diligence", "the engagement is loaded")
        check(ctx.overall_objective.startswith("Assess"), "the overall objective comes along")
        check(ctx.ti_key_risks == [], "no topic memo yet reads as no risks, not as a crash")
        check(ctx.ia_prework == [], "and no prework rather than a KeyError")

        print("\nan engagement with nothing planned yet:")
        db.add(Engagement(id=ENGAGEMENT + "-bare", name="Empty", entity="GRP",
                          audit_type="operational", status="to_be_scheduled"))
        await db.commit()
        bare = await load(db, ENGAGEMENT + "-bare")
        check(bare.in_scope == [] and bare.frameworks == [],
              "an empty engagement loads empty rather than failing")

        from sqlalchemy import select
        for row in (await db.execute(
            select(Engagement).where(Engagement.id == ENGAGEMENT + "-bare")
        )).scalars().all():
            await db.delete(row)
        await _clean(db)


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
