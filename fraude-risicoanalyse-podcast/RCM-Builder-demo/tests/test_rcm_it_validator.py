import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'scripts'))

from rcm_it_validator import (  # noqa: E402
    apply_it_validation,
    assess_it_dependency,
    derive_control_reliability,
    evaluate_ipe_reliability,
)


def test_assess_it_dependency_returns_itgc_types_and_system_fields():
    matrix_entry = {
        "control_id": "CTRL-0001",
        "system_name": "ERP General Ledger Module",
        "itgc_dependency_types": ["Access", "Change"],
        "ipe_details": {
            "report_name": "Journal Entry Exception Report",
            "system_generated": True,
            "editable_after_export": False,
            "reconciliation_exists": True,
        },
    }
    result = assess_it_dependency(matrix_entry)
    assert result["itgc_dependency_type"] == ["Access", "Change"]
    assert result["system_name"] == "ERP General Ledger Module"
    assert result["report_name"] == "Journal Entry Exception Report"
    assert result["ipe_validation_level"] == "Strong"


def test_assess_it_dependency_non_it_control():
    result = assess_it_dependency(None)
    assert result["itgc_dependency_type"] == []
    assert result["ipe_validation_level"] == "N/A"


def test_evaluate_ipe_strong():
    ipe_details = {
        "system_generated": True,
        "editable_after_export": False,
        "reconciliation_exists": True,
    }
    assert evaluate_ipe_reliability(ipe_details) == "Strong"


def test_evaluate_ipe_weak():
    ipe_details = {
        "system_generated": True,
        "editable_after_export": True,
        "reconciliation_exists": False,
    }
    assert evaluate_ipe_reliability(ipe_details) == "Weak"


def test_evaluate_ipe_none_when_not_system_generated():
    ipe_details = {
        "system_generated": False,
        "editable_after_export": True,
        "reconciliation_exists": False,
    }
    assert evaluate_ipe_reliability(ipe_details) == "None"


def test_derive_control_reliability_reliable_for_strong_preventive_key_control():
    control = {
        "significance": "Key",
        "nature": "Preventive",
        "control_design_effectiveness": "Strong",
    }
    assert derive_control_reliability(control, "Strong") == "Reliable"


def test_derive_control_reliability_downgraded_on_weak_ipe():
    control = {
        "significance": "Key",
        "nature": "Preventive",
        "control_design_effectiveness": "Strong",
    }
    reliability, downgraded = derive_control_reliability(control, "Weak", return_downgrade=True)
    assert reliability == "Unreliable"
    assert downgraded is True


def test_apply_it_validation_enriches_stage3_and_adds_system_fields():
    draft_rcm = {
        "rcm_version": "2.0.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "risks": [
            {
                "risk_id": "RISK-0001",
                "stage1": {
                    "risk_category": "Financial",
                    "source_use_cases": ["UC-01"],
                    "risk_sources": ["Historical Audit Findings"],
                    "source_references": ["AUD-1"],
                },
                "stage2": {
                    "inherent_risk_score": 12,
                    "preliminary_residual_risk": 4.8,
                    "design_gap": False,
                    "controls": [
                        {
                            "control_id": "CTRL-0001",
                            "it_dependent": True,
                            "significance": "Key",
                            "nature": "Preventive",
                            "control_design_effectiveness": "Strong",
                        }
                    ],
                },
            }
        ],
    }
    it_matrix = {
        "it_dependency_matrix": [
            {
                "control_id": "CTRL-0001",
                "system_name": "ERP General Ledger Module",
                "itgc_dependency_types": ["Access", "Change"],
                "ipe_details": {
                    "report_name": "Journal Entry Exception Report",
                    "system_generated": True,
                    "editable_after_export": False,
                    "reconciliation_exists": True,
                    "ipe_reliability": "Strong",
                },
            }
        ]
    }
    result = apply_it_validation(draft_rcm, it_matrix)
    risk = result["risks"][0]
    assessment = risk["stage3"]["controls_it_assessment"][0]
    assert assessment["system_name"] == "ERP General Ledger Module"
    assert assessment["report_name"] == "Journal Entry Exception Report"
    assert assessment["control_reliability"] == "Reliable"
    assert risk["stage3"]["new_risk_flag"] is False


def test_apply_it_validation_creates_uc6_risk_for_missing_matrix_entry():
    draft_rcm = {
        "rcm_version": "2.0.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "risks": [
            {
                "risk_id": "RISK-0001",
                "stage1": {
                    "process_id": "PRC-001",
                    "process_name": "User Access Management",
                    "sub_process_id": "SP-001.1",
                    "sub_process_name": "Access Provisioning",
                    "objective_id": "OBJ-0001",
                    "objective": "Ensure access is approved",
                    "risk_category": "IT",
                    "cause": "Workflow gaps",
                    "event": "unauthorized access is granted",
                    "impact": "sensitive systems are exposed",
                    "risk_statement": "As a result of Workflow gaps, there is a risk that unauthorized access is granted, leading to sensitive systems are exposed.",
                    "source_use_cases": ["UC-03"],
                    "risk_sources": ["Incident and Issue Data"],
                    "source_references": ["INC-1"],
                },
                "stage2": {
                    "inherent_risk_score": 12,
                    "preliminary_residual_risk": 7.8,
                    "design_gap": False,
                    "controls": [
                        {
                            "control_id": "CTRL-9999",
                            "it_dependent": True,
                            "significance": "Key",
                            "nature": "Preventive",
                            "control_design_effectiveness": "Strong",
                        }
                    ],
                },
            }
        ],
    }
    result = apply_it_validation(draft_rcm, {"it_dependency_matrix": []})
    original_risk = result["risks"][0]
    assessment = original_risk["stage3"]["controls_it_assessment"][0]
    assert assessment["control_reliability"] == "Not Assessed"
    assert assessment["additional_itgc_control_required"] is True
    assert original_risk["stage3"]["new_risk_flag"] is True
    derived_risks = [risk for risk in result["risks"] if risk["stage1"].get("uc6_generated")]
    assert len(derived_risks) == 1
    assert derived_risks[0]["stage1"]["derived_from_risk_id"] == "RISK-0001"
