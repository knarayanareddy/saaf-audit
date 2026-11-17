"""The Run button has to start something.

    venv/Scripts/python.exe -m tests.test_scan_start

Pressing Run on Topic Intelligence did nothing, twice, for two different reasons
that the same test would have caught:

1. The start screen sent `manual_keyword: null` and the API only accepted text,
   so the request was rejected with a 422 before any agent existed.
2. Past that, the endpoint called `attributed(...)`, which was never imported. It
   crashed on the line that hands the work to the background — *after* it had
   already flipped the scan to "agents_pending" and created three pending runs.
   The page then showed "Agents running…" over a scan nobody was running.

Neither was visible to the suites that existed: nothing called the endpoint, and
nothing looked for names that exist nowhere. So this does both. It presses the
button the way the browser does — including with no keyword — with the pipeline
itself replaced, so it costs nothing and starts no agent; and it scans the
backend for names used but never defined, which is the class of mistake the
second bug was.
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import select

from auth import require_auth  # noqa: F401  — importing main wires the app
from config import settings
from database import AsyncSessionLocal, create_tables, run_migrations
from models.agent_run import AgentRun
from models.engagement import Engagement
from models.planning import TopicIntelligence

failures: list[str] = []
BACKEND = Path(__file__).resolve().parent.parent


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _press_run(body: dict):
    """Run the endpoint with the pipeline swapped for one that does nothing."""
    import main
    from routers import agents as agents_router

    started = []

    async def fake_pipeline(*args, **kwargs):
        started.append(args)

    original = agents_router.run_topic_intelligence_v2
    agents_router.run_topic_intelligence_v2 = fake_pipeline

    engagement_id = str(uuid4())
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=engagement_id, audit_code="TEST-SCAN", name="Scan start test",
                          entity="GRP", audit_type="it", team_members="[]"))
        await db.commit()

    try:
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test",
                                     auth=(settings.APP_USERNAME, settings.APP_PASSWORD)) as client:
            response = await client.post(f"/api/engagements/{engagement_id}/agents/run-v2", json=body)

        async with AsyncSessionLocal() as db:
            runs = (await db.execute(
                select(AgentRun).where(AgentRun.engagement_id == engagement_id)
            )).scalars().all()
            ti = (await db.execute(
                select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
            )).scalar_one_or_none()
        return response, started, runs, ti
    finally:
        agents_router.run_topic_intelligence_v2 = original
        async with AsyncSessionLocal() as db:
            for model in (AgentRun, TopicIntelligence):
                for row in (await db.execute(
                    select(model).where(model.engagement_id == engagement_id)
                )).scalars().all():
                    await db.delete(row)
            eng = await db.get(Engagement, engagement_id)
            if eng:
                await db.delete(eng)
            await db.commit()
        # The edit register records the deletions above too; a test's own
        # records go with the test, in a separate step so the rows written by
        # this cleanup's flush are included.
        from models.edit_register import FieldEdit
        async with AsyncSessionLocal() as db:
            for row in (await db.execute(
                select(FieldEdit).where(FieldEdit.engagement_id == engagement_id)
            )).scalars().all():
                await db.delete(row)
            await db.commit()


async def test_the_button_starts_a_scan():
    # Exactly what the start screen sends when no keyword is typed.
    response, started, runs, ti = await _press_run({
        "urls": [], "use_web_search": False, "custom_queries": [],
        "manual_keyword": "", "extra_context": "",
    })
    check(response.status_code == 200, f"Run is accepted (got {response.status_code}: {response.text[:120]})")
    check(len(started) == 1, "and the pipeline is actually handed the work")
    check(len(runs) == 3, f"three lens runs exist ({len(runs)})")
    check(ti is not None and ti.status == "agents_pending", "and the scan says it is running")


async def test_no_keyword_may_arrive_as_null():
    # An older client, or any caller, may still send null for "nothing".
    response, started, _runs, _ti = await _press_run({
        "urls": [], "use_web_search": False, "custom_queries": [],
        "manual_keyword": None, "extra_context": "",
    })
    check(response.status_code == 200, f"null for 'no keyword' is accepted (got {response.status_code})")
    check(len(started) == 1, "and still starts the scan")


async def test_the_context_reaches_the_pipeline():
    response, started, _runs, _ti = await _press_run({
        "urls": [], "use_web_search": False, "custom_queries": [],
        "manual_keyword": "DORA", "extra_context": "Last year's onboarding checks were not evidenced.",
    })
    args = started[0] if started else ()
    check(response.status_code == 200 and "DORA" in args, "the keyword is passed on")
    check("Last year's onboarding checks were not evidenced." in args,
          "and so is what the auditor added")


def test_no_name_is_used_that_exists_nowhere():
    try:
        from pyflakes.api import check as flake
        from pyflakes.reporter import Reporter
    except ImportError:
        check(False, "pyflakes is installed (venv/Scripts/python.exe -m pip install pyflakes)")
        return

    import io
    out = io.StringIO()
    bad = 0
    for folder in ("routers", "services", "models"):
        for path in sorted((BACKEND / folder).glob("*.py")):
            flake(path.read_text(encoding="utf-8"), str(path), Reporter(out, out))
    for name in ("main.py", "auth.py", "database.py", "paths.py", "schemas.py", "config.py"):
        flake((BACKEND / name).read_text(encoding="utf-8"), name, Reporter(out, out))

    undefined = [line for line in out.getvalue().splitlines() if "undefined name" in line]
    for line in undefined:
        print(f"        {line}")
        bad += 1
    check(bad == 0, f"no undefined names anywhere in the backend ({bad} found)")


async def run_all():
    await create_tables()
    await run_migrations()
    await test_the_button_starts_a_scan()
    await test_no_keyword_may_arrive_as_null()
    await test_the_context_reaches_the_pipeline()
    test_no_name_is_used_that_exists_nowhere()


def main():
    asyncio.run(run_all())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
