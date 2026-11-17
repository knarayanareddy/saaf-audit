# Executive Board Risk Report

Run id: `demo`  
Status: Draft - human approval required  
Overall risk posture: **Critical**

## Executive Summary

The uploaded GRC dataset was analyzed for control weaknesses, high residual risks and correlations between both. The current posture is assessed as **Critical** based on configured thresholds and uploaded evidence. This report is a decision-support draft and does not provide a legal or regulatory assurance opinion.

## Key Metrics

- Controls analyzed: 5
- Weak controls: 4
- Risks analyzed: 5
- High risks: 3
- Critical risks: 1
- Direct weak-control correlations: 3
- Contextual correlations: 0

## Key Themes

| Theme | High Risks | Weak Controls | Max Score |
|---|---:|---:|---:|
| Identity and Access | 2 | 2 | 21 |
| Third Party Risk | 1 | 1 | 18 |
| Policy Management | 0 | 1 | 11 |
| Resilience | 0 | 0 | 9 |

## Strategic Recommendations

- Prioritize remediation and retesting for C-001, C-004; confirm owner, due date and residual risk acceptance for R-004.
- Prioritize remediation and retesting for C-002; confirm owner, due date and residual risk acceptance for R-002.
- Prioritize remediation and retesting for C-001, C-004; confirm owner, due date and residual risk acceptance for R-001.
- Validate remediation plan and retest control C-005; confirm whether risk mapping is complete.

## Decision Points for Management

- Decide whether critical and high findings require immediate remediation or formal risk acceptance.
- Confirm whether additional control evidence is needed before external or board publication.
- Assign accountable owners for weak controls and unmapped high risks.
- Use the dashboard (`dashboard.html`) to review visual summaries and source traceability.

## Assurance and Limitations

- Applicable frameworks in profile: ISO 27001, SOC 2, ISAE 3402, NIS2, DORA, COSO ERM.
- The analysis uses uploaded data only and does not modify source data.
- Conclusions are traceable through `audit_trail.ndjson`, `audit_summary.md` and `analysis_result.json`.
- Human review remains mandatory before final board publication when `EXEC_SUMMARY_REQUIRE_HUMAN_APPROVAL` is true.
