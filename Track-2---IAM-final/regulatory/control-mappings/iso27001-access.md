# ISO/IEC 27001:2022 — Access Control Mapping

**Standard:** ISO/IEC 27001:2022 Annex A
**Audit domain:** Access Management
**SAAF prompt reference:** `prompts/audit-use-cases/access-review-agent.md`

---

## Control Mappings

| Control ID | Control Name | Auditable Control | Risk Rating | SAAF Prompt Reference |
|---|---|---|---|---|
| A.5.18 | Access rights | User access rights are provisioned, modified, and revoked based on documented role changes and termination records. Quarterly recertification is performed and evidenced. | High | `prompts/audit-use-cases/access-review-agent.md` |
| A.5.18 | Access rights — orphaned accounts | AD accounts belonging to departed employees are disabled within the organisation's defined SLA (typically 24 hours of termination). | High | `prompts/audit-use-cases/access-review-agent.md` |
| A.5.18 | Access rights — role changes | Access rights are updated when an employee changes role or department. Approvals for access changes are documented. | Medium | `prompts/audit-use-cases/access-review-agent.md` |
| A.8.2 | Privileged access rights | Privileged accounts (DomainAdmin, SysAdmin, root) are subject to a separate review cycle. The number of privileged users is documented and justified. | High | `prompts/audit-use-cases/access-review-agent.md` |
| A.8.3 | Information access restriction | Access to systems is granted on a need-to-know basis. Accounts with cross-departmental access are reviewed for business justification. | Medium | `prompts/audit-use-cases/access-review-agent.md` |
| A.8.5 | Secure authentication | Accounts with no login activity beyond a defined threshold (e.g. 90 days) are flagged for review and disabled if inactive access is unjustified. | Low | `prompts/audit-use-cases/access-review-agent.md` |

---

## Audit Objectives

1. All active AD accounts correspond to a current employee or documented service account.
2. Access rights reflect current job functions and are removed within SLA upon role change or termination.
3. Privileged accounts are minimised and subject to enhanced review.
4. Stale accounts are identified and disabled in line with policy.

---

## Evidence Typically Required

- Active Directory export (all enabled user accounts) as of review date
- HR active-employee list as of the same date
- Access provisioning / deprovisioning request records
- Previous access review sign-off documentation
- Privileged access register
