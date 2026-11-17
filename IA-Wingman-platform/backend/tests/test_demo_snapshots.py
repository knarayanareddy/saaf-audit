"""Demo snapshots: an audit built by hand, carried into every fresh start.

    venv/Scripts/python.exe -m tests.test_demo_snapshots

Two things can go wrong silently. A column renamed after the export makes the
snapshot fail to load on the host, at startup, where nobody is looking. And
seeding that the register records makes every fresh start look like a day of
edits. No API calls; the register test writes to a throwaway engagement and
removes it.
"""
import asyncio
import json
import sys
from uuid import uuid4

from sqlalchemy import select

import main  # noqa: F401 — registers every model and installs the register
from database import AsyncSessionLocal, create_tables, run_migrations
from models.edit_register import FieldEdit
from models.engagement import Engagement
from models.racm import RacmRisk
from services import edit_register
from services.seed_demo_snapshots import SNAPSHOT_DIR, SNAPSHOT_TABLES, model_for

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def test_every_snapshot_still_fits_the_schema():
    print("the snapshots against today's models:")
    files = sorted(SNAPSHOT_DIR.glob("*.json"))
    check(any(f.name == "26-047.json" for f in files), "26-047 is among the demo snapshots")
    for path in files:
        snap = json.loads(path.read_text(encoding="utf-8"))
        unknown_tables = [t for t in snap["tables"] if t not in SNAPSHOT_TABLES]
        check(not unknown_tables, f"{path.name}: every table is one the loader knows ({unknown_tables})")
        stale = []
        for table, rows in snap["tables"].items():
            columns = {a.key for a in model_for(table).__mapper__.column_attrs}
            for row in rows[:1]:
                stale += [f"{table}.{k}" for k in row if k not in columns]
        check(not stale, f"{path.name}: every column still exists ({stale[:5]})")
        eng = (snap["tables"].get("engagements") or [{}])[0]
        check(eng.get("id") == snap["engagement_id"], f"{path.name}: the audit row matches the snapshot's id")


async def test_seeding_is_not_recorded():
    print("seeding and the register:")
    eng_id = f"snapshot-test-{uuid4()}"
    seeded, edited = str(uuid4()), str(uuid4())
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=eng_id, name="Snapshot test", entity="GRP", audit_type="it", team_members="[]"))
        await db.commit()
    try:
        with edit_register.paused():
            async with AsyncSessionLocal() as db:
                db.add(RacmRisk(id=seeded, engagement_id=eng_id, title="Seeded", origin="ai"))
                await db.commit()
        async with AsyncSessionLocal() as db:
            db.add(RacmRisk(id=edited, engagement_id=eng_id, title="Made after startup", origin="ai"))
            await db.commit()
        async with AsyncSessionLocal() as db:
            ids = set((await db.execute(select(FieldEdit.entity_id).where(
                FieldEdit.entity_id.in_([seeded, edited])))).scalars().all())
        check(seeded not in ids, "a record written while the register is paused leaves no register row")
        check(edited in ids, "and once the pause ends, the register records again")
    finally:
        async with AsyncSessionLocal() as db:
            for model, rid in ((RacmRisk, seeded), (RacmRisk, edited), (Engagement, eng_id)):
                row = await db.get(model, rid)
                if row:
                    await db.delete(row)
            for row in (await db.execute(select(FieldEdit).where(FieldEdit.engagement_id == eng_id))).scalars():
                await db.delete(row)
            await db.commit()


async def run_all():
    await create_tables()
    await run_migrations()
    test_every_snapshot_still_fits_the_schema()
    await test_seeding_is_not_recorded()


def main_():
    asyncio.run(run_all())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
