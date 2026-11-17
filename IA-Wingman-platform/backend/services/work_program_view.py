"""The work program, projected from the spine.

A work program row is a path through the matrix: an objective, the risk under
it, the control under that, and the tests under the control. Those were two
separate stores — `WorkProgram.rows` as a JSON blob, and the five `racm_*`
tables — with no reference between them and a keyword comparison in
`coverage_service` standing in for a join.

The measurement that settled it: of nine engagements holding either, **two hold
both**. Four built a matrix and never signed a work program, so the gate that
opens fieldwork never closed. Three signed a work program with an empty matrix,
so fieldwork had nothing to test against. They were never two copies drifting
apart; they were a fork where both branches stop.

So the spine is the store and this is the view. One row per *test-bearing path*,
because a work program row is a unit of testing: an objective with two controls
under one risk yields two rows, and an objective nobody has written a test for
still yields a row, so a gap stays visible rather than disappearing from the
projection that is supposed to reveal it.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from sqlalchemy import select

from models.planning import WorkProgram
from models.racm import RacmControl, RacmObjective, RacmRisk, RacmTest


@dataclass
class Row:
    """One work program row, as the screen and the exports expect it.

    `node_ids` is not display data. It is what lets an edit on this row reach
    the right node, and what lets a signed snapshot be compared to the live
    spine node by node rather than only as a whole.
    """

    id: str
    process: str = ""
    activity: str = ""
    risk_description: str = ""
    control_objective: str = ""
    test_steps: list[str] = field(default_factory=list)
    priority: str = "medium"
    responsibility: str = ""
    status: str = "not_started"
    node_ids: dict = field(default_factory=dict)


def _first(values, default=""):
    for v in values:
        if v:
            return v
    return default


async def rows_for(engagement_id: str, db, *, as_signed: bool = False) -> list[dict]:
    """The work program for an engagement.

    `as_signed=True` returns the snapshot taken when the auditor signed, not the
    live spine — what was agreed, rather than what it has become since.
    """
    if as_signed:
        wp = (await db.execute(
            select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
        )).scalar_one_or_none()
        if not wp or not wp.signed_off_at or not wp.rows:
            return []
        try:
            return json.loads(wp.rows)
        except (json.JSONDecodeError, TypeError):
            return []

    async def _all(model):
        return (await db.execute(
            select(model).where(model.engagement_id == engagement_id)
            .order_by(model.sort_order)
        )).scalars().all()

    objectives = await _all(RacmObjective)
    risks = await _all(RacmRisk)
    controls = await _all(RacmControl)
    tests = await _all(RacmTest)

    tests_by_control: dict[str, list[RacmTest]] = {}
    for t in tests:
        tests_by_control.setdefault(t.control_id or "", []).append(t)
    controls_by_risk: dict[str, list[RacmControl]] = {}
    for c in controls:
        controls_by_risk.setdefault(c.risk_id or "", []).append(c)
    risks_by_objective: dict[str, list[RacmRisk]] = {}
    for r in risks:
        risks_by_objective.setdefault(r.objective_id or "", []).append(r)

    rows: list[Row] = []

    def emit(objective, risk=None, control=None):
        group = tests_by_control.get(control.id, []) if control else []
        rows.append(Row(
            id=f"wp_{len(rows) + 1}",
            process=objective.title if objective else "",
            activity=(objective.description if objective else "") or "",
            risk_description=risk.title if risk else "",
            control_objective=control.title if control else "",
            test_steps=[t.title for t in group],
            # A control's tests may disagree; the row shows the most pressing
            # and the least finished, because a row is done when its last test is.
            priority=_first([t.priority for t in group], "medium"),
            responsibility=_first([t.assigned_to for t in group], ""),
            status=_first([t.progress for t in group if t.progress != "complete"],
                          "complete" if group else "not_started"),
            node_ids={
                "objective": objective.id if objective else None,
                "risk": risk.id if risk else None,
                "control": control.id if control else None,
                "tests": [t.id for t in group],
            },
        ))

    for objective in objectives:
        obj_risks = risks_by_objective.get(objective.id, [])
        if not obj_risks:
            emit(objective)                      # an objective with no risk yet
            continue
        for risk in obj_risks:
            risk_controls = controls_by_risk.get(risk.id, [])
            if not risk_controls:
                emit(objective, risk)            # a risk nobody has controlled
                continue
            for control in risk_controls:
                emit(objective, risk, control)   # the ordinary case

    # Risks and controls an agent proposed before any objective exists still
    # belong in the view. Dropping them would hide exactly the proposals the
    # auditor is meant to act on.
    for risk in risks_by_objective.get("", []):
        for control in controls_by_risk.get(risk.id, []) or [None]:
            emit(None, risk, control)

    return [asdict(r) for r in rows]


#: Which node a projected field belongs to. The projection is two-way, so this
#: map is the whole of it — a field with no entry cannot be edited, which is
#: better than an edit that silently goes nowhere.
FIELD_TO_NODE = {
    "process": ("objective", "title"),
    "activity": ("objective", "description"),
    "risk_description": ("risk", "title"),
    "control_objective": ("control", "title"),
}

#: Fields that live on every test under the row rather than on one node.
TEST_FIELDS = {"priority": "priority", "responsibility": "assigned_to", "status": "progress"}


async def apply_patch(engagement_id: str, db, row_id: str, payload: dict) -> list[str]:
    """Apply an edit made on a projected row. Returns the fields that landed.

    A field the map does not know is ignored and reported by omission. The
    alternative — accepting it and writing nowhere — is how an auditor comes to
    believe they corrected something.

    `test_steps` is deliberately not editable here: adding or removing a step
    means creating or deleting a test node, which is a spine operation with its
    own endpoint and its own provenance.
    """
    from models.racm import RacmControl, RacmObjective, RacmRisk, RacmTest

    rows = await rows_for(engagement_id, db)
    row = next((r for r in rows if r["id"] == row_id), None)
    if row is None:
        return []

    ids = row["node_ids"]
    models = {"objective": RacmObjective, "risk": RacmRisk, "control": RacmControl}
    applied: list[str] = []

    for field, value in payload.items():
        if field in FIELD_TO_NODE:
            node_kind, column = FIELD_TO_NODE[field]
            node_id = ids.get(node_kind)
            if not node_id:
                continue  # the row has no such node — an incomplete path
            node = await db.get(models[node_kind], node_id)
            if node is None:
                continue
            setattr(node, column, value)
            applied.append(field)
        elif field in TEST_FIELDS:
            column = TEST_FIELDS[field]
            for test_id in ids.get("tests") or []:
                test = await db.get(RacmTest, test_id)
                if test is not None:
                    setattr(test, column, value)
            if ids.get("tests"):
                applied.append(field)

    await db.commit()
    return applied


async def snapshot(engagement_id: str, db) -> str:
    """The rows as JSON, for storing as what was signed.

    Node ids ride along. Without them a later comparison can say that something
    changed but not what, which is useless at the one moment it is needed — when
    an auditor is asked whether the tests being run are the tests they approved.
    """
    return json.dumps(await rows_for(engagement_id, db))


async def drift_since_signoff(engagement_id: str, db) -> dict:
    """What has moved in the spine since the auditor signed.

    Compares node by node, not row by row: rows are renumbered whenever the
    spine changes shape, so `wp_3` in the snapshot and `wp_3` today are often
    not the same path. Node ids are stable, which is why they are stored.

    Returns empty lists when nothing signed, which reads as "no drift" and is
    correct — there is no signature to drift from.
    """
    signed = await rows_for(engagement_id, db, as_signed=True)
    if not signed:
        return {"signed": False, "added": [], "removed": [], "changed": []}

    def index(rows):
        out = {}
        for r in rows:
            ids = r.get("node_ids") or {}
            key = (ids.get("objective"), ids.get("risk"), ids.get("control"))
            if any(key):
                out[key] = r
        return out

    was, now = index(signed), index(await rows_for(engagement_id, db))

    changed = []
    for key in was.keys() & now.keys():
        a, b = was[key], now[key]
        fields = [f for f in ("process", "risk_description", "control_objective", "test_steps")
                  if a.get(f) != b.get(f)]
        if fields:
            changed.append({"row": b["id"], "fields": fields,
                            "control_objective": b.get("control_objective")})

    return {
        "signed": True,
        "added": [now[k]["id"] for k in now.keys() - was.keys()],
        "removed": [was[k]["id"] for k in was.keys() - now.keys()],
        "changed": changed,
    }
