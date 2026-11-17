"""
Tests for access_review_agent.py

Run from repo root:
    python3 -m pytest tools/scripts/bart/tests/ -v
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

# Ensure the bart directory is on the path so we can import access_review_agent
sys.path.insert(0, str(Path(__file__).parents[1]))

from access_review_agent import (
    anonymize_users,
    detect_exceptions,
    normalize_key,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def hr_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "username": ["jdoe", "asmith", "cformer"],
            "department": ["Finance", "IT", "Operations"],
            "role": ["Finance User", "IT Support", "Operations User"],
            "status": ["Active", "Active", "Terminated"],
            "termination_date": ["", "", "2026-03-15"],
        }
    )


@pytest.fixture()
def access_df() -> pd.DataFrame:
    # bwilliams: orphaned (not in HR), stale (login 2025-10-01)
    # cformer: departed but enabled
    # asmith: role mismatch (IT Admin vs IT Support in HR)
    # svc_backup: excluded by pattern
    return pd.DataFrame(
        {
            "username": ["jdoe", "asmith", "bwilliams", "cformer", "svc_backup"],
            "department": ["Finance", "IT", "Finance", "Operations", "IT"],
            "access_role": ["Finance User", "IT Admin", "Finance User", "Operations User", "Backup Service"],
            "enabled": ["true", "true", "true", "true", "true"],
            "last_login": ["2026-04-20", "2026-04-22", "2025-10-01", "2026-04-01", "2026-05-01"],
        }
    )


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------


def test_orphaned_account_detected(hr_df: pd.DataFrame, access_df: pd.DataFrame) -> None:
    """bwilliams is in access but not HR — should produce a High orphaned finding."""
    results = detect_exceptions(hr_df, access_df, stale_days=90)
    findings = results["findings"]
    orphaned = [f for f in findings if f["category"] == "orphaned"]
    assert len(orphaned) >= 1, "Expected at least one orphaned finding"
    # The finding should reference bwilliams via USER-NNN, not the real name
    bwilliams_ref = results["_anon_map"][normalize_key("bwilliams")]
    assert any(f["affected_user_ref"] == bwilliams_ref for f in orphaned), (
        f"Expected orphaned finding for bwilliams ({bwilliams_ref})"
    )
    # Risk must be High
    for f in orphaned:
        if f["affected_user_ref"] == bwilliams_ref:
            assert f["risk_rating"] == "High"


def test_departed_employee_detected(hr_df: pd.DataFrame, access_df: pd.DataFrame) -> None:
    """cformer is Terminated in HR but still enabled in access — High finding."""
    results = detect_exceptions(hr_df, access_df, stale_days=90)
    findings = results["findings"]
    departed = [f for f in findings if f["category"] == "departed"]
    assert len(departed) >= 1, "Expected at least one departed finding"
    cformer_ref = results["_anon_map"][normalize_key("cformer")]
    assert any(f["affected_user_ref"] == cformer_ref for f in departed)
    for f in departed:
        if f["affected_user_ref"] == cformer_ref:
            assert f["risk_rating"] == "High"


def test_role_mismatch_detected(hr_df: pd.DataFrame, access_df: pd.DataFrame) -> None:
    """asmith has IT Admin in access but IT Support in HR — Medium finding."""
    results = detect_exceptions(hr_df, access_df, stale_days=90)
    findings = results["findings"]
    mismatches = [f for f in findings if f["category"] == "role_mismatch"]
    assert len(mismatches) >= 1, "Expected at least one role_mismatch finding"
    asmith_ref = results["_anon_map"][normalize_key("asmith")]
    assert any(f["affected_user_ref"] == asmith_ref for f in mismatches)
    for f in mismatches:
        if f["affected_user_ref"] == asmith_ref:
            assert f["risk_rating"] == "Medium"


def test_stale_account_detected(hr_df: pd.DataFrame) -> None:
    """Account with last_login > 90 days ago should produce a Low stale finding."""
    stale_date = (date.today() - timedelta(days=100)).isoformat()
    access = pd.DataFrame(
        {
            "username": ["jdoe"],
            "department": ["Finance"],
            "access_role": ["Finance User"],
            "enabled": ["true"],
            "last_login": [stale_date],
        }
    )
    results = detect_exceptions(hr_df, access, stale_days=90)
    stale = [f for f in results["findings"] if f["category"] == "stale"]
    assert len(stale) >= 1, f"Expected stale finding for last_login {stale_date}"
    assert stale[0]["risk_rating"] == "Low"


def test_service_account_excluded(hr_df: pd.DataFrame, access_df: pd.DataFrame) -> None:
    """svc_backup matches 'svc*' pattern and must not appear in findings."""
    results = detect_exceptions(hr_df, access_df, stale_days=90)
    findings = results["findings"]
    # Get all user refs in findings
    user_refs = {f["affected_user_ref"] for f in findings}
    # svc_backup should be anonymized — get its ref
    svc_key = normalize_key("svc_backup")
    svc_ref = results["_anon_map"].get(svc_key)
    if svc_ref:
        assert svc_ref not in user_refs, "svc_backup should be excluded from findings"
    assert results["excluded_count"] >= 1, "Expected at least 1 excluded account"


def test_anonymization_stable() -> None:
    """Same input always produces the same USER-NNN mapping."""
    keys = ["alice", "bob", "charlie"]
    anon1, _ = anonymize_users(keys)
    anon2, _ = anonymize_users(keys)
    assert anon1 == anon2, "Anonymization mapping must be stable across calls"
    # Order is alphabetical, so alice=USER-001, bob=USER-002, charlie=USER-003
    assert anon1["alice"] == "USER-001"
    assert anon1["bob"] == "USER-002"
    assert anon1["charlie"] == "USER-003"


def test_no_real_identifiers_in_findings(hr_df: pd.DataFrame, access_df: pd.DataFrame) -> None:
    """Findings JSON must not contain raw usernames from either export."""
    results = detect_exceptions(hr_df, access_df, stale_days=90)
    findings_json = str(results["findings"])
    real_usernames = list(hr_df["username"]) + list(access_df["username"])
    for username in real_usernames:
        assert username not in findings_json, (
            f"Real username '{username}' found in findings output — anonymization failed"
        )


def test_empty_access_file(hr_df: pd.DataFrame) -> None:
    """Empty access DataFrame should not crash and should produce zero findings."""
    empty_access = pd.DataFrame(
        columns=["username", "department", "access_role", "enabled", "last_login"]
    )
    results = detect_exceptions(hr_df, empty_access, stale_days=90)
    assert results["findings"] == [], "Empty access file should produce no findings"
    assert results["excluded_count"] == 0


def test_finding_schema_valid(hr_df: pd.DataFrame, access_df: pd.DataFrame) -> None:
    """Every finding must contain all required schema fields."""
    required_fields = [
        "id",
        "title",
        "risk_rating",
        "category",
        "affected_user_ref",
        "control_refs",
        "observation",
        "recommendation",
        "detected_at",
        "source",
    ]
    results = detect_exceptions(hr_df, access_df, stale_days=90)
    for finding in results["findings"]:
        for field in required_fields:
            assert field in finding, (
                f"Finding {finding.get('id', '?')} is missing required field '{field}'"
            )
        # id must match F-NNN pattern
        import re
        assert re.match(r"^F-\d{3,}$", finding["id"]), f"id '{finding['id']}' does not match F-NNN pattern"
        # risk_rating must be valid
        assert finding["risk_rating"] in ("High", "Medium", "Low", "Informational")
        # control_refs must be a list
        assert isinstance(finding["control_refs"], list)
