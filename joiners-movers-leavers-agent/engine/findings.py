"""Findings: a deterministic draft, and validation of any draft (model or not).

Findings follow the SAAF finding schema (schemas/finding-schema.json, copied from
SAAF-Project/outputs/schemas). Validation is deterministic: a finding that cites a
record that was not in the input is rejected, never silently kept.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "finding-schema.json"
FINDING_SCHEMA: dict = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
FINDING_FIELDS = set(FINDING_SCHEMA["properties"])
RISK_ORDER = ["High", "Medium", "Low", "Informational"]
ID_PATTERN = re.compile(FINDING_SCHEMA["properties"]["id"]["pattern"])
REF_IN_TEXT = re.compile(r"\b(?:EX-\d{2,}|[A-Z][A-Z0-9]{1,9}-\d{3,})\b")

LIFECYCLE_TEXT = {
    "joiner": {
        "title": "Access for joiners is not consistently backed by specific, independently approved requests",
        "control_objective": "Access is granted only on an approved request that names the access, approved by "
                             "someone other than the requester, before provisioning (ISO/IEC 27001:2022 A.5.18, "
                             "SOC 2 CC6.2).",
        "root_cause": "To be confirmed with management: provisioning does not appear to check for an approved, "
                      "specific ticket before access is granted.",
        "impact": "Users can obtain access, including privileged access, that nobody authorised.",
        "recommendation": "Block provisioning until an approved ticket that names each role or group exists, require "
                          "an approver other than the requester, and review the listed accounts.",
    },
    "mover": {
        "title": "Access from previous roles is not removed when employees change roles",
        "control_objective": "Access is adjusted when a user changes role, and no user holds conflicting rights "
                             "(ISO/IEC 27001:2022 A.5.18 and A.5.3, SOC 2 CC6.3).",
        "root_cause": "To be confirmed with management: transfers trigger new access requests, but no removal of "
                      "the previous role's access.",
        "impact": "Access accumulates over time and can create segregation of duties conflicts.",
        "recommendation": "Make removal of previous-role access part of every transfer, re-check SoD rules on each "
                          "change, and remediate the listed users.",
    },
    "leaver": {
        "title": "Leaver access is not removed completely and on time",
        "control_objective": "All access of leavers is removed on the last working day "
                             "(ISO/IEC 27001:2022 A.5.18, SOC 2 CC6.2).",
        "root_cause": "To be confirmed with management: offboarding relies on manual steps per system and is not "
                      "monitored against the SLA.",
        "impact": "Former employees can keep, and use, access to systems and data after leaving.",
        "recommendation": "Disable directory accounts and application roles automatically from the HR termination "
                          "date, monitor the SLA, and investigate the post-termination login.",
    },
    "baseline": {
        "title": "Directory accounts exist that are not linked to HR or not in use",
        "control_objective": "Every account belongs to a known person and is in use "
                             "(ISO/IEC 27001:2022 A.5.18).",
        "root_cause": "To be confirmed with management: no periodic reconciliation of the directory against HR.",
        "impact": "Unowned or dormant accounts increase the risk of misuse.",
        "recommendation": "Assign an owner to each account or disable it, and reconcile the directory against HR "
                          "each quarter.",
    },
}


def _max_risk(risks: list[str]) -> str:
    return min(risks, key=RISK_ORDER.index) if risks else "Informational"


def deterministic_findings(review: dict, lifecycle_of: dict[str, str]) -> list[dict]:
    """One finding per lifecycle with exceptions. Used when no model draft is available."""
    findings = []
    n = 0
    for lc in ("joiner", "mover", "leaver", "baseline"):
        exc = [e for e in review["exceptions"] if lifecycle_of.get(e["test_id"]) == lc]
        if not exc:
            continue
        n += 1
        text = LIFECYCLE_TEXT[lc]
        lines = [f"{e['id']} ({e['test_id']}, {e['risk_rating']}): {e['summary']}" for e in exc]
        tickets = sorted({t for e in exc for t in e["tickets"]})
        findings.append({
            "id": f"F-{n:02d}",
            "title": text["title"][:100],
            "risk_rating": _max_risk([e["risk_rating"] for e in exc]),
            "control_objective": text["control_objective"],
            "observation": f"{len(exc)} exception(s) in the period {review['audit_period']['start']} to "
                           f"{review['audit_period']['end']}:\n" + "\n".join(lines),
            "root_cause": text["root_cause"],
            "impact": text["impact"],
            "recommendation": text["recommendation"],
            "status": "Open",
            "ai_assisted": False,
            "evidence_references": [e["id"] for e in exc] + tickets,
        })
    return findings


def deterministic_assessments(review: dict) -> list[dict]:
    return [{"exception_id": e["id"], "conclusion": "Confirmed exception",
             "rationale": "Deterministic test result; not yet assessed by a model or an auditor.",
             "follow_up": "Auditor to confirm with the system owner."} for e in review["exceptions"]]


def validate_draft(draft: dict, allowed: set[str], exception_ids: list[str]) -> dict:
    """Check a draft against the finding schema and the input. Returns the cleaned draft and the checks."""
    issues: list[str] = []
    kept: list[dict] = []
    seen_ids: set[str] = set()
    for f in draft.get("findings", []):
        fid = str(f.get("id", "?"))
        problems = []
        for req in FINDING_SCHEMA["required"]:
            if not str(f.get(req, "")).strip():
                problems.append(f"missing {req}")
        extra = set(f) - FINDING_FIELDS
        if extra:
            problems.append(f"fields outside the schema: {', '.join(sorted(extra))}")
        if not ID_PATTERN.match(fid) or fid in seen_ids:
            problems.append("invalid or duplicate id")
        if f.get("risk_rating") not in RISK_ORDER:
            problems.append("invalid risk_rating")
        if len(str(f.get("title", ""))) > FINDING_SCHEMA["properties"]["title"]["maxLength"]:
            problems.append("title longer than 100 characters")
        refs = f.get("evidence_references") or []
        if not refs:
            problems.append("no evidence references")
        unknown = [r for r in refs if r not in allowed]
        if unknown:
            problems.append(f"cites records that were not in the input: {', '.join(unknown)}")
        text = " ".join(str(f.get(k, "")) for k in ("title", "observation", "root_cause", "impact", "recommendation"))
        unknown_text = sorted({m for m in REF_IN_TEXT.findall(text) if m not in allowed})
        if unknown_text:
            problems.append(f"mentions identifiers that were not in the input: {', '.join(unknown_text)}")
        if problems:
            issues.append(f"{fid} rejected: " + "; ".join(problems))
            continue
        seen_ids.add(fid)
        kept.append(f)

    assessments = [a for a in draft.get("assessments", []) if a.get("exception_id") in exception_ids]
    assessed = {a["exception_id"] for a in assessments}
    not_assessed = [x for x in exception_ids if x not in assessed]
    if not_assessed:
        issues.append("exceptions without an assessment: " + ", ".join(not_assessed))
    cited = {r for f in kept for r in f.get("evidence_references", [])}
    not_covered = [x for x in exception_ids if x not in cited]
    if not_covered:
        issues.append("exceptions not covered by any finding: " + ", ".join(not_covered))

    rejected = len(draft.get("findings", [])) - len(kept)
    return {
        "draft": {**draft, "findings": kept, "assessments": assessments},
        "checks": {
            "findings_received": len(draft.get("findings", [])),
            "findings_kept": len(kept),
            "findings_rejected": rejected,
            "exceptions_assessed": len(assessed),
            "exceptions_covered": len(exception_ids) - len(not_covered),
            "exceptions_total": len(exception_ids),
            "passed": not issues,
            "issues": issues,
        },
    }
