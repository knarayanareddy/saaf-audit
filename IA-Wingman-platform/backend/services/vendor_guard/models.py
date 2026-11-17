"""Finding model for Vendor Guard, with deterministic status/severity normalisation."""

from typing import Literal

from pydantic import BaseModel, field_validator

VALID_SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]
VALID_STATUSES = ["Compliant", "Gap", "Partial", "Not Applicable"]

SEVERITY_ALIASES = {
    "informational": "Info", "information": "Info", "none": "Info",
    "critical": "Critical", "high": "High", "medium": "Medium", "moderate": "Medium",
    "low": "Low", "info": "Info", "minor": "Low", "major": "High", "severe": "Critical",
}

STATUS_ALIASES = {
    "compliant": "Compliant", "gap": "Gap", "partial": "Partial",
    "partially compliant": "Partial", "partially met": "Partial",
    "not applicable": "Not Applicable", "not assessed": "Not Applicable",
    "n/a": "Not Applicable", "na": "Not Applicable",
    "met": "Compliant", "fully compliant": "Compliant",
    "non-compliant": "Gap", "noncompliant": "Gap", "not compliant": "Gap",
    "missing": "Gap", "absent": "Gap", "not met": "Gap", "not provided": "Gap",
    "in progress": "Partial", "requires monitoring": "Partial",
    "requires improvement": "Partial", "needs improvement": "Partial",
    "observation": "Partial", "planned": "Partial", "under review": "Partial",
}


def normalize_severity(v: str) -> str:
    key = str(v).lower().strip()
    if key in SEVERITY_ALIASES:
        return SEVERITY_ALIASES[key]
    if v in VALID_SEVERITIES:
        return v
    return "Medium"


def normalize_status(v: str) -> str:
    key = str(v).lower().strip()
    if key in STATUS_ALIASES:
        return STATUS_ALIASES[key]
    if v in VALID_STATUSES:
        return v
    return "Partial"


class Finding(BaseModel):
    framework: str
    control_id: str
    control_name: str
    status: Literal["Compliant", "Gap", "Partial", "Not Applicable"]
    severity: Literal["Critical", "High", "Medium", "Low", "Info"]
    evidence: str
    recommendation: str

    @field_validator("severity", mode="before")
    @classmethod
    def _norm_sev(cls, v: str) -> str:
        return normalize_severity(v)

    @field_validator("status", mode="before")
    @classmethod
    def _norm_stat(cls, v: str) -> str:
        return normalize_status(v)
