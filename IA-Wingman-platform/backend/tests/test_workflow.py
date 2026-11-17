"""Dependency-free tests for the Workflow map (services/workflow_service.py).

Run from the backend dir:
    venv/Scripts/python.exe -m tests.test_workflow

Deterministic and read-only: no AI calls and no writes to the database.
Covers the graph's integrity (phases, edges, no cycles, human gates), the
routes that follow the moved agent panels, and that the live view agrees with
compute_engagement_pack on the golden engagement.
"""
import asyncio
import sys

from sqlalchemy import select, func

from database import AsyncSessionLocal
from models.copilot import CopilotTask
from models.engagement import Engagement
from models.racm import RacmObjective, RacmRisk, RacmControl, RacmTest, RacmEvidence
from services.golden_path_service import GOLDEN_NAME
from services.orchestrator import STAGE_GRAPH, compute_engagement_pack
from services.workflow_service import (
    method_map, engagement_workflow, PHASES, PHASE_OF, STAGE_INFO, COMPANIONS, HUMAN_GATES,
)

failures: list[str] = []
PHASE_INDEX = {p["key"]: i for i, p in enumerate(PHASES)}


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def _is_acyclic(keys, edges) -> bool:
    indegree = {k: 0 for k in keys}
    out = {k: [] for k in keys}
    for e in edges:
        out[e["from"]].append(e["to"])
        indegree[e["to"]] += 1
    queue = [k for k, d in indegree.items() if d == 0]
    seen = 0
    while queue:
        k = queue.pop()
        seen += 1
        for nxt in out[k]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    return seen == len(keys)


def test_method_map():
    print("method map:")
    wf = method_map()
    keys = [n["key"] for n in wf["nodes"]]
    stage_keys = {s["key"] for s in STAGE_GRAPH}
    known = set(keys)
    phase = {n["key"]: n["phase"] for n in wf["nodes"]}

    check(stage_keys <= set(PHASE_OF), "every STAGE_GRAPH stage has a phase")
    check(stage_keys <= set(STAGE_INFO), "every STAGE_GRAPH stage has a description")
    check(len(keys) == len(known) == len(STAGE_GRAPH) + len(COMPANIONS),
          f"{len(keys)} unique nodes ({len(STAGE_GRAPH)} stages + {len(COMPANIONS)} companions)")
    check(all(n["phase"] in PHASE_INDEX for n in wf["nodes"]), "every node sits in a known phase")
    check(all(e["from"] in known and e["to"] in known for e in wf["edges"]),
          f"all {len(wf['edges'])} edges connect existing nodes")
    check(all(PHASE_INDEX[phase[e["from"]]] <= PHASE_INDEX[phase[e["to"]]] for e in wf["edges"]),
          "no edge points back to an earlier phase")
    check(_is_acyclic(keys, wf["edges"]), "the gate graph has no cycles")
    check(all(g["stage"] in known and g.get("unlocks", g["stage"]) in known for g in HUMAN_GATES),
          "human gates reference existing stages")
    check(any(e["kind"] == "hard_gate" and e["from"] == "work_program" and e["to"] == "fieldwork" for e in wf["edges"]),
          "Work Program sign-off is a hard gate into Fieldwork")
    check(all(n["description"] for n in wf["nodes"]), "every node explains what happens in it")


def test_routes_follow_panels():
    print("routes follow the moved agent panels:")
    by_key = {s["key"]: s for s in STAGE_GRAPH}
    check(all(by_key[k]["route"] == "fieldwork" for k in ("racm_governance", "racm_data_analysis", "racm_evidence_chase")),
          "governance / data analysis / evidence chase open Fieldwork")
    check(by_key["racm_scoping"]["route"] == "racm", "RACM scoping still opens the matrix")


def test_live_workflow():
    print("live workflow (golden engagement):")

    async def go():
        async with AsyncSessionLocal() as db:
            eng = (await db.execute(select(Engagement).where(Engagement.name == GOLDEN_NAME))).scalars().first()
            if not eng:
                return None
            tasks_before = (await db.execute(select(func.count(CopilotTask.id)))).scalar_one()
            wf = await engagement_workflow(eng.id, db)
            tasks_after = (await db.execute(select(func.count(CopilotTask.id)))).scalar_one()
            pack = await compute_engagement_pack(eng.id, db)
            matrix = 0
            for model in (RacmObjective, RacmRisk, RacmControl, RacmTest, RacmEvidence):
                matrix += (await db.execute(
                    select(func.count()).select_from(model)
                    .where(model.engagement_id == eng.id, model.origin == "ai", model.accepted.is_(False))
                )).scalar_one()
            missing = await engagement_workflow("does-not-exist", db)
        return eng, wf, pack, matrix, tasks_before, tasks_after, missing

    result = asyncio.run(go())
    if result is None:
        check(False, "golden engagement exists")
        return
    eng, wf, pack, matrix, tasks_before, tasks_after, missing = result

    live = {n["key"]: n["status"] for n in wf["nodes"] if not n["companion"]}
    check(all(live[s["key"]] == s["status"] for s in pack["stages"]), "stage statuses equal compute_engagement_pack")
    check(wf["next_gate"] == pack["next_gate"], f"next gate equals the pack ({pack['next_gate']})")
    valid = {"locked", "available", "in_progress", "complete"}
    check(all(n["status"] in valid for n in wf["nodes"]), "every node, companions included, has a valid status")
    check(wf["pending"]["matrix"] == matrix, f"matrix proposals awaiting a decision match a direct count ({matrix})")
    check(wf["pending"]["total"] == sum(n["pending_decisions"] for n in wf["nodes"]),
          f"per-node decision badges add up to the total ({wf['pending']['total']})")
    check(wf["engagement"]["id"] == eng.id and wf["engagement"]["status"] == eng.status, "engagement header attached")
    check(tasks_before == tasks_after, "read-only: no copilot work was queued")
    check(missing is None, "unknown engagement returns None (the router answers 404)")


def test_frontend_fixture_in_sync():
    print("frontend fixture:")
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "frontend" / "tests" / "fixtures" / "workflow-method.json"
    check(path.exists(), "frontend/tests/fixtures/workflow-method.json exists")
    if path.exists():
        check(json.loads(path.read_text(encoding="utf-8")) == json.loads(json.dumps(method_map())),
              "fixture matches method_map() — regenerate it when the graph changes")


def main():
    test_method_map()
    test_frontend_fixture_in_sync()
    test_routes_follow_panels()
    test_live_workflow()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
