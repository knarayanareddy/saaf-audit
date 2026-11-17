#!/usr/bin/env python3
"""Validate the committed SAAF Strapi seed files and optional live endpoint counts.

Usage:
  python3 tools/scripts/verify_strapi_seed.py
  python3 tools/scripts/verify_strapi_seed.py --check-api --base-url http://localhost:1340
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "strapi" / "seed"
FINDING_SCHEMA_PATH = ROOT.parent / "outputs" / "schemas" / "finding-schema.json"
EXPECTED_COUNTS = {
    "jira-incidents": 500,
    "access-reviews": 200,
    "change-tickets": 150,
    "vendor-contracts": 50,
    "audit-findings": 100,
}
RESERVED_NAME_FRAGMENTS = ["John", "Jane", "Acme", "Globex", "Contoso"]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_counts() -> None:
    for name, expected_count in EXPECTED_COUNTS.items():
        records = load_json(SEED_DIR / f"{name}.json")
        assert_true(isinstance(records, list), f"{name} is not a JSON array")
        assert_true(len(records) == expected_count, f"{name} expected {expected_count} records, found {len(records)}")


def validate_no_obvious_real_data() -> None:
    for path in SEED_DIR.glob("*.json"):
        content = path.read_text(encoding="utf-8")
        for fragment in RESERVED_NAME_FRAGMENTS:
            assert_true(fragment not in content, f"{path.name} contains reserved fragment {fragment!r}")


def validate_findings() -> None:
    schema = load_json(FINDING_SCHEMA_PATH)
    records = load_json(SEED_DIR / "audit-findings.json")
    required = set(schema["required"])
    allowed = set(schema["properties"])
    id_pattern = re.compile(schema["properties"]["id"]["pattern"])

    for index, record in enumerate(records, start=1):
        missing = required - set(record)
        assert_true(not missing, f"Finding {index} missing required fields: {sorted(missing)}")
        extra = set(record) - allowed
        assert_true(not extra, f"Finding {index} has extra fields: {sorted(extra)}")
        assert_true(id_pattern.match(record["id"]) is not None, f"Finding {index} has invalid id {record['id']}")
        assert_true(record["risk_rating"] in schema["properties"]["risk_rating"]["enum"], f"Finding {index} has invalid risk")
        assert_true(record["status"] in schema["properties"]["status"]["enum"], f"Finding {index} has invalid status")
        assert_true(isinstance(record["ai_assisted"], bool), f"Finding {index} ai_assisted must be boolean")
        assert_true(isinstance(record["evidence_references"], list), f"Finding {index} evidence_references must be a list")


def validate_api(base_url: str) -> None:
    for name, expected_count in EXPECTED_COUNTS.items():
        url = f"{base_url}/api/{name}?pagination[pageSize]=1"
        with urllib.request.urlopen(url) as response:
            payload = json.loads(response.read().decode("utf-8"))
        count = payload["meta"]["pagination"]["total"]
        assert_true(count == expected_count, f"{name} API count mismatch: expected {expected_count}, found {count}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-api", action="store_true")
    parser.add_argument("--base-url", default="http://localhost:1340")
    args = parser.parse_args()

    try:
        validate_counts()
        validate_no_obvious_real_data()
        validate_findings()
        if args.check_api:
            validate_api(args.base_url)
    except (AssertionError, urllib.error.URLError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print("Seed files validated successfully.")
    if args.check_api:
        print(f"API counts validated successfully against {args.base_url}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
