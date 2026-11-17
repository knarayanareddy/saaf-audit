import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent import find_stale_accounts  # noqa: E402


def test_flags_only_stale_accounts() -> None:
    rows = [
        {"user_id": "u-001", "role": "approver", "last_login": "2026-10-01"},
        {"user_id": "u-002", "role": "approver", "last_login": "2026-03-14"},
    ]
    findings = find_stale_accounts(rows, date(2026, 11, 17))
    assert [f["title"] for f in findings] == ["Stale account u-002"]
    assert findings[0]["id"] == "F-01"
    assert findings[0]["risk_rating"] in {"High", "Medium", "Low", "Informational"}
