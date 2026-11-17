"""Sign-off, snapshot and drift (services/work_program_view.py).

    venv/Scripts/python.exe -m tests.test_work_program_signoff

What this protects is the reason the whole projection was built. Before it, an
auditor signed `WorkProgram.rows` — a JSON blob nothing else read — while
fieldwork tested the matrix, which was built separately. The signature sat on a
document that had no connection to the work.

Now the signature takes a snapshot of the spine, and anything that moves
afterwards is nameable. The test that matters is the last one: drift has to say
*which* path changed, not merely that something did.
"""
import asyncio
import sys
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.planning import WorkProgram
from models.racm import RacmControl, RacmObjective, RacmRisk, RacmTest
from services.work_program_view import apply_patch, drift_since_signoff, rows_for, snapshot

failures: list[str] = []
E = "test-wp-signoff"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean(db):
    for model in (RacmTest, RacmControl, RacmRisk, RacmObjective, WorkProgram):
        for row in (await db.execute(
            select(model).where(model.engagement_id == E)
        )).scalars().all():
            await db.delete(row)
    await db.commit()


async def run() -> None:
    async with AsyncSessionLocal() as db:
        await _clean(db)

        def node(model, **kw):
            n = model(id=str(uuid4()), engagement_id=E, **kw)
            db.add(n)
            return n

        o = node(RacmObjective, title="Onboarding", sort_order=0)
        await db.flush()
        r = node(RacmRisk, objective_id=o.id, title="No UBO check", sort_order=0)
        await db.flush()
        c = node(RacmControl, risk_id=r.id, title="UBO verified", sort_order=0)
        c2 = node(RacmControl, risk_id=r.id, title="Four eyes on approval", sort_order=1)
        await db.flush()
        node(RacmTest, control_id=c.id, title="Sample 25", sort_order=0)
        wp = WorkProgram(id=str(uuid4()), engagement_id=E, status="ready")
        db.add(wp)
        await db.commit()

        print("\nbefore anyone signs:")
        check(await rows_for(E, db, as_signed=True) == [], "there is no snapshot")
        drift = await drift_since_signoff(E, db)
        check(drift["signed"] is False, "and no drift, because there is nothing to drift from")

        print("\nsigning takes a snapshot of the spine:")
        wp.status = "signed_off"
        wp.signed_off_at = datetime.utcnow()
        wp.rows = await snapshot(E, db)
        await db.commit()
        signed = await rows_for(E, db, as_signed=True)
        check(len(signed) == 2, "both controls are in the snapshot")
        check(all(row.get("node_ids") for row in signed),
              "and every row carries its node ids — without them drift cannot be located")
        check((await drift_since_signoff(E, db))["changed"] == [],
              "nothing has moved yet")

        print("\nthe snapshot does not follow the spine:")
        await apply_patch(E, db, "wp_1", {"control_objective": "UBO verified AND recorded"})
        after = await rows_for(E, db, as_signed=True)
        check(after[0]["control_objective"] == "UBO verified",
              "what was signed still reads as it did")
        live = await rows_for(E, db)
        check(live[0]["control_objective"] == "UBO verified AND recorded",
              "while the live spine has the edit")

        print("\ndrift names what moved, not just that something did:")
        drift = await drift_since_signoff(E, db)
        check(drift["signed"] is True, "it knows there is a signature")
        check(len(drift["changed"]) == 1, "one path changed")
        check(drift["changed"][0]["fields"] == ["control_objective"],
              "and it names the field")

        print("\nadding and removing a path:")
        c3 = node(RacmControl, risk_id=r.id, title="Screening at onboarding", sort_order=2)
        await db.flush()
        await db.delete(await db.get(RacmControl, c2.id))
        await db.commit()
        drift = await drift_since_signoff(E, db)
        check(len(drift["added"]) == 1, "the new control shows as added")
        check(len(drift["removed"]) == 1, "and the deleted one as removed")

        await _clean(db)


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
