"""Structural quality gate for every hand-off between sub-agents.

Deliberately dependency-free (pure Python, no ``jsonschema``) so the package
runs on system Python without a ``pip install`` step, per the repo guardrails.
Each validator returns a list of human-readable error strings; an empty list
means the document passed the gate.
"""

from typing import Any, Dict, List

_RATINGS = {"High", "Medium", "Low"}


def _require_keys(obj: Dict[str, Any], keys: List[str], where: str) -> List[str]:
    """Return an error per missing key in ``obj``."""
    return [f"{where}: missing required key '{k}'" for k in keys if k not in obj]


def validate_rcm(doc: Dict[str, Any]) -> List[str]:
    """Validate a UC7 RCM document."""
    errors: List[str] = []
    rows = doc.get("rcm")
    if not isinstance(rows, list) or not rows:
        return ["rcm: expected a non-empty list under key 'rcm'"]

    required = [
        "risk_id",
        "sub_process",
        "business_objective",
        "risk_description",
        "control_id",
        "control_description",
        "control_type",
        "inherent_risk",
        "residual_risk",
    ]
    for i, row in enumerate(rows):
        where = f"rcm[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{where}: expected an object")
            continue
        errors.extend(_require_keys(row, required, where))
        if row.get("control_type") not in {"Manual", "Automated", None}:
            errors.append(f"{where}: control_type must be 'Manual' or 'Automated'")
        for band in ("inherent_risk", "residual_risk"):
            score = row.get(band)
            if isinstance(score, dict) and score.get("rating") not in _RATINGS:
                errors.append(f"{where}.{band}: rating must be one of {sorted(_RATINGS)}")
    return errors


def validate_work_program(doc: Dict[str, Any]) -> List[str]:
    """Validate a UC8 Work Program document."""
    errors: List[str] = []
    tasks = doc.get("work_program")
    if not isinstance(tasks, list) or not tasks:
        return ["work_program: expected a non-empty list under key 'work_program'"]

    required = [
        "task_id",
        "control_id",
        "test_type",
        "objective",
        "procedure",
        "methodology",
        "assigned_to",
        "estimated_hours",
    ]
    for i, task in enumerate(tasks):
        where = f"work_program[{i}]"
        if not isinstance(task, dict):
            errors.append(f"{where}: expected an object")
            continue
        errors.extend(_require_keys(task, required, where))
        if task.get("test_type") not in {"ToD", "ToE", None}:
            errors.append(f"{where}: test_type must be 'ToD' or 'ToE'")
        hours = task.get("estimated_hours")
        if hours is not None and not isinstance(hours, (int, float)):
            errors.append(f"{where}: estimated_hours must be a number")

    report = doc.get("resource_report")
    if not isinstance(report, dict):
        errors.append("resource_report: expected an object")
    else:
        errors.extend(
            _require_keys(report, ["total_hours_required", "available_hours"], "resource_report")
        )
    return errors


def validate_quality(doc: Dict[str, Any]) -> List[str]:
    """Validate a UC9 Quality & Resource Guard verdict."""
    errors: List[str] = []
    verdict = doc.get("verdict")
    if verdict not in {"Go", "No-Go"}:
        errors.append("quality: verdict must be 'Go' or 'No-Go'")
    if not isinstance(doc.get("gaps", []), list):
        errors.append("quality: gaps must be a list")
    if verdict == "No-Go" and not doc.get("gaps"):
        errors.append("quality: a No-Go verdict must list at least one gap")
    return errors


# Maps a sub-agent tool name to the validator that gates its output.
VALIDATORS = {
    "run_rcm_builder": validate_rcm,
    "run_work_program": validate_work_program,
    "run_quality_guard": validate_quality,
}


def validate(tool_name: str, doc: Dict[str, Any]) -> List[str]:
    """Run the gate for ``tool_name``; unknown tools pass with no error."""
    validator = VALIDATORS.get(tool_name)
    return validator(doc) if validator else []
