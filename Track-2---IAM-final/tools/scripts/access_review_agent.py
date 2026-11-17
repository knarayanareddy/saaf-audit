#!/usr/bin/env python3
"""
access_review_agent.py
Automated user access review agent using the Claude API.

Compares an Active Directory (AD) export against an HR active-employee list
to identify orphaned accounts, stale accounts, and role mismatches.
Calls Claude with the access-review-agent system prompt and writes structured
findings to outputs/access-review/findings.json conforming to the SAAF finding
schema (outputs/schemas/finding-schema.json).

Usage:
    python3 tools/scripts/access_review_agent.py \\
        --ad tools/scripts/test_data/ad_export.csv \\
        --hr tools/scripts/test_data/hr_export.csv \\
        --threshold-days 90

Requirements:
    pip install anthropic
    ANTHROPIC_API_KEY environment variable must be set.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parents[2]
PROMPT_FILE = REPO_ROOT / "prompts" / "audit-use-cases" / "access-review-agent.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "access-review"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        logger.error("File not found: %s", path)
        raise SystemExit(1)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Anonymisation — must run before any data reaches the API
# ---------------------------------------------------------------------------

def anonymise(users: list[dict], counter_start: int = 1) -> tuple[list[dict], dict[str, str]]:
    """Replace 'username' values with USER-NNN placeholders.

    Returns the anonymised list and a mapping {placeholder: original} for
    local reference only (never sent to the API).
    """
    mapping: dict[str, str] = {}
    result: list[dict] = []
    for i, user in enumerate(users, start=counter_start):
        placeholder = f"USER-{i:03d}"
        original = user.get("username", "")
        mapping[placeholder] = original
        anon = dict(user)
        anon["username"] = placeholder
        result.append(anon)
    return result, mapping


# ---------------------------------------------------------------------------
# Exception detection
# ---------------------------------------------------------------------------

def find_orphaned(ad_users: list[dict], hr_users: list[dict]) -> list[dict]:
    """Return AD accounts with no matching username in the HR list."""
    hr_usernames = {u["username"] for u in hr_users}
    return [u for u in ad_users if u["username"] not in hr_usernames]


def find_stale(ad_users: list[dict], threshold_days: int = 90) -> list[dict]:
    """Return AD accounts whose last_login is older than threshold_days."""
    today = date.today()
    stale: list[dict] = []
    for user in ad_users:
        raw = user.get("last_login", "")
        try:
            last_login = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Could not parse last_login '%s' for %s — skipped", raw, user.get("username"))
            continue
        if (today - last_login).days > threshold_days:
            stale.append(user)
    return stale


def find_role_mismatches(ad_users: list[dict], hr_users: list[dict]) -> list[dict]:
    """Return accounts where the department field differs between AD and HR."""
    hr_by_username = {u["username"]: u for u in hr_users}
    mismatches: list[dict] = []
    for ad_user in ad_users:
        username = ad_user["username"]
        hr_user = hr_by_username.get(username)
        if hr_user and ad_user.get("department") != hr_user.get("department"):
            mismatches.append({
                "username": username,
                "ad_department": ad_user.get("department", ""),
                "hr_department": hr_user.get("department", ""),
                "role": ad_user.get("role", ""),
                "last_login": ad_user.get("last_login", ""),
            })
    return mismatches


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def load_system_prompt() -> str:
    if not PROMPT_FILE.exists():
        logger.error("System prompt not found: %s", PROMPT_FILE)
        raise SystemExit(1)
    text = PROMPT_FILE.read_text(encoding="utf-8")
    match = re.search(r"## System Context\n\n(.+?)(?=\n---\n)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def build_user_prompt(
    orphaned: list[dict],
    stale: list[dict],
    mismatches: list[dict],
    threshold_days: int,
) -> str:
    lines: list[str] = [
        "I am performing a user access review.",
        "All usernames have been anonymised to USER-NNN placeholders.",
        "",
    ]

    if orphaned:
        lines.append(f"Orphaned AD accounts (no matching HR record — {len(orphaned)} found):")
        for u in orphaned:
            lines.append(
                f"  {u['username']}, department: {u.get('department', 'N/A')}, "
                f"role: {u.get('role', 'N/A')}, last_login: {u.get('last_login', 'N/A')}"
            )
    else:
        lines.append("Orphaned AD accounts: none found.")

    lines.append("")

    if stale:
        lines.append(
            f"Stale accounts (no login in >{threshold_days} days — {len(stale)} found):"
        )
        for u in stale:
            lines.append(
                f"  {u['username']}, department: {u.get('department', 'N/A')}, "
                f"last_login: {u.get('last_login', 'N/A')}"
            )
    else:
        lines.append(f"Stale accounts (>{threshold_days} days): none found.")

    lines.append("")

    if mismatches:
        lines.append(f"Role mismatches (department differs between AD and HR — {len(mismatches)} found):")
        for m in mismatches:
            lines.append(
                f"  {m['username']}: AD department = {m['ad_department']}, "
                f"HR department = {m['hr_department']}"
            )
    else:
        lines.append("Role mismatches: none found.")

    lines.append("")
    lines.append("Please produce SAAF findings for all exceptions listed above.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def call_claude(system: str, user: str) -> Optional[str]:
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed — run: pip install anthropic")
        raise SystemExit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        raise SystemExit(1)

    client = anthropic.Anthropic(api_key=api_key)
    logger.info("Calling Claude API (model: %s, max_tokens: %d)", MODEL, MAX_TOKENS)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = response.content[0].text
    logger.info("Received response (%d chars)", len(raw))
    return raw


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_findings(findings_raw: str) -> list[dict]:
    """Parse and validate findings against required SAAF schema fields."""
    required_fields = {"id", "title", "risk_rating", "observation", "recommendation"}
    valid_ratings = {"High", "Medium", "Low", "Informational"}
    id_pattern = re.compile(r"^F-\d{2,4}$")

    json_match = re.search(r"```json\s*(\[.*?\])\s*```", findings_raw, re.DOTALL)
    raw_block = json_match.group(1) if json_match else findings_raw.strip()

    try:
        findings = json.loads(raw_block)
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse findings JSON: %s", exc)
        logger.debug("Raw response:\n%s", findings_raw)
        return []

    validated: list[dict] = []
    for i, finding in enumerate(findings):
        missing = required_fields - set(finding.keys())
        if missing:
            logger.warning("Finding %d missing required fields: %s — skipped", i + 1, missing)
            continue
        if not id_pattern.match(finding["id"]):
            logger.warning("Finding %s has invalid id format — skipped", finding.get("id"))
            continue
        if finding["risk_rating"] not in valid_ratings:
            logger.warning(
                "Finding %s has invalid risk_rating '%s' — skipped",
                finding["id"],
                finding["risk_rating"],
            )
            continue
        validated.append(finding)

    logger.info("Validated %d/%d findings", len(validated), len(findings))
    return validated


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_outputs(output_dir: Path, findings: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    findings_file = output_dir / "findings.json"
    findings_file.write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Written %d findings → %s", len(findings), findings_file)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated access review agent — compares AD export to HR list and produces SAAF findings."
    )
    parser.add_argument(
        "--ad",
        required=True,
        help="Path to Active Directory export CSV (columns: username, department, role, last_login)",
    )
    parser.add_argument(
        "--hr",
        required=True,
        help="Path to HR active-employee list CSV (columns: employee_id, username, department, status)",
    )
    parser.add_argument(
        "--threshold-days",
        type=int,
        default=90,
        help="Days of inactivity before an account is considered stale (default: 90)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write findings.json (default: outputs/access-review/)",
    )
    args = parser.parse_args()

    ad_raw = load_csv(Path(args.ad))
    hr_raw = load_csv(Path(args.hr))
    logger.info("Loaded %d AD accounts, %d HR records", len(ad_raw), len(hr_raw))

    # Anonymise AD users before any processing that touches usernames
    ad_anon, anon_map = anonymise(ad_raw, counter_start=1)
    # Build a reverse map: original → placeholder for HR matching
    orig_to_placeholder = {v: k for k, v in anon_map.items()}
    hr_anon = [
        {**u, "username": orig_to_placeholder.get(u["username"], u["username"])}
        for u in hr_raw
    ]

    orphaned = find_orphaned(ad_anon, hr_anon)
    stale = find_stale(ad_anon, threshold_days=args.threshold_days)
    mismatches = find_role_mismatches(ad_anon, hr_anon)

    logger.info(
        "Exceptions — orphaned: %d, stale: %d, role mismatches: %d",
        len(orphaned),
        len(stale),
        len(mismatches),
    )

    if not orphaned and not stale and not mismatches:
        logger.info("No exceptions found. No findings to produce.")
        sys.exit(0)

    system_prompt = load_system_prompt()
    user_prompt = build_user_prompt(orphaned, stale, mismatches, args.threshold_days)

    raw_response = call_claude(system_prompt, user_prompt)
    findings = validate_findings(raw_response)

    output_dir = Path(args.output_dir)
    write_outputs(output_dir, findings)

    print(f"\nDone — {len(findings)} finding(s) written to {output_dir}/findings.json")
    print(f"  Orphaned accounts reviewed : {len(orphaned)}")
    print(f"  Stale accounts reviewed    : {len(stale)}")
    print(f"  Role mismatches reviewed   : {len(mismatches)}")


if __name__ == "__main__":
    main()
