"""The coverage sweep answers by reference where it can, and says when it guessed.

    venv/Scripts/python.exe -m tests.test_coverage_reference

Check 2 asked "is this key risk area reflected in scope?" by comparing words.
A scope item cascaded from Topic Intelligence now records the risk area that
produced it, so for anything written since the answer is a fact. The word pass
survives for items that predate the field, and the check reports how many of
each it used — the whole point being that those are not the same claim.
"""
import asyncio
import json
import sys
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import KeyAuditQuestion, ScopeItem, ScopeObjectives, TopicIntelligence
from models.racm import RacmControl, RacmObjective, RacmRisk, RacmTest
from services import scope_sources
from services.coverage_service import compute_coverage

failures: list[str] = []
E = "test-coverage-reference"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean(db):
    # Deepest first, so a parent is never deleted out from under a child.
    scoped = {ScopeItem, KeyAuditQuestion}   # these hang off the scope, not the engagement
    for model in (RacmTest, RacmControl, RacmRisk, RacmObjective,
                  ScopeItem, KeyAuditQuestion, ScopeObjectives, TopicIntelligence):
        for row in (await db.execute(select(model))).scalars().all():
            mine = (row.scope_id.startswith("sc-" + E) if model in scoped
                    else getattr(row, "engagement_id", None) == E)
            if mine:
                await db.delete(row)
    eng = await db.get(Engagement, E)
    if eng:
        await db.delete(eng)
    await db.commit()


async def _row(db, label="Risk areas in scope"):
    cov = await compute_coverage(E, db)
    return next(c for c in cov["checks"] if c["label"] == label)


async def run() -> None:
    async with AsyncSessionLocal() as db:
        await _clean(db)
        db.add(Engagement(id=E, audit_code="IA-TEST-CR", name="Coverage reference test",
                          entity="GRP", audit_type="compliance", status="in_planning"))
        db.add(TopicIntelligence(id=str(uuid4()), engagement_id=E, key_risk_areas=json.dumps([
            {"id": "ra1", "title": "Beneficial ownership verification"},
            {"id": "ra2", "title": "Periodic rescreening cadence"},
            {"id": "ra3", "title": "Sanctions list currency"},
        ])))
        scope = ScopeObjectives(id="sc-" + E, engagement_id=E, status="in_progress")
        db.add(scope)
        await db.flush()

        def item(desc, **kw):
            db.add(ScopeItem(id=str(uuid4()), scope_id=scope.id, item_type="in_scope",
                             description=desc, **kw))

        # ra1 by reference; its words deliberately do NOT match.
        item("Onboarding controls", **scope_sources.stamp(scope_sources.TOPIC_INTELLIGENCE, "ra1"))
        # ra2 only by wording — a legacy item with no reference.
        item("Periodic rescreening after onboarding", source="manual", source_ref=None)
        await db.commit()

        print("\nwhat is referenced is answered, what is not is guessed:")
        row = await _row(db)
        check("1 by reference" in row["detail"],
              f"one area answered by reference ({row['detail']})")
        check("1 on wording" in row["detail"], "and one on wording")
        check(row["status"] == "gap", "the third is still a gap")
        check("Sanctions list currency" in (row["gap"] or ""), "and it is named")

        print("\na reference beats the words, not the other way round:")
        # "Onboarding controls" shares no meaningful word with ra1's title;
        # without the reference it would read as uncovered.
        check("2/3" in row["detail"], "two of three covered")

        print("\nthe word pass reads every in-scope item, whatever its source:")
        # An item from the frameworks agent carries a source_ref of its own.
        # Narrowing the fallback to reference-less items would turn it into a
        # gap — a stricter check dressed up as a more precise one.
        item("Sanctions list currency and update frequency",
             **scope_sources.stamp(scope_sources.FRAMEWORKS, "run-1"))
        await db.commit()
        row = await _row(db)
        check(row["status"] == "ok", f"nothing is a gap now ({row['detail']})")
        check("1 by reference, 2 on wording" in row["detail"],
              "and the split is reported honestly")

        print("\na question is answered by a tested objective, not by a wording match:")
        # The work program generator was never given the key audit questions at
        # all, so the check compared the wording of a question against the
        # wording of a test — two things that had never been introduced.
        q = KeyAuditQuestion(id=str(uuid4()), scope_id=scope.id, is_accepted=True,
                             question_text="Are onboarding files complete?",
                             source="manual", sort_order=0)
        db.add(q)
        await db.flush()

        obj = RacmObjective(id=str(uuid4()), engagement_id=E, title="Zzz unrelated wording",
                            origin="ai", accepted=False, sort_order=0,
                            provenance=json.dumps({"source_type": "work_program_generator",
                                                   "answers": [q.id]}))
        db.add(obj)
        await db.flush()
        risk2 = RacmRisk(id=str(uuid4()), engagement_id=E, objective_id=obj.id,
                         title="Zzz", origin="ai", accepted=False, sort_order=1)
        db.add(risk2)
        await db.flush()
        ctrl = RacmControl(id=str(uuid4()), engagement_id=E, risk_id=risk2.id,
                           title="Zzz", origin="ai", accepted=False, sort_order=0)
        db.add(ctrl)
        await db.flush()
        await db.commit()

        row = await _row(db, "Tests cover questions")
        check(row["status"] == "gap",
              f"an objective naming the question but testing nothing is not an answer ({row['detail']})")

        db.add(RacmTest(id=str(uuid4()), engagement_id=E, control_id=ctrl.id,
                        title="Zzz", origin="ai", accepted=False, sort_order=0))
        await db.commit()
        row = await _row(db, "Tests cover questions")
        check("1 by reference" in row["detail"] and row["status"] == "ok",
              f"once a test hangs under it, the question is answered ({row['detail']})")

        print("\nthe same holds one step further, from risk area to matrix:")
        # The scoping engine records the id of the row a proposed risk came
        # from. Titles here deliberately share nothing, so only the reference
        # can answer — the score would read this as a gap.
        db.add(RacmRisk(id=str(uuid4()), engagement_id=E, title="Ownership chain work",
                        origin="ai", accepted=False, sort_order=0,
                        provenance=json.dumps({"source_type": "scoping_engine",
                                               "source_ref": "Topic Intelligence",
                                               "source_id": "ra1"})))
        await db.commit()
        row = await _row(db, "Key risks reflected in RACM scoping")
        check("1 by reference" in row["detail"],
              f"the proposed risk answers for its area ({row['detail']})")
        check(row["status"] == "gap" and "Periodic rescreening cadence" in (row["gap"] or ""),
              "and the areas with nothing in the matrix are still named")

        await _clean(db)


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
