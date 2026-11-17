"""Pseudonymise a review before any of it leaves the deterministic engine.

The model only sees USER-NNN references. Names and usernames are replaced in
structured fields and in free text (ticket summaries and descriptions). The
mapping back to real identities stays local and is used only to display results
to the auditor.
"""

from __future__ import annotations

import json
import re
from typing import Any

PERSON_FIELDS = {"username", "manager_username", "reporter", "approver", "subject_username"}


class Pseudonymiser:
    def __init__(self, anon_map: dict[str, str], people: dict[str, str]):
        self.anon_map = anon_map
        self.reveal_map = {v: k for k, v in anon_map.items()}
        self.people = people  # username -> full name
        pairs: list[tuple[str, str]] = []
        first_names: dict[str, list[str]] = {}
        for key, ref in anon_map.items():
            full = people.get(key, "")
            if full and full != key:
                pairs.append((full, ref))
                first = full.split()[0]
                if len(first) >= 3:
                    first_names.setdefault(first, []).append(ref)
            pairs.append((key, ref))
        # Unique first names are replaced too; ambiguous ones would point at the wrong person.
        for first, refs in first_names.items():
            if len(refs) == 1:
                pairs.append((first, refs[0]))
        pairs.sort(key=lambda p: -len(p[0]))  # longest first: "Bas Groen" before "Bas"
        self._patterns = [(re.compile(r"(?<![\w.])" + re.escape(a) + r"(?![\w])", re.IGNORECASE), b) for a, b in pairs]

    def text(self, value: str) -> str:
        out = str(value)
        for pat, ref in self._patterns:
            out = pat.sub(ref, out)
        return out

    def value(self, key: str, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: self.value(k, v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.value(key, v) for v in value]
        if isinstance(value, str):
            if key in PERSON_FIELDS:
                return self.anon_map.get(value.strip().lower(), self.text(value))
            return self.text(value)
        return value

    def reveal(self, text: str) -> str:
        """Replace USER-NNN with 'Full Name (USER-NNN)' for local display."""
        def sub(m: re.Match) -> str:
            ref = m.group(0)
            key = self.reveal_map.get(ref)
            return f"{self.people.get(key, key)} ({ref})" if key else ref
        return re.sub(r"USER-\d{3}", sub, str(text))


def build_payload(review: dict, pz: Pseudonymiser) -> dict:
    """The exact input the model receives: exceptions, evidence and test context, no identities."""
    exceptions = []
    for e in review["exceptions"]:
        exceptions.append({
            "exception_id": e["id"],
            "test_id": e["test_id"],
            "risk_rating": e["risk_rating"],
            "user_ref": e["user_ref"],
            "user_lifecycle": e["user_lifecycle"],
            "summary": pz.text(e["summary"]),
            "entitlements": [{k: v for k, v in x.items() if k != "ref"} for x in e["entitlements"]],
            "tickets": e["tickets"],
            "evidence": [pz.value("evidence", ev) for ev in e["evidence"]],
            "facts": e.get("facts", {}),
        })
    tests = [{k: t[k] for k in ("id", "lifecycle", "name", "control", "control_refs", "tested", "exceptions",
                                "exception_ids")} for t in review["tests"]]
    return {
        "review": {
            "organisation": review["organisation"],
            "audit_period": review["audit_period"],
            "extraction_date": review["extraction_date"],
            "policy": review["policy"],
            "population": {k: (len(v) if isinstance(v, list) else v) for k, v in review["population"].items()},
        },
        "tests": tests,
        "exceptions": exceptions,
    }


def allowed_references(payload: dict) -> set[str]:
    """Every identifier the model may cite: exception ids, ticket ids, source row refs, SoD rules, users."""
    refs: set[str] = set()
    for e in payload["exceptions"]:
        refs.add(e["exception_id"])
        refs.add(e["user_ref"])
        refs.update(e["tickets"])
        for ev in e["evidence"]:
            refs.add(ev["ref"])
            if ev.get("ticket_id"):
                refs.add(ev["ticket_id"])
    for t in payload["tests"]:
        refs.add(t["id"])
    for rule in payload["review"]["policy"].get("sod_rules", []):
        refs.add(rule["rule_id"])
    # Reporters, approvers and managers appear as USER-NNN inside the evidence fields.
    refs.update(re.findall(r"USER-\d{3}", json.dumps(payload)))
    return refs
