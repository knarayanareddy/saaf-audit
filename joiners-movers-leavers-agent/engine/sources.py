"""Load the sources the agent reads: HR, directory accounts, entitlements, Jira tickets and policy.

Every row keeps a reference to where it came from (file name and line number), so
each exception can point back to the exact source record.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from engine.access_review import load_file

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parents[1]
DEFAULT_SOURCES = REPO_ROOT / "sources.sample.yaml"

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "hr": ["username", "full_name", "department", "role", "status", "start_date", "transfer_date",
           "previous_role", "termination_date"],
    "accounts": ["username", "department", "access_role", "enabled", "last_login"],
    "entitlements": ["username", "entitlement", "granted_date", "removed_date"],
    "tickets": ["ticket_id", "issue_type", "status", "subject_username", "system", "requested_access",
                "reporter", "approver", "approved_at"],
}


@dataclass
class SourceFile:
    """One loaded export, with the metadata the UI and the audit trail need."""

    key: str
    label: str
    path: Path
    df: pd.DataFrame
    sha256: str
    kind: str

    @property
    def rows(self) -> list[dict]:
        """Rows as plain dicts with empty strings instead of NaN, plus a source reference."""
        records = self.df.fillna("").to_dict("records")
        for i, r in enumerate(records):
            r["_ref"] = f"{self.path.name}:{i + 2}"  # line 1 is the header
        return records

    def summary(self) -> dict:
        return {"key": self.key, "label": self.label, "file": self.path.name, "rows": len(self.df),
                "sha256": self.sha256, "kind": self.kind}


@dataclass
class Sources:
    """All inputs for one review."""

    name: str
    config_path: Path
    hr: SourceFile
    accounts: SourceFile
    systems: list[dict]  # each: name, label, type, file (SourceFile)
    tickets: SourceFile
    policy: dict
    policy_path: Path
    policy_sha256: str
    extra: dict = field(default_factory=dict)

    def files(self) -> list[SourceFile]:
        return [self.hr, self.accounts, *[s["file"] for s in self.systems], self.tickets]

    def summaries(self) -> list[dict]:
        out = [f.summary() for f in self.files()]
        out.append({"key": "policy", "label": "Access policy and role model", "file": self.policy_path.name,
                    "rows": len(self.policy.get("role_matrix", {})), "sha256": self.policy_sha256,
                    "kind": "policy"})
        return out

    def fingerprint(self) -> str:
        """One hash over all inputs, so a prepared result can be matched to its exact data set."""
        h = hashlib.sha256()
        for s in self.summaries():
            h.update(s["sha256"].encode())
        return h.hexdigest()[:16]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_columns(df: pd.DataFrame, kind: str, path: Path) -> None:
    missing = [c for c in REQUIRED_COLUMNS[kind] if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} is missing required columns for {kind}: {', '.join(missing)}")


def _load(key: str, label: str, path: Path, kind: str) -> SourceFile:
    df = load_file(path)
    _check_columns(df, kind, path)
    log.info("Loaded %s (%d rows) from %s", label, len(df), path)
    return SourceFile(key=key, label=label, path=path, df=df, sha256=_sha256(path), kind=kind)


def load_sources(config_path: Optional[Path] = None) -> Sources:
    """Read a sources YAML file and load every export it names."""
    config_path = Path(config_path or DEFAULT_SOURCES).resolve()
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    base = config_path.parent

    def p(rel: str) -> Path:
        path = (base / rel).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        return path

    hr = _load("hr", "HR employee master data", p(cfg["hr"]), "hr")
    directory = cfg["directory"]
    accounts = _load("accounts", directory.get("label", "Directory accounts"), p(directory["accounts"]), "accounts")
    systems = []
    for s in cfg["systems"]:
        f = _load(f"system:{s['name']}", s.get("label", s["name"]), p(s["entitlements"]), "entitlements")
        systems.append({"name": s["name"], "label": s.get("label", s["name"]), "type": s.get("type", "application"),
                        "file": f})
    tickets_cfg = cfg["tickets"]
    tickets = _load("tickets", tickets_cfg.get("label", "Access request tickets"), p(tickets_cfg["file"]), "tickets")
    policy_path = p(cfg["policy"])
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    for key in ("audit_period", "extraction_date", "role_matrix", "sod_rules"):
        if key not in policy:
            raise ValueError(f"{policy_path.name} is missing '{key}'")

    return Sources(name=cfg.get("name", config_path.stem), config_path=config_path, hr=hr, accounts=accounts,
                   systems=systems, tickets=tickets, policy=policy, policy_path=policy_path,
                   policy_sha256=_sha256(policy_path))
