from typing import Literal
from pydantic import BaseModel, model_validator


VALID_SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]
VALID_STATUSES = ["Compliant", "Gap", "Partial", "Not Applicable"]

SEVERITY_ALIASES = {
    "informational": "Info",
    "information": "Info",
    "none": "Info",
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "info": "Info",
    "minor": "Low",
    "major": "High",
    "severe": "Critical",
}

STATUS_ALIASES = {
    "compliant": "Compliant",
    "gap": "Gap",
    "partial": "Partial",
    "partially compliant": "Partial",
    "partially met": "Partial",
    "not applicable": "Not Applicable",
    "not assessed": "Not Applicable",
    "n/a": "Not Applicable",
    "na": "Not Applicable",
    "met": "Compliant",
    "fully compliant": "Compliant",
    "non-compliant": "Gap",
    "noncompliant": "Gap",
    "not compliant": "Gap",
    "missing": "Gap",
    "absent": "Gap",
    "not met": "Gap",
    "not provided": "Gap",
    "in progress": "Partial",
    "requires monitoring": "Partial",
    "requires improvement": "Partial",
    "needs improvement": "Partial",
    "observation": "Partial",
    "planned": "Partial",
    "under review": "Partial",
}


# Fail-safe fallbacks for values the model returns that we don't recognise.
# An auditor must never under-report, so unknown values map to the worst case
# and the finding is flagged for human review in its evidence text.
UNKNOWN_STATUS_FALLBACK = "Gap"
UNKNOWN_SEVERITY_FALLBACK = "High"
REVIEW_FLAG = "[HUMAN REVIEW REQUIRED]"


def _normalize_severity(v: str) -> str | None:
    """Map a raw severity to a valid value, or None if unrecognised."""
    return SEVERITY_ALIASES.get(v.lower().strip())


def _normalize_status(v: str) -> str | None:
    """Map a raw status to a valid value, or None if unrecognised."""
    return STATUS_ALIASES.get(v.lower().strip())


class Finding(BaseModel):
    framework: str
    control_id: str
    control_name: str
    status: Literal["Compliant", "Gap", "Partial", "Not Applicable"]
    severity: Literal["Critical", "High", "Medium", "Low", "Info"]
    evidence: str
    recommendation: str

    @model_validator(mode="before")
    @classmethod
    def normalize_status_and_severity(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        notes = []
        for field, normalize, fallback in (
            ("status", _normalize_status, UNKNOWN_STATUS_FALLBACK),
            ("severity", _normalize_severity, UNKNOWN_SEVERITY_FALLBACK),
        ):
            raw = data.get(field)
            if not isinstance(raw, str):
                continue  # missing or non-string: let type validation reject it
            normalized = normalize(raw)
            if normalized is None:
                notes.append(f"unrecognised {field} {raw!r} treated as {fallback}")
                normalized = fallback
            data[field] = normalized
        if notes:
            data["evidence"] = f"{data.get('evidence', '')} {REVIEW_FLAG} {'; '.join(notes)}.".strip()
        return data


class VendorProfile(BaseModel):
    name: str
    sector: str
    services: list[str]
    processes_personal_data: bool
    is_ai_system: bool
    is_dutch_government_vendor: bool
    applicable_frameworks: list[str]
