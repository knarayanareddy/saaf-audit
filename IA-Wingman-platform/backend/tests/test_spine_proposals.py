"""Regenerating a work program replaces its own proposals, and only those.

    venv/Scripts/python.exe -m tests.test_spine_proposals

Before this, `routers/phase3.py` refused to regenerate a *signed* work program
and allowed everything else, while `rows_to_spine` wrote unconditionally. Two
presses of Regenerate gave two complete matrices.

The hard case is the third test here. The spine is a tree, so the obvious rule
— delete my unaccepted proposals — destroys accepted work by orphaning it: an
accepted control hanging from a proposed risk becomes unreachable the moment
that risk is deleted, and disappears from every view while still sitting in the
table. No accepted row is deleted and the auditor's decision is gone anyway.
"""
import asyncio
import json
import sys
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.racm import RacmControl, RacmEvidence, RacmObjective, RacmRisk, RacmTest
from services.spine_proposals import replace_previous
from services.work_program_migration import rows_to_spine

failures: list[str] = []
E = "test-spine-proposals"
MINE = "work_program_generator"
OTHER = "governance_assessor"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean(db):
    for model in (RacmEvidence, RacmTest, RacmControl, RacmRisk, RacmObjective):
        for row in (await db.execute(
            select(model).where(model.engagement_id == E)
        )).scalars().all():
            await db.delete(row)
    await db.commit()


async def _count(db, model) -> int:
    return len((await db.execute(
        select(model).where(model.engagement_id == E)
    )).scalars().all())


ROWS = [
    {"id": "wp_1", "process": "Onboarding", "risk_description": "No UBO check",
     "control_objective": "UBO verified", "test_steps": ["Obtain population", "Sample 25"],
     "evidence": [{"title": "UBO register extract", "kind": "document",
                   "requested_from": "Compliance", "period": "FY2026 H1"}]},
    {"id": "wp_2", "process": "Onboarding", "risk_description": "No screening",
     "control_objective": "Screening at onboarding", "test_steps": ["Re-perform 10"]},
]


async def run() -> None:
    async with AsyncSessionLocal() as db:
        await _clean(db)

        print("\ngenerating twice does not give two matrices:")
        first = await rows_to_spine(db, E, ROWS, source_type=MINE)
        await db.commit()
        check(first["controls"] == 2 and first["tests"] == 3, "the first run writes the rows")
        check(first["evidence"] == 1, "including the evidence a row declares")

        second = await rows_to_spine(db, E, ROWS, source_type=MINE)
        await db.commit()
        check(second["cleared"]["controls"] == 2, "the second run clears the first's controls")
        check(await _count(db, RacmControl) == 2, "so there are still two controls, not four")
        check(await _count(db, RacmTest) == 3, "and three tests, not six")
        check(await _count(db, RacmEvidence) == 1, "and one evidence need, not two")

        print("\nanother source's proposals are left alone:")
        other = RacmRisk(id=str(uuid4()), engagement_id=E, title="Vendor concentration",
                         origin="ai", accepted=False,
                         provenance=json.dumps({"source_type": OTHER}), sort_order=99)
        db.add(other)
        await db.commit()
        await rows_to_spine(db, E, ROWS, source_type=MINE)
        await db.commit()
        check(await db.get(RacmRisk, other.id) is not None,
              "a governance proposal survives a work program regenerate")

        print("\nthe migration and the generator are one writer:")
        # The ESG spine was written by the migration. A regenerate that only
        # recognised its own name cleared nothing and added a second matrix.
        migrated = RacmRisk(id=str(uuid4()), engagement_id=E, title="From the old work program",
                            origin="ai", accepted=False,
                            provenance=json.dumps({"source_type": "work_program_migration"}),
                            sort_order=98)
        db.add(migrated)
        await db.commit()
        await rows_to_spine(db, E, ROWS, source_type=MINE)
        await db.commit()
        check(await db.get(RacmRisk, migrated.id) is None,
              "a regenerate clears what the migration proposed")

        print("\nan accepted node is never orphaned by clearing its parent:")
        risk = (await db.execute(
            select(RacmRisk).where(RacmRisk.engagement_id == E,
                                   RacmRisk.title == "No UBO check")
        )).scalars().first()
        control = (await db.execute(
            select(RacmControl).where(RacmControl.risk_id == risk.id)
        )).scalars().first()
        control.accepted = True
        control.accepted_by = "DA"
        await db.commit()

        cleared = await replace_previous(db, E, MINE)
        await db.commit()
        check(await db.get(RacmControl, control.id) is not None,
              "the accepted control is still there")
        check(await db.get(RacmRisk, risk.id) is not None,
              "and so is the proposed risk it hangs from — not ours to remove")
        objective = await db.get(RacmObjective, risk.objective_id)
        check(objective is not None, "and the objective above that")
        check(cleared["kept_for_children"] >= 2,
              f"the run reports what it left behind ({cleared['kept_for_children']})")

        print("\nand the other branch, which holds nothing accepted, does go:")
        check(cleared["controls"] == 1, "the second control was cleared")
        check(await _count(db, RacmControl) == 1, "one control remains")

        await _clean(db)


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
