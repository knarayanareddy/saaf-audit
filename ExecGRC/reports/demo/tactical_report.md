# Tactical GRC Report

Run id: `demo`  
Status: Draft - human approval required  
Reporting profile: Default GRC reporting profile

## Scope and Source Data

- `data/synthetic/grc_sample.csv` (10 records, sha256 `06c25a3509aeb3f05be9c7475d677bef2c97b08d52d501dc3fa37f59b894689e`)

Detected records:

- Controls: 5
- Risks: 5
- Skipped records: 0

## Control Effectiveness

- partially effective: 2
- ineffective: 2
- effective: 1

Weak control statuses are configured as: ineffective, not effective, onvoldoende, partially effective

## Risk Overview

Overall posture: **Critical**

- High: 2
- Medium: 2
- Critical: 1

Configured thresholds:

- High risk: 15
- Critical risk: 20

## Findings and Recommended Actions

| ID | Severity | Confidence | Theme | Finding | Recommendation |
|---|---|---|---|---|---|
| F-001 | Critical | High | Identity and Access | High residual risk linked to weak controls: Credential theft through phishing | Prioritize remediation and retesting for C-001, C-004; confirm owner, due date and residual risk acceptance for R-004. |
| F-002 | High | High | Third Party Risk | High residual risk linked to weak controls: Critical supplier outage | Prioritize remediation and retesting for C-002; confirm owner, due date and residual risk acceptance for R-002. |
| F-003 | High | High | Identity and Access | High residual risk linked to weak controls: Privileged access misuse | Prioritize remediation and retesting for C-001, C-004; confirm owner, due date and residual risk acceptance for R-001. |
| F-004 | Medium | High | Policy Management | Weak control requires remediation: Policy exception review | Validate remediation plan and retest control C-005; confirm whether risk mapping is complete. |

## Data Quality Notes

- No material data quality issues detected in the uploaded structure.

## Traceability Matrix

| Finding | Risk | Controls | Sources | Confidence |
|---|---|---|---|---|
| F-001 | R-004 | C-001, C-004 | data/synthetic/grc_sample.csv:9, data/synthetic/grc_sample.csv:2, data/synthetic/grc_sample.csv:8 | High |
| F-002 | R-002 | C-002 | data/synthetic/grc_sample.csv:5, data/synthetic/grc_sample.csv:4 | High |
| F-003 | R-001 | C-001, C-004 | data/synthetic/grc_sample.csv:3, data/synthetic/grc_sample.csv:2, data/synthetic/grc_sample.csv:8 | High |
| F-004 | R-005 | C-005 | data/synthetic/grc_sample.csv:10, data/synthetic/grc_sample.csv:11 | High |

## Human Validation Checklist

- Confirm that source records are complete and current.
- Validate that control-risk mappings reflect management intent.
- Confirm remediation owners and due dates for high and critical findings.
- Review whether any legal, regulatory or customer-facing language requires specialist approval.

## Assumptions

- Residual risk scores are interpreted on the configured score scale.
- Control-risk relationships are based on uploaded identifiers first and shared process or department second.
- Reports remain draft until a human reviewer validates the conclusions.
