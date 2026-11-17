"""Evidence the tests need, against the requests actually made.

    venv/Scripts/python.exe -m tests.test_evidence_needs

The plan said the DRL is arithmetic once tests declare their evidence. It is
not — the numbers are in the module docstring — so what is built here is the
link, not a replacement. These tests protect the two claims that link makes:

  1. a need is matched to a request **by reference**, never by comparing words,
     and a reference to a request that no longer exists counts as unmet;
  2. an interview is not a document request, so it never appears in the list of
     things nobody asked the auditee for.
"""
import asyncio
import json
import sys
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.planning import DRLDocument
from models.racm import RacmControl, RacmEvidence, RacmObjective, RacmRisk, RacmTest
from services.evidence_needs import coverage, link, needs_for

failures: list[str] = []
E = "test-evidence-needs"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _clean(db):
    for model in (RacmEvidence, RacmTest, RacmControl, RacmRisk, RacmObjective, DRLDocument):
        for row in (await db.execute(
            select(model).where(model.engagement_id == E)
        )).scalars().all():
            await db.delete(row)
    await db.commit()


async def run() -> None:
    async with AsyncSessionLocal() as db:
        await _clean(db)

        def node(model, **kw):
            n = model(id=str(uuid4()), engagement_id=E, **kw)
            db.add(n)
            return n

        o = node(RacmObjective, title="Onboarding", sort_order=0)
        await db.flush()
        r = node(RacmRisk, objective_id=o.id, title="No UBO check", sort_order=0)
        await db.flush()
        c1 = node(RacmControl, risk_id=r.id, title="UBO verified", sort_order=0)
        c2 = node(RacmControl, risk_id=r.id, title="Four eyes on approval", sort_order=1)
        await db.flush()
        t1 = node(RacmTest, control_id=c1.id, title="Obtain the population", sort_order=0)
        node(RacmTest, control_id=c1.id, title="Sample 25 and inspect", sort_order=1)
        node(RacmTest, control_id=c2.id, title="Re-perform the approval", sort_order=0)
        await db.flush()

        node(RacmEvidence, test_id=t1.id, ref="E1", kind="document",
             title="UBO register extract", requested_from="Compliance",
             period="FY2026 H1", sort_order=0)
        node(RacmEvidence, test_id=t1.id, ref="E2", kind="interview",
             title="Process owner on UBO exceptions", sort_order=1)
        db.add(DRLDocument(id=str(uuid4()), engagement_id=E, items=json.dumps([
            {"id": "drl_1", "document": "UBO register extract", "covers": ["E1"]},
            {"id": "drl_2", "document": "Board minutes", "covers": []},
        ])))
        await db.commit()

        print("\nbefore anything is linked:")
        cov = await coverage(E, db)
        check(len(cov.needs) == 2, "both needs are read")
        check(len(cov.requestable_needs) == 1,
              "only one is requestable — an interview is arranged, not requested")
        check([n.ref for n in cov.unrequested] == ["E1"],
              "and the document shows as not yet asked for")
        check(sorted(u["id"] for u in cov.unused_requests) == ["drl_1", "drl_2"],
              "neither request covers anything yet")

        print("\nthe control with tests but no evidence is named:")
        check([c["title"] for c in cov.controls_without_needs] == ["Four eyes on approval"],
              "the second control declares nothing")
        check(len(cov.controls_without_needs) == 1,
              "and the first is not counted per test — its two steps share one document")

        print("\nlinking is by reference, not by resemblance:")
        linked = await link(E, db, {"drl_1": ["E1"]})
        check(linked == 1, "one need linked")
        cov = await coverage(E, db)
        check(cov.unrequested == [], "nothing is unrequested now")
        check([u["id"] for u in cov.unused_requests] == ["drl_2"],
              "and the request that covers no need is still named")
        check(cov.summary()["drl_items"] == 2, "the summary counts the whole list")

        print("\na request that is deleted does not leave a need looking satisfied:")
        drl = (await db.execute(
            select(DRLDocument).where(DRLDocument.engagement_id == E)
        )).scalar_one()
        drl.items = json.dumps([{"id": "drl_2", "document": "Board minutes", "covers": []}])
        await db.commit()
        cov = await coverage(E, db)
        check([n.ref for n in cov.unrequested] == ["E1"],
              "the need points at a request that is gone, so it is unmet again")

        print("\na regenerate does not inherit the old list's links:")
        # DRL ids are positional — drl_1, drl_2 as the generator writes them —
        # so a link left over from the previous list points at whatever is
        # third in the new one. It would be wrong and it would look right.
        from services.evidence_needs import unlink_all

        await link(E, db, {"drl_1": ["E1"]})
        cleared = await unlink_all(E, db)
        await db.commit()
        check(cleared == 1, "the stale link is cleared before the new list claims anything")
        cov = await coverage(E, db)
        check([n.ref for n in cov.unrequested] == ["E1"],
              "so a need only counts as requested when a list actually claimed it")

        print("\nthe endpoint keeps counts and rows apart:")
        # They were spread into one object, so each list overwrote its own
        # count and the screen rendered an array where a number belonged.
        from routers.phase3 import drl_coverage

        payload = await drl_coverage(E, db)
        check(all(isinstance(payload[k], int)
                  for k in ("needs", "requestable", "unrequested",
                            "unused_requests", "controls_without_needs")),
              "every count is a number")
        check(isinstance(payload["detail"]["unused_requests"], list),
              "and the rows live under detail")
        # The advice on the screen depends on this: a signed work program
        # cannot be regenerated, so telling its auditor to regenerate it is the
        # one instruction they cannot follow.
        check(payload["work_program_signed"] is False,
              "an unsigned engagement says so, so the screen offers a regenerate")

        print("\na need carries the test it serves:")
        needs = await needs_for(E, db)
        check(needs[0].test_title == "Obtain the population",
              "so the auditor reading the list knows what it is for")

        await _clean(db)


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
