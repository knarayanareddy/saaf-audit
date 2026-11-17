"""Clearing a generator's own earlier proposals, when they form a tree.

`risk_proposals.replace_previous()` already states the rule this platform lives
by: **a re-run clears only its own unaccepted proposals.** Anything a human
accepted is theirs, and an agent that deletes an accepted node has overwritten a
decision.

The work program generator had no such step at all. `routers/phase3.py` refuses
to regenerate a *signed* work program and allows everything else, so pressing
Regenerate twice wrote a second complete set of objectives, risks, controls,
tests and evidence beside the first. Two matrices, no way to tell which row the
auditor had been reading.

Why this is not just `risk_proposals` with more models: the spine is a tree, and
the obvious rule destroys accepted work. Consider an objective proposed by a
run, whose control the auditor then accepted:

    objective   ai, not accepted   <- the obvious rule deletes this
      risk      ai, not accepted   <- and this
        control ai, ACCEPTED       <- leaving this hanging from nothing

The control survives the delete and becomes unreachable: it belongs to a risk
that no longer exists, so it vanishes from the projection, from the work program
and from the matrix, while still sitting in the table. The auditor's acceptance
is destroyed without a single accepted row being deleted.

So the rule here is stricter, and it is the whole point of the module:

    **A node is cleared only when nothing survives beneath it.**

An unaccepted proposal holding an accepted descendant stays, because it is the
only thing that descendant hangs from. It is not this run's to remove.
"""
from __future__ import annotations

import json

from sqlalchemy import select

from models.racm import RacmControl, RacmEvidence, RacmObjective, RacmRisk, RacmTest

#: Child to parent, deepest first. Deleting in this order means a node is
#: considered only after everything below it has been decided.
LEVELS = [
    (RacmEvidence, "test_id"),
    (RacmTest, "control_id"),
    (RacmControl, "risk_id"),
    (RacmRisk, "objective_id"),
    (RacmObjective, None),
]


#: Two source names, one writer. The migration and the generator both write
#: *the work program* into the spine, so a regenerate must clear what the
#: migration put there as well — otherwise the first regenerate on a migrated
#: engagement stacks a second matrix on the first, which is the bug this module
#: exists to stop. Found by running it: the ESG spine carried
#: `work_program_migration` throughout, and the generator cleared nothing.
FAMILIES = {
    "work_program_generator": {"work_program_generator", "work_program_migration"},
    "work_program_migration": {"work_program_generator", "work_program_migration"},
}


def _source_of(row) -> str:
    try:
        return (json.loads(row.provenance) if row.provenance else {}).get("source_type") or ""
    except (json.JSONDecodeError, TypeError):
        return ""


def _is_own_proposal(row, source_type: str) -> bool:
    return (row.origin == "ai" and not row.accepted
            and _source_of(row) in FAMILIES.get(source_type, {source_type}))


async def replace_previous(db, engagement_id: str, source_type: str) -> dict:
    """Remove this source's earlier proposals, bottom up. Returns what went.

    `kept_for_children` counts the proposals that stayed because something
    accepted still hangs from them. It is reported rather than swallowed: a
    regenerate that leaves nodes behind should say so, since the auditor will
    see rows from the previous run sitting beside the new ones.
    """
    removed = {"objectives": 0, "risks": 0, "controls": 0, "tests": 0, "evidence": 0}
    kept = 0
    #: Ids that still exist after this level was processed — a parent with any
    #: of these beneath it is not ours to delete.
    surviving: set[str] = set()

    names = {RacmEvidence: "evidence", RacmTest: "tests", RacmControl: "controls",
             RacmRisk: "risks", RacmObjective: "objectives"}

    for model, parent_field in LEVELS:
        rows = (await db.execute(
            select(model).where(model.engagement_id == engagement_id)
        )).scalars().all()

        parents_with_survivors = set()
        doomed = []
        for row in rows:
            if _is_own_proposal(row, source_type) and row.id not in surviving:
                doomed.append(row)
            else:
                surviving.add(row.id)

        # A parent is protected by anything of ours that is staying, at any
        # level below it — which is why `surviving` accumulates across levels.
        for row in rows:
            if row.id in surviving and parent_field:
                pid = getattr(row, parent_field, None)
                if pid:
                    parents_with_survivors.add(pid)

        for row in doomed:
            await db.delete(row)
            removed[names[model]] += 1

        # Carry the protection upwards: the next level up must see these ids.
        surviving |= parents_with_survivors
        kept += sum(1 for row in rows
                    if row.id in surviving and _is_own_proposal(row, source_type))

    await db.flush()
    return {**removed, "kept_for_children": kept}
