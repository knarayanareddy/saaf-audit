# Skills and Agents Reference

> **Source:** `SAAF Project Drive/Hand-out folder/Session 3 - Hackathon 2 (24-03-2026)/Skills and Agents examples.xlsx`  
> **Maintained by:** SAAF Project Organisation  
> **Purpose:** Reference catalog of 12 agent/skill archetypes for internal audit, organized by audit phase. Each entry includes building blocks mapped to the four SAAF pillars (Prompts, Tools, Regulatory, Outputs).

See also: [`plans/hackathon-3/saaf-skills-registry-and-matching.md`](../../plans/hackathon-3/saaf-skills-registry-and-matching.md) — skills questionnaire and matching workflow.

---

## Agents by Audit Phase

### Phase 1: Planning & Scoping

#### Risk Assessment Agent

| Field | Detail |
|---|---|
| **Audit Phase** | Planning |
| **What it does** | Analyzes historical data, previous audit reports, board minutes, and industry trends to identify potential high-risk areas |
| **Prompts** | Risk narrative drafting logic |
| **Tools** | Document parsing scripts |
| **Regulatory** | Risk Appetite framework |
| **Outputs** | Risk ranking with narrative rationale |
| **Related SAAF plans** | `frank-van-dissel-uc2-previous-audit-intelligence.md`, `frank-van-dissel-uc4-fraud-risk-assessment.md`, `anonymous-audit-rep-analysis.md` |

#### Audit Program Generator Agent

| Field | Detail |
|---|---|
| **Audit Phase** | Planning |
| **What it does** | Generates a customized audit work program based on audit scope and relevant standards (ISO 27001, COBIT, DORA, NIST) |
| **Prompts** | Control-to-standard mapping logic |
| **Tools** | — |
| **Regulatory** | Applicable legal/standard frameworks |
| **Outputs** | Structured audit work program |
| **Related SAAF plans** | `frank-van-dissel-uc8-audit-work-program.md`, `floris-stokkers-work-program-agent.md`, `the-rcm-rangers-audit-work-program-agent.md` |

---

### Phase 2: Evidence Gathering

#### Automated Evidence Harvester

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Automatically collects evidence from target systems via APIs or automated scripts (Active Directory, AWS, Azure, SAP logs) |
| **Prompts** | — |
| **Tools** | API connectors / Python scripts (MCP server) |
| **Regulatory** | Security / Access permissions |
| **Outputs** | Raw datasets with integrity hash |
| **Related SAAF plans** | `frank-van-dissel-uc6-it-dependency-identifier.md`, `plans/hackathon-3/saaf-jira-confluence-mcp.md` |

#### Evidence Integrity Checker

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Validates that provided evidence meets basic audit trail requirements (timestamps, no manual alteration, population completeness) |
| **Prompts** | Document validation logic (chain of thought) |
| **Tools** | — |
| **Regulatory** | GIAS evidence sufficiency standards |
| **Outputs** | Go/No-Go report for auditor |
| **Related SAAF plans** | `mollie-group-x-evidence-audit.md`, `frank-van-dissel-uc9-quality-resource-guard.md` |

---

### Phase 3: Analysis & Testing

#### User Access Reviewer (100% check)

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Analyzes the entire user population for access risks — dormant accounts, orphan accounts, SoD conflicts, leaver deactivation |
| **Prompts** | SoD analysis matrix logic |
| **Tools** | Data analysis scripts (Pandas) |
| **Regulatory** | ISO 27001 A.9, NIST SP 800-63 |
| **Outputs** | Exception report with risk classification |
| **Related SAAF plans** | `frank-van-dissel-uc1-policy-process-intake.md`, `example-synthetic-access-review.md` |

#### Change Management Analyzer

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Reconciles administrative change tickets (Jira/ServiceNow) with actual production deployments (GitHub/GitLab). Identifies unauthorized changes. |
| **Prompts** | Matching and anomaly detection logic |
| **Tools** | API connectors to Jira/GitHub |
| **Regulatory** | ITIL, COBIT (Change Management GITC) |
| **Outputs** | Compliance dashboard with exception list |
| **Related SAAF plans** | `frank-van-dissel-uc3-incident-issue-intelligence.md`, `plans/hackathon-3/saaf-jira-confluence-mcp.md` |

#### Financial 3-Way Match Agent

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Automates the classic financial control test by matching Purchase Orders (PO), Goods Receipts, and Invoices across 100% of the population |
| **Prompts** | Matching and rounding-tolerance logic |
| **Tools** | OCR capability |
| **Regulatory** | COSO, SOx |
| **Outputs** | Exception list with unmatched items |
| **Related SAAF plans** | `themontechristo-threewaysecurity.md` |

#### Policy Interpreter Agent (Compliance)

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Assesses internal company policies against external laws and regulations (GDPR, DORA, EU AI Act). Identifies gaps. |
| **Prompts** | Legal reasoning (chain of thought) |
| **Tools** | — |
| **Regulatory** | EU AI Act, GDPR legal text |
| **Outputs** | Gap analysis report |
| **Related SAAF plans** | `johannesiv-policy-to-controls-extractor.md`, `frank-van-dissel-uc5-regulatory-criteria.md`, `robeminem94-gdpr-ai-audit-agent.md` |

---

### Phase 3: Specialized Domains

#### AI Act Classifier Agent

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Assists in classifying AI systems under the EU AI Act (High Risk, Limited Risk, etc.) based on intended purpose and data types |
| **Prompts** | Multi-step classification logic |
| **Tools** | — |
| **Regulatory** | EU AI Act classification criteria |
| **Outputs** | AI system risk classification with rationale |
| **Related SAAF plans** | `ellert-van-der-vecht-llm-owasp.md`, `group-5-hackers-ai-audit-agents.md` |

#### DORA ICT Risk Reviewer

| Field | Detail |
|---|---|
| **Audit Phase** | Execution |
| **What it does** | Assesses an entity's ICT risk management framework against DORA requirements; analyzes incident reports and BC test summaries |
| **Prompts** | Risk narrative drafting logic |
| **Tools** | — |
| **Regulatory** | DORA regulation text |
| **Outputs** | DORA compliance assessment with gaps |
| **Related SAAF plans** | `frank-van-dissel-uc5-regulatory-criteria.md`, `rohan-sobha-compliance-report-generator.md` |

---

### Phase 4: Reporting

#### Findings Draftsman Agent

| Field | Detail |
|---|---|
| **Audit Phase** | Reporting |
| **What it does** | Converts raw audit exceptions into professional audit findings structured by Condition, Criterion, Cause, and Effect |
| **Prompts** | Narrative restructuring logic |
| **Tools** | — |
| **Regulatory** | Audit reporting standards |
| **Outputs** | Draft Audit Report with structured findings |
| **Related SAAF plans** | `mollie-group-x-evidence-audit.md`, `anonymous-audit-rep-analysis.md` |

#### Audit Chaser Bot

| Field | Detail |
|---|---|
| **Audit Phase** | Reporting / Follow-up |
| **What it does** | Manages communication with audit clients regarding missing evidence or open action plans. Sends automated reminders via email/Teams and escalates on deadlines. |
| **Prompts** | — |
| **Tools** | SMTP / Teams API connector |
| **Regulatory** | Escalation matrix |
| **Outputs** | Communication log, escalation triggers |
| **Related SAAF plans** | `diyve-garg-pbc-assistant-isabelle.md` |

---

## Summary Statistics

- **Total agents/skills:** 12
- **Phases covered:** Planning (2), Execution (7), Reporting (2), Follow-up (1)
- **Techniques mentioned:** Chain of thought, SoD analysis, OCR, API connectors, anomaly detection
- **Regulatory frameworks:** GDPR, DORA, EU AI Act, ISO 27001, COBIT, ITIL, COSO, SOx
