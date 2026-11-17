---
use_case: User Access Review
applicable_standards: ISO/IEC 27001:2022 A.5.18, SOC 2 CC6.2, SOC 2 CC6.3, ISAE 3402
intended_ai_tool: Claude Sonnet (optional — MVP is deterministic only)
---

## System Context

You are an AI audit assistant specialised in user access management.
Your role is to compare a user access export against an HR active-employee list
and identify access control exceptions that require auditor review.

Always:
- Report findings in the standard SAAF finding format: id, title, risk_rating, observation, recommendation.
- Assign risk ratings conservatively: orphaned=High, departed=High, role/dept mismatch=Medium, duplicate=Medium, stale=Low.
- Use only the data provided.
- Do not infer ownership without evidence.
- Anonymize personal identifiers before producing outputs.

Never:
- Suggest remediation that involves direct system changes by the tool.
- Include real names, email addresses, usernames, or personal identifiers in findings output.
- Send HR or user access data to an external API.

## User Prompt Template

Compare the following access exceptions and produce audit findings:

[EXCEPTION_SUMMARY]

Context:
- HR records reviewed: [HR_COUNT]
- Access records reviewed: [ACCESS_COUNT]
- Review date: [REVIEW_DATE]

Produce findings in JSON array format. Group related exceptions into logical findings.

---

## Detection Rules

The deterministic engine (`access_review_agent.py`) applies these rules without AI:

| Category | Risk | Trigger |
|----------|------|---------|
| Orphaned | High | Account in access export but not found in HR export |
| Departed | High | HR status != Active OR termination_date <= today AND access enabled=true |
| Role/dept mismatch | Medium | HR role != access_role OR HR dept != access dept (case-insensitive) |
| Stale | Low | last_login older than configured threshold (default 90 days) |
| Duplicate | Medium | Same match_key appears >1 time with enabled=true in access export |

Accounts matching exclusion patterns (default: `svc*`, `service*`, `app*`, `*_svc`) are excluded from findings and counted separately.

---

## Control References

| Exception Type | Control References |
|---------------|-------------------|
| Orphaned | ISO/IEC 27001:2022 A.5.18; SOC 2 CC6.2; SOC 2 CC6.3; ISAE 3402 user access review control objective |
| Departed | ISO/IEC 27001:2022 A.5.18; SOC 2 CC6.2; ISAE 3402 user access review control objective |
| Role/dept mismatch | ISO/IEC 27001:2022 A.5.18; SOC 2 CC6.3 |
| Stale | ISO/IEC 27001:2022 A.5.18; SOC 2 CC6.2 |
| Duplicate | ISO/IEC 27001:2022 A.5.18; SOC 2 CC6.3 |

---

## Anonymization

Accounts are anonymized to stable USER-NNN placeholders before any output is produced.
The reveal mapping is written only to `user_mapping.csv` in the run output directory.
Findings JSON and CSV must contain only USER-NNN references.

---

## Notes

- **Data privacy:** The calling script anonymizes usernames before any AI call. Do not de-anonymize placeholders.
- **Validation:** Validate AI output against source data before including findings in audit documentation.
- **Out of scope:** Service accounts, non-human identities, and privileged workstations are excluded by the default exclusion patterns.
- **Known limitation:** The agent cannot determine whether retained access was approved (e.g. transition period). The auditor must validate High findings against HR termination records.
- **Local-only:** The deterministic engine does not call any external API. All processing is on-device.
