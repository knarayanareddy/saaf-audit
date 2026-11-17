"""Topic Intelligence starts when the auditor presses Run — and not before.

    venv/Scripts/python.exe -m tests.test_auditor_starts_ti

It used to start itself. Any page that polled /agents/pack ran the orchestrator's
scan, which queued every stage whose gate was open, Topic Intelligence first —
so opening the audit started a scan nobody had briefed: no documents, no
keyword, none of what the auditor already knew. A chat proposal could do the
same, with an empty request. Both are closed; this holds every route that could
start a stage to that.

No API calls: the fan-out and the ordering advice are replaced, and the test
asserts on what would have been started.
"""
import asyncio
import sys
from uuid import uuid4

import httpx
from fastapi import BackgroundTasks
from sqlalchemy import select

import main  # noqa: F401 — wires the app and the routers
from config import settings
from database import AsyncSessionLocal, create_tables, run_migrations
from models.agent_run import AgentRun
from models.copilot import CopilotTask
from models.engagement import Engagement
from models.planning import TopicIntelligence
from services import copilot_orchestrator
from services.ai_service import CHAT_TOOLS
from services.stage_actions import AUDITOR_STARTED_STAGE_KEYS, STAGE_RUN_ACTIONS

failures: list[str] = []
ENG = f"ti-by-hand-{uuid4()}"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def tasks_for(stage_key=None):
    async with AsyncSessionLocal() as db:
        q = select(CopilotTask).where(CopilotTask.engagement_id == ENG)
        if stage_key:
            q = q.where(CopilotTask.stage_key == stage_key)
        return (await db.execute(q)).scalars().all()


async def test_the_orchestrator_does_not_queue_it():
    print("the automatic scan:")
    fanned_out: list = []

    async def capture(items, engagement_id):
        fanned_out.extend(items)

    async def keep_order(eng, summary, candidates):
        return {"order": [c["key"] for c in candidates], "rationale": {}}

    real_run, real_advice = copilot_orchestrator._run_tasks, copilot_orchestrator.advise_stage_order
    copilot_orchestrator._run_tasks, copilot_orchestrator.advise_stage_order = capture, keep_order
    try:
        queued = await copilot_orchestrator.scan_and_queue(ENG, BackgroundTasks())
        # Run the queued background call the way the app would, with the fan-out captured.
        bt = BackgroundTasks()
        await copilot_orchestrator.scan_and_queue(ENG, bt)
        for task in bt.tasks:
            await task()
    finally:
        copilot_orchestrator._run_tasks, copilot_orchestrator.advise_stage_order = real_run, real_advice

    started = {stage for _, stage in fanned_out}
    check("topic_intelligence" not in started, f"a fresh audit's scan does not start Topic Intelligence ({sorted(started)})")
    check(not await tasks_for("topic_intelligence"), "and it leaves no task for it behind")
    check("topic_intelligence" not in copilot_orchestrator.TIER_A_STAGE_KEYS,
          "it is not among the stages the orchestrator may start")
    check("frameworks" in copilot_orchestrator.TIER_A_STAGE_KEYS and "bra" in copilot_orchestrator.TIER_A_STAGE_KEYS,
          "while the other planning stages still are — only this one changed")
    async with AsyncSessionLocal() as db:
        ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == ENG))).scalar_one_or_none()
        runs = (await db.execute(select(AgentRun).where(AgentRun.engagement_id == ENG))).scalars().all()
    check(ti is None or ti.status in (None, "not_started"), "the scan is still 'not started'")
    check(not [r for r in runs if r.agent_type.startswith("lens")], "and no lens run exists")
    return queued


async def test_chat_cannot_start_it():
    print("the chat:")
    tool = next(t for t in CHAT_TOOLS if t["name"] == "propose_run_stage")
    offered = tool["input_schema"]["properties"]["stage_key"]["enum"]
    check("topic_intelligence" not in offered, "the assistant cannot propose running it")
    check("Topic Intelligence" in tool["description"] and "its own page" in tool["description"],
          "and its tool description says why and where to send the auditor")
    check("topic_intelligence" not in STAGE_RUN_ACTIONS, "there is no stage action for it")
    check(set(offered) <= set(STAGE_RUN_ACTIONS), "every stage the assistant may propose still has an action")

    result = await copilot_orchestrator.run_stage_now(ENG, "topic_intelligence", BackgroundTasks())
    check(result == {"status": "auditor_starts_this", "task_id": None}, f"run_stage_now refuses it ({result})")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test",
                                 auth=(settings.APP_USERNAME, settings.APP_PASSWORD)) as c:
        r = await c.post(f"/api/copilot/{ENG}/stages/topic_intelligence/run")
    check(r.status_code == 422 and "its own page" in r.text, f"and so does the endpoint an accepted proposal calls ({r.status_code})")
    check(not await tasks_for("topic_intelligence"), "none of it left a task behind")


async def test_the_run_button_still_works():
    print("the button:")
    check("topic_intelligence" in AUDITOR_STARTED_STAGE_KEYS, "the stage is declared as the auditor's to start")
    from routers import agents as agents_router
    check(hasattr(agents_router, "run_agents_v2"), "and the endpoint behind the Run button is untouched (tests.test_scan_start presses it)")


async def cleanup():
    async with AsyncSessionLocal() as db:
        for model in (CopilotTask, AgentRun, TopicIntelligence):
            for row in (await db.execute(select(model).where(model.engagement_id == ENG))).scalars().all():
                await db.delete(row)
        eng = await db.get(Engagement, ENG)
        if eng:
            await db.delete(eng)
        await db.commit()


async def run_all():
    await create_tables()
    await run_migrations()
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=ENG, audit_code="TI-BY-HAND", name="Run by hand test", entity="GRP",
                          audit_type="it", team_members="[]"))
        await db.commit()
    try:
        await test_the_orchestrator_does_not_queue_it()
        await test_chat_cannot_start_it()
        await test_the_run_button_still_works()
    finally:
        await cleanup()


def main_():
    asyncio.run(run_all())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
