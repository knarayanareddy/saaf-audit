"""Python port of frontend/src/lib/briefing.js — deterministic "what needs
attention" rules, reused by the copilot's portfolio digest (ai_chat.py, no
active engagement) and per-engagement deadline context (ai_chat.py, with an
engagement). No AI decides what matters here, on either side of the port —
same principle as the JS original, see its own module docstring.

Kept in sync BY HAND with briefing.js (same rules, same ranks, same
DEADLINE_WINDOW_DAYS) — two implementations of the same small, stable rule
set, in two languages. A future rule change must update both.

Deliberately omits briefing.js's "stale board narrative" rule: that needs an
extra network round trip to the AI board narrative and is portfolio-level
presentation polish, not an action item — not worth the extra async call here.
"""
from datetime import date, datetime

ACTIVE_STATUSES = {"in_planning", "in_fieldwork", "in_reporting"}
DEADLINE_WINDOW_DAYS = 14

_RANK = {"overdue": 0, "ownership": 1, "deadline": 2}


def _to_day(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _days_between(date_str: str | None, today: date) -> int | None:
    target = _to_day(date_str)
    if target is None:
        return None
    return (target - today).days


def build_briefing(engagements: list[dict], now: datetime) -> list[dict]:
    """engagements: dicts shaped like routers/engagements.py's serialize()
    output. Returns attention items sorted overdue → ownership gaps →
    upcoming deadlines, each with rank/title/engagement/reason/meta."""
    today = now.date()
    items = []
    for e in engagements:
        status = e.get("status")
        active = status in ACTIVE_STATUSES

        if status == "to_be_scheduled":
            d = _days_between(e.get("planning_date"), today)
            if d is not None and d < 0:
                items.append({
                    "rank": _RANK["overdue"], "sort_key": e.get("planning_date") or "",
                    "title": "Planning overdue", "engagement": e.get("name"), "engagement_id": e.get("id"),
                    "reason": f"Planning was due {abs(d)} day{'s' if abs(d) != 1 else ''} ago and has not started.",
                    "meta": f"{abs(d)}d overdue",
                })

        if active and not e.get("lead_auditor"):
            items.append({
                "rank": _RANK["ownership"], "sort_key": e.get("name") or "",
                "title": "No lead assigned", "engagement": e.get("name"), "engagement_id": e.get("id"),
                "reason": "An active audit has no lead auditor assigned.", "meta": None,
            })
        elif active and not e.get("start_date"):
            items.append({
                "rank": _RANK["ownership"], "sort_key": e.get("name") or "",
                "title": "No fieldwork dates", "engagement": e.get("name"), "engagement_id": e.get("id"),
                "reason": "An active audit has no fieldwork start date set.", "meta": None,
            })

        if active:
            candidates = []
            for label, key in (("Draft report", "draft_report_date"), ("Final report", "final_report_date")):
                d = _days_between(e.get(key), today)
                if d is not None and 0 <= d <= DEADLINE_WINDOW_DAYS:
                    candidates.append((d, label, e.get(key)))
            if candidates:
                d, label, date_str = min(candidates, key=lambda c: c[0])
                items.append({
                    "rank": _RANK["deadline"], "sort_key": date_str or "",
                    "title": f"{label} due soon", "engagement": e.get("name"), "engagement_id": e.get("id"),
                    "reason": f"{label} is due in {d} day{'s' if d != 1 else ''}.",
                    "meta": "due today" if d == 0 else f"{d}d left",
                })

    items.sort(key=lambda i: (i["rank"], i["sort_key"], i["engagement"] or ""))
    return items


def format_digest(items: list[dict], max_items: int = 8) -> str:
    """Compact, prompt-friendly rendering of build_briefing's output."""
    if not items:
        return "Nothing needs attention right now — no overdue items, missing leads or looming deadlines."
    lines = [
        f"- {i['title']} — {i['engagement']} (id={i['engagement_id']}): {i['reason']}"
        for i in items[:max_items]
    ]
    if len(items) > max_items:
        lines.append(f"- …and {len(items) - max_items} more item(s).")
    return "\n".join(lines)
