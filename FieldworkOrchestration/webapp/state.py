"""Lightweight per-run state persistence for the demo webapp.

The agents/orchestrator layer returns data from function calls — nothing
about a run's ``pbc_list`` / ``validation_status`` is persisted anywhere on
its own (the audit trail records the raw Claude calls, not the caller's
higher-level state). A web server handling separate HTTP requests needs
something to read that state back between requests. This is that, nothing
more: one JSON file per run, ``runs/<run_id>/webapp_state.json``. Not part
of the agents' own contract — the webapp is the only reader/writer, and no
agent module depends on it existing.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.audit_trail import RUNS_DIR


def state_path(run_id: str) -> Path:
    return RUNS_DIR / run_id / "webapp_state.json"


def load_state(run_id: str) -> dict | None:
    path = state_path(run_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(run_id: str, state: dict) -> None:
    path = state_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def list_runs() -> list[dict]:
    """List every run that has webapp state, newest first (run ids sort by time)."""
    if not RUNS_DIR.exists():
        return []
    runs = []
    for run_dir in RUNS_DIR.iterdir():
        path = run_dir / "webapp_state.json"
        if not path.exists():
            continue
        state = json.loads(path.read_text(encoding="utf-8"))
        runs.append(
            {
                "run_id": run_dir.name,
                "audit_scope": state.get("audit_scope"),
                "audit_period": state.get("audit_period"),
                "auditee_contact": state.get("auditee_contact"),
                "item_count": len(state.get("pbc_list", {}).get("items", [])),
            }
        )
    runs.sort(key=lambda r: r["run_id"], reverse=True)
    return runs
