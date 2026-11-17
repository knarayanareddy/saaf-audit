# SOC 2 Type II — CC6 Access Control Mapping

**Standard:** SOC 2 Type II (AICPA Trust Services Criteria)
**Category:** CC6 — Logical and Physical Access Controls
**Audit domain:** Access Management
**SAAF prompt reference:** `prompts/audit-use-cases/access-review-agent.md`

---

## Control Mappings

| Criteria | Description | Auditable Control | Risk Rating | SAAF Prompt Reference |
|---|---|---|---|---|
| CC6.2 | Prior to issuing system credentials and granting system access, the entity registers and authorises new internal and external users. | New user accounts are created only upon receipt of an approved access request. Approvals are documented and retained. | High | `prompts/audit-use-cases/access-review-agent.md` |
| CC6.2 | Access provisioning — completeness | The provisioning process captures all required attributes (role, department, approver) before account creation. | Medium | `prompts/audit-use-cases/access-review-agent.md` |
| CC6.3 | The entity authorises, modifies, or removes access to data, software, functions, and other protected information assets based on approved and documented access requests and changes to employment status. | Access rights are revoked or modified within a defined SLA upon termination or role change. AD accounts are cross-checked against HR records quarterly. | High | `prompts/audit-use-cases/access-review-agent.md` |
| CC6.3 | Role-based access | Access is granted based on documented job roles. Segregation of duties conflicts are identified and mitigated. | Medium | `prompts/audit-use-cases/access-review-agent.md` |
| CC6.6 | The entity implements logical access security measures to protect against threats from sources outside its system boundaries. | Stale accounts (no login beyond threshold) are reviewed and disabled to reduce the attack surface from compromised credentials. | Low | `prompts/audit-use-cases/access-review-agent.md` |
| CC6.6 | Privileged account controls | Privileged accounts are restricted to authorised personnel. Use of privileged accounts is logged and reviewed. | High | `prompts/audit-use-cases/access-review-agent.md` |

---

## Audit Objectives

1. System access is granted only to authorised users based on approved requests.
2. Access is promptly modified or revoked upon employment change or termination.
3. Access rights reflect current roles; segregation of duties conflicts are identified.
4. Inactive accounts are detected and disabled, reducing the risk of credential compromise.

---

## Evidence Typically Required

- Access provisioning and deprovisioning request log for the audit period
- Active Directory export and HR employee list as of review date
- Termination checklist showing IT access revocation steps
- Access recertification sign-off records (quarterly or annual)
- Privileged account register and access logs
- User access review results and management sign-off
