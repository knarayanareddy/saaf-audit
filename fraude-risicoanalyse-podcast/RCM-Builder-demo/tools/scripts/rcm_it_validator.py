"""
RCM IT Validator — Stage 3
Assesses IT dependency types, IPE validation, control reliability, and
recalculates final residual risk. Can also introduce UC6-derived IT risks.
"""

from __future__ import annotations

from typing import Any

_RELIABILITY_REDUCTION = {
    "Reliable": 0.60,
    "Partially Reliable": 0.35,
    "Unreliable": 0.15,
    "Not Assessed": 0.00,
}

_DESIGN_REDUCTION = {"Strong": 0.60, "Moderate": 0.35, "Weak": 0.15, None: 0.00}


def _get_risk_rating(score: float) -> str:
    if score <= 9:
        return "Low"
    if score <= 15:
        return "Medium"
    return "High"


def assess_it_dependency(matrix_entry: dict | None) -> dict:
    if matrix_entry is None:
        return {
            "itgc_dependency_type": [],
            "ipe_validation_level": "N/A",
            "system_name": "",
            "report_name": "",
        }

    ipe_details = matrix_entry.get("ipe_details", {})
    ipe_validation_level = ipe_details.get("ipe_reliability") or evaluate_ipe_reliability(ipe_details)
    return {
        "itgc_dependency_type": matrix_entry.get("itgc_dependency_types", []),
        "ipe_validation_level": ipe_validation_level,
        "system_name": matrix_entry.get("system_name", ""),
        "report_name": ipe_details.get("report_name", ""),
    }


def evaluate_ipe_reliability(ipe_details: dict) -> str:
    if not ipe_details.get("system_generated", False):
        return "None"

    editable = ipe_details.get("editable_after_export", False)
    reconciliation = ipe_details.get("reconciliation_exists", False)
    if not editable and reconciliation:
        return "Strong"
    if editable and not reconciliation:
        return "Weak"
    return "Moderate"


def derive_control_reliability(
    control: dict,
    ipe_validation_level: str,
    return_downgrade: bool = False,
) -> str | tuple[str, bool]:
    downgraded = False

    if ipe_validation_level in ("Weak", "None"):
        reliability = "Unreliable"
        downgraded = True
    elif control.get("significance") == "Non-Key":
        reliability = "Unreliable"
    elif (
        control.get("significance") == "Key"
        and control.get("nature") == "Preventive"
        and control.get("control_design_effectiveness") == "Strong"
    ):
        reliability = "Reliable"
    else:
        reliability = "Partially Reliable"

    if return_downgrade:
        return reliability, downgraded
    return reliability


def _describe_itgc_control(dep_types: list[str], system_name: str, report_name: str) -> str:
    focus = ", ".join(dep_types) if dep_types else "ITGC"
    if report_name:
        return f"Implement and evidence {focus} controls over {system_name or 'the supporting system'} and validate the IPE '{report_name}'."
    return f"Implement and evidence {focus} controls over {system_name or 'the supporting system'} supporting this control."


def _build_new_risk_description(assessment: dict) -> str:
    if assessment["control_reliability"] == "Not Assessed":
        return (
            "UC6 identified an unassessed IT dependency: the underlying system or report "
            "supporting this control has not been validated for ITGC and IPE reliability."
        )
    if assessment["ipe_validation_level"] in ("Weak", "None"):
        return (
            f"UC6 identified an IPE reliability risk over '{assessment.get('report_name') or 'the supporting report'}' "
            "that may undermine reliance on the control."
        )
    return (
        f"UC6 identified a residual IT control risk over {assessment.get('system_name') or 'the supporting system'} "
        "requiring additional ITGC coverage."
    )


def _non_it_assessment(control: dict) -> dict:
    mapping = {
        "Strong": "Reliable",
        "Moderate": "Partially Reliable",
        "Weak": "Unreliable",
    }
    return {
        "control_id": control["control_id"],
        "system_name": "",
        "report_name": "",
        "itgc_dependency_type": [],
        "ipe_validation_level": "N/A",
        "control_reliability": mapping.get(control.get("control_design_effectiveness"), "Partially Reliable"),
        "reliability_downgraded": False,
        "downgrade_reason": "",
        "additional_itgc_control_required": False,
        "itgc_control_description": "",
    }


def _draft_uc6_control(control_id: str, issue_text: str) -> dict:
    return {
        "control_id": control_id,
        "description": "ITGC and IPE validation review for UC6-derived risk",
        "who": "IT Control Owner",
        "control_owner": "IT Control Owner",
        "what": "Reviews system access, change, operations, and report validation evidence to confirm the supporting IT environment is reliable.",
        "when": "Before reliance is placed on the related control and after significant IT changes",
        "frequency": "Monthly",
        "where": "IT governance and control review workflow",
        "how": f"Uses ITGC evidence, report configuration, and reconciliation documentation to address the issue: {issue_text}",
        "why": "Mitigates the risk that unreliable IT dependencies or unvalidated IPE undermine control reliance.",
        "evidence": "ITGC review checklist, reconciliation evidence, and management sign-off",
        "evidence_type": "Documentation-Based",
        "execution_type": "Manual",
        "nature": "Detective",
        "significance": "Key",
        "control_design_effectiveness": "Moderate",
        "it_dependent": False,
    }


def _build_uc6_risk(
    template_risk: dict,
    new_risk_id: str,
    control_id: str,
    new_risk_description: str,
    source_reference: str,
) -> dict:
    stage1 = template_risk["stage1"]
    control = _draft_uc6_control(control_id, new_risk_description)
    inherent_score = 12
    preliminary_residual = round(inherent_score * (1 - _DESIGN_REDUCTION[control["control_design_effectiveness"]]), 2)
    final_residual = round(inherent_score * (1 - _RELIABILITY_REDUCTION["Partially Reliable"]), 2)
    return {
        "risk_id": new_risk_id,
        "stage1": {
            "process_id": stage1.get("process_id", ""),
            "process_name": stage1.get("process_name", ""),
            "sub_process_id": stage1.get("sub_process_id", ""),
            "sub_process_name": stage1.get("sub_process_name", ""),
            "objective_id": stage1.get("objective_id", ""),
            "objective": stage1.get("objective", ""),
            "cause": "Weak or incomplete IT dependency assurance",
            "event": "the control cannot be relied upon because system access, changes, operations, or IPE validation are insufficient",
            "impact": "audit reliance is reduced and the underlying business risk remains insufficiently mitigated",
            "risk_statement": (
                "As a result of weak or incomplete IT dependency assurance, there is a risk that "
                "the control cannot be relied upon because system access, changes, operations, or IPE validation are insufficient, "
                "leading to audit reliance is reduced and the underlying business risk remains insufficiently mitigated."
            ),
            "risk_category": "IT",
            "source_use_cases": list(dict.fromkeys(stage1.get("source_use_cases", []) + ["UC6"])),
            "risk_sources": list(dict.fromkeys(stage1.get("risk_sources", []) + ["UC6 IT Validation"])),
            "source_references": list(dict.fromkeys(stage1.get("source_references", []) + [source_reference])),
            "gias_compliance": {
                "standard_13_2": True,
                "standard_13_6": True,
            },
            "derived_from_risk_id": template_risk["risk_id"],
            "uc6_generated": True,
        },
        "stage2": {
            "inherent_impact": 4,
            "inherent_likelihood": 3,
            "inherent_risk_score": inherent_score,
            "inherent_risk_rating": _get_risk_rating(inherent_score),
            "preliminary_residual_risk": preliminary_residual,
            "preliminary_residual_rating": _get_risk_rating(preliminary_residual),
            "design_gap": False,
            "design_gap_type": "None",
            "design_gap_description": "No design gap identified.",
            "controls": [control],
        },
        "stage3": {
            "has_it_dependency": False,
            "controls_it_assessment": [
                {
                    "control_id": control_id,
                    "system_name": "",
                    "report_name": "",
                    "itgc_dependency_type": [],
                    "ipe_validation_level": "N/A",
                    "control_reliability": "Partially Reliable",
                    "reliability_downgraded": False,
                    "downgrade_reason": "",
                    "additional_itgc_control_required": False,
                    "itgc_control_description": "",
                }
            ],
            "final_residual_risk": final_residual,
            "final_residual_rating": _get_risk_rating(final_residual),
            "residual_risk_change": round(final_residual - preliminary_residual, 2),
            "new_risk_flag": False,
            "new_risk_description": "",
            "generated_uc6_risk_ids": [],
        },
    }


def apply_it_validation(draft_rcm: dict, it_matrix: dict) -> dict:
    matrix_lookup = {
        entry["control_id"]: entry
        for entry in it_matrix.get("it_dependency_matrix", [])
        if entry.get("control_id")
    }

    next_risk_index = len(draft_rcm.get("risks", [])) + 1
    next_control_index = 1
    for risk in draft_rcm.get("risks", []):
        for control in risk.get("stage2", {}).get("controls", []):
            try:
                next_control_index = max(next_control_index, int(control["control_id"].split("-")[1]) + 1)
            except (IndexError, ValueError, KeyError):
                continue

    derived_risks: list[dict] = []
    original_risks = list(draft_rcm.get("risks", []))

    for risk in original_risks:
        controls = risk.get("stage2", {}).get("controls", [])
        inherent_score = risk.get("stage2", {}).get("inherent_risk_score", 0)
        preliminary_residual = risk.get("stage2", {}).get("preliminary_residual_risk", inherent_score)
        has_it_dependency = any(control.get("it_dependent", False) for control in controls)
        it_assessments: list[dict[str, Any]] = []
        best_reduction = 0.0
        uc6_issue_descriptions: list[str] = []
        generated_uc6_risk_ids: list[str] = []
        primary_issue_reference = ""

        for control in controls:
            control_id = control["control_id"]
            if not control.get("it_dependent", False):
                assessment = _non_it_assessment(control)
            else:
                matrix_entry = matrix_lookup.get(control_id)
                if matrix_entry is None:
                    assessment = {
                        "control_id": control_id,
                        "system_name": "",
                        "report_name": "",
                        "itgc_dependency_type": [],
                        "ipe_validation_level": "N/A",
                        "control_reliability": "Not Assessed",
                        "reliability_downgraded": False,
                        "downgrade_reason": "No IT dependency matrix entry found for this control.",
                        "additional_itgc_control_required": True,
                        "itgc_control_description": "Document the supporting system, validate IPE, and establish relevant ITGC coverage before relying on this control.",
                    }
                else:
                    dep_info = assess_it_dependency(matrix_entry)
                    reliability, downgraded = derive_control_reliability(
                        control,
                        dep_info["ipe_validation_level"],
                        return_downgrade=True,
                    )
                    additional_itgc_control_required = (
                        reliability != "Reliable" or dep_info["ipe_validation_level"] in ("Weak", "None")
                    )
                    assessment = {
                        "control_id": control_id,
                        "system_name": dep_info["system_name"],
                        "report_name": dep_info["report_name"],
                        "itgc_dependency_type": dep_info["itgc_dependency_type"],
                        "ipe_validation_level": dep_info["ipe_validation_level"],
                        "control_reliability": reliability,
                        "reliability_downgraded": downgraded,
                        "downgrade_reason": (
                            f"IPE validation level is '{dep_info['ipe_validation_level']}'; reliability downgraded."
                            if downgraded else ""
                        ),
                        "additional_itgc_control_required": additional_itgc_control_required,
                        "itgc_control_description": (
                            _describe_itgc_control(
                                dep_info["itgc_dependency_type"],
                                dep_info["system_name"],
                                dep_info["report_name"],
                            )
                            if additional_itgc_control_required else ""
                        ),
                    }

            it_assessments.append(assessment)
            best_reduction = max(best_reduction, _RELIABILITY_REDUCTION.get(assessment["control_reliability"], 0.0))

            if not risk.get("stage1", {}).get("uc6_generated") and (
                assessment["control_reliability"] in ("Unreliable", "Not Assessed")
                or assessment["additional_itgc_control_required"]
            ):
                new_risk_description = _build_new_risk_description(assessment)
                uc6_issue_descriptions.append(new_risk_description)
                if not primary_issue_reference:
                    primary_issue_reference = assessment.get("report_name") or assessment.get("system_name") or control_id

        if uc6_issue_descriptions and not risk.get("stage1", {}).get("uc6_generated"):
            new_risk_id = f"RISK-{next_risk_index:04d}"
            new_control_id = f"CTRL-{next_control_index:04d}"
            next_risk_index += 1
            next_control_index += 1
            generated_uc6_risk_ids.append(new_risk_id)
            derived_risks.append(
                _build_uc6_risk(
                    risk,
                    new_risk_id,
                    new_control_id,
                    "; ".join(dict.fromkeys(uc6_issue_descriptions)),
                    primary_issue_reference or risk["risk_id"],
                )
            )

        final_residual = round(inherent_score * (1 - best_reduction), 2)
        risk["stage3"] = {
            "has_it_dependency": has_it_dependency,
            "controls_it_assessment": it_assessments,
            "final_residual_risk": final_residual,
            "final_residual_rating": _get_risk_rating(final_residual),
            "residual_risk_change": round(final_residual - preliminary_residual, 2),
            "new_risk_flag": bool(generated_uc6_risk_ids),
            "new_risk_description": "; ".join(dict.fromkeys(uc6_issue_descriptions)),
            "generated_uc6_risk_ids": generated_uc6_risk_ids,
        }

    draft_rcm.setdefault("risks", []).extend(derived_risks)
    return draft_rcm
