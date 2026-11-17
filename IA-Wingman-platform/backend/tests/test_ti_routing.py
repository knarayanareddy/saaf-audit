"""Topic Intelligence, step 2: ten frameworks to choose from, and questions in the wrong place.

    venv/Scripts/python.exe -m tests.test_ti_routing

The first run on 26-047 proposed ten frameworks with six selected, and sent every
sponsor and SME question to Scope as a "key audit question". Now:

1. Frameworks come in tiers. At most five are core, and only core is selected.
2. Sponsor questions go to the kick-off notes, SME questions to the interview
   guide, and Scope gets its own key audit questions.

No API calls: the model is not involved, only what is done with its answer.
"""
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

import main  # noqa: F401  (registers every model)
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import ApplicableFramework, KeyAuditQuestion, ScopeObjectives, TopicIntelligence
from routers.planning import accept_topic_intelligence
from services.auditee_context import load as load_auditee_context
from services.orchestrator_agent import (
    MAX_CORE_FRAMEWORKS, _build_synthesis_prompt, _validate_synthesis, apply_framework_tiers,
)

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def fw(code, tier=None, primary=False):
    item = {"framework_code": code, "framework_name": code, "id": code, "included": True, "is_primary": primary}
    if tier is not None:
        item["tier"] = tier
    return item


def test_frameworks_are_tiered_and_only_core_is_selected():
    print("frameworks:")
    fws = [fw("A", "optional"), fw("B", "core"), fw("C", "supporting"), fw("D", "core")]
    apply_framework_tiers(fws)
    check([f["framework_code"] for f in fws] == ["B", "D", "C", "A"], "core first, then supporting, then optional")
    check([f["included"] for f in fws] == [True, True, False, False], "only core is selected")

    many = [fw(f"F{i}", "core", primary=(i == 6)) for i in range(8)]
    apply_framework_tiers(many)
    core = [f for f in many if f["tier"] == "core"]
    check(len(core) == MAX_CORE_FRAMEWORKS and sum(f["included"] for f in many) == MAX_CORE_FRAMEWORKS,
          f"never more than {MAX_CORE_FRAMEWORKS} core, whatever the model says")
    check(any(f["framework_code"] == "F6" for f in core), "and the primary one stays core when the rest is cut")

    none_core = [fw("X", "supporting"), fw("Y", "optional", primary=True)]
    apply_framework_tiers(none_core)
    check(none_core[0]["framework_code"] == "Y" and none_core[0]["included"] and none_core[0]["tier"] == "core",
          "no core given: the primary framework becomes core, so the auditor never starts empty")

    odd = [fw("P", "mandatory"), fw("Q")]
    apply_framework_tiers(odd)
    check({f["tier"] for f in odd} == {"core", "supporting"} and sum(f["included"] for f in odd) == 1,
          "a missing or invalid tier is read as supporting (then one becomes core if none is)")
    empty: list = []
    apply_framework_tiers(empty)
    check(empty == [], "no frameworks: nothing happens")


def good_synthesis(**agenda_extra):
    return {
        "key_risk_areas": [{"title": "t"}], "excluded_areas": [{"title": "e"}],
        "interview_agenda": {"sponsor": [{"question_text": "S?"}], "sme": [{"question_text": "M?"}],
                             "ia_prework": ["p"], **agenda_extra},
        "conclusion": "c",
        "proposed_frameworks": [{"framework_code": "A", "framework_name": "A law", "tier": "core"}],
    }


def test_the_contract_accepts_the_new_group_and_the_old_shape():
    print("synthesis contract:")
    check(_validate_synthesis(good_synthesis()), "a scan without key audit questions (the old shape) still validates")
    check(_validate_synthesis(good_synthesis(key_audit_questions=[{"question_text": "K?"}])),
          "and one with them validates")
    check(not _validate_synthesis(good_synthesis(key_audit_questions=["K?"])),
          "key audit questions that are plain strings are rejected, like the other groups")
    check(not _validate_synthesis(good_synthesis(surprise=[])), "an unknown agenda group is still rejected")
    eng = Engagement(name="AI", entity="GRP", audit_type="it")
    prompt = _build_synthesis_prompt(eng, "l1", "l2", "l3", None)
    check('"tier": "core|supporting|optional"' in prompt and "At most 5" in prompt,
          "the prompt asks for a tier on every framework, core at most five")
    check("key_audit_questions" in prompt and "kick-off meeting" in prompt and "in an interview" in prompt,
          "and writes each kind of question for its own place")


async def test_accepting_routes_each_question_to_its_place():
    print("accepting the memo:")
    eid = f"tmp-routing-{uuid4()}"
    agenda = {
        "sponsor": [{"id": "s1", "question_text": "What does success look like?", "included": True},
                    {"id": "s2", "question_text": "Unticked sponsor question", "included": False}],
        "sme": [{"id": "m1", "question_text": "How is an AI system inventoried?", "included": True}],
        "ia_prework": ["Read the AI policy"],
        "key_audit_questions": [{"id": "k1", "question_text": "Does the bank know every AI system?", "included": True},
                                {"id": "k2", "question_text": "Unticked key question", "included": False}],
    }
    fws = [{**fw("EU-AI-ACT", "core"), "included": True},
           {**fw("GDPR", "supporting"), "included": False}]
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=eid, audit_code="TMP-RT", name="AI", entity="GRP", audit_type="it", team_members="[]"))
        db.add(TopicIntelligence(id=str(uuid4()), engagement_id=eid, status="review",
                                 key_risk_areas=json.dumps([]), excluded_areas=json.dumps([]),
                                 interview_agenda=json.dumps(agenda), proposed_frameworks=json.dumps(fws)))
        await db.commit()
    try:
        async with AsyncSessionLocal() as db:
            summary = await accept_topic_intelligence(eid, db)
        async with AsyncSessionLocal() as db:
            scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == eid))).scalar_one()
            kaq = [q.question_text for q in (await db.execute(
                select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars()]
            fw_rows = [f.framework_code for f in (await db.execute(
                select(ApplicableFramework).where(ApplicableFramework.engagement_id == eid))).scalars()]
            ctx = await load_auditee_context(db, eid)
        check(kaq == ["Does the bank know every AI system?"],
              f"Scope gets only the ticked key audit questions, not sponsor or SME questions ({kaq})")
        check(summary["questions_queued"] == 1, "and the summary counts them")
        check(fw_rows == ["EU-AI-ACT"], f"only the selected (core) framework is queued ({fw_rows})")
        check(ctx.sponsor_questions == ["What does success look like?"],
              "the kick-off reads the ticked sponsor questions from the memo")
        check(ctx.sme_questions == ["How is an AI system inventoried?"],
              "the interview guide reads the ticked SME questions from the memo")
    finally:
        async with AsyncSessionLocal() as db:
            for model in (ApplicableFramework, TopicIntelligence):
                for row in (await db.execute(select(model).where(model.engagement_id == eid))).scalars().all():
                    await db.delete(row)
            scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == eid))).scalar_one_or_none()
            if scope:
                for q in (await db.execute(select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars().all():
                    await db.delete(q)
                await db.delete(scope)
            e = await db.get(Engagement, eid)
            if e:
                await db.delete(e)
            await db.commit()


def test_the_drafters_are_told_about_their_questions():
    print("the drafters' prompts:")
    root = Path(__file__).resolve().parent.parent / "services"
    kick = (root / "kickoff_drafter.py").read_text(encoding="utf-8")
    guide = (root / "interview_v2_service.py").read_text(encoding="utf-8")
    check("ctx.sponsor_questions" in kick and "Start with the sponsor questions listed above" in kick,
          "the kick-off prompt carries the sponsor questions and asks to start from them")
    check('ctx["sme_questions"]' in guide and "PROPOSES FOR SUBJECT-MATTER EXPERTS" in guide,
          "the interview-guide prompt carries the SME questions")


def main_():
    test_frameworks_are_tiered_and_only_core_is_selected()
    test_the_contract_accepts_the_new_group_and_the_old_shape()
    asyncio.run(test_accepting_routes_each_question_to_its_place())
    test_the_drafters_are_told_about_their_questions()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
