"""The AI-share panel: how much of an audit file IA Wingman proposed.

    venv/Scripts/python.exe -m tests.test_ai_share

Through the real endpoint, on a throwaway engagement holding a few of each
kind of record. The point under test is what each number claims: an item
without an AI marker is a person's only where the marker says so, and is
"no AI run recorded" where the marker is just a run column.

No API calls. Removes everything it created afterwards.
"""
import asyncio
import sys
from uuid import uuid4

import httpx
from sqlalchemy import select

import main  # noqa: F401 — installs the flush listener
from config import settings
from database import AsyncSessionLocal, create_tables, run_migrations
from models.edit_register import FieldEdit
from models.engagement import Engagement
from models.planning import (
    ApplicableFramework, AuditNotificationLetter, FieldworkObservation, KeyAuditQuestion,
    KickoffAgenda, ScopeItem, ScopeObjectives, WorkProgram,
)
from models.racm import RacmRisk
from models.reporting import Finding
from services.agent_ledger import agent_context

failures: list[str] = []
ENG = f"ai-share-test-{uuid4()}"
BACKGROUND_ROW = str(uuid4())
SCOPE = str(uuid4())
CREATED: list[tuple] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def share():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test",
                                 auth=(settings.APP_USERNAME, settings.APP_PASSWORD)) as c:
        r = await c.get(f"/api/engagements/{ENG}/ai-share")
    return r.json()


async def add(*objs):
    async with AsyncSessionLocal() as db:
        for o in objs:
            db.add(o)
            CREATED.append((type(o), o.id))
        await db.commit()


async def test_the_file_as_its_records_say():
    print("from the records themselves:")
    await add(
        RacmRisk(id=str(uuid4()), engagement_id=ENG, title="Proposed, accepted", origin="ai", accepted=True),
        RacmRisk(id=str(uuid4()), engagement_id=ENG, title="Proposed, open", origin="ai", accepted=False),
        RacmRisk(id=str(uuid4()), engagement_id=ENG, title="A person's", origin="human", accepted=True),
        ApplicableFramework(id=str(uuid4()), engagement_id=ENG, framework_code="DORA",
                            framework_name="DORA", source="ai_suggested", is_accepted=False),
        ApplicableFramework(id=str(uuid4()), engagement_id=ENG, framework_code="OWN",
                            framework_name="Own policy", source="manual", is_accepted=True),
        ScopeObjectives(id=SCOPE, engagement_id=ENG, overall_objective="Assess approvals"),
        Finding(id=str(uuid4()), engagement_id=ENG, title="Drafted", drafter_run_id="run-x"),
        Finding(id=str(uuid4()), engagement_id=ENG, title="No run on record"),
        FieldworkObservation(id=str(uuid4()), engagement_id=ENG, title="Late approvals", is_ai_generated=True),
        WorkProgram(id=str(uuid4()), engagement_id=ENG, status="ready", rows="[]", generator_run_id="run-wp"),
        AuditNotificationLetter(id=str(uuid4()), engagement_id=ENG, background="x", head_ia_status="approved",
                                status="approved"),
        KickoffAgenda(id=str(uuid4()), engagement_id=ENG, status="not_started"),
    )
    await add(
        ScopeItem(id=str(uuid4()), scope_id=SCOPE, item_type="in_scope", description="Payments",
                  source="from_frameworks", is_accepted=True),
        KeyAuditQuestion(id=str(uuid4()), scope_id=SCOPE, question_text="Who approves?", source="manual"),
    )
    # The records exist; what the register made of them is the next test's.
    async with AsyncSessionLocal() as db:
        for row in (await db.execute(select(FieldEdit).where(
                FieldEdit.entity_id.in_([i for _, i in CREATED])))).scalars().all():
            await db.delete(row)
        # `recorded_since` is the start of the whole register, so the test supplies one earlier row
        # of its own rather than relying on what other tests or the app left in the database.
        db.add(FieldEdit(id=BACKGROUND_ROW, entity="ai_share_test_background", entity_id=BACKGROUND_ROW,
                         field="*", actor_kind="human", actor="DA", decision="created"))
        await db.commit()

    p = await share()
    h = p["headline"]
    check((h["proposed"], h["accepted"], h["open"], h["by_person"], h["no_run_recorded"]) == (6, 2, 2, 3, 1),
          f"the headline adds the kinds up ({h})")
    kinds = {k["key"]: k for k in p["kinds"]}
    risks = kinds.get("racm_risks", {})
    check((risks.get("proposed"), risks.get("accepted"), risks.get("open"), risks.get("by_person")) == (2, 1, 1, 1),
          f"risks: proposed and accepted, proposed and open, a person's ({risks})")
    check(kinds.get("scope_items", {}).get("accepted") == 1,
          "scope items are found through the audit's scope, though they have no engagement column")
    findings = kinds.get("findings", {})
    check(findings.get("by_person") == 0 and findings.get("no_run_recorded") == 1,
          f"a finding without a drafter run is 'no AI run recorded', not claimed as a person's ({findings})")
    obs = kinds.get("fieldwork_observations", {})
    check(obs.get("has_decision") is False and obs.get("open") == 0,
          "an observation has no decision step, so nothing about it is 'open'")
    check("racm_tests" not in kinds, "kinds the file holds none of are left out")
    docs = {d["key"]: d for d in p["documents"]}
    check(docs.get("work_programs", {}).get("written_by") == "ai"
          and docs["work_programs"]["decision"] == {"step": "sign-off", "done": False},
          f"the work program: an AI draft, not yet signed off ({docs.get('work_programs')})")
    check(docs.get("audit_notification_letters", {}).get("written_by") == "no_run_recorded"
          and docs["audit_notification_letters"]["decision"]["done"] is True,
          "the letter: no run on record, approved by the Head of IA")
    check("kickoff_agendas" not in docs, "a document not started yet is not listed")
    check(p["basis"] == "records" and p["register"]["kinds"] == [],
          "with nothing in the register for this audit, the panel says its basis is the records alone")
    check(p["register"]["recorded_since"] is not None, "and says since when the register exists")


async def test_the_register_sees_scope_items_too():
    print("from the register:")
    item = ScopeItem(id=str(uuid4()), scope_id=SCOPE, item_type="in_scope", description="Refunds",
                     source="from_topic_intelligence", is_accepted=False)
    with agent_context(agent="scope_engine", run_id="run-scope"):
        await add(item)
    p = await share()
    reg = {k["key"]: k for k in p["register"]["kinds"]}
    check(reg.get("scope_items", {}).get("unchanged") == 1,
          f"a proposed scope item's register rows count for its audit ({reg.get('scope_items')})")
    check(reg.get("scope_items", {}).get("label") == "Scope items", "with the kind's label")
    check(p["basis"] == "records+register", "and the basis now includes the register")


async def cleanup():
    async with AsyncSessionLocal() as db:
        for model, rid in reversed(CREATED):
            row = await db.get(model, rid)
            if row:
                await db.delete(row)
        await db.commit()
    async with AsyncSessionLocal() as db:
        ids = [i for _, i in CREATED]
        for row in (await db.execute(select(FieldEdit).where(
                (FieldEdit.engagement_id == ENG) | FieldEdit.entity_id.in_(ids + [BACKGROUND_ROW])))).scalars().all():
            await db.delete(row)
        eng = await db.get(Engagement, ENG)
        if eng:
            await db.delete(eng)
        await db.commit()


async def run_all():
    await create_tables()
    await run_migrations()
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=ENG, name="AI share test", entity="GRP", audit_type="it", team_members="[]"))
        await db.commit()
    try:
        await test_the_file_as_its_records_say()
        await test_the_register_sees_scope_items_too()
    finally:
        await cleanup()


def main_():
    asyncio.run(run_all())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
