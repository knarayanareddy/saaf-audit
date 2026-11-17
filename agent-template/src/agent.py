"""Minimal example agent: flags accounts that have not logged in for 180 days.

Deterministic, no model calls, synthetic data only. Replace it with your own agent.
"""
import csv
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("agent")
STALE_AFTER_DAYS = 180


def find_stale_accounts(rows: List[Dict[str, str]], today: date) -> List[Dict[str, str]]:
    """Return one finding per account whose last login is older than the limit."""
    findings: List[Dict[str, str]] = []
    for row in rows:
        last_login = date.fromisoformat(row["last_login"])
        days = (today - last_login).days
        if days > STALE_AFTER_DAYS:
            findings.append({
                "id": f"F-{len(findings) + 1:02d}",
                "title": f"Stale account {row['user_id']}",
                "risk_rating": "Medium",
                "observation": f"{row['user_id']} ({row['role']}) last logged in {days} days ago.",
                "recommendation": "Confirm with the owner whether the account is still needed.",
            })
    return findings


def main(path: str) -> None:
    with Path(path).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    findings = find_stale_accounts(rows, date.today())
    LOG.info("read %d rows, wrote %d findings", len(rows), len(findings))
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
