"""Move existing work programs into the spine.

Sixty-three rows across five engagements, two of them signed. Small enough to
run in one pass, and idempotent: a second run finds the nodes already there by
provenance and does nothing.

**Everything migrates as an unaccepted AI proposal.** A signed work program is a
human decision, and it would be convenient to mark the nodes it becomes as
accepted. But acceptance in the spine is per node, with the initials of the
person who confirmed it, and `WorkProgram` records no signer — only a date. So
marking them accepted would put a human's agreement on a node no human looked
at, attributed to nobody.

The sign-off is not lost: it goes into each node's provenance. What the auditor
sees is a matrix full of proposals with a date attached, which is the truth —
they signed a document, not twenty-four nodes.
"""
from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import select

from models.planning import WorkProgram
from models.racm import RacmControl, RacmEvidence, RacmObjective, RacmRisk, RacmTest

SOURCE = "work_program_migration"


def _steps(row: dict) -> list[str]:
    """The test steps, whichever shape this row was written in.

    Two shapes exist in the stored data. Newer rows carry `test_steps`, a list.
    Older ones carry `test_approach`, a single string — and a first pass that
    knew only the list silently dropped the test content of thirty-two of the
    sixty-three rows. It looked like a clean migration.
    """
    steps = row.get("test_steps")
    if isinstance(steps, list) and steps:
        return [str(s) for s in steps if str(s).strip()]
    approach = row.get("test_approach")
    if isinstance(approach, str) and approach.strip():
        return [approach.strip()]
    return []


def _prov(row_id: str, signed_off_at, source_type: str = SOURCE,
          answers: list | None = None) -> str:
    """Provenance for a node written from one work program row.

    `answers` holds the ids of the key audit questions that row helps answer.
    It is the one thing here that points forwards rather than back — provenance
    says where a node came from, and this says what it is for — but it belongs
    on the same record, because the row is the only place both are known and a
    second table for one list would be a table nobody keeps in step.
    """
    return json.dumps({
        "source_type": source_type,
        "source_ref": row_id,
        "rationale": ("From the work program signed off on "
                      f"{signed_off_at:%Y-%m-%d}" if signed_off_at
                      else "From the work program, which was never signed off"),
        "run_id": None,
        "answers": list(answers or []),
    })


def _merge_answers(provenance: str | None, answers: list | None) -> str:
    """Add these question ids to what the node already answers, without repeats."""
    try:
        prov = json.loads(provenance) if provenance else {}
    except (json.JSONDecodeError, TypeError):
        prov = {}
    have = list(prov.get("answers") or [])
    for qid in answers or []:
        if qid not in have:
            have.append(qid)
    prov["answers"] = have
    return json.dumps(prov)


async def already_migrated(db, engagement_id: str) -> bool:
    rows = (await db.execute(
        select(RacmObjective).where(RacmObjective.engagement_id == engagement_id)
    )).scalars().all()
    for r in rows:
        try:
            if json.loads(r.provenance or "{}").get("source_type") == SOURCE:
                return True
        except (json.JSONDecodeError, TypeError):
            continue
    return False


async def rows_to_spine(db, engagement_id: str, rows: list[dict],
                        *, source_type: str, signed_off_at=None) -> dict:
    """Write work program rows into the spine as unaccepted proposals.

    Shared by the migration and by the generator, because they do the same
    thing: the generator produces rows the auditor has not seen yet, and so did
    the work program that is being migrated. Both are proposals until somebody
    accepts them node by node.

    A re-run clears this source's own earlier proposals first. Without that
    step, regenerating a work program wrote a second complete matrix beside the
    first — `routers/phase3.py` only refuses to regenerate a *signed* one.
    """
    from services.spine_proposals import replace_previous

    cleared = await replace_previous(db, engagement_id, source_type)
    made = {"objectives": 0, "risks": 0, "controls": 0, "tests": 0, "evidence": 0}
    order = 0

    # One objective per distinct process: the work program repeats the process
    # name down the rows, and each repetition is the same objective.
    objectives: dict[str, RacmObjective] = {}

    for row in rows:
        prov = _prov(row.get("id") or f"wp_{order}", signed_off_at, source_type,
                     answers=row.get("answers"))
        process = (row.get("process") or "").strip() or "Unspecified process"

        objective = objectives.get(process)
        if objective is None:
            objective = RacmObjective(
                id=str(uuid4()), engagement_id=engagement_id,
                title=process[:500], description=(row.get("activity") or "")[:2000] or None,
                origin="ai", accepted=False, provenance=prov, sort_order=len(objectives),
            )
            db.add(objective)
            objectives[process] = objective
            made["objectives"] += 1
            await db.flush()
        else:
            # Several rows share one objective, and each may answer a different
            # question. Without this merge only the first row's questions would
            # survive, and the rest would read as answered by nothing.
            objective.provenance = _merge_answers(objective.provenance, row.get("answers"))

        risk = RacmRisk(
            id=str(uuid4()), engagement_id=engagement_id, objective_id=objective.id,
            title=(row.get("risk_description") or "Unstated risk")[:500],
            inherent_rating=(row.get("priority") or "medium").lower(),
            origin="ai", accepted=False, provenance=prov, sort_order=order,
        )
        db.add(risk)
        made["risks"] += 1
        await db.flush()

        control = RacmControl(
            id=str(uuid4()), engagement_id=engagement_id, risk_id=risk.id,
            title=(row.get("control_objective") or "Unstated control objective")[:500],
            origin="ai", accepted=False, provenance=prov, sort_order=order,
        )
        db.add(control)
        made["controls"] += 1
        await db.flush()

        first_test = None
        for i, step in enumerate(_steps(row)):
            if not str(step).strip():
                continue
            test = RacmTest(
                id=str(uuid4()), engagement_id=engagement_id, control_id=control.id,
                title=str(step)[:500],
                priority=(row.get("priority") or "medium").lower(),
                assigned_to=row.get("responsibility") or None,
                progress=row.get("status") or "not_started",
                origin="ai", accepted=False, provenance=prov, sort_order=i,
            )
            db.add(test)
            first_test = first_test or test
            made["tests"] += 1

        # Evidence belongs to the row's testing, not to one of its steps:
        # obtain the population, sample it, inspect it — all three want the same
        # document. It hangs off the first test because that is the finest node
        # the spine has; `evidence_needs.coverage()` reads it per control, which
        # is the question an auditor actually asks.
        if first_test is not None:
            for i, want in enumerate(row.get("evidence") or []):
                title = str(want.get("title") or "").strip()
                if not title:
                    continue
                made["evidence"] = made.get("evidence", 0) + 1
                db.add(RacmEvidence(
                    id=str(uuid4()), engagement_id=engagement_id,
                    test_id=first_test.id,
                    ref=f"E{made['evidence']}",
                    kind=(want.get("kind") or "document").strip().lower(),
                    title=title[:500],
                    requested_from=(want.get("requested_from") or "")[:120] or None,
                    period=(want.get("period") or "")[:120] or None,
                    origin="ai", accepted=False, provenance=prov, sort_order=i,
                ))

        order += 1

    return {"rows": len(rows), **made, "cleared": cleared}


async def migrate(db, engagement_id: str) -> dict:
    """Turn one engagement's stored work program rows into spine nodes."""
    wp = (await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )).scalar_one_or_none()
    if not wp or not wp.rows:
        return {"rows": 0, "skipped": "no work program"}
    if await already_migrated(db, engagement_id):
        return {"rows": 0, "skipped": "already migrated"}

    try:
        rows = json.loads(wp.rows)
    except (json.JSONDecodeError, TypeError):
        return {"rows": 0, "skipped": "rows are not readable JSON"}

    result = await rows_to_spine(db, engagement_id, rows,
                                 source_type=SOURCE, signed_off_at=wp.signed_off_at)
    return {**result, "signed": bool(wp.signed_off_at)}


async def migrate_all(db) -> list[dict]:
    """Every engagement holding a work program. Returns one report per engagement."""
    wps = (await db.execute(select(WorkProgram))).scalars().all()
    out = []
    for wp in wps:
        result = await migrate(db, wp.engagement_id)
        result["engagement_id"] = wp.engagement_id
        out.append(result)
    await db.commit()
    return out
