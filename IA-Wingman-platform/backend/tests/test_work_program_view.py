"""Tests for the work program projection (services/work_program_view.py).

    venv/Scripts/python.exe -m tests.test_work_program_view

The projection exists because the work program and the matrix were two stores
with nothing between them. Of nine engagements holding either, two held both;
four built a matrix and never signed, three signed with an empty matrix.

What these tests protect is not the mapping — that is obvious — but the three
cases where a naive join would hide something:

  * an objective with no risk yet still produces a row
  * a risk with no control still produces a row
  * a risk an agent proposed before any objective exists still produces a row

Each of those is a gap the auditor needs to see, and each would vanish from an
inner join.
"""
import asyncio
import sys
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.racm import RacmControl, RacmObjective, RacmRisk, RacmTest
from services.work_program_view import rows_for

failures: list[str] = []
ENGAGEMENT = "test-wp-view"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean(db):
    for model in (RacmTest, RacmControl, RacmRisk, RacmObjective):
        for row in (await db.execute(
            select(model).where(model.engagement_id == ENGAGEMENT)
        )).scalars().all():
            await db.delete(row)
    await db.commit()


async def run() -> None:
    async with AsyncSessionLocal() as db:
        await _clean(db)

        def node(model, **kw):
            n = model(id=str(uuid4()), engagement_id=ENGAGEMENT, **kw)
            db.add(n)
            return n

        # The ordinary case: a full path, with two tests under one control.
        o1 = node(RacmObjective, title="Client onboarding is controlled",
                  description="New corporate clients", sort_order=0)
        await db.flush()
        r1 = node(RacmRisk, objective_id=o1.id, title="Client onboarded without UBO check",
                  sort_order=0)
        await db.flush()
        c1 = node(RacmControl, risk_id=r1.id, title="UBO verified before approval", sort_order=0)
        await db.flush()
        node(RacmTest, control_id=c1.id, title="Sample 25 files", sort_order=0,
             priority="high", assigned_to="DA", progress="in_progress")
        node(RacmTest, control_id=c1.id, title="Trace to policy", sort_order=1,
             progress="complete")

        # An objective nobody has written a risk for.
        node(RacmObjective, title="Periodic review is timely", sort_order=1)

        # A risk with no control.
        o3 = node(RacmObjective, title="Escalation works", sort_order=2)
        await db.flush()
        node(RacmRisk, objective_id=o3.id, title="Breaches are not escalated", sort_order=1)

        # A risk an agent proposed before any objective exists.
        node(RacmRisk, objective_id=None, title="Vendor gap: no exit plan",
             origin="ai", accepted=False, sort_order=2)
        await db.commit()

        rows = await rows_for(ENGAGEMENT, db)
        by_process = {r["process"]: r for r in rows}

        print("\nthe ordinary case:")
        full = by_process["Client onboarding is controlled"]
        check(full["risk_description"] == "Client onboarded without UBO check", "risk mapped")
        check(full["control_objective"] == "UBO verified before approval", "control mapped")
        check(full["test_steps"] == ["Sample 25 files", "Trace to policy"],
              "both tests became steps, in order")
        check(full["priority"] == "high", "priority comes from the tests")
        check(full["responsibility"] == "DA", "assignee comes from the tests")
        check(full["status"] == "in_progress",
              "a row is only complete when its last test is")

        print("\nnothing that is missing disappears:")
        check("Periodic review is timely" in by_process,
              "an objective with no risk still produces a row")
        check(by_process["Periodic review is timely"]["risk_description"] == "",
              "and says so by being empty, not by being absent")
        check("Escalation works" in by_process, "a risk with no control still produces a row")
        check(by_process["Escalation works"]["control_objective"] == "",
              "with an empty control")
        orphan = [r for r in rows if r["risk_description"] == "Vendor gap: no exit plan"]
        check(len(orphan) == 1, "a proposal with no objective yet is still shown")

        print("\nevery row carries its node ids:")
        check(full["node_ids"]["control"] == c1.id, "the control id is on the row")
        check(len(full["node_ids"]["tests"]) == 2, "and both test ids")
        check(all("node_ids" in r for r in rows), "every row, not only the full one")

        print("\nan unsigned engagement has no snapshot:")
        check(await rows_for(ENGAGEMENT, db, as_signed=True) == [],
              "as_signed returns nothing before anyone signed")

        await _clean(db)


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
