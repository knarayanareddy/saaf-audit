"""Evidence chase matches by reference, and says when it guessed.

    venv/Scripts/python.exe -m tests.test_evidence_chase

It used to match a document request to captured evidence on "at least two
shared meaningful words", for every row. A request now records which evidence
needs it settles, so most rows have a reference. The keyword pass survives for
rows written before that link existed — and a row says which way it was
matched, because a guess shown the same way as a fact is how an auditor comes
to believe a document arrived.
"""
import asyncio
import json
import sys
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import DRLDocument
from models.racm import RacmEvidence
from routers.racm import evidence_chase

failures: list[str] = []
E = "test-evidence-chase"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean(db):
    for model in (RacmEvidence, DRLDocument):
        for row in (await db.execute(
            select(model).where(model.engagement_id == E)
        )).scalars().all():
            await db.delete(row)
    eng = await db.get(Engagement, E)
    if eng:
        await db.delete(eng)
    await db.commit()


async def run() -> None:
    async with AsyncSessionLocal() as db:
        await _clean(db)
        db.add(Engagement(id=E, audit_code="IA-TEST-EC", name="Evidence chase test",
                          entity="GRP", audit_type="compliance", status="in_fieldwork"))
        db.add(DRLDocument(id=str(uuid4()), engagement_id=E, items=json.dumps([
            {"id": "drl_1", "document": "UBO register extract", "requested_from": "Compliance"},
            {"id": "drl_2", "document": "Board minutes Q1", "requested_from": "Management"},
            {"id": "drl_3", "document": "Screening exception log", "requested_from": "Operations"},
        ])))
        # drl_1 is linked. drl_2 has only a word overlap. drl_3 has nothing.
        db.add(RacmEvidence(id=str(uuid4()), engagement_id=E, ref="E1",
                            title="Something else entirely", drl_item_id="drl_1", sort_order=0))
        db.add(RacmEvidence(id=str(uuid4()), engagement_id=E, ref="E2",
                            title="Board minutes from the first quarter",
                            description="minutes board", sort_order=1))
        await db.commit()

        result = await evidence_chase(E, db)
        rows = {r["id"]: r for r in result["items"]}

        print("\na linked request is matched by its reference:")
        check(rows["drl_1"]["matched_by"] == "linked", "drl_1 matched by reference")
        check(rows["drl_1"]["matched_evidence"] == "E1",
              "to the evidence that names it, not to the one whose words look right")

        print("\nan unlinked request still falls back to words, and says so:")
        check(rows["drl_2"]["matched_by"] == "keyword", "drl_2 matched by keyword")
        check(rows["drl_2"]["matched_evidence"] == "E2", "to the row sharing its words")

        print("\nand a request with neither is outstanding:")
        check(rows["drl_3"]["matched_by"] is None, "drl_3 is not matched at all")
        check(rows["drl_3"]["outstanding"] is True, "so it counts as outstanding")
        check("Follow up with Operations" in (rows["drl_3"]["followup"] or ""),
              "with a follow-up naming who holds it")

        print("\nthe totals separate the two kinds:")
        check(result["matched_by_reference"] == 1, "one matched by reference")
        check(result["matched_by_keyword"] == 1, "one guessed")
        check(result["outstanding"] == 1, "one outstanding")

        print("\nevidence claimed by one request is not offered to another:")
        # E1's title would keyword-match nothing here, but the rule matters when
        # it would: a linked row belongs to the request that claimed it.
        claimed = [r for r in result["items"] if r["matched_evidence"] == "E1"]
        check(len(claimed) == 1, "E1 answers exactly one request")

        await _clean(db)


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
