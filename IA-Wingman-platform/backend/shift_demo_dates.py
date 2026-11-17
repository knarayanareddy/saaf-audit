"""Shift every planned date in the demo data forward (or back) by a fixed number of days.

Why this exists
---------------
`services/backfill_service.py` derives all planning dates from a fixed ANCHOR. As
real time moves past that anchor the whole portfolio drifts into the past, and
`briefing_service` — which compares those dates with today — starts flagging almost
every audit as overdue. The backfill only ever fills EMPTY fields, so it cannot
repair rows that already have dates. This script does that one-off repair.

It is deliberately NOT wired into startup: shifting is a one-time correction, and a
startup hook would shift again on every restart.

Usage (from the backend directory)
----------------------------------
    venv/Scripts/python.exe shift_demo_dates.py              # dry run, writes nothing
    venv/Scripts/python.exe shift_demo_dates.py --apply      # actually shift
    venv/Scripts/python.exe shift_demo_dates.py --days 30 --apply

Only strict ISO values ("YYYY-MM-DD") are touched. Free text ("TBD", "Week 12"),
empty fields and timestamps the database manages itself (created_at/updated_at) are
left exactly as they are, so relative ordering across the portfolio is preserved —
everything simply lands N days later.

SQLAlchemy ORM throughout; no raw SQL.
"""
import argparse
import asyncio
import json
from datetime import datetime, timedelta

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import AuditNotificationLetter, DRLDocument, KickoffAgenda, ResourcePlan

# Plain date columns, per model: the fields that hold a planned date as a string.
DATE_COLUMNS = [
    (Engagement, ["planning_date", "start_date", "end_date", "draft_report_date", "final_report_date"]),
    (KickoffAgenda, ["meeting_date"]),
    (ResourcePlan, ["planned_fieldwork_start", "planned_fieldwork_end", "planned_report_date"]),
    (AuditNotificationLetter, [
        "timing_fieldwork_start", "timing_fieldwork_end",
        "timing_draft_report", "timing_mgmt_response", "timing_final_report",
    ]),
]

# JSON columns holding a list of objects with one date-bearing key.
JSON_LIST_COLUMNS = [
    (ResourcePlan, "milestones", "date"),   # [{name, date, done}]
    (DRLDocument, "items", "deadline"),     # [{document, ..., deadline?}]
]


def shift_iso(value: str | None, days: int) -> str | None:
    """Return the value shifted by `days`, or None when it isn't a plain ISO date."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
    return (parsed + timedelta(days=days)).isoformat()


def shift_json_list(raw: str | None, key: str, days: int) -> tuple[str | None, int]:
    """Shift `key` inside every object of a JSON list column. Returns (new_json, count)."""
    if not raw:
        return None, 0
    try:
        items = json.loads(raw)
    except (ValueError, TypeError):
        return None, 0
    if not isinstance(items, list):
        return None, 0
    changed = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        shifted = shift_iso(item.get(key), days)
        if shifted:
            item[key] = shifted
            changed += 1
    if not changed:
        return None, 0
    return json.dumps(items, ensure_ascii=False), changed


async def run(days: int, apply: bool) -> int:
    """Shift everything by `days`. Returns the number of values changed."""
    total = 0
    async with AsyncSessionLocal() as db:
        # 1 — plain date columns
        for model, columns in DATE_COLUMNS:
            rows = (await db.execute(select(model))).scalars().all()
            touched = 0
            for row in rows:
                for column in columns:
                    shifted = shift_iso(getattr(row, column, None), days)
                    if shifted:
                        setattr(row, column, shifted)
                        touched += 1
            total += touched
            print(f"  {model.__tablename__:<28} {touched:>4} date(s) in {len(rows)} row(s)")

        # 2 — dates nested inside JSON list columns
        for model, column, key in JSON_LIST_COLUMNS:
            rows = (await db.execute(select(model))).scalars().all()
            touched = 0
            for row in rows:
                new_json, changed = shift_json_list(getattr(row, column, None), key, days)
                if changed:
                    setattr(row, column, new_json)
                    touched += changed
            total += touched
            print(f"  {model.__tablename__ + '.' + column:<28} {touched:>4} {key}(s)")

        # 3 — a readable before/after for the engagements themselves
        engagements = (await db.execute(select(Engagement).order_by(Engagement.start_date))).scalars().all()
        print(f"\n  {'audit':<44} {'planning':<12} {'fieldwork':<12} {'final report'}")
        for e in engagements[:40]:
            name = (e.name or "")[:42]
            print(f"  {name:<44} {e.planning_date or '—':<12} {e.start_date or '—':<12} {e.final_report_date or '—'}")

        if apply:
            await db.commit()
            print(f"\nApplied: {total} value(s) shifted by {days:+d} day(s).")
        else:
            await db.rollback()
            print(f"\nDry run: {total} value(s) WOULD shift by {days:+d} day(s). "
                  f"Nothing was written — re-run with --apply to commit.")
    return total


def main():
    parser = argparse.ArgumentParser(description="Shift demo planning dates forward or back.")
    parser.add_argument("--days", type=int, default=61,
                        help="Days to shift; negative moves back. Default 61 (~2 months).")
    parser.add_argument("--apply", action="store_true",
                        help="Actually write the change. Without it the script only reports.")
    args = parser.parse_args()
    print(f"Shifting demo dates by {args.days:+d} day(s){'' if args.apply else ' (dry run)'}:\n")
    asyncio.run(run(args.days, args.apply))


if __name__ == "__main__":
    main()
