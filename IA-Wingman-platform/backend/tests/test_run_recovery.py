"""A scan may only say it is running when something is running.

    venv/Scripts/python.exe -m tests.test_run_recovery

Two audits in the demo database sat on "Agents running…" forever: one whose
three lens runs never started, one whose lenses finished but whose synthesis
died with the process. Both looked, on screen, exactly like a scan in progress.
Nothing was in progress — the process that would have done the work had been
gone for days.

The status was a claim nobody could withdraw. This is the withdrawal: at
startup, no run from a previous process can still be alive, so any run still
marked pending or running is corrected, with a reason, and the scan lands on a
screen the auditor can act on.

Writes to the real database, so it works on rows it creates and removes them
again.
"""
import asyncio
import json
import sys
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal, create_tables, run_migrations
from models.agent_run import AgentRun
from models.planning import TopicIntelligence
from services.run_recovery import INTERRUPTED, recover_interrupted_runs

failures: list[str] = []
MINE = f"recovery-test-{uuid4()}"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _seed(status, *, lens_summary=None, run_statuses=()):
    """One engagement's worth of state, returned as its engagement id."""
    engagement_id = f"{MINE}-{uuid4()}"
    async with AsyncSessionLocal() as db:
        db.add(TopicIntelligence(
            id=str(uuid4()), engagement_id=engagement_id,
            status=status, progress_pct=60, lens1_summary=lens_summary,
        ))
        for i, run_status in enumerate(run_statuses):
            db.add(AgentRun(
                id=str(uuid4()), engagement_id=engagement_id,
                agent_type=f"lens{i + 1}", status=run_status,
            ))
        await db.commit()
    return engagement_id


async def _ti(engagement_id):
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
        )).scalar_one()


async def _runs(engagement_id):
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(AgentRun).where(AgentRun.engagement_id == engagement_id)
        )).scalars().all()


async def _cleanup():
    async with AsyncSessionLocal() as db:
        for model in (AgentRun, TopicIntelligence):
            rows = (await db.execute(
                select(model).where(model.engagement_id.like(f"{MINE}%"))
            )).scalars().all()
            for row in rows:
                await db.delete(row)
        await db.commit()


async def run_all():
    await create_tables()
    await run_migrations()

    # The one that never started: three pending runs, nothing produced.
    never_started = await _seed("agents_pending", run_statuses=("pending", "pending", "pending"))
    # The one that died halfway: lenses done, synthesis never finished.
    died_halfway = await _seed("agents_pending", lens_summary="Lens 1 found three obligations.")
    # An untouched scan, to prove recovery does not reach past what it is for.
    finished = await _seed("agreed", lens_summary="Done.", run_statuses=("complete",))

    report = await recover_interrupted_runs()

    check(report["runs"] >= 3, f"it reports how many runs it corrected ({report['runs']})")
    check(report["scans"] >= 2, f"and how many scans it unstuck ({report['scans']})")

    ti = await _ti(never_started)
    check(ti.status == "not_started",
          f"a scan with nothing to show goes back to the start screen (got {ti.status!r})")
    check(ti.progress_pct == 0, "and its progress bar does not keep claiming 60%")

    runs = await _runs(never_started)
    check(all(r.status == "failed" for r in runs), "every unfinished run is marked failed")
    reasons = [json.loads(r.raw_output or "{}").get("error") for r in runs]
    check(all(r == INTERRUPTED for r in reasons),
          "each one says what happened, rather than failing namelessly")
    check("restarted" in INTERRUPTED,
          "and the reason names the restart, not the agent — nothing went wrong with the work")

    ti = await _ti(died_halfway)
    check(ti.status == "review",
          f"a scan that produced something lands on that result (got {ti.status!r})")
    check(ti.lens1_summary == "Lens 1 found three obligations.",
          "and what the lenses did produce is left exactly as it was")

    ti = await _ti(finished)
    check(ti.status == "agreed", "a finished scan is not touched")
    check((await _runs(finished))[0].status == "complete", "nor is its completed run")

    # Running it twice must be as safe as running it once — a restart loop
    # would otherwise keep rewriting rows it already corrected.
    again = await recover_interrupted_runs()
    check(again["runs"] == 0 and again["scans"] == 0,
          "a second pass finds nothing left to do")

    await _cleanup()


def main():
    asyncio.run(run_all())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
