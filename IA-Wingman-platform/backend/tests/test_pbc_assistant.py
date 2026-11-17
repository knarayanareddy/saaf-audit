"""Dependency-free tests for the PBC ("Isabelle") assistant.

No pytest required. Run from the backend dir:

    venv/Scripts/python.exe -m tests.test_pbc_assistant

Covers the DETERMINISTIC surface only (no AI calls):
  - compute_dashboard counts, completion %, and derived overdue detection
  - overdue only applies to outstanding items with a passed deadline
  - not_needed items are excluded from the completion denominator
  - reminder escalation threshold (days_overdue > 7) via days computation
The AI drafts (email/reminders/validation) are opt-in and not exercised here.
"""
import sys
from datetime import date

from services.pbc_assistant import compute_dashboard, _days_overdue

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def _items():
    return [
        {"id": "drl_1", "document": "Access list", "status": "received", "deadline": "2026-01-01"},
        {"id": "drl_2", "document": "JML log", "status": "requested", "deadline": "2026-01-01"},   # overdue
        {"id": "drl_3", "document": "Policy", "status": "requested", "deadline": "2099-01-01"},     # not overdue
        {"id": "drl_4", "document": "Contract", "status": "not_requested", "deadline": None},        # outstanding, no deadline
        {"id": "drl_5", "document": "Old report", "status": "not_needed", "deadline": "2020-01-01"}, # excluded
    ]


def test_dashboard_counts():
    print("dashboard counts:")
    d = compute_dashboard(_items(), today=date(2026, 6, 1))
    check(d["total_items"] == 5, "total_items = 5")
    check(d["received_count"] == 1, "received = 1")
    check(d["requested_count"] == 2, "requested = 2")
    check(d["not_requested_count"] == 1, "not_requested = 1")
    check(d["not_needed_count"] == 1, "not_needed = 1")
    check(d["outstanding_count"] == 3, "outstanding = 3 (requested x2 + not_requested)")


def test_overdue_derivation():
    print("overdue derivation:")
    d = compute_dashboard(_items(), today=date(2026, 6, 1))
    overdue_ids = {r["id"] for r in d["overdue"]}
    check(overdue_ids == {"drl_2"}, "only drl_2 overdue (passed deadline + outstanding)")
    check(d["overdue_count"] == 1, "overdue_count = 1")
    # future-deadline and no-deadline outstanding items are NOT overdue
    check("drl_3" not in overdue_ids and "drl_4" not in overdue_ids, "future/no-deadline not overdue")
    # a received item with a passed deadline is NOT overdue
    check("drl_1" not in overdue_ids, "received item never overdue")


def test_completion_pct():
    print("completion %:")
    d = compute_dashboard(_items(), today=date(2026, 6, 1))
    # received (1) / in-scope (total 5 - not_needed 1 = 4) * 100 = 25.0
    check(d["completion_pct"] == 25.0, "completion = received / (total - not_needed) = 25.0%")
    check(compute_dashboard([], today=date(2026, 6, 1))["completion_pct"] == 0.0, "empty DRL -> 0%")


def test_days_overdue():
    print("days overdue:")
    check(_days_overdue("2026-01-01", date(2026, 1, 9)) == 8, "8 days past deadline")
    check(_days_overdue("2026-01-01", date(2026, 1, 1)) == 0, "on the deadline = 0")
    check(_days_overdue("2099-01-01", date(2026, 1, 1)) == 0, "future deadline = 0")
    check(_days_overdue(None, date(2026, 1, 1)) == 0, "no deadline = 0")
    check(_days_overdue("2026-01-01", date(2026, 1, 9)) > 7, "escalation threshold crossed (>7)")


def main():
    test_dashboard_counts()
    test_overdue_derivation()
    test_completion_pct()
    test_days_overdue()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
