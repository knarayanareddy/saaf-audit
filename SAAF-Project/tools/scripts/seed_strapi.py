#!/usr/bin/env python3
"""Reset and seed the local SAAF Strapi sandbox over the admin API.

Usage:
  python3 tools/scripts/seed_strapi.py --base-url http://localhost:1340

Environment:
  SAAF_STRAPI_ADMIN_EMAIL
  SAAF_STRAPI_ADMIN_PASSWORD
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "strapi" / "seed"
DATASETS = [
    ("jira-incidents", "api::jira-incident.jira-incident"),
    ("access-reviews", "api::access-review.access-review"),
    ("change-tickets", "api::change-ticket.change-ticket"),
    ("vendor-contracts", "api::vendor-contract.vendor-contract"),
    ("audit-findings", "api::audit-finding.audit-finding"),
]


def http_json(url: str, method: str = "GET", payload: dict | None = None, token: str | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else {}


def login(base_url: str, email: str, password: str) -> str:
    response = http_json(
        f"{base_url}/admin/login",
        method="POST",
        payload={"email": email, "password": password},
    )
    return response["data"]["token"]


def load_dataset(name: str) -> list[dict]:
    return json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8"))


def transform_record(dataset: str, record: dict) -> dict:
    if dataset != "audit-findings":
        return record
    finding = dict(record)
    finding["id_code"] = finding.pop("id")
    return finding


def model_url(base_url: str, model: str) -> str:
    encoded_model = urllib.parse.quote(model, safe=":.")
    return f"{base_url}/content-manager/collection-types/{encoded_model}"


def list_existing(base_url: str, model: str, token: str) -> list[dict]:
    response = http_json(f"{model_url(base_url, model)}?page=1&pageSize=100", token=token)
    return response.get("results", [])


def delete_existing(base_url: str, model: str, token: str) -> None:
    while True:
        existing = list_existing(base_url, model, token)
        if not existing:
            return
        for item in existing:
            http_json(f"{model_url(base_url, model)}/{item['id']}", method="DELETE", token=token)


def create_records(base_url: str, model: str, dataset: str, token: str) -> None:
    for record in load_dataset(dataset):
        http_json(
            model_url(base_url, model),
            method="POST",
            payload=transform_record(dataset, record),
            token=token,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("STRAPI_BASE_URL", "http://localhost:1340"))
    parser.add_argument("--skip-delete", action="store_true", help="Create records without removing existing entries first.")
    args = parser.parse_args()

    email = os.environ.get("SAAF_STRAPI_ADMIN_EMAIL") or os.environ.get("STRAPI_ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("SAAF_STRAPI_ADMIN_PASSWORD") or os.environ.get("STRAPI_ADMIN_PASSWORD", "ChangeMe123!")

    try:
        token = login(args.base_url, email, password)
        for dataset, model in DATASETS:
            if not args.skip_delete:
                delete_existing(args.base_url, model, token)
            create_records(args.base_url, model, dataset, token)
            print(f"Seeded {dataset}")
        return 0
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"Failed to seed Strapi: {exc}\n{details}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, KeyError) as exc:
        print(f"Failed to seed Strapi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
