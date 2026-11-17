"""What the tests need, and whether anyone asked the auditee for it.

The plan for this phase said the document request list is arithmetic: let every
test declare the evidence it needs, and the DRL falls out. One engagement was
enough to show that it does not. Conduct Risk, 17 tests:

    62 evidence needs derived from the tests
    48 of them document or data      — the rest are interviews and observations,
                                        which are not things to ask an auditee to send
    19 items in the DRL the agent wrote
    40 of the 48 had a counterpart in that DRL
     8 did not
     2 of the 62 cited more than one test
    28 departments named, against the agent's 4

The fan-out is arithmetic. The **reduction** is not. Merging six needs across
three tests into "Outcome testing results, last four quarters", and addressing
it to Compliance rather than to "Conduct Risk/QA", is the judgement that makes a
list an auditee can act on. A request list addressed to 28 invented departments
is not a better DRL; it is a worse one.

So the agent stays, and what it gains is the link. It is handed the needs and
must say, per request, which ones it covers. Two numbers follow from that, and
neither can be obtained today:

    needs with no request      evidence a test requires that nobody asked for
    requests serving no test   a request made for no test in the program

Both are stated by reference, never by keyword. `coverage_service` already
bridges two stores by comparing words, and that comparison is the reason nobody
trusts the number it produces.

A need is a `RacmEvidence` row: the need before it is met and the record after,
distinguished by `source_document_id`. A `drl_item_id` is the request that
covers it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import select

from models.planning import DRLDocument
from models.racm import RacmControl, RacmEvidence, RacmTest

#: The kinds that can become a document request. An interview is arranged and an
#: observation is scheduled; neither is something the auditee sends over.
REQUESTABLE = {"document", "data"}


@dataclass
class Need:
    """One piece of evidence a test needs."""

    id: str
    test_id: str
    ref: str = ""
    kind: str = "document"
    title: str = ""
    requested_from: str = ""
    period: str = ""
    drl_item_id: str = ""
    test_title: str = ""

    @property
    def requestable(self) -> bool:
        return (self.kind or "document") in REQUESTABLE


@dataclass
class Coverage:
    """How the tests and the request list line up."""

    needs: list[Need] = field(default_factory=list)
    #: Requestable needs with no `drl_item_id` — nobody asked the auditee.
    unrequested: list[Need] = field(default_factory=list)
    #: DRL item ids that cover no need — a request made for no test.
    unused_requests: list[dict] = field(default_factory=list)
    #: Controls whose testing declares no evidence at all. Counted per control
    #: rather than per test on purpose: a need belongs to the testing of one
    #: control, and its steps — obtain the population, sample it, inspect it —
    #: share the same document. Counting per test would report four of every
    #: five steps as lacking evidence, which is arithmetic, not a finding.
    controls_without_needs: list[dict] = field(default_factory=list)
    drl_item_count: int = 0

    @property
    def requestable_needs(self) -> list[Need]:
        return [n for n in self.needs if n.requestable]

    def summary(self) -> dict:
        return {
            "needs": len(self.needs),
            "requestable": len(self.requestable_needs),
            "unrequested": len(self.unrequested),
            "unused_requests": len(self.unused_requests),
            "controls_without_needs": len(self.controls_without_needs),
            "drl_items": self.drl_item_count,
        }


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


async def needs_for(engagement_id: str, db) -> list[Need]:
    """Every evidence need the tests of this engagement declare."""
    tests = (await db.execute(
        select(RacmTest).where(RacmTest.engagement_id == engagement_id)
    )).scalars().all()
    titles = {t.id: t.title for t in tests}

    rows = (await db.execute(
        select(RacmEvidence).where(RacmEvidence.engagement_id == engagement_id)
        .order_by(RacmEvidence.sort_order)
    )).scalars().all()

    return [
        Need(
            id=r.id,
            test_id=r.test_id or "",
            ref=r.ref or "",
            kind=r.kind or "document",
            title=r.title or "",
            requested_from=r.requested_from or "",
            period=r.period or "",
            drl_item_id=r.drl_item_id or "",
            test_title=titles.get(r.test_id or "", ""),
        )
        for r in rows
    ]


async def coverage(engagement_id: str, db) -> Coverage:
    """The two numbers an auditor cannot get today, stated by reference."""
    needs = await needs_for(engagement_id, db)

    drl = (await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
    )).scalar_one_or_none()
    items = _loads(drl.items if drl else None, [])
    item_ids = {str(i.get("id")) for i in items if i.get("id")}

    covered = {n.drl_item_id for n in needs if n.drl_item_id}

    tests = (await db.execute(
        select(RacmTest).where(RacmTest.engagement_id == engagement_id)
    )).scalars().all()
    controls = (await db.execute(
        select(RacmControl).where(RacmControl.engagement_id == engagement_id)
    )).scalars().all()

    tests_with_needs = {n.test_id for n in needs}
    controls_with_needs = {t.control_id for t in tests if t.id in tests_with_needs}
    tested = {t.control_id for t in tests}

    return Coverage(
        needs=needs,
        # A need pointing at a request that no longer exists counts as
        # unrequested. Deleting the request is exactly when this matters.
        unrequested=[n for n in needs
                     if n.requestable and n.drl_item_id not in item_ids],
        unused_requests=[
            {"id": str(i.get("id")), "document": i.get("document", "")}
            for i in items if str(i.get("id")) not in covered
        ],
        # Only controls that have tests. A control nobody has written a test for
        # is a gap the work program already reports; repeating it here would
        # count the same hole twice.
        controls_without_needs=[
            {"id": c.id, "title": c.title}
            for c in controls if c.id in tested and c.id not in controls_with_needs
        ],
        drl_item_count=len(items),
    )


async def unlink_all(engagement_id: str, db) -> int:
    """Drop every need's link to a request. Returns how many were cleared.

    Called before a regenerate, because DRL item ids are positional — the
    generator numbers them `drl_1`, `drl_2` as it writes. A need pointing at
    `drl_3` and left alone across a regenerate now points at whatever document
    happens to be third in the new list, and `coverage()` counts it as
    requested. It would be wrong and it would look right, which is the pairing
    this platform keeps trying to design out.

    Clearing first means a need is linked only by a list that claimed it.
    """
    rows = (await db.execute(
        select(RacmEvidence).where(
            RacmEvidence.engagement_id == engagement_id,
            RacmEvidence.drl_item_id.isnot(None),
        )
    )).scalars().all()
    for row in rows:
        row.drl_item_id = None
    await db.flush()
    return len(rows)


async def link(engagement_id: str, db, assignments: dict[str, list[str]]) -> int:
    """Record which request covers which needs. Returns the number linked.

    `assignments` maps a DRL item id to the evidence refs it covers — the
    generator's own answer about its own output, not a guess made afterwards by
    comparing words.
    """
    rows = (await db.execute(
        select(RacmEvidence).where(RacmEvidence.engagement_id == engagement_id)
    )).scalars().all()
    by_ref = {r.ref: r for r in rows if r.ref}
    by_id = {r.id: r for r in rows}

    linked = 0
    for item_id, refs in (assignments or {}).items():
        for ref in refs or []:
            row = by_ref.get(ref) or by_id.get(ref)
            if row is not None:
                row.drl_item_id = str(item_id)
                linked += 1
    await db.commit()
    return linked
