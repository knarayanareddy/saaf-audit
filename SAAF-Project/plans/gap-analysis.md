# SAAF Gap Analysis — 53 Audit Domains vs. Existing Plans

> **Last updated:** April 2026 (Hackathon #3 preparation)  
> **Source for domains:** [`docs/reference/domains-and-frameworks.md`](../docs/reference/domains-and-frameworks.md) — 53 domains across 12 main categories  
> **Plans counted:** 26 Hackathon 2 plans + 29 Hackathon 3 plans + 4 Alignment plans = **59 total plans**  
> **See also:** [`plans/overview.md`](overview.md) — per-plan critical review table

---

## Coverage Legend

| Status | Meaning |
|---|---|
| ✅ **Covered** | One or more dedicated plans address this domain directly |
| ⚠️ **Partially** | Tangentially addressed by existing plans; a gap remains |
| ❌ **Not covered** | No existing plan addresses this domain |

---

## Summary Statistics

| Status | Count | % |
|---|---|---|
| ✅ Covered | 18 | 34% |
| ⚠️ Partially | 20 | 38% |
| ❌ Not covered | 15 | 28% |
| **Total** | **53** | 100% |

**Update (April 2026 — post video + chat analysis):** 21 new H3 plans added (14 from video transcriptions + 7 from WhatsApp chat analysis + 1 community request); 2 domains moved from ❌ to ⚠️ (IT Resource Management via `audit-skills-transformation-curriculum.md`; Patch Management via `cli-audit-system-wrapper.md`). The 7 chat-sourced plans address AI Governance, AI Security, and Compliance cross-cutting concerns. Priority gaps remain in IT Operations (Backup, Network Security, Asset Management, Cloud), Financial (Treasury), and Specialized Audits (Forensic, ESG).

---

## 1. IT Governance & Strategy

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| IT Governance Framework | ⚠️ Partially | `auditflow-ai.md`, `icfcop-control-testing-agent.md` | ICFCOP covers governance framework controls but no dedicated plan for IT strategy alignment or IT investment decisions |
| IT Risk Management | ⚠️ Partially | `frank-van-dissel-uc4-fraud-risk-assessment.md`, `frank-van-dissel-uc2-previous-audit-intelligence.md` | Fraud risk and historical audit risk covered; general IT risk identification/analysis not explicitly addressed |
| IT Resource Management | ⚠️ Partially | `audit-skills-transformation-curriculum.md` | AI audit skills development (4-stage reskilling path) now covered; broader IT personnel management and outsourcing governance still not addressed |
| Performance Measurement | ❌ Not covered | — | No plan addresses IT KPIs, management reporting dashboards, or benchmarking |

**Suggested next plan:** `it-performance-dashboard-agent.md` — KPI monitoring and IT management reporting using COBIT/ITIL metrics

---

## 2. Information Security (Cyber)

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Information Security Policy | ✅ Covered | `johannesiv-policy-to-controls-extractor.md`, `frank-van-dissel-uc1-policy-process-intake.md`, `robeminem94-gdpr-ai-audit-agent.md` | Policy extraction, completeness, and currency well covered |
| Identity & Access Management (IAM) | ✅ Covered | `example-synthetic-access-review.md`, `saaf-jira-confluence-mcp.md`, `audit-automation-overview.md`, `cli-audit-system-wrapper.md` | User access reviews, SoD conflicts, access request workflows covered; CLI wrapper adds AD inactive user querying |
| Network Security | ❌ Not covered | — | No plan covers firewall audits, network segmentation, IDS/IPS, or VPN controls |
| Physical Security | ❌ Not covered | — | No plan addresses data center physical access or clean desk/screen policies |
| Incident Management | ✅ Covered | `frank-van-dissel-uc3-incident-issue-intelligence.md`, `koekenpan-ia-fieldwork-preparation.md` | Incident intelligence, change/incident Jira analysis well covered |
| Vulnerability Management | ⚠️ Partially | `ellert-van-der-vecht-llm-owasp.md` | Covers LLM-specific vulnerabilities (OWASP LLM Top 10); traditional patch/vuln scan workflows not addressed |
| Cryptography & Encryption | ❌ Not covered | — | No plan addresses key management or encryption controls |
| Security Awareness & Training | ❌ Not covered | — | No plan covers phishing simulation analysis or awareness program assessment |

**Priority gap:** Network Security and Cryptography — foundational GITC controls missing from the SAAF portfolio.

---

## 3. IT Operations & Infrastructure

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Change Management (GITC) | ✅ Covered | `frank-van-dissel-uc3-incident-issue-intelligence.md`, `saaf-jira-confluence-mcp.md`, `icfcop-control-testing-agent.md` | Change freeze detection, Jira evidence collection, ITIL/COBIT alignment covered |
| Patch Management | ⚠️ Partially | `cli-audit-system-wrapper.md` | CLI wrapper can query patch data from SIEM/AD; timeliness scoring and completeness assessment not yet modelled |
| Backup & Recovery | ❌ Not covered | — | No plan addresses backup schedule verification or restoration testing |
| Data Center Operations | ❌ Not covered | — | No plan covers environmental controls or hardware monitoring |
| Asset Management | ❌ Not covered | — | No plan covers IT asset inventory, license management, or lifecycle |
| Problem & Incident Management (Ops) | ✅ Covered | `frank-van-dissel-uc3-incident-issue-intelligence.md` | Root cause analysis, MTTR, major incident classification covered |
| Capacity Management | ❌ Not covered | — | No plan addresses CPU/memory/storage capacity planning |
| Cloud Governance & Security | ⚠️ Partially | `frank-van-dissel-uc6-it-dependency-identifier.md` | IT dependency identification includes cloud; CSA CCM controls not explicitly addressed |

**Priority gap:** Patch Management, Backup & Recovery — high-frequency GITC controls with no coverage.

---

## 4. Systems & Software

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Software Development Life Cycle (SDLC) | ⚠️ Partially | `frank-van-dissel-uc3-incident-issue-intelligence.md`, `ellert-van-der-vecht-llm-owasp.md` | Change management and Jira/GitHub cross-reference covers SDLC tangentially; OWASP covers LLM-specific dev risks; dedicated SDLC audit plan missing |
| Application Controls | ⚠️ Partially | `themontechristo-threewaysecurity.md` | 3-way match covers financial application controls; broader input/processing/output validation not addressed |
| Database Security & Management | ❌ Not covered | — | No plan covers database hardening, table-level access, or audit logging |

---

## 5. Business Continuity & DR

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Business Continuity Management (BCM) | ⚠️ Partially | `icfcop-control-testing-agent.md` | BC/DR is one of the 6 ICFCOP mega-controls; no dedicated BCM audit plan with BIA analysis |
| Disaster Recovery (DR) | ⚠️ Partially | `icfcop-control-testing-agent.md` | DR covered as a mega-control in ICFCOP; RTO/RPO and DR test analysis not explicitly modelled |

**Suggested next plan:** `bc-dr-audit-agent.md` — automated assessment of BCP currency, RTO/RPO definitions, and DR test outcomes

---

## 6. Third-Party & Vendor Risk

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Vendor Selection & Due Diligence | ✅ Covered | `robeminem94-vendor-guard.md` | Vendor risk assessment, financial stability, and security questionnaire covered |
| Service Level Agreements (SLA) | ⚠️ Partially | `robeminem94-vendor-guard.md` | SLA monitoring mentioned; automated SLA breach detection not explicitly modelled |
| Third-Party Assurance (TPRM) | ✅ Covered | `robeminem94-vendor-guard.md` | SOC1/SOC2/ISAE 3402 review workflow included in vendor guard plan |

---

## 7. Data & Privacy

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Privacy Governance | ✅ Covered | `robeminem94-gdpr-ai-audit-agent.md`, `johannesiv-policy-to-controls-extractor.md` | DPO role assessment, data processing register review covered |
| Data Lifecycle Management | ⚠️ Partially | `robeminem94-gdpr-ai-audit-agent.md` | GDPR retention and deletion covered; broader data classification and archiving lifecycle not modelled |
| GDPR Compliance | ✅ Covered | `robeminem94-gdpr-ai-audit-agent.md`, `johannesiv-policy-to-controls-extractor.md`, `icfcop-control-testing-agent.md` | Data subject rights, DPIAs, breach notification — well covered |
| Data Quality & Integrity | ⚠️ Partially | `mollie-group-x-evidence-audit.md` | Evidence integrity checking covered; broader data quality (accuracy, completeness, timeliness) not addressed |

---

## 8. Compliance & Regulatory

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| General Laws & Regulations | ✅ Covered | `frank-van-dissel-uc5-regulatory-criteria.md`, `rohan-sobha-compliance-report-generator.md`, `yellowraptor-whats-the-news.md`, `saaf-intelligence-monitor.md` | Regulatory criteria retrieval, compliance reporting, and monitoring well covered |
| Industry-Specific Regulations | ✅ Covered | `frank-van-dissel-uc5-regulatory-criteria.md`, `robeminem94-gdpr-ai-audit-agent.md`, `icfcop-control-testing-agent.md` | DORA, GDPR, EU AI Act, ISO 27001, NIS2 all addressed |
| Sanctions & Export Controls | ❌ Not covered | — | No plan addresses OFAC, EU sanctions lists, or export control compliance |

---

## 9. Financial & Accounting

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| ICOFR (Internal Control over Financial Reporting) | ⚠️ Partially | `themontechristo-threewaysecurity.md`, `frank-van-dissel-uc7-rcm-builder.md`, `the-control-freaks-uc7-rcm-builder.md` | 3-way match and RCM building partially address ICOFR; COSO/SOx control framework not explicitly assessed |
| Procure-to-Pay (P2P) | ✅ Covered | `themontechristo-threewaysecurity.md` | PO/invoice/GRN 3-way match covers P2P controls |
| Order-to-Cash (O2C) | ✅ Covered | `themontechristo-threewaysecurity.md` | Sales order, invoicing, and AR controls included in 3-way match |
| Treasury & Cash Management | ❌ Not covered | — | No plan addresses cash flow monitoring, bank reconciliation, or FX risk |

---

## 10. Operational & Business

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Human Resources (HR) Security | ⚠️ Partially | `example-synthetic-access-review.md`, `koekenpan-ia-fieldwork-preparation.md` | Leavers with active accounts (joiner/mover/leaver) covered via access reviews; broader HR security (background checks, disciplinary process) not addressed |
| Inventory Management | ❌ Not covered | — | No plan covers physical inventory, valuation, or obsolete stock |
| Manufacturing & Production | ❌ Not covered | — | No plan addresses process efficiency or quality control |
| Marketing & Sales | ❌ Not covered | — | No plan covers advertising compliance or customer data practices |

**Note:** Operational/Business domains (Manufacturing, Inventory, Marketing) are outside the financial-services focus of most SAAF member organizations. Low priority for the current portfolio.

---

## 11. Projects & Programmes

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| Project Governance | ❌ Not covered | — | No plan covers project initiation, budget oversight, or steering committee reporting |
| Project Risk Management | ❌ Not covered | — | No plan addresses risk identification in project contexts |
| Post-Implementation Review (PIR) | ❌ Not covered | — | No plan covers PIR evaluation of IT project goals and benefits |

**Suggested next plan:** `project-audit-agent.md` — automated PIR and project risk assessment using PRINCE2/PMBOK criteria

---

## 12. Emerging Technology

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| AI Governance | ✅ Covered | `robeminem94-gdpr-ai-audit-agent.md`, `group-5-hackers-ai-audit-agents.md`, `johannesiv-policy-to-controls-extractor.md`, `icfcop-control-testing-agent.md`, `ai-audit-explainability-framework.md`, `eu-ai-act-compliance-monitor.md`, `ai-agent-visibility-scanner.md` | EU AI Act (incl. GPAI Aug 2026 deadline), ALTAI self-assessment, shadow AI inventory, NIST AI RMF, AI system classification, audit finding explainability covered |
| AI Security | ✅ Covered | `ellert-van-der-vecht-llm-owasp.md`, `ellert-van-der-vecht-multi-model-validation.md`, `llm-hallucination-detection-agent.md`, `owasp-ai-testing-agent.md` | OWASP LLM Top 10, full OWASP AI Testing Guide v1.0, multi-model validation, adversarial ML risks, hallucination detection covered |
| Blockchain / Distributed Ledger | ❌ Not covered | — | No plan addresses smart contracts or distributed ledger technology |
| IoT Security | ❌ Not covered | — | No plan covers connected device security or firmware management |

---

## Specialized Audits

| Domain | Status | Covering Plans | Gap / Notes |
|---|---|---|---|
| ESG / Sustainability Reporting | ❌ Not covered | — | No plan covers CSRD, GRI, or non-financial KPI audits |
| Fraud Risk Assessment | ✅ Covered | `frank-van-dissel-uc4-fraud-risk-assessment.md`, `frank-van-dissel-uc2-previous-audit-intelligence.md` | Proactive fraud risk identification and pattern analysis covered |
| Forensic Audit | ❌ Not covered | — | No plan covers forensic investigation or financial irregularity analysis |

---

## Priority Gap Matrix

The following domains are highest priority based on **frequency of occurrence in real audits** × **absence from SAAF portfolio**:

| Priority | Domain | Suggested Plan | Effort |
|---|---|---|---|
| 🔴 High | Patch Management | `patch-management-audit-agent.md` | Low — script-based patch data analysis |
| 🔴 High | Backup & Recovery | `backup-recovery-audit-agent.md` | Low — backup log analysis |
| 🔴 High | Network Security | `network-security-audit-agent.md` | Medium — firewall rule analysis |
| 🔴 High | ICOFR / SOx | `icofr-sox-audit-agent.md` | Medium — COSO control framework mapping |
| 🟡 Medium | Business Continuity | `bc-dr-audit-agent.md` | Medium — BCP/DR test result analysis |
| 🟡 Medium | SDLC | `sdlc-audit-agent.md` | Medium — code review + CI/CD gate analysis |
| 🟡 Medium | Database Security | `database-audit-agent.md` | Medium — CIS benchmark comparison |
| 🟡 Medium | Cloud Governance | `cloud-governance-audit-agent.md` | Medium — AWS/Azure config analysis |
| 🟡 Medium | HR Security | `hr-security-audit-agent.md` | Low — joiner/mover/leaver workflow + background check tracing |
| 🟢 Low | Project Audit / PIR | `project-audit-agent.md` | Medium — project data from Jira/Confluence |
| 🟢 Low | ESG Reporting | `esg-audit-agent.md` | High — new domain, no established data sources |
| 🟢 Low | Sanctions & Export Controls | `sanctions-screening-agent.md` | High — requires external data feeds |

---

## Notes on Methodology

1. **Counting**: A domain is "Covered" if at least one plan addresses it as its primary scope. "Partially" means it appears as a sub-topic in one or more plans but the domain is not the plan's main focus.
2. **Infrastructure plans excluded from domain mapping**: `saaf-rag-knowledge-base.md`, `saaf-strapi-synthetic-data.md`, `saaf-jira-confluence-mcp.md`, `saaf-skills-registry-and-matching.md`, `saaf-intelligence-monitor.md`, `audit-automation-overview.md`, `audit-loop-orchestration-sdk.md`, `audit-agent-gamified-ui.md`, `audit-memory-knowledge-system.md`, `audit-subagent-coordination-framework.md`, `audit-workflow-automation-levels.md`, `n8n-audit-workflow-migration.md`, `open-source-audit-agent-framework.md`, `overnight-audit-batch-processing-agent.md`, `always-on-audit-agent.md`, `power-bi-audit-dashboard-mcp.md`, `audit-evidence-visualization.md` are infrastructure/meta plans that support all domains but are not domain-specific. Two exceptions: `audit-skills-transformation-curriculum.md` (partially covers IT Resource Management) and `cli-audit-system-wrapper.md` (partially covers Patch Management and IAM).
3. **ICFCOP mega-controls**: The ICFCOP plan (`icfcop-control-testing-agent.md`) covers 6 mega-controls (IAM, Change/SDLC, BC/DR, Incident/Problem, Data Protection, Vendor Risk) and therefore partially covers multiple domains simultaneously.
4. **Update trigger**: This document should be updated whenever a new SAAF plan is submitted or when the Domains.xlsx taxonomy changes.
