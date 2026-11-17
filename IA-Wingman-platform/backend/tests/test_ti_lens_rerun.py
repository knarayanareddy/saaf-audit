"""Topic Intelligence: run one lens again.

    venv/Scripts/python.exe -m tests.test_ti_lens_rerun

An auditor who is happy with two lenses and not with the third had one choice: throw the
whole scan away and pay for all three again. Now one lens can be run again, and only
that lens changes. The lenses are replaced by scripts here; no API calls.
"""
import asyncio
import json
import sys
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select

import main  # noqa: F401  (registers every model)
import services.orchestrator as orch
from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.engagement import Engagement
from models.planning import TopicIntelligence
from routers.planning import get_topic_intelligence, rerun_topic_lens

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def setup(accepted=False, status="review"):
    eid = f"tmp-rerun-{uuid4()}"
    old_ids = {n: str(uuid4()) for n in (1, 2, 3)}
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=eid, audit_code="TMP-RR", name="AI", entity="GRP", audit_type="it", team_members="[]"))
        for n, rid in old_ids.items():
            db.add(AgentRun(id=rid, engagement_id=eid, agent_type=f"lens{n}", status="complete",
                            raw_output=json.dumps({"summary": f"old summary {n}"}),
                            search_progress=json.dumps({"searches_used": 3, "searches_allowed": 8, "web_search": True})))
        db.add(TopicIntelligence(
            id=str(uuid4()), engagement_id=eid, status=status, memo_accepted=accepted, extra_context="note",
            lens1_summary="old summary 1", lens1_run_id=old_ids[1], lens1_sources="[]",
            lens2_summary="old summary 2", lens2_run_id=old_ids[2], lens2_sources="[]",
            lens3_summary="old summary 3", lens3_run_id=old_ids[3], lens3_sources="[]",
            conclusion="The auditor's edited conclusion", topic_primer="primer"))
        await db.commit()
    return eid, old_ids


async def cleanup(eid):
    async with AsyncSessionLocal() as db:
        for model in (AgentRun, TopicIntelligence):
            for row in (await db.execute(select(model).where(model.engagement_id == eid))).scalars().all():
                await db.delete(row)
        e = await db.get(Engagement, eid)
        if e:
            await db.delete(e)
        await db.commit()


def scripted_lens(summary, status="complete", error=None, seen=None):
    async def fake(run_id, engagement_id, *args):
        if seen is not None:
            seen.append(args)
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.status = status
            if status == "complete":
                run.raw_output = json.dumps({"summary": summary, "sources": [{"title": "New", "url": "https://x.example/n"}],
                                             "materiality_signal": "It matters."})
                run.search_progress = json.dumps({"searches_used": 4, "searches_allowed": 8, "web_search": True, "queries": ["q"]})
            else:
                run.raw_output = json.dumps({"error": error})
                run.search_progress = json.dumps({"stage": "failed", "error": error})
            await db.commit()
    return fake


async def test_only_the_chosen_lens_changes():
    print("re-running lens 3:")
    eid, old = await setup()
    seen, real = [], orch.run_lens_society_agent
    orch.run_lens_society_agent = scripted_lens("NEW summary 3", seen=seen)
    try:
        async with AsyncSessionLocal() as db:
            started = await rerun_topic_lens(eid, 3, BackgroundTasks(), db)
            ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == eid))).scalar_one()
            check(ti.status == "agents_pending" and started["lens"] == 3, "the page is told a run is going: status 'agents_pending'")
        await orch.rerun_lens(eid, 3, started["run_id"])
        async with AsyncSessionLocal() as db:
            ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == eid))).scalar_one()
        sources = json.loads(ti.lens3_sources)
        check(ti.lens3_summary == "NEW summary 3" and ti.lens3_run_id == started["run_id"], "lens 3 has the new result and run")
        check(sources[0]["materiality_signal"] == "It matters.", "with its materiality signal where the page reads it")
        check(ti.lens1_summary == "old summary 1" and ti.lens2_summary == "old summary 2"
              and ti.lens1_run_id == old[1] and ti.lens2_run_id == old[2], "the other lenses are untouched")
        check(ti.conclusion == "The auditor's edited conclusion" and ti.topic_primer == "primer",
              "so are the proposal and the primer the auditor may have edited")
        check(ti.status == "review", "the memo is back in review")
        check(seen and seen[0][-1] == "note", "the lens gets the auditor's own note again")
        async with AsyncSessionLocal() as db:
            page = await get_topic_intelligence(eid, db)
        check(page["lens3_search"]["used"] == 4 and page["lens3_search"]["queries"] == ["q"] and page["lens_errors"] == {},
              "the page shows the new search record and no error")
    finally:
        orch.run_lens_society_agent = real
        await cleanup(eid)


async def test_a_failed_rerun_keeps_the_old_result_and_says_why():
    print("a re-run that fails:")
    eid, old = await setup()
    real = orch.run_lens_supervisory_agent
    orch.run_lens_supervisory_agent = scripted_lens(None, status="failed", error="The search was unavailable")
    try:
        async with AsyncSessionLocal() as db:
            started = await rerun_topic_lens(eid, 2, BackgroundTasks(), db)
        await orch.rerun_lens(eid, 2, started["run_id"])
        async with AsyncSessionLocal() as db:
            ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == eid))).scalar_one()
            page = await get_topic_intelligence(eid, db)
        check(ti.lens2_summary == "old summary 2" and ti.lens2_run_id == old[2], "the earlier result stays on the memo")
        check(ti.status == "review", "and the memo is not left 'running'")
        check(page["lens_errors"] == {"lens2": "The search was unavailable"}, f"the page is given the reason ({page['lens_errors']})")

        orch.run_lens_supervisory_agent = scripted_lens("Second try worked")
        async with AsyncSessionLocal() as db:
            second = await rerun_topic_lens(eid, 2, BackgroundTasks(), db)
        await orch.rerun_lens(eid, 2, second["run_id"])
        async with AsyncSessionLocal() as db:
            ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == eid))).scalar_one()
            page = await get_topic_intelligence(eid, db)
        check(ti.lens2_summary == "Second try worked" and page["lens_errors"] == {},
              "a later re-run that works replaces the lens and clears the old reason")
    finally:
        orch.run_lens_supervisory_agent = real
        await cleanup(eid)


async def test_what_may_not_be_rerun():
    print("the endpoint's guards:")
    for label, kwargs, lens, code in (("an accepted memo", {"accepted": True, "status": "agreed"}, 1, 409),
                                      ("a scan that is running", {"status": "agents_pending"}, 1, 409),
                                      ("a lens that does not exist", {}, 4, 422)):
        eid, _ = await setup(**kwargs)
        try:
            async with AsyncSessionLocal() as db:
                try:
                    await rerun_topic_lens(eid, lens, BackgroundTasks(), db)
                    got = None
                except HTTPException as exc:
                    got = exc.status_code
            check(got == code, f"{label}: refused with {code}")
        finally:
            await cleanup(eid)
    async with AsyncSessionLocal() as db:
        try:
            await rerun_topic_lens("does-not-exist", 1, BackgroundTasks(), db)
            got = None
        except HTTPException as exc:
            got = exc.status_code
    check(got == 404, "no memo: 404")


def main_():
    asyncio.run(test_only_the_chosen_lens_changes())
    asyncio.run(test_a_failed_rerun_keeps_the_old_result_and_says_why())
    asyncio.run(test_what_may_not_be_rerun())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
