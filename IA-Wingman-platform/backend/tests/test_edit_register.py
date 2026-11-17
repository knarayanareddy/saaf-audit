"""The edit register: who proposed each value, and who decided about it.

    venv/Scripts/python.exe -m tests.test_edit_register

Driven through the real app where a person acts (the API, with the actor
header the browser sends) and through the real agent context where a model
acts, because the register decides between those two from context alone — a
test that stamped rows directly would prove nothing about that decision.

No API calls. Writes to the real database on a throwaway engagement and removes
everything it created afterwards.
"""
import asyncio
import json
import sys
from uuid import uuid4

import httpx
from sqlalchemy import select

import main  # noqa: F401 — installs the flush listener and the actor dependency
from config import settings
from database import AsyncSessionLocal, create_tables, run_migrations
from models.agent_call import AgentCall
from models.edit_register import FieldEdit
from models.engagement import Engagement
from models.planning import TopicIntelligence
from models.racm import RacmRisk
from models.reporting import Finding
from services.agent_ledger import agent_context
from services.risk_proposals import ProposedRisk, write as write_proposals

failures: list[str] = []
ENG = f"edit-register-test-{uuid4()}"
RUN = f"run-{uuid4().hex[:8]}"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def client(actor="DA"):
    headers = {"X-IA-Actor": actor} if actor else {}
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test",
                             auth=(settings.APP_USERNAME, settings.APP_PASSWORD), headers=headers)


async def rows_for(entity_id):
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(FieldEdit).where(FieldEdit.entity_id == entity_id)
                                 .order_by(FieldEdit.created_at, FieldEdit.id))).scalars().all()


async def risks():
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(RacmRisk).where(RacmRisk.engagement_id == ENG)
                                 .order_by(RacmRisk.sort_order))).scalars().all()


async def propose(*titles):
    with agent_context(agent="racm_governance", run_id=RUN):
        await write_proposals(ENG, RUN, "governance_assessment",
                              [ProposedRisk(title=t, description="Gap found", inherent_rating="high",
                                            source_ref="Policy.pdf", rationale="Not covered")
                               for t in titles])


async def test_a_proposal_is_recorded_as_the_agents():
    print("an agent proposes:")
    await propose("Third-party register missing", "Incident timelines unclear")
    first = (await risks())[0]
    rows = await rows_for(first.id)
    check(len(rows) == 1 and rows[0].decision == "proposed", f"one 'proposed' row ({[r.decision for r in rows]})")
    check(rows[0].actor_kind == "ai" and rows[0].actor == "racm_governance",
          f"recorded as the agent, not a person ({rows[0].actor_kind}/{rows[0].actor})")
    check(rows[0].run_id == RUN, "with the run that produced it")
    check(json.loads(rows[0].after).get("title") == "Third-party register missing",
          "and what it proposed")


async def test_a_person_edits_accepts_and_cannot_rewrite_origin():
    print("a person edits and decides:")
    first = (await risks())[0]
    async with client("DA") as c:
        r = await c.patch(f"/api/racm/{ENG}/risks/{first.id}", json={"title": "No register of ICT third parties"})
        check(r.status_code == 200, f"the edit is accepted by the API ({r.status_code})")
        await c.patch(f"/api/racm/{ENG}/risks/{first.id}", json={"title": "No register of ICT third parties"})
        r = await c.patch(f"/api/racm/{ENG}/risks/{first.id}", json={"accepted": True, "accepted_by": "You"})
        accepted_by = r.json().get("accepted_by")
        r = await c.patch(f"/api/racm/{ENG}/risks/{first.id}", json={"origin": "human"})
        check(r.status_code == 422, f"turning an AI node into a 'human' one is refused ({r.status_code})")

    rows = await rows_for(first.id)
    edits = [x for x in rows if x.decision == "modified"]
    check(len(edits) == 1, f"the edit is one row; repeating the same value adds none ({len(edits)})")
    if edits:
        e = edits[0]
        check(e.field == "title" and json.loads(e.before) == "Third-party register missing"
              and json.loads(e.after) == "No register of ICT third parties",
              "with the field, and the value before and after")
        check(e.actor_kind == "human" and e.actor == "DA" and e.actor_verified is False,
              "by the person in the header, marked unverified")
    check(any(x.decision == "accepted" and x.actor == "DA" for x in rows), "the acceptance is a row of its own")
    check(accepted_by == "DA", f"accepted_by is who sent the request, never the payload's 'You' ({accepted_by})")

    async with AsyncSessionLocal() as db:
        node = await db.get(RacmRisk, first.id)
    check(node.origin == "ai", "and the node still says a model proposed it")


async def test_removing_a_proposal_is_a_rejection():
    print("rejecting and superseding:")
    second = (await risks())[1]
    async with client("DA") as c:
        await c.delete(f"/api/racm/{ENG}/risks/{second.id}")
    rows = await rows_for(second.id)
    check(rows and rows[-1].decision == "rejected" and rows[-1].actor == "DA",
          f"a person deleting an open AI proposal rejects it ({[r.decision for r in rows]})")

    await propose("A proposal the next run will replace")
    replaced = [r for r in await risks() if r.title == "A proposal the next run will replace"][0]
    await propose("Its replacement")
    rows = await rows_for(replaced.id)
    check(rows and rows[-1].decision == "superseded" and rows[-1].actor_kind == "ai",
          f"an agent clearing its own open proposal on a re-run supersedes it ({[r.decision for r in rows]})")
    accepted = (await risks())[0]
    check(accepted.title == "No register of ICT third parties",
          "and the re-run left the accepted risk alone")


async def test_a_person_creating_a_node():
    print("a person creates:")
    async with client("JV") as c:
        r = await c.post(f"/api/racm/{ENG}/risks", json={"title": "Manual risk from walkthrough"})
    rows = await rows_for(r.json()["id"])
    check(rows and rows[0].decision == "created" and rows[0].actor == "JV" and rows[0].actor_kind == "human",
          f"recorded as created by that person ({[(x.decision, x.actor) for x in rows]})")


async def test_no_header_is_said_not_guessed():
    print("without the header:")
    first = (await risks())[0]
    async with client(None) as c:
        await c.patch(f"/api/racm/{ENG}/risks/{first.id}", json={"description": "Edited without a name"})
    rows = [x for x in await rows_for(first.id) if x.field == "description"]
    check(rows and rows[-1].actor == "unknown", f"the actor is 'unknown', not a filled-in name ({rows[-1].actor if rows else None})")


async def test_the_register_and_the_change_share_one_transaction():
    print("one transaction:")
    first = (await risks())[0]
    before = len(await rows_for(first.id))
    async with AsyncSessionLocal() as db:
        node = await db.get(RacmRisk, first.id)
        node.title = "A change that will be rolled back"
        await db.flush()
        await db.rollback()
    check(len(await rows_for(first.id)) == before, "a rolled-back change leaves no register row behind")


FINDING = str(uuid4())


async def test_the_drafter_replacing_the_auditors_text_is_on_record():
    print("the finding drafter:")
    fid = FINDING
    async with AsyncSessionLocal() as db:
        db.add(Finding(id=fid, engagement_id=ENG, title="Re-screening",
                       condition="Customers not re-screened", status="draft"))
        await db.commit()
    with agent_context(agent="finding_drafter", run_id=RUN):
        async with AsyncSessionLocal() as db:
            f = await db.get(Finding, fid)
            f.condition = "14 of 60 sampled customers had not been re-screened since onboarding."
            await db.commit()
    rows = [x for x in await rows_for(fid) if x.field == "condition"]
    check(rows and rows[-1].decision == "proposed" and rows[-1].actor == "finding_drafter",
          "a model replacing a field is recorded as its proposal")
    check(rows and json.loads(rows[-1].before) == "Customers not re-screened",
          "with the auditor's own text it replaced kept as 'before'")


async def test_a_lens_summary_names_its_own_run():
    print("Topic Intelligence:")
    tid, lens1 = str(uuid4()), f"lens1-{uuid4().hex[:6]}"
    async with AsyncSessionLocal() as db:
        db.add(TopicIntelligence(id=tid, engagement_id=ENG, status="agents_pending"))
        await db.commit()
    check(not await rows_for(tid), "an empty status row is not recorded as a decision")
    with agent_context(agent="topic_intelligence"):
        async with AsyncSessionLocal() as db:
            ti = await db.get(TopicIntelligence, tid)
            ti.lens1_run_id = lens1
            ti.lens1_summary = "DORA applies from January 2025."
            await db.commit()
    rows = [x for x in await rows_for(tid) if x.field == "lens1_summary"]
    check(rows and rows[-1].run_id == lens1,
          f"lens 1's summary is linked to lens 1's run, not the scan's ({rows[-1].run_id if rows else None})")


async def test_the_rest_of_the_file():
    """The other surfaces where people change what an agent wrote — tracked by
    configuration, so each needs only to show its own particularity works."""
    print("the rest of the file:")
    from datetime import datetime, timezone
    from models.planning import AuditNotificationLetter, FieldworkObservation, ScopeItem, ScopeObjectives, WorkProgram

    wp_id, anl_id, obs_id, scope_id, item_id = (str(uuid4()) for _ in range(5))
    anl_run = f"anl-{uuid4().hex[:6]}"
    with agent_context(agent="work_program_generator", run_id=RUN):
        async with AsyncSessionLocal() as db:
            db.add(WorkProgram(id=wp_id, engagement_id=ENG, status="draft",
                               rows='[{"step": "Inspect approvals"}]', generator_run_id=RUN))
            await db.commit()
    with agent_context(agent="anl_drafter"):
        async with AsyncSessionLocal() as db:
            db.add(AuditNotificationLetter(id=anl_id, engagement_id=ENG, background="Drafted background",
                                           drafter_run_id=anl_run))
            await db.commit()
    async with AsyncSessionLocal() as db:
        db.add(FieldworkObservation(id=obs_id, engagement_id=ENG, title="Late approvals",
                                    is_ai_generated=True))
        db.add(ScopeObjectives(id=scope_id, engagement_id=ENG, overall_objective="Assess approvals"))
        await db.commit()
    async with AsyncSessionLocal() as db:
        db.add(ScopeItem(id=item_id, scope_id=scope_id, item_type="in_scope",
                         description="Payment approvals", is_accepted=False))
        await db.commit()
    async with AsyncSessionLocal() as db:
        wp = await db.get(WorkProgram, wp_id)
        wp.signed_off_at = datetime.now(timezone.utc)
        item = await db.get(ScopeItem, item_id)
        item.is_accepted = True
        await db.commit()

    wp_rows = await rows_for(wp_id)
    check([r.decision for r in wp_rows] == ["proposed", "accepted"],
          f"a work program is proposed by its generator, then signed off ({[r.decision for r in wp_rows]})")
    anl_rows = await rows_for(anl_id)
    check(anl_rows and anl_rows[0].run_id == anl_run,
          "an ANL draft names the drafter's run from its own run column")
    obs_rows = await rows_for(obs_id)
    check(obs_rows and obs_rows[0].decision == "proposed" and obs_rows[0].actor_kind == "ai",
          "a fieldwork observation marked is_ai_generated is recorded as a machine's proposal")
    item_rows = await rows_for(item_id)
    check([r.decision for r in item_rows] == ["created", "accepted"],
          f"a scope item, which has no engagement column, is still recorded ({[r.decision for r in item_rows]})")

    async with AsyncSessionLocal() as db:
        for model, rid in ((WorkProgram, wp_id), (AuditNotificationLetter, anl_id),
                           (FieldworkObservation, obs_id), (ScopeItem, item_id), (ScopeObjectives, scope_id)):
            row = await db.get(model, rid)
            if row:
                await db.delete(row)
        await db.commit()
    async with AsyncSessionLocal() as db:
        # Rows of tables without an engagement column carry no engagement, so
        # cleanup() cannot find them by it; this test removes its own.
        for row in (await db.execute(select(FieldEdit).where(FieldEdit.entity_id == item_id))).scalars().all():
            await db.delete(row)
        await db.commit()


async def test_history_and_profile():
    print("reading it back:")
    first = (await risks())[0]
    async with client("DA") as c:
        h = (await c.get(f"/api/history/racm_risks/{first.id}")).json()
    runs = [r["run"] for r in h["rows"] if r["run"]]
    check(runs and runs[0]["linked"] is False,
          "a proposal whose run has no ledger rows says 'not linked' instead of naming no model")

    async with AsyncSessionLocal() as db:
        db.add(AgentCall(id=str(uuid4()), engagement_id=ENG, agent="racm_governance", run_id=RUN,
                         model="claude-sonnet-5-5", prompt_version="abc123def456",
                         input_tokens=10, output_tokens=5, cached_tokens=0, thinking_tokens=0,
                         duration_ms=1, cost_usd=0.001, ok=True))
        await db.commit()
    async with client("DA") as c:
        h = (await c.get(f"/api/history/racm_risks/{first.id}")).json()
        bad = await c.get(f"/api/history/engagements/{ENG}")
    run = next(r["run"] for r in h["rows"] if r["run"])
    check(run["linked"] and run["models"] == ["claude-sonnet-5-5"] and run["prompt_versions"] == ["abc123def456"],
          f"with a ledger row it names the model and the prompt version ({run})")
    check(h["recorded_since"] is not None, "and says since when the register has been keeping records")
    check(bad.status_code == 404, "and only tracked records have a history endpoint")

    async def register_kinds():
        async with client("DA") as c:
            p = (await c.get(f"/api/engagements/{ENG}/ai-share")).json()
        return {k["key"]: k for k in p["register"]["kinds"]}, p

    reg, p = await register_kinds()
    r = reg.get("racm_risks", {})
    check((r.get("changed_by_person"), r.get("rejected"), r.get("superseded"), r.get("unchanged"),
           r.get("created_by_person")) == (1, 1, 1, 1, 1),
          f"each risk has one outcome: changed, rejected, replaced, unchanged, a person's own ({r})")
    check(p["basis"] == "records+register", "and the panel says the register is part of its basis")
    check(reg.get("findings", {}).get("unchanged") == 1,
          f"a drafted finding has no decision step, so it stands as 'unchanged' rather than open forever "
          f"({reg.get('findings')})")

    async with client("DA") as c:
        await c.patch(f"/api/reporting/{ENG}/findings/{FINDING}", json={"condition": "14 of 60, see W/P 4.2."})
    reg, _ = await register_kinds()
    check(reg.get("findings", {}).get("changed_by_person") == 1, "a person's edit after the draft counts as theirs")
    with agent_context(agent="finding_drafter", run_id=RUN):
        async with AsyncSessionLocal() as db:
            f = await db.get(Finding, FINDING)
            f.condition = "14 of 60 sampled customers were not re-screened (W/P 4.2)."
            await db.commit()
    reg, _ = await register_kinds()
    check(reg.get("findings", {}).get("unchanged") == 1,
          f"but when the drafter rewrites it afterwards, what stands is the drafter's text again ({reg.get('findings')})")


async def test_the_prompt_version_reaches_the_ledger():
    print("prompt version:")
    from types import SimpleNamespace
    from services import ai_service
    from services.agent_contract import prompt_version, run_agent
    from services.agent_schemas import RatingChallenge

    reply = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps(
            {"agrees": True, "suggested_rating": "high", "rationale": "The control is absent."}))],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                              cache_creation_input_tokens=0))

    async def script(**kwargs):
        return reply

    original = ai_service._call_with_retry
    ai_service._call_with_retry = script
    try:
        with agent_context(record=False):
            a = await run_agent("You give second opinions.", "x", RatingChallenge)
            b = await run_agent("You give second opinions, carefully.", "x", RatingChallenge)
    finally:
        ai_service._call_with_retry = original
    check(len(a.meta.prompt_version) == 12, f"each call carries a prompt version ({a.meta.prompt_version})")
    check(a.meta.prompt_version != b.meta.prompt_version, "and a changed system prompt is a new version")
    check(prompt_version("same") == prompt_version("same"), "the same instructions give the same version")


async def cleanup():
    async with AsyncSessionLocal() as db:
        for model in (RacmRisk, Finding, TopicIntelligence, AgentCall):
            for row in (await db.execute(select(model).where(model.engagement_id == ENG))).scalars().all():
                await db.delete(row)
        await db.commit()
    async with AsyncSessionLocal() as db:
        for row in (await db.execute(select(FieldEdit).where(FieldEdit.engagement_id == ENG))).scalars().all():
            await db.delete(row)
        await db.commit()


async def run_all():
    await create_tables()
    await run_migrations()
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=ENG, name="Edit register test", entity="GRP", audit_type="it", team_members="[]"))
        await db.commit()
    try:
        await test_a_proposal_is_recorded_as_the_agents()
        await test_a_person_edits_accepts_and_cannot_rewrite_origin()
        await test_removing_a_proposal_is_a_rejection()
        await test_a_person_creating_a_node()
        await test_no_header_is_said_not_guessed()
        await test_the_register_and_the_change_share_one_transaction()
        await test_the_drafter_replacing_the_auditors_text_is_on_record()
        await test_a_lens_summary_names_its_own_run()
        await test_the_rest_of_the_file()
        await test_history_and_profile()
        await test_the_prompt_version_reaches_the_ledger()
    finally:
        await cleanup()
        async with AsyncSessionLocal() as db:
            eng = await db.get(Engagement, ENG)
            if eng:
                await db.delete(eng)
                await db.commit()


def main_():
    asyncio.run(run_all())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
