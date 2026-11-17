"""Demo audits kept as snapshots: an audit built by hand, carried into every fresh start.

The other seeders write their demo content in code. An audit that was built in
the app — its Topic Intelligence scan, frameworks, scope, spine and documents,
made by agents and accepted by a person — cannot be written that way, and on a
host without a persistent disk it would be gone at every restart. So it is
exported once (`export_demo_engagement.py`) to a JSON file under
`seed_data/demo_engagements/`, and loaded here when the audit is missing.

Loaded with bulk inserts, which bypass the session's flush and so the edit
register — a snapshot is not a change anyone made today. Startup also runs all
seeding under `edit_register.paused()`; the bulk insert keeps that true when
this is called from anywhere else.

What is left out: notifications and the activity feed (`copilot_tasks`,
`agent_activity`), which describe a moment rather than the audit.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Date, DateTime, insert, select

from database import AsyncSessionLocal, Base
from models.engagement import Engagement

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "seed_data" / "demo_engagements"

#: In insert order: an audit before what hangs from it, a scope before its items,
#: each spine layer before the one below it.
SNAPSHOT_TABLES = (
    "engagements",
    "scope_objectives", "scope_items", "key_audit_questions",
    "applicable_frameworks", "reg_requirements", "process_notes", "topic_intelligence",
    "background_risk_assessments", "audit_notification_letters", "kickoff_agendas",
    "work_programs", "interview_guides", "drl_documents", "ai_analyses",
    "racm_objectives", "racm_risks", "racm_controls", "racm_tests", "racm_evidence",
    "agent_runs", "agent_calls",
)

#: Tables that belong to an audit through its scope, not an engagement column.
VIA_SCOPE = ("scope_items", "key_audit_questions")


def model_for(table: str):
    for mapper in Base.registry.mappers:
        if mapper.class_.__tablename__ == table:
            return mapper.class_
    raise KeyError(f"No model for table '{table}'")


def _restore(model, row: dict) -> dict:
    """JSON back into column values: dates and timestamps were written as ISO text."""
    out = {}
    for attr in model.__mapper__.column_attrs:
        if attr.key not in row:
            continue
        value = row[attr.key]
        col_type = attr.columns[0].type
        if isinstance(value, str) and isinstance(col_type, DateTime):
            value = datetime.fromisoformat(value)
        elif isinstance(value, str) and isinstance(col_type, Date):
            value = date.fromisoformat(value)
        out[attr.key] = value
    return out


def snapshot_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


async def load_snapshot(path: Path) -> bool:
    """Load one snapshot if its audit is not there. True when it was loaded."""
    snap = json.loads(path.read_text(encoding="utf-8"))
    async with AsyncSessionLocal() as db:
        if await db.get(Engagement, snap["engagement_id"]):
            return False
        # An audit with the same code made by someone on this instance wins:
        # two "26-047"s would be worse than a missing snapshot.
        code = snap.get("audit_code")
        if code and (await db.execute(select(Engagement.id).where(Engagement.audit_code == code))).first():
            return False
        for table in SNAPSHOT_TABLES:
            rows = snap["tables"].get(table) or []
            if rows:
                model = model_for(table)
                await db.execute(insert(model), [_restore(model, r) for r in rows])
        await db.commit()
    return True


async def seed_demo_snapshots() -> None:
    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        await load_snapshot(path)
