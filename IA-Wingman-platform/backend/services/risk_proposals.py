"""How an agent proposes a risk into the matrix. One place, one discipline.

The governance assessor and Vendor Guard do the same thing to different
documents: read a document set against a framework set, and put the gaps into
the matrix as proposals. Both held the same scaffolding — clear my own
unaccepted proposals, find the next sort order, build the provenance JSON, write
a `RacmRisk` with `origin='ai', accepted=False` — differing only in which items
they keep and how they phrase a title.

The filters stay with the agents, because *which* gap is worth proposing is
domain judgement. The scaffolding moves here, because it carries a rule that
must never differ between them:

    **A re-run clears only its own UNACCEPTED proposals.**

Anything a human accepted is theirs. An agent that re-runs and deletes an
accepted risk has overwritten a decision, which is the one thing this platform
promises it will not do. Both copies got this right; neither said why, and the
next copy would have been written by someone reading only one of them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.racm import RacmRisk


@dataclass(frozen=True)
class ProposedRisk:
    """One gap an agent wants to put in front of the auditor.

    `source_ref` and `rationale` are not decoration: they become the provenance
    the auditor reads when deciding whether to accept, and the record of why
    this appeared if anyone asks a quarter later.
    """

    title: str
    description: str | None = None
    category: str | None = None
    inherent_rating: str = "medium"
    confidence: str | None = "medium"
    source_ref: str | None = None
    #: The id of the upstream row this came from, where there is one. `source_ref`
    #: is what the auditor reads — "AM RCSA 2026.xlsx, sheet row 8" — and this is
    #: what a machine follows back. The coverage sweep already answers by
    #: reference where one exists and says so where it had to compare words; a
    #: proposal that can name its row is one more answer that is a fact.
    source_id: str | None = None
    rationale: str | None = None


async def replace_previous(db, engagement_id: str, source_type: str) -> int:
    """Remove this source's earlier unaccepted proposals. Returns how many.

    Scoped three ways — this engagement, `origin='ai'`, `accepted=False` — and
    then by provenance, so one agent's re-run never clears another agent's
    proposals. A vendor assessment and a governance assessment can sit in the
    same matrix without eating each other.
    """
    rows = (await db.execute(
        select(RacmRisk).where(
            RacmRisk.engagement_id == engagement_id,
            RacmRisk.origin == "ai",
            RacmRisk.accepted == False,  # noqa: E712
        )
    )).scalars().all()

    removed = 0
    for row in rows:
        try:
            prov = json.loads(row.provenance) if row.provenance else {}
        except (json.JSONDecodeError, TypeError):
            prov = {}
        if prov.get("source_type") == source_type:
            await db.delete(row)
            removed += 1
    return removed


async def write(engagement_id: str, run_id: str, source_type: str,
                proposals: list[ProposedRisk]) -> int:
    """Replace this source's proposals with these. Returns how many were written.

    Owns its own session and commits: both callers used it as the last step of a
    run, and a half-written set of proposals is worse than none.
    """
    async with AsyncSessionLocal() as db:
        await replace_previous(db, engagement_id, source_type)

        last = (await db.execute(
            select(RacmRisk).where(RacmRisk.engagement_id == engagement_id)
            .order_by(RacmRisk.sort_order.desc())
        )).scalars().first()
        order = (last.sort_order + 1) if last else 0

        created = 0
        for p in proposals:
            title = (p.title or "").strip()
            if not title:
                continue  # an unnamed risk is a failure to find one, not a risk
            db.add(RacmRisk(
                id=str(uuid4()),
                engagement_id=engagement_id,
                objective_id=None,
                title=title[:500],
                description=p.description,
                category=p.category,
                inherent_rating=(p.inherent_rating or "medium").lower(),
                origin="ai",
                accepted=False,
                confidence=p.confidence,
                provenance=json.dumps({
                    "source_type": source_type,
                    "source_ref": p.source_ref,
                    "source_id": p.source_id,
                    "rationale": p.rationale,
                    "run_id": run_id,
                }),
                sort_order=order + created,
            ))
            created += 1
        await db.commit()
    return created
