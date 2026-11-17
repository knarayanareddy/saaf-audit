import json
import os
import pathlib
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'scripts'))

from rcm_builder import (  # noqa: E402
    build_draft_rcm,
    calculate_preliminary_residual,
    deduplicate_risks,
    draft_control,
    normalize_risk,
    parse_use_cases,
    run_pipeline,
    score_inherent_risk,
    to_markdown_table,
)


SAMPLE_INPUT = {
    "context": {
        "risk_appetite": {
            "financial_reporting": "Low - Minimal tolerance for misstatement",
            "operational": "Moderate - Acceptable disruption within budget",
            "compliance": "Zero - No tolerance for violations",
            "strategic": "Moderate"
        }
    },
    "processes": [
        {
            "process_id": "PRC-001",
            "process_name": "Revenue Recognition",
            "sub_processes": [
                {
                    "sub_process_id": "SP-001.1",
                    "sub_process_name": "Journal Entry Processing",
                    "business_objectives": [
                        "Ensure revenue is recognized accurately"
                    ]
                }
            ]
        }
    ],
    "use_cases": [
        {
            "id": "UC-01",
            "process_id": "PRC-001",
            "sub_process_id": "SP-001.1",
            "process_name": "Revenue Recognition",
            "sub_process_name": "Journal Entry Processing",
            "objective": "Ensure revenue is recognized accurately",
            "risks": [
                {
                    "cause": "Lack of controls over journal entry posting",
                    "event": "unauthorized journal entries are recorded",
                    "impact": "financial statements are misstated",
                    "risk_category": "Financial Reporting"
                }
            ]
        },
        {
            "id": "UC-02",
            "process_id": "PRC-001",
            "sub_process_id": "SP-001.1",
            "process_name": "Revenue Recognition",
            "sub_process_name": "Journal Entry Processing",
            "objective": "Ensure revenue is recognized accurately",
            "risks": [
                {
                    "cause": "Inadequate segregation of duties in journal entry process",
                    "event": "unauthorized journal entries are posted without detection",
                    "impact": "revenue figures are overstated in financial reports",
                    "risk_category": "Financial Reporting"
                }
            ]
        }
    ]
}

RICH_SOURCE_INPUT = {
    "processes": [
        {
            "process_id": "PRC-100",
            "process_name": "User Access Management",
            "sub_processes": [
                {
                    "sub_process_id": "SP-100.1",
                    "sub_process_name": "Access Provisioning",
                    "business_objectives": [
                        "Ensure only authorized users receive system access"
                    ]
                }
            ]
        }
    ],
    "incidents": [
        {
            "process_id": "PRC-100",
            "process_name": "User Access Management",
            "sub_process_id": "SP-100.1",
            "sub_process_name": "Access Provisioning",
            "objective": "Ensure only authorized users receive system access",
            "incident_id": "INC-2026-041",
            "risk_description": "As a result of weak approval controls, there is a risk that unauthorized privileged access is granted, leading to data breaches.",
            "risk_category": "IT"
        }
    ],
    "fraud_scenarios": [
        {
            "process_id": "PRC-100",
            "process_name": "User Access Management",
            "sub_process_id": "SP-100.1",
            "sub_process_name": "Access Provisioning",
            "objective": "Ensure only authorized users receive system access",
            "finding_id": "FRAUD-12",
            "description": "Approvers collude to provision access without proper review",
            "event": "fraudulent access requests are approved",
            "impact": "sensitive systems can be manipulated for personal gain",
            "risk_category": "Fraud"
        }
    ],
    "regulatory_risks": [
        {
            "process_id": "PRC-100",
            "process_name": "User Access Management",
            "sub_process_id": "SP-100.1",
            "sub_process_name": "Access Provisioning",
            "objective": "Ensure only authorized users receive system access",
            "regulation_reference": "GDPR Art. 32",
            "summary": "Failure to restrict access to personal data",
            "event": "unauthorized users access regulated information",
            "impact": "regulatory penalties and customer harm",
            "risk_category": "Compliance"
        }
    ]
}

IT_MATRIX = {
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
                "ipe_reliability": "Strong"
            }
        },
        {
            "control_id": "CTRL-0002",
            "system_name": "ERP General Ledger Module",
            "itgc_dependency_types": ["Access", "Change"],
            "ipe_details": {
                "report_name": "Journal Entry Exception Report",
                "system_generated": True,
                "editable_after_export": True,
                "reconciliation_exists": False,
                "ipe_reliability": "Weak"
            }
        }
    ]
}

SCHEMA_PATH = pathlib.Path(__file__).parents[1] / "outputs" / "schemas" / "rcm-schema.json"


def test_parse_use_cases_returns_flat_risk_list_with_traceability():
    risks = parse_use_cases(SAMPLE_INPUT)
    assert len(risks) == 2
    assert risks[0]["source_use_case"] == "UC-01"
    assert risks[0]["risk_source"]
    assert risks[0]["source_reference"]
    assert risks[0]["risk_category"] == "Financial"


def test_parse_use_cases_supports_rich_uc2_to_uc5_collections():
    risks = parse_use_cases(RICH_SOURCE_INPUT)
    assert len(risks) == 3
    assert {risk["risk_category"] for risk in risks} == {"IT", "Fraud", "Compliance"}
    assert any(risk["source_reference"] == "INC-2026-041" for risk in risks)
    assert any("Fraud" in risk["risk_category"] for risk in risks)


def test_normalize_risk_produces_canonical_statement():
    risk = {
        "cause": "Lack of controls over journal entry posting",
        "event": "unauthorized journal entries are recorded",
        "impact": "financial statements are misstated"
    }
    result = normalize_risk(risk)
    assert result["risk_statement"] == (
        "As a result of Lack of controls over journal entry posting, "
        "there is a risk that unauthorized journal entries are recorded, "
        "leading to financial statements are misstated."
    )


def test_deduplicate_risks_merges_traceability_metadata():
    risks = [
        normalize_risk({
            "source_use_case": "UC-02",
            "risk_source": "Historical Audit Findings",
            "source_reference": "AUD-1",
            "cause": "Weak approval controls",
            "event": "unauthorized access is granted",
            "impact": "sensitive data is exposed",
            "risk_category": "IT"
        }),
        normalize_risk({
            "source_use_case": "UC-04",
            "risk_source": "Fraud Scenarios",
            "source_reference": "FR-9",
            "cause": "Weak approval controls",
            "event": "unauthorized access is granted",
            "impact": "sensitive data is exposed",
            "risk_category": "Fraud"
        }),
    ]
    deduped = deduplicate_risks(risks, similarity_threshold=0.60)
    assert len(deduped) == 1
    assert deduped[0]["source_use_cases"] == ["UC-02", "UC-04"]
    assert deduped[0]["risk_sources"] == ["Historical Audit Findings", "Fraud Scenarios"]
    assert deduped[0]["source_references"] == ["AUD-1", "FR-9"]


@pytest.mark.parametrize("category", ["Financial", "Operational", "IT", "Compliance", "Fraud"])
def test_draft_control_it_dependent_consistent_with_execution_type(category):
    risk = {
        "stage1": {
            "risk_category": category,
            "process_name": "Access Management",
            "sub_process_name": "Access Provisioning",
            "objective": "Ensure access is approved",
            "event": "unauthorized access is granted"
        }
    }
    control = draft_control(risk, control_index=1)
    assert control["it_dependent"] == (control["execution_type"] in ("IT-Dependent", "Automated"))


def test_draft_control_structure_uses_uc7_terms():
    risk = {
        "stage1": {
            "risk_category": "IT",
            "process_name": "User Access Management",
            "sub_process_name": "Access Provisioning",
            "objective": "Ensure only authorized users receive access",
            "event": "unauthorized access is granted"
        }
    }
    control = draft_control(risk, control_index=1)
    assert control["control_id"] == "CTRL-0001"
    assert control["execution_type"] in ("Manual", "IT-Dependent", "Automated")
    assert control["nature"] in ("Preventive", "Detective")
    assert control["significance"] in ("Key", "Non-Key")
    assert control["control_design_effectiveness"] in ("Strong", "Moderate", "Weak")
    for field in (
        "who", "control_owner", "what", "when", "frequency", "where",
        "how", "why", "evidence", "evidence_type"
    ):
        assert field in control and control[field]


def test_score_inherent_risk():
    assert score_inherent_risk(impact=4, likelihood=3) == 12
    assert score_inherent_risk(impact=5, likelihood=5) == 25
    assert score_inherent_risk(impact=1, likelihood=1) == 1


def test_calculate_preliminary_residual_strong_control():
    residual = calculate_preliminary_residual(inherent_score=20, control_design_effectiveness="Strong")
    assert residual == pytest.approx(8.0)


def test_build_draft_rcm_has_required_uc7_keys():
    result = build_draft_rcm(SAMPLE_INPUT)
    assert result["rcm_version"] == "2.0.0"
    assert "warnings" in result
    assert "quality_checks" in result
    risk = result["risks"][0]
    assert risk["stage1"]["objective_id"] == "OBJ-0001"
    assert risk["stage1"]["risk_sources"]
    assert risk["stage1"]["source_references"]
    assert risk["stage1"]["risk_category"] == "Financial"
    assert len(risk["stage2"]["controls"]) >= 1
    assert risk["stage2"]["inherent_risk_rating"] in ("Low", "Medium", "High")


def test_build_draft_rcm_warns_on_empty_sub_process():
    input_data = {
        "processes": [
            {
                "process_id": "PRC-010",
                "process_name": "Access Management",
                "sub_processes": [
                    {
                        "sub_process_id": "SP-010.1",
                        "sub_process_name": "Provisioning",
                        "business_objectives": ["Ensure access is approved before provisioning"]
                    },
                    {
                        "sub_process_id": "SP-010.2",
                        "sub_process_name": "Termination",
                        "business_objectives": ["Remove access promptly for leavers"]
                    }
                ]
            }
        ],
        "use_cases": [
            {
                "id": "UC-10",
                "process_id": "PRC-010",
                "sub_process_id": "SP-010.1",
                "process_name": "Access Management",
                "sub_process_name": "Provisioning",
                "objective": "Ensure access is approved before provisioning",
                "risks": [
                    {
                        "cause": "Requests are approved outside the workflow",
                        "event": "access is provisioned without authorization",
                        "impact": "unauthorized users gain access to systems",
                        "risk_category": "IT"
                    }
                ]
            }
        ]
    }

    result = build_draft_rcm(input_data)
    assert result["quality_checks"]["structural_integrity"]["passed"] is False
    assert any("SP-010.2 - Termination" in warning for warning in result["warnings"])


def test_build_draft_rcm_flags_unmapped_control_design():
    input_data = {
        "use_cases": [
            {
                "id": "UC-20",
                "process_id": "PRC-020",
                "sub_process_id": "SP-020.1",
                "process_name": "IT Change Management",
                "sub_process_name": "Change Request",
                "objective": "Ensure changes are properly documented",
                "risks": [
                    {
                        "cause": "Emergency changes bypass standard approval workflow",
                        "event": "unapproved changes are deployed to production",
                        "impact": "system instability or security vulnerabilities",
                        "risk_category": "Operational"
                    }
                ]
            }
        ]
    }
    result = build_draft_rcm(input_data)
    assert result["risks"][0]["stage2"]["design_gap_type"] in ("None", "Unmapped")


def test_build_draft_rcm_flags_redundant_control_designs_within_same_objective():
    input_data = {
        "use_cases": [
            {
                "id": "UC-30",
                "process_id": "PRC-030",
                "sub_process_id": "SP-030.1",
                "process_name": "User Access Management",
                "sub_process_name": "Access Provisioning",
                "objective": "Ensure new user access is approved before provisioning",
                "risks": [
                    {
                        "cause": "Approvals are captured outside the access workflow",
                        "event": "access is granted without documented authorization",
                        "impact": "unauthorized users gain access to systems",
                        "risk_category": "IT"
                    },
                    {
                        "cause": "Provisioning requests are copied from outdated onboarding trackers",
                        "event": "accounts are created with excessive permissions",
                        "impact": "users receive inappropriate system access",
                        "risk_category": "IT"
                    }
                ]
            }
        ]
    }
    result = build_draft_rcm(input_data)
    assert result["risks"][1]["stage2"]["design_gap_type"] == "Redundant"


def test_run_pipeline_output_validates_against_schema():
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text())
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    jsonschema.validate(result, schema)


def test_run_pipeline_stage3_present_and_uc6_fields_populated():
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    risk = result["risks"][0]
    assert "stage3" in risk
    assert risk["stage3"]["final_residual_risk"] <= risk["stage2"]["preliminary_residual_risk"]
    assessment = risk["stage3"]["controls_it_assessment"][0]
    assert assessment["system_name"] == "ERP General Ledger Module"
    assert assessment["report_name"] == "Journal Entry Exception Report"
    assert assessment["ipe_validation_level"] == "Strong"
    assert assessment["control_reliability"] == "Reliable"


def test_run_pipeline_introduces_uc6_risk_when_reliability_is_weak():
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    original_risk = result["risks"][1]
    assert original_risk["stage3"]["new_risk_flag"] is True
    assert original_risk["stage3"]["generated_uc6_risk_ids"]
    derived_risks = [risk for risk in result["risks"] if risk["stage1"].get("uc6_generated")]
    assert derived_risks
    assert derived_risks[0]["stage1"]["risk_category"] == "IT"


def test_to_markdown_table_contains_new_uc7_headers():
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    markdown = to_markdown_table(result)
    assert "| Risk Sources |" in markdown
    assert "| Source References |" in markdown
    assert "| Additional ITGC Control |" in markdown
    assert "RISK-0001" in markdown
