"""
access_review.py
Baseline account review engine.

Origin: spin-off of SAAF-Project/Track-2---IAM-final, file
tools/scripts/bart/access_review_agent.py by Bart van den Broek
(SAAF Local User Access Review Comparator). Reused with permission.

Changes in this copy (kept small on purpose so the two can be compared):
- detect_exceptions() takes an optional `as_of` date instead of always using
  date.today(), so a review over a fixed extraction date is reproducible.
- detected_at uses a timezone-aware UTC timestamp.
- The CLI example paths point at this repository.

The JML-specific tests (joiners, movers, leavers against Jira tickets) live in
engine/jml_checks.py and use this engine for the baseline account checks.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import logging
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Control reference mapping
# ---------------------------------------------------------------------------

CONTROL_REFS: dict[str, list[str]] = {
    "orphaned": [
        "ISO/IEC 27001:2022 A.5.18",
        "SOC 2 CC6.2",
        "SOC 2 CC6.3",
        "ISAE 3402 user access review control objective",
    ],
    "departed": [
        "ISO/IEC 27001:2022 A.5.18",
        "SOC 2 CC6.2",
        "ISAE 3402 user access review control objective",
    ],
    "role_mismatch": [
        "ISO/IEC 27001:2022 A.5.18",
        "SOC 2 CC6.3",
    ],
    "stale": [
        "ISO/IEC 27001:2022 A.5.18",
        "SOC 2 CC6.2",
    ],
    "duplicate": [
        "ISO/IEC 27001:2022 A.5.18",
        "SOC 2 CC6.3",
    ],
}

DEFAULT_EXCLUSION_PATTERNS: list[str] = ["svc*", "service*", "app*", "*_svc"]

REQUIRED_FINDING_FIELDS = [
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

# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------


def load_file(path: "str | Path") -> pd.DataFrame:
    """Load a CSV or XLSX file and return a DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, dtype=str)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use .csv or .xlsx")
    # Strip whitespace from column names and string values
    df.columns = [c.strip() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_key(val: str) -> str:
    """Strip whitespace and lowercase."""
    return str(val).strip().lower()


def _is_excluded(username: str, patterns: list[str]) -> bool:
    """Return True if username matches any glob exclusion pattern."""
    u = username.lower()
    return any(fnmatch.fnmatch(u, p.lower()) for p in patterns)


def _parse_bool(val: Optional[str]) -> bool:
    """Parse a boolean-like string ('true'/'false'/'1'/'0')."""
    if val is None:
        return False
    return str(val).strip().lower() in ("true", "1", "yes")


def _parse_date(val: Optional[str]) -> Optional[date]:
    """Parse an ISO date string, return None on failure."""
    if not val or pd.isna(val):
        return None
    val = str(val).strip()
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Anonymization
# ---------------------------------------------------------------------------


def anonymize_users(
    keys: list[str],
) -> "tuple[dict[str, str], dict[str, str]]":
    """
    Build stable USER-NNN anonymization maps.

    Returns:
        anon_map:   real_identifier -> USER-001
        reveal_map: USER-001 -> real_identifier
    """
    # Sort for stability
    unique_keys = sorted(set(normalize_key(k) for k in keys if k))
    anon_map: dict[str, str] = {}
    reveal_map: dict[str, str] = {}
    for i, key in enumerate(unique_keys, start=1):
        ref = f"USER-{i:03d}"
        anon_map[key] = ref
        reveal_map[ref] = key
    return anon_map, reveal_map


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_exceptions(
    hr_df: pd.DataFrame,
    access_df: pd.DataFrame,
    match_key: str = "username",
    stale_days: int = 90,
    exclusion_patterns: Optional[list[str]] = None,
    hr_status_col: str = "status",
    hr_termination_col: str = "termination_date",
    access_enabled_col: str = "enabled",
    access_last_login_col: str = "last_login",
    hr_dept_col: str = "department",
    hr_role_col: str = "role",
    access_dept_col: str = "department",
    access_role_col: str = "access_role",
    as_of: Optional[date] = None,
) -> dict:
    """
    Detect access control exceptions by comparing HR and access exports.

    Returns a dict with keys:
        findings        list of finding dicts (anonymized)
        excluded_count  number of accounts excluded by pattern
        summary         high-level counts
    Also embeds _anon_map and _reveal_map for the caller.
    """
    if exclusion_patterns is None:
        exclusion_patterns = DEFAULT_EXCLUSION_PATTERNS

    today = as_of or date.today()
    detected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- normalise match keys ----
    if match_key not in hr_df.columns:
        raise ValueError(f"match_key '{match_key}' not found in HR data. Columns: {list(hr_df.columns)}")
    if match_key not in access_df.columns:
        raise ValueError(f"match_key '{match_key}' not found in access data. Columns: {list(access_df.columns)}")

    hr_df = hr_df.copy()
    access_df = access_df.copy()

    hr_df["_key"] = hr_df[match_key].apply(normalize_key)
    access_df["_key"] = access_df[match_key].apply(normalize_key)

    # ---- collect all real identifiers for anonymization ----
    all_keys = list(hr_df["_key"]) + list(access_df["_key"])
    anon_map, reveal_map = anonymize_users(all_keys)

    # ---- build HR lookup ----
    hr_lookup: dict[str, dict] = {}
    for _, row in hr_df.iterrows():
        k = row["_key"]
        hr_lookup[k] = row.to_dict()

    findings: list[dict] = []
    excluded_count = 0
    finding_counter = 0

    def make_finding(
        category: str,
        risk: str,
        key: str,
        title: str,
        observation: str,
        recommendation: str,
    ) -> dict:
        nonlocal finding_counter
        finding_counter += 1
        user_ref = anon_map.get(normalize_key(key), f"USER-???")
        return {
            "id": f"F-{finding_counter:03d}",
            "title": title,
            "risk_rating": risk,
            "category": category,
            "affected_user_ref": user_ref,
            "control_refs": CONTROL_REFS.get(category, []),
            "observation": observation,
            "recommendation": recommendation,
            "detected_at": detected_at,
            "source": "access_review_agent",
        }

    # ---- Track processed keys for duplicate detection ----
    seen_keys: dict[str, int] = {}

    for _, row in access_df.iterrows():
        key = row["_key"]

        # --- Exclusion ---
        if _is_excluded(key, exclusion_patterns):
            excluded_count += 1
            log.info("Excluded (pattern match): %s", key)
            continue

        # --- Duplicate tracking ---
        enabled = _parse_bool(row.get(access_enabled_col))
        if enabled:
            seen_keys[key] = seen_keys.get(key, 0) + 1

        # A. Orphaned — in access but not in HR
        if key not in hr_lookup:
            findings.append(
                make_finding(
                    category="orphaned",
                    risk="High",
                    key=key,
                    title="Orphaned account — no matching HR record",
                    observation=(
                        f"Account '{anon_map.get(key, key)}' exists in the access system "
                        f"but has no corresponding record in the HR export. "
                        f"This may indicate a former employee, contractor, or generic account "
                        f"that was not properly deprovisioned."
                    ),
                    recommendation=(
                        "Immediately review and disable this account. "
                        "Investigate whether the account belongs to a terminated user or is "
                        "an unmanaged generic/service account. Deprovision if no legitimate "
                        "business owner can be identified."
                    ),
                )
            )
            continue  # no further checks possible without HR record

        hr_row = hr_lookup[key]

        # B. Departed with active access
        hr_status = str(hr_row.get(hr_status_col, "")).strip()
        term_date_str = hr_row.get(hr_termination_col)
        term_date = _parse_date(term_date_str)

        departed = (hr_status.lower() != "active") or (term_date is not None and term_date <= today)

        if departed and enabled:
            term_info = f" (termination date: {term_date})" if term_date else ""
            findings.append(
                make_finding(
                    category="departed",
                    risk="High",
                    key=key,
                    title="Active access for departed employee",
                    observation=(
                        f"Account '{anon_map.get(key, key)}' has an active enabled status in the "
                        f"access system, but the HR record shows status '{hr_status}'{term_info}. "
                        f"This represents a segregation-of-duties risk and potential unauthorized access."
                    ),
                    recommendation=(
                        "Immediately disable and revoke all access for this account. "
                        "Confirm with HR the effective termination date. Review system logs for "
                        "any access activity after the termination date. Document the remediation."
                    ),
                )
            )

        # C. Role / department mismatch
        has_hr_role = hr_role_col in hr_df.columns and hr_role_col in hr_row
        has_access_role = access_role_col in access_df.columns and access_role_col in row
        has_hr_dept = hr_dept_col in hr_df.columns and hr_dept_col in hr_row
        has_access_dept = access_dept_col in access_df.columns and access_dept_col in row

        mismatches = []
        if has_hr_role and has_access_role:
            hr_role = normalize_key(str(hr_row.get(hr_role_col, "")))
            acc_role = normalize_key(str(row.get(access_role_col, "")))
            if hr_role and acc_role and hr_role != acc_role:
                mismatches.append(
                    f"role (HR: '{hr_row.get(hr_role_col)}' vs access: '{row.get(access_role_col)}')"
                )
        if has_hr_dept and has_access_dept:
            hr_dept = normalize_key(str(hr_row.get(hr_dept_col, "")))
            acc_dept = normalize_key(str(row.get(access_dept_col, "")))
            if hr_dept and acc_dept and hr_dept != acc_dept:
                mismatches.append(
                    f"department (HR: '{hr_row.get(hr_dept_col)}' vs access: '{row.get(access_dept_col)}')"
                )

        if mismatches:
            mismatch_desc = "; ".join(mismatches)
            findings.append(
                make_finding(
                    category="role_mismatch",
                    risk="Medium",
                    key=key,
                    title="Role or department mismatch between HR and access system",
                    observation=(
                        f"Account '{anon_map.get(key, key)}' has a discrepancy between HR and access records: "
                        f"{mismatch_desc}. This may indicate the access system was not updated when the "
                        f"employee changed roles or departments, creating excessive or inappropriate privileges."
                    ),
                    recommendation=(
                        "Review the current role and department assignment for this user. "
                        "Update the access system to reflect the current HR record. "
                        "Revoke any access rights that are no longer appropriate for the current role."
                    ),
                )
            )

        # D. Stale — last_login older than stale_days
        if access_last_login_col in access_df.columns:
            last_login_str = row.get(access_last_login_col)
            if last_login_str and str(last_login_str).strip().lower() == "never":
                # Never logged in = infinitely stale
                findings.append(
                    make_finding(
                        category="stale",
                        risk="Low",
                        key=key,
                        title="Stale account — never logged in",
                        observation=(
                            f"Account '{anon_map.get(key, key)}' has never logged in to the access system. "
                            f"Accounts with no login activity may indicate orphaned or unnecessary access."
                        ),
                        recommendation=(
                            "Confirm whether this account is still required. "
                            "If the account is no longer needed, disable and schedule for removal. "
                            "If required, document the business justification."
                        ),
                    )
                )
            elif last_login_str:
                last_login = _parse_date(str(last_login_str))
                if last_login is not None:
                    days_since = (today - last_login).days
                    if days_since > stale_days:
                        findings.append(
                            make_finding(
                                category="stale",
                                risk="Low",
                                key=key,
                                title=f"Stale account — no login for {days_since} days",
                                observation=(
                                    f"Account '{anon_map.get(key, key)}' has not logged in for {days_since} days "
                                    f"(last login: {last_login}, threshold: {stale_days} days). "
                                    f"Inactive accounts increase the attack surface without business benefit."
                                ),
                                recommendation=(
                                    f"Review whether this account is still required. "
                                    f"If dormant accounts are not actively managed, implement an automated "
                                    f"policy to disable accounts after {stale_days} days of inactivity."
                                ),
                            )
                        )

    # E. Duplicate enabled accounts
    for key, count in seen_keys.items():
        if count > 1 and not _is_excluded(key, exclusion_patterns):
            findings.append(
                make_finding(
                    category="duplicate",
                    risk="Medium",
                    key=key,
                    title=f"Duplicate enabled accounts ({count} entries)",
                    observation=(
                        f"The access export contains {count} enabled entries for account "
                        f"'{anon_map.get(key, key)}'. Duplicate accounts may indicate provisioning errors "
                        f"or attempts to circumvent access controls."
                    ),
                    recommendation=(
                        "Investigate why multiple enabled entries exist for this user. "
                        "Disable all but the authorised record and review audit logs for any "
                        "activity on the duplicate accounts."
                    ),
                )
            )

    # ---- Summary ----
    risk_counts: dict[str, int] = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    for f in findings:
        risk_counts[f["risk_rating"]] = risk_counts.get(f["risk_rating"], 0) + 1

    summary = {
        "hr_records": len(hr_df),
        "access_records": len(access_df),
        "excluded_accounts": excluded_count,
        "total_findings": len(findings),
        "findings_by_risk": risk_counts,
        "review_date": today.isoformat(),
    }

    return {
        "findings": findings,
        "excluded_count": excluded_count,
        "summary": summary,
        "_anon_map": anon_map,
        "_reveal_map": reveal_map,
    }


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------


def write_run_outputs(
    results: dict,
    anon_map: dict,
    reveal_map: dict,
    out_dir: Path,
) -> None:
    """Write all run output files to out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    findings = results["findings"]
    summary = results["summary"]

    # findings.json
    findings_path = out_dir / "findings.json"
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    log.info("Wrote %s", findings_path)

    # findings.csv
    csv_path = out_dir / "findings.csv"
    if findings:
        fieldnames = REQUIRED_FINDING_FIELDS
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for finding in findings:
                row = dict(finding)
                row["control_refs"] = "; ".join(row.get("control_refs", []))
                writer.writerow(row)
    else:
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(",".join(REQUIRED_FINDING_FIELDS) + "\n")
    log.info("Wrote %s", csv_path)

    # summary.json
    summary_path = out_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    log.info("Wrote %s", summary_path)

    # user_mapping.csv (SENSITIVE — maps USER-NNN to real identifiers)
    mapping_path = out_dir / "user_mapping.csv"
    with open(mapping_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_ref", "real_identifier"])
        for ref, real in sorted(reveal_map.items()):
            writer.writerow([ref, real])
    log.info("Wrote %s (SENSITIVE)", mapping_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAAF Local User Access Review Comparator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m engine.access_review \\
    --hr sample_data/hr_employees.csv \\
    --access sample_data/ad_accounts.csv \\
    --out runs/baseline \\
    --match-key username \\
    --stale-days 90
""",
    )
    parser.add_argument("--hr", required=True, help="Path to HR export (CSV or XLSX)")
    parser.add_argument("--access", required=True, help="Path to access export (CSV or XLSX)")
    parser.add_argument("--out", required=True, help="Output directory for findings")
    parser.add_argument("--match-key", default="username", help="Column to join on (default: username)")
    parser.add_argument("--stale-days", type=int, default=90, help="Days of inactivity before stale (default: 90)")
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=None,
        help="Glob patterns to exclude (default: svc* service* app* *_svc)",
    )
    args = parser.parse_args()

    hr_df = load_file(args.hr)
    access_df = load_file(args.access)

    log.info("HR records: %d  |  Access records: %d", len(hr_df), len(access_df))

    results = detect_exceptions(
        hr_df=hr_df,
        access_df=access_df,
        match_key=args.match_key,
        stale_days=args.stale_days,
        exclusion_patterns=args.exclude,
    )

    anon_map = results.pop("_anon_map")
    reveal_map = results.pop("_reveal_map")

    out_dir = Path(args.out)
    write_run_outputs(results, anon_map, reveal_map, out_dir)

    summary = results["summary"]
    print("\n=== Access Review Summary ===")
    print(f"HR records reviewed   : {summary['hr_records']}")
    print(f"Access records reviewed: {summary['access_records']}")
    print(f"Excluded accounts     : {summary['excluded_accounts']}")
    print(f"Total findings        : {summary['total_findings']}")
    for risk, count in summary["findings_by_risk"].items():
        if count:
            print(f"  {risk:<15}: {count}")
    print(f"\nOutputs written to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
