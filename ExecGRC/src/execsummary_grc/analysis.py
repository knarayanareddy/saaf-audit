from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil, sqrt
from typing import Any

from .config import Settings
from .models import AnalysisResult, Control, Dataset, Finding, Risk


def analyze_dataset(dataset: Dataset, settings: Settings) -> AnalysisResult:
    controls_by_id = {_id_key(control.control_id): control for control in dataset.controls}
    risks_by_id = {_id_key(risk.risk_id): risk for risk in dataset.risks}

    weak_controls = [control for control in dataset.controls if is_weak_control(control, settings)]
    high_risks = [risk for risk in dataset.risks if risk_score(risk) >= settings.high_risk_threshold]
    critical_risks = [risk for risk in dataset.risks if risk_score(risk) >= settings.critical_risk_threshold]
    increasing_risks = [risk for risk in dataset.risks if _is_increasing(risk.trend)]

    findings: list[Finding] = []
    used_control_ids: set[str] = set()
    direct_correlations = 0
    contextual_correlations = 0

    for risk in sorted(high_risks, key=risk_score, reverse=True):
        direct_controls = _direct_controls_for_risk(risk, dataset.controls, controls_by_id)
        weak_direct_controls = [control for control in direct_controls if is_weak_control(control, settings)]
        contextual_controls = []
        confidence = "High"
        evidence_type = "direct"

        if weak_direct_controls:
            related_controls = weak_direct_controls
            direct_correlations += 1
        else:
            contextual_controls = _contextual_controls_for_risk(risk, weak_controls)
            related_controls = contextual_controls
            if contextual_controls:
                contextual_correlations += 1
                confidence = "Medium"
                evidence_type = "contextual"
            else:
                confidence = "Low"
                evidence_type = "unmapped"

        control_ids = [control.control_id for control in related_controls]
        used_control_ids.update(_id_key(control_id) for control_id in control_ids)
        finding_id = f"F-{len(findings) + 1:03d}"
        severity = _severity_for(risk, related_controls, settings)
        title = _finding_title(risk, related_controls, evidence_type)
        evidence = [
            f"Risk {risk.risk_id} residual score: {risk_score(risk):g}",
            f"Risk trend: {risk.trend or 'unknown'}",
        ]
        if related_controls:
            evidence.append(
                "Related weak controls: "
                + ", ".join(f"{control.control_id} ({control.effectiveness})" for control in related_controls)
            )
        else:
            evidence.append("No weak mapped control was identified in the uploaded dataset.")

        findings.append(
            Finding(
                finding_id=finding_id,
                title=title,
                severity=severity,
                confidence=confidence,
                theme=_theme_for(risk),
                risk_id=risk.risk_id,
                control_ids=control_ids,
                evidence=evidence,
                source_refs=_source_refs(risk, related_controls),
                recommendation=_recommendation_for(risk, related_controls, evidence_type),
            )
        )

    for control in weak_controls:
        if _id_key(control.control_id) in used_control_ids:
            continue
        linked_risks = [risks_by_id[_id_key(risk_id)] for risk_id in control.risk_ids if _id_key(risk_id) in risks_by_id]
        if any(risk_score(risk) >= settings.high_risk_threshold for risk in linked_risks):
            continue
        finding_id = f"F-{len(findings) + 1:03d}"
        findings.append(
            Finding(
                finding_id=finding_id,
                title=f"Weak control requires remediation: {control.name}",
                severity="Medium",
                confidence="High" if linked_risks else "Medium",
                theme=_theme_for(control),
                risk_id=", ".join(risk.risk_id for risk in linked_risks),
                control_ids=[control.control_id],
                evidence=[
                    f"Control {control.control_id} status: {control.effectiveness}",
                    "No linked high residual risk was detected above the configured threshold.",
                ],
                source_refs=[control.source.label] + [risk.source.label for risk in linked_risks],
                recommendation=(
                    f"Validate remediation plan and retest control {control.control_id}; "
                    "confirm whether risk mapping is complete."
                ),
            )
        )

    metrics = {
        "total_controls": len(dataset.controls),
        "total_risks": len(dataset.risks),
        "weak_controls": len(weak_controls),
        "high_risks": len(high_risks),
        "critical_risks": len(critical_risks),
        "increasing_risks": len(increasing_risks),
        "direct_correlations": direct_correlations,
        "contextual_correlations": contextual_correlations,
        "skipped_records": len(dataset.skipped_records),
        "controls_by_effectiveness": dict(Counter(control.effectiveness or "unknown" for control in dataset.controls)),
        "risks_by_rating": dict(Counter(risk_rating_label(risk, settings) for risk in dataset.risks)),
        "risk_matrix": _risk_matrix(dataset.risks),
        "process_effectiveness": _process_effectiveness(dataset.controls, dataset.risks, weak_controls, high_risks),
        "trend_counts": _trend_counts(dataset.risks),
        "trend_by_process": _trend_by_process(dataset.risks, high_risks),
        "risk_impact_by_process": _risk_impact_by_process(dataset.controls, dataset.risks, weak_controls),
        "source_files": dataset.source_files,
    }

    data_quality = _data_quality_notes(dataset)
    themes = _theme_summary(dataset.controls, dataset.risks, weak_controls, high_risks)
    traceability = _traceability(findings)
    posture = _overall_posture(dataset, findings, high_risks, weak_controls, settings)
    assumptions = [
        "Residual risk scores are interpreted on the configured score scale.",
        "Control-risk relationships are based on uploaded identifiers first and shared process or department second.",
        "Reports remain draft until a human reviewer validates the conclusions.",
    ]

    return AnalysisResult(
        posture=posture,
        metrics=metrics,
        findings=findings,
        themes=themes,
        data_quality=data_quality,
        traceability=traceability,
        assumptions=assumptions,
    )


def is_weak_control(control: Control, settings: Settings) -> bool:
    return _normalize(control.effectiveness) in settings.ineffective_statuses


def risk_score(risk: Risk) -> float:
    return risk.residual_score if risk.residual_score is not None else 0.0


def risk_rating_label(risk: Risk, settings: Settings) -> str:
    score = risk_score(risk)
    if score >= settings.critical_risk_threshold:
        return "Critical"
    if score >= settings.high_risk_threshold:
        return "High"
    if score >= settings.high_risk_threshold * 0.6:
        return "Medium"
    if score > 0:
        return "Low"
    return risk.rating or "Unknown"


def risk_matrix_position(risk: Risk) -> tuple[int, int]:
    if risk.impact is not None and risk.likelihood is not None:
        return _clamp_matrix_value(risk.impact), _clamp_matrix_value(risk.likelihood)
    score = risk_score(risk)
    if score <= 0:
        return 1, 1
    impact = _clamp_matrix_value(ceil(sqrt(score)))
    likelihood = _clamp_matrix_value(ceil(score / max(impact, 1)))
    return impact, likelihood


def _direct_controls_for_risk(
    risk: Risk, controls: list[Control], controls_by_id: dict[str, Control]
) -> list[Control]:
    related: dict[str, Control] = {}
    for control_id in risk.control_ids:
        control = controls_by_id.get(_id_key(control_id))
        if control:
            related[_id_key(control.control_id)] = control
    for control in controls:
        if _id_key(risk.risk_id) in {_id_key(risk_id) for risk_id in control.risk_ids}:
            related[_id_key(control.control_id)] = control
    return list(related.values())


def _contextual_controls_for_risk(risk: Risk, weak_controls: list[Control]) -> list[Control]:
    matches: list[Control] = []
    for control in weak_controls:
        if risk.process and _same(risk.process, control.process):
            matches.append(control)
        elif risk.department and _same(risk.department, control.department):
            matches.append(control)
        elif risk.framework and _same(risk.framework, control.framework):
            matches.append(control)
    return matches[:5]


def _severity_for(risk: Risk, controls: list[Control], settings: Settings) -> str:
    score = risk_score(risk)
    if score >= settings.critical_risk_threshold and controls:
        return "Critical"
    if score >= settings.critical_risk_threshold:
        return "High"
    if score >= settings.high_risk_threshold and controls:
        return "High"
    if score >= settings.high_risk_threshold:
        return "Medium"
    return "Low"


def _finding_title(risk: Risk, controls: list[Control], evidence_type: str) -> str:
    if controls and evidence_type == "direct":
        return f"High residual risk linked to weak controls: {risk.name}"
    if controls:
        return f"High residual risk contextually aligned with weak controls: {risk.name}"
    return f"High residual risk lacks effective control evidence: {risk.name}"


def _recommendation_for(risk: Risk, controls: list[Control], evidence_type: str) -> str:
    if controls:
        control_ids = ", ".join(control.control_id for control in controls)
        if evidence_type == "direct":
            return (
                f"Prioritize remediation and retesting for {control_ids}; confirm owner, due date "
                f"and residual risk acceptance for {risk.risk_id}."
            )
        return (
            f"Validate whether {control_ids} should be formally mapped to {risk.risk_id}; "
            "then remediate weak controls or document compensating controls."
        )
    return (
        f"Assign a control owner for {risk.risk_id}, map relevant controls and document residual risk treatment."
    )


def _source_refs(risk: Risk, controls: list[Control]) -> list[str]:
    refs = [risk.source.label]
    refs.extend(control.source.label for control in controls)
    return refs


def _traceability(findings: list[Finding]) -> list[dict[str, Any]]:
    return [
        {
            "finding_id": finding.finding_id,
            "risk_id": finding.risk_id,
            "control_ids": finding.control_ids,
            "source_refs": finding.source_refs,
            "confidence": finding.confidence,
        }
        for finding in findings
    ]


def _risk_matrix(risks: list[Risk]) -> list[dict[str, Any]]:
    cells: dict[tuple[int, int], dict[str, Any]] = {}
    for impact in range(1, 6):
        for likelihood in range(1, 6):
            cells[(impact, likelihood)] = {
                "impact": impact,
                "likelihood": likelihood,
                "count": 0,
                "risk_ids": [],
                "max_score": 0.0,
            }

    for risk in risks:
        impact, likelihood = risk_matrix_position(risk)
        cell = cells[(impact, likelihood)]
        cell["count"] += 1
        cell["risk_ids"].append(risk.risk_id)
        cell["max_score"] = max(cell["max_score"], risk_score(risk))

    return [cells[(impact, likelihood)] for impact in range(1, 6) for likelihood in range(1, 6)]


def _process_effectiveness(
    controls: list[Control], risks: list[Risk], weak_controls: list[Control], high_risks: list[Risk]
) -> list[dict[str, Any]]:
    processes = sorted({_theme_for(control) for control in controls} | {_theme_for(risk) for risk in risks})
    weak_ids = {_id_key(control.control_id) for control in weak_controls}
    high_risk_ids = {_id_key(risk.risk_id) for risk in high_risks}
    rows: list[dict[str, Any]] = []
    for process in processes:
        process_controls = [control for control in controls if _theme_for(control) == process]
        process_risks = [risk for risk in risks if _theme_for(risk) == process]
        weak_count = sum(1 for control in process_controls if _id_key(control.control_id) in weak_ids)
        high_count = sum(1 for risk in process_risks if _id_key(risk.risk_id) in high_risk_ids)
        effective_count = max(len(process_controls) - weak_count, 0)
        average_score = (
            sum(risk_score(risk) for risk in process_risks) / len(process_risks) if process_risks else 0.0
        )
        rows.append(
            {
                "process": process,
                "controls": len(process_controls),
                "effective_controls": effective_count,
                "weak_controls": weak_count,
                "effectiveness_ratio": effective_count / max(len(process_controls), 1),
                "risks": len(process_risks),
                "high_risks": high_count,
                "average_residual_score": round(average_score, 2),
            }
        )
    return sorted(rows, key=lambda row: (row["high_risks"], row["weak_controls"], row["average_residual_score"]), reverse=True)


def _trend_counts(risks: list[Risk]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for risk in risks:
        counter[_trend_label(risk.trend)] += 1
    return dict(counter)


def _trend_by_process(risks: list[Risk], high_risks: list[Risk]) -> list[dict[str, Any]]:
    high_ids = {_id_key(risk.risk_id) for risk in high_risks}
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for risk in risks:
        process = _theme_for(risk)
        grouped[process][_trend_label(risk.trend)] += 1
        if _id_key(risk.risk_id) in high_ids:
            grouped[process]["high_risks"] += 1
    rows = []
    for process, counts in grouped.items():
        rows.append(
            {
                "process": process,
                "increasing": counts.get("Increasing", 0),
                "stable": counts.get("Stable", 0),
                "decreasing": counts.get("Decreasing", 0),
                "unknown": counts.get("Unknown", 0),
                "high_risks": counts.get("high_risks", 0),
            }
        )
    return sorted(rows, key=lambda row: (row["increasing"], row["high_risks"]), reverse=True)


def _risk_impact_by_process(
    controls: list[Control], risks: list[Risk], weak_controls: list[Control]
) -> list[dict[str, Any]]:
    weak_by_process = Counter(_theme_for(control) for control in weak_controls)
    control_by_process = Counter(_theme_for(control) for control in controls)
    rows: list[dict[str, Any]] = []
    for process in sorted({_theme_for(risk) for risk in risks} | set(control_by_process)):
        process_risks = [risk for risk in risks if _theme_for(risk) == process]
        total_residual = sum(risk_score(risk) for risk in process_risks)
        max_residual = max([risk_score(risk) for risk in process_risks] or [0.0])
        weak_count = weak_by_process.get(process, 0)
        exposure = total_residual + (weak_count * 2)
        rows.append(
            {
                "process": process,
                "risk_count": len(process_risks),
                "total_residual_score": round(total_residual, 2),
                "max_residual_score": round(max_residual, 2),
                "weak_controls": weak_count,
                "control_count": control_by_process.get(process, 0),
                "exposure_index": round(exposure, 2),
            }
        )
    return sorted(rows, key=lambda row: row["exposure_index"], reverse=True)


def _theme_summary(
    controls: list[Control], risks: list[Risk], weak_controls: list[Control], high_risks: list[Risk]
) -> list[dict[str, Any]]:
    by_theme: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"theme": "", "controls": 0, "weak_controls": 0, "risks": 0, "high_risks": 0, "max_score": 0.0}
    )
    for control in controls:
        theme = _theme_for(control)
        by_theme[theme]["theme"] = theme
        by_theme[theme]["controls"] += 1
    for control in weak_controls:
        theme = _theme_for(control)
        by_theme[theme]["theme"] = theme
        by_theme[theme]["weak_controls"] += 1
    for risk in risks:
        theme = _theme_for(risk)
        by_theme[theme]["theme"] = theme
        by_theme[theme]["risks"] += 1
        by_theme[theme]["max_score"] = max(by_theme[theme]["max_score"], risk_score(risk))
    for risk in high_risks:
        theme = _theme_for(risk)
        by_theme[theme]["theme"] = theme
        by_theme[theme]["high_risks"] += 1

    return sorted(
        by_theme.values(),
        key=lambda item: (item["high_risks"], item["weak_controls"], item["max_score"]),
        reverse=True,
    )[:10]


def _data_quality_notes(dataset: Dataset) -> list[str]:
    notes: list[str] = []
    if not dataset.controls:
        notes.append("No controls were detected in the uploaded data.")
    if not dataset.risks:
        notes.append("No risks were detected in the uploaded data.")
    if dataset.skipped_records:
        notes.append(f"{len(dataset.skipped_records)} records were skipped because their type could not be inferred.")

    risks_without_score = [risk.risk_id for risk in dataset.risks if risk.residual_score is None and not risk.rating]
    if risks_without_score:
        notes.append("Risks without residual score or rating: " + ", ".join(risks_without_score[:10]))

    unmapped_risks = [risk.risk_id for risk in dataset.risks if not risk.control_ids]
    if unmapped_risks:
        notes.append("Risks without mapped controls: " + ", ".join(unmapped_risks[:10]))

    unmapped_controls = [control.control_id for control in dataset.controls if not control.risk_ids]
    if unmapped_controls:
        notes.append("Controls without mapped risks: " + ", ".join(unmapped_controls[:10]))

    missing_owners = [
        item_id
        for item_id, owner in [(control.control_id, control.owner) for control in dataset.controls]
        + [(risk.risk_id, risk.owner) for risk in dataset.risks]
        if not owner
    ]
    if missing_owners:
        notes.append("Records without owner: " + ", ".join(missing_owners[:10]))

    return notes or ["No material data quality issues detected in the uploaded structure."]


def _overall_posture(
    dataset: Dataset,
    findings: list[Finding],
    high_risks: list[Risk],
    weak_controls: list[Control],
    settings: Settings,
) -> str:
    if not dataset.risks and not dataset.controls:
        return "Unknown"

    critical_findings = [finding for finding in findings if finding.severity == "Critical"]
    risk_ratio = len(high_risks) / max(len(dataset.risks), 1)
    weak_ratio = len(weak_controls) / max(len(dataset.controls), 1)

    if critical_findings or any(risk_score(risk) >= settings.critical_risk_threshold for risk in high_risks):
        return "Critical"
    if risk_ratio >= 0.35 or weak_ratio >= 0.30:
        return "Elevated"
    if high_risks or weak_controls:
        return "Moderate"
    return "Stable"


def _theme_for(item: Control | Risk) -> str:
    return item.process or item.department or item.framework or "Unmapped"


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _same(left: str, right: str) -> bool:
    return _normalize(left) == _normalize(right)


def _id_key(value: str) -> str:
    return value.strip().upper()


def _is_increasing(value: str) -> bool:
    normalized = _normalize(value)
    return normalized in {"increasing", "stijgend", "rising"} or "increase" in normalized


def _trend_label(value: str) -> str:
    normalized = _normalize(value)
    if normalized in {"increasing", "stijgend", "rising"} or "increase" in normalized:
        return "Increasing"
    if normalized in {"decreasing", "dalend", "falling"} or "decrease" in normalized:
        return "Decreasing"
    if normalized in {"stable", "unchanged", "gelijkblijvend"}:
        return "Stable"
    return "Unknown"


def _clamp_matrix_value(value: float) -> int:
    return min(5, max(1, int(round(value))))
