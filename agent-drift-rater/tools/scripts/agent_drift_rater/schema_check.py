"""Stdlib validator for outputs/schemas/finding-schema.json.

Deliberately avoids `jsonschema` — the SAAF guardrails forbid runtime `pip install`, and the
existing orchestrator validates with pure Python for the same reason. Returns a list of error
strings; an empty list means the document conforms.
"""

import re
from typing import Any, Dict, List

REQUIRED = ["id", "title", "risk_rating", "observation", "recommendation"]
ALLOWED = set(REQUIRED) | {
    "control_objective", "root_cause", "impact", "management_response", "target_date",
    "owner", "status", "ai_assisted", "evidence_references",
}
ID_RE = re.compile(r"^F-[0-9]{2,4}$")
RATINGS = {"High", "Medium", "Low", "Informational"}
STATUSES = {"Open", "In Progress", "Closed"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_finding(finding: Dict[str, Any], where: str = "finding") -> List[str]:
    errors: List[str] = []
    if not isinstance(finding, dict):
        return [f"{where}: not an object"]
    for key in REQUIRED:
        if key not in finding:
            errors.append(f"{where}: missing required '{key}'")
    for key in finding:
        if key not in ALLOWED:
            errors.append(f"{where}: unexpected property '{key}' (additionalProperties: false)")
    if "id" in finding and not ID_RE.match(str(finding["id"])):
        errors.append(f"{where}: id '{finding['id']}' does not match ^F-[0-9]{{2,4}}$")
    if "title" in finding and len(str(finding["title"])) > 100:
        errors.append(f"{where}: title exceeds maxLength 100")
    if "risk_rating" in finding and finding["risk_rating"] not in RATINGS:
        errors.append(f"{where}: risk_rating '{finding['risk_rating']}' not in {sorted(RATINGS)}")
    if "status" in finding and finding["status"] not in STATUSES:
        errors.append(f"{where}: status '{finding['status']}' not in {sorted(STATUSES)}")
    if "ai_assisted" in finding and not isinstance(finding["ai_assisted"], bool):
        errors.append(f"{where}: ai_assisted must be boolean")
    if "target_date" in finding and not DATE_RE.match(str(finding["target_date"])):
        errors.append(f"{where}: target_date must be YYYY-MM-DD")
    if "evidence_references" in finding and not isinstance(finding["evidence_references"], list):
        errors.append(f"{where}: evidence_references must be an array")
    return errors


def validate_findings(findings: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    for i, finding in enumerate(findings):
        errors.extend(validate_finding(finding, f"finding[{i}]"))
    return errors
