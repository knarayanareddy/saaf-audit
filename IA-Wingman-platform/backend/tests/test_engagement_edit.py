"""Correcting an audit's details: a typo in a name, from the screen or from the assistant.

    venv/Scripts/python.exe -m tests.test_engagement_edit

The assistant, asked to fix "Intellegence", said it had no tool for it and did not know where
the name could be edited. The edit existed, on the Engagements list only. Now the assistant
can propose the correction, and what it proposes is limited to a few text fields; the
server refuses a name that is empty. No API calls.
"""
import asyncio
import sys
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select

import main  # noqa: F401  (registers every model)
from database import AsyncSessionLocal
from models.engagement import Engagement
from routers.engagements import update_engagement
from schemas import EngagementUpdate
from services.ai_service import CHAT_TOOLS

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def test_the_tool_offers_only_what_it_should():
    print("the assistant's tool:")
    tool = next((t for t in CHAT_TOOLS if t["name"] == "propose_update_engagement_details"), None)
    check(tool is not None, "it exists")
    props = set(tool["input_schema"]["properties"])
    check(props == {"name", "audit_code", "summary", "lead_auditor", "scope_period", "rationale"},
          f"it offers the text fields and a rationale, nothing else ({sorted(props)})")
    check(not {"status", "entity", "audit_type", "planning_date", "team_members"} & props,
          "not status, entity, type, dates or team: those are the human's, from the pencil")
    check("required" not in tool["input_schema"], "no field is required: only what changes is sent")
    names = [t["name"] for t in CHAT_TOOLS]
    check(len(names) == len(set(names)), "and tool names are still unique")


def test_a_name_cannot_be_emptied():
    print("the name:")
    check(EngagementUpdate(name="  Artificial Intelligence  ").name == "Artificial Intelligence", "a name is trimmed")
    check(EngagementUpdate().name is None, "no name in the request leaves it alone")
    for bad in ("", "   ", "x" * 501):
        try:
            EngagementUpdate(name=bad)
            refused = False
        except ValidationError:
            refused = True
        check(refused, f"a name of {len(bad)} characters ({'blank' if not bad.strip() else 'too long'}) is refused")


async def test_the_correction_is_saved_and_nothing_else_changes():
    print("saving:")
    eid = f"tmp-edit-{uuid4()}"
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=eid, audit_code="26-047", name="Artificial Intellegence", entity="GRP", audit_type="it",
                          team_members='["AA"]', lead_auditor="Lead One", summary="Keep me"))
        await db.commit()
    try:
        async with AsyncSessionLocal() as db:
            out = await update_engagement(eid, EngagementUpdate(name="Artificial Intelligence"), db)
        check(out["name"] == "Artificial Intelligence", "the name is corrected")
        async with AsyncSessionLocal() as db:
            e = (await db.execute(select(Engagement).where(Engagement.id == eid))).scalar_one()
        check(e.audit_code == "26-047" and e.lead_auditor == "Lead One" and e.summary == "Keep me" and e.team_members == '["AA"]',
              "the code, lead, summary and team are untouched")
    finally:
        async with AsyncSessionLocal() as db:
            e = await db.get(Engagement, eid)
            if e:
                await db.delete(e)
            await db.commit()


def main_():
    test_the_tool_offers_only_what_it_should()
    test_a_name_cannot_be_emptied()
    asyncio.run(test_the_correction_is_saved_and_nothing_else_changes())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
