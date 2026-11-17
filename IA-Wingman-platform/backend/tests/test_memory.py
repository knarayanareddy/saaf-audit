"""Tests for cross-engagement memory (services/memory_context.py).

    venv/Scripts/python.exe -m tests.test_memory

Creates a throwaway engagement, runs the drafters against a scripted client, and
deletes everything it made. No API calls.

The thing being defended is easy to lose: `audit_memory` existed for months and
no agent ever called it, so the Background Risk Assessment kept answering its own
prompt's question about "what we know from prior audits" by making something up.
These tests assert that the recall is actually in the prompt, and that it arrives
with the framing that keeps a precedent from being read as evidence.
"""
import asyncio
import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import delete, select

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.engagement import Engagement
from models.planning import BackgroundRiskAssessment
from services import ai_service
from services.agent_ledger import agent_context
from services.memory_context import Memory, recall_for

failures: list[str] = []
MARK = "memory-test"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean():
    async with AsyncSessionLocal() as db:
        engs = (await db.execute(select(Engagement).where(Engagement.audit_code == MARK))).scalars().all()
        for e in engs:
            await db.execute(delete(BackgroundRiskAssessment)
                             .where(BackgroundRiskAssessment.engagement_id == e.id))
            await db.execute(delete(AgentRun).where(AgentRun.engagement_id == e.id))
            await db.delete(e)
        await db.commit()


async def _throwaway() -> str:
    """An engagement on a topic the demo data has precedents for."""
    async with AsyncSessionLocal() as db:
        eng = Engagement(
            id=str(uuid4()), audit_code=MARK,
            name="Customer onboarding and sanctions screening review",
            entity="GRP", audit_type="Compliance", status="in_planning",
            summary="Onboarding due diligence, beneficial ownership and periodic re-screening.",
        )
        db.add(eng)
        await db.commit()
        return eng.id


# ── The recall itself ────────────────────────────────────────────────────────

def test_a_precedent_says_where_it_came_from_and_how_settled_it_is():
    print("recall:")
    eng_id = asyncio.run(_throwaway())

    async def run():
        async with AsyncSessionLocal() as db:
            return await recall_for(db, eng_id, limit=6, kinds=("finding", "risk"))

    memory = asyncio.run(run())
    check(not memory.is_empty, f"the demo data yields precedents for this topic ({len(memory.items)})")
    if memory.is_empty:
        return

    check(all(i.get("source_engagement_name") for i in memory.items),
          "every precedent names the audit it came from")
    check(all("settled" in i for i in memory.items),
          "and whether that audit's conclusion is settled or still in flight")
    check(all(i.get("shared") for i in memory.items),
          "and the terms it matched on, so a coincidence can be dismissed")
    check(all(i["kind"] in ("finding", "risk") for i in memory.items),
          "the kind filter is honoured — an agent is not shown material it cannot use")
    check("prior audit" in memory.sentence(),
          f"the receipt line reads plainly: {memory.sentence()}")


def test_the_block_frames_a_precedent_as_context_not_evidence():
    print("framing:")
    eng_id = asyncio.run(_throwaway())

    async def run():
        async with AsyncSessionLocal() as db:
            return await recall_for(db, eng_id, limit=4)

    memory = asyncio.run(run())
    # The preamble is wrapped prose, so a phrase that reads as one line in the
    # source may span two. Asserting on the wrapped form would be testing the
    # line breaks rather than what the block says.
    block = " ".join(memory.block.split())
    check("context, never evidence" in block,
          "the block says outright that a precedent is not evidence about this audit")
    check("Never state a prior finding as a fact about this audit" in block,
          "and forbids the specific misuse")
    check("[settled]" in block and "[in progress]" in block,
          "it explains both marks before using them")
    check("naming the audit it came from" in block,
          "and requires the agent to attribute what it borrows")
    check("keyword overlap, not judgement" in block,
          "it admits how the match was made, so an irrelevant one can be ignored")

    # The thing the schema cannot support must not be claimed.
    for phrase in ("still open", "remediat", "follow-up", "implemented"):
        check(phrase not in block.lower(),
              f"it makes no claim about {phrase!r} — nothing here tracks that")


def test_an_engagement_with_no_precedents_says_so():
    print("nothing on file:")
    empty = Memory()
    check(empty.is_empty, "an empty recall is empty")
    check(empty.sentence() == "no prior-audit precedents matched",
          f"and says so rather than going quiet: {empty.sentence()}")
    check(empty.block == "", "with no block to put in a prompt")


# ── The agents that use it ───────────────────────────────────────────────────

def test_the_risk_assessment_is_given_the_history_its_prompt_asks_for():
    print("the Background Risk Assessment:")
    eng_id = asyncio.run(_throwaway())
    captured = {}

    async def fake(system_prompt, user_prompt, max_tokens=4096, tier=None):
        captured["prompt"] = user_prompt
        return {
            "section_strategy": "s", "section_risk_tolerance": "t",
            "section_governance": "g", "section_frameworks": "f",
            "risk_items": [],
        }

    async def run():
        async with AsyncSessionLocal() as db:
            bra = BackgroundRiskAssessment(id=str(uuid4()), engagement_id=eng_id, status="drafting")
            run_row = AgentRun(id=str(uuid4()), engagement_id=eng_id,
                               agent_type="bra_drafter", status="pending")
            db.add_all([bra, run_row])
            await db.commit()
            ids = (bra.id, run_row.id)

        from services import bra_drafter
        original = bra_drafter.run_agent_to_json
        bra_drafter.run_agent_to_json = fake
        try:
            with agent_context(record=False):
                await bra_drafter.run_bra_drafter(ids[0], ids[1], eng_id)
        finally:
            bra_drafter.run_agent_to_json = original

    asyncio.run(run())
    prompt = captured.get("prompt", "")
    check(bool(prompt), "the drafter built a prompt")
    check("PRIOR AUDITS ON ADJACENT TOPICS" in prompt,
          "which now carries what earlier audits found")
    check("context, never evidence" in prompt,
          "with the framing attached, not just the list")
    # The prompt's own question, which used to have no answer.
    check("what we know from prior audits" in prompt,
          "the section that asks for prior-audit knowledge is still there…")
    check(prompt.index("PRIOR AUDITS ON ADJACENT TOPICS") < prompt.index("Produce ONLY a JSON object"),
          "…and the material to answer it now arrives before the instruction")


def test_the_rating_challenge_sees_how_comparable_findings_were_rated():
    print("the rating challenge:")
    src = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "services" / "finding_drafter.py").read_text(encoding="utf-8")
    check("HOW COMPARABLE FINDINGS WERE RATED ELSEWHERE" in src,
          "the challenge prompt carries comparable ratings")
    check('kinds=("finding",)' in src,
          "and only findings — a prior control tells it nothing about a severity call")
    check("a prior rating is not binding" in src,
          "while saying plainly that precedent does not decide it")


def test_the_other_two_agents_are_wired():
    print("the rest:")
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "services"
    for name, why in (
        ("work_program_generator.py", "a prior finding is a reason to test something here"),
        ("orchestrator.py", "an area already covered is a scoping input"),
    ):
        src = (root / name).read_text(encoding="utf-8")
        check("recall_for" in src, f"{name}: {why}")


def main():
    asyncio.run(_clean())
    try:
        test_a_precedent_says_where_it_came_from_and_how_settled_it_is()
        test_the_block_frames_a_precedent_as_context_not_evidence()
        test_an_engagement_with_no_precedents_says_so()
        test_the_risk_assessment_is_given_the_history_its_prompt_asks_for()
        test_the_rating_challenge_sees_how_comparable_findings_were_rated()
        test_the_other_two_agents_are_wired()
    finally:
        asyncio.run(_clean())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
