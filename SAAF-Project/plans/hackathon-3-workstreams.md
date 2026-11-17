# Hackathon #3 — Workstream Decomposition & Team Assignments

> **Purpose:** This document decomposes all 59 SAAF plans into shared components, workflow clusters, and concrete hackathon-day tracks — so that every group works on something distinct, infra is built once and consumed by all, and the day produces integrated end-to-end results.
>
> **Hackathon:** April 21, 2026 · Wolters Kluwer, Alphen aan den Rijn · 4–5 hours build time
>
> **Key principle:** Everyone tests, but only one team builds each infrastructure layer.

---

## 1. Shared Components Matrix

These 7 building blocks appear across multiple plans. They must be built **once** (by Track 0) and consumed by all other tracks. Do NOT build your own version.

| # | Component | Used by | Built by | Time | Description |
|---|---|---|---|---|---|
| S1 | **Finding Schema validator** | 47 plans | Track 0 | 15 min | JSON schema (`outputs/schemas/finding-schema.json`) + Python validator function. All agents must output findings in this format: `id` (F-XXXX), `title`, `risk_rating`, `observation`, `recommendation`. |
| S2 | **Strapi Synthetic Data sandbox** | 34 plans | Track 0 | 1h | Docker instance with 5 content types: Jira incidents, access reviews, vendor contracts, audit findings, policy documents. All tracks test against this data — no one invents their own test data. |
| S3 | **RAG Knowledge Base** | 24 plans | Track 0 | 2h | ChromaDB + Nomic Embed Text v1.5 (local). Corpus: DORA full text, GDPR, ISO 27001, EU AI Act, GIAS 13.2/13.6, NIS2 summaries, all 59 SAAF plan files. Exposes `query(question, domain_filter) → chunks[]`. |
| S4 | **Jira/Confluence MCP servers** | 15+ plans | Track 0 | 1.5h | Two MCP servers: `jira_search(query)` and `confluence_search(query)`. Connected to Strapi synthetic data (or a mock Jira/Confluence). Agents call these instead of building their own integrations. |
| S5 | **Loop Orchestration SDK** | 15 plans | Track 0 | 2h | Python package `audit_sdk` with 3 primitives: `Task`, `Loop`, `Agent`. State persisted to JSON. Any track running batch operations uses this SDK instead of writing their own retry/state logic. |
| S6 | **Regulatory Corpus** (curated text) | 56 plans | Vaktechniek (Track 3) | ongoing | Plain-text excerpts of key articles from DORA, GDPR, ISO 27001, EU AI Act, GIAS, NIS2. Ingested into RAG KB (S3). Updated throughout the day as vaktechniek team identifies missing articles. |
| S7 | **Hallucination Detection layer** | all agent plans | Track 5 | 1.5h | 3-step skill: extract claims → RAG verification → risk score. Every finding produced by any track should pass through this layer before entering the audit dossier. |

### Component Usage per Plan

The following table shows which shared components each plan needs. Plans not listed here are reference/framework documents that don't produce runtime output.

| Plan | S1 | S2 | S3 | S4 | S5 | S6 | S7 |
|---|---|---|---|---|---|---|---|
| **GIAS Pipeline (UC1–UC9)** | | | | | | | |
| UC1 policy-process-intake | x | x | x | | | x | |
| UC2 previous-audit-intelligence | x | | x | | | x | |
| UC3 incident-issue-intelligence | x | x | | x | | x | |
| UC4 fraud-risk-assessment | x | x | x | | | x | x |
| UC5 regulatory-criteria | x | | x | | | x | |
| UC6 it-dependency-identifier | x | x | | x | | x | |
| UC7 rcm-builder (both versions) | x | x | x | | | x | |
| UC8 audit-work-program | x | | x | | | x | |
| UC9 quality-resource-guard | x | | | | | x | x |
| **Evidence Collection** | | | | | | | |
| document-evidence-extraction | x | x | | | | | |
| cli-audit-system-wrapper | x | x | | | | | |
| example-synthetic-access-review | x | x | | | | | |
| koekenpan-ia-fieldwork-preparation | x | x | | x | | x | |
| diyve-garg-pbc-assistant-isabelle | x | | | | | | |
| grc-copilot-mindshift-agent | | | | | | | |
| mollie-group-x-evidence-audit | x | x | | | | | |
| **Compliance Assessment** | | | | | | | |
| robeminem94-gdpr-ai-audit-agent | x | x | x | | | x | x |
| johannesiv-policy-to-controls-extractor | x | | x | | | x | |
| eu-ai-act-compliance-monitor | x | | x | | | x | x |
| icfcop-control-testing-agent | x | x | x | | | x | |
| robeminem94-vendor-guard | x | x | x | | | x | x |
| rohan-sobha-compliance-report-generator | x | | x | | | x | |
| ai-agent-visibility-scanner | x | | | | | | |
| **Reporting** | | | | | | | |
| audit-report-generator-from-work-program | x | | | | | | x |
| audit-evidence-visualization | x | | | | | | |
| power-bi-audit-dashboard-mcp | x | | | | | | |
| anonymous-audit-rep-analysis | x | | | | | | |
| themontechristo-threewaysecurity | x | x | | | | | |
| **Agent Infrastructure** | | | | | | | |
| audit-loop-orchestration-sdk | | | | | x | | |
| overnight-audit-batch-processing-agent | x | | | | x | | |
| audit-subagent-coordination-framework | x | x | | | | | x |
| always-on-audit-agent | | | x | | | x | |
| audit-agent-gamified-ui | | | | | x | | |
| open-source-audit-agent-framework | | | | | | | |
| **AI Governance & Quality** | | | | | | | |
| ellert-van-der-vecht-llm-owasp | x | | | | | | |
| owasp-ai-testing-agent | x | | x | | | | |
| llm-hallucination-detection-agent | x | | x | | | | |
| ai-audit-explainability-framework | x | | | | | | |
| ellert-van-der-vecht-multi-model-validation | x | | | | | | |

---

## 2. Workflow Clusters

### Cluster 1: GIAS Audit Planning Pipeline

**9 plans** — sequential pipeline designed by Frank van Dissel & Lauren Browne (Mollie).

```
UC1 → UC2 → UC3 → UC4 → UC5 → UC6 → UC7 → UC8 → UC9
 │         │                       │         │
 Policy    Previous   Incidents  Fraud   Regulatory  IT Deps   RCM    Work Prog  Quality
 Intake    Audits    & Issues   Risk    Criteria    Mapping   Builder Generator  Guard
```

- **Input:** Synthetic policy document + Strapi data
- **Output:** Complete audit planning package: Risk Control Matrix + Work Program + Quality Report
- **Previous contributors:** Frank van Dissel, Lauren Browne (Mollie), The Control Freaks (UC7 alt.)
- **Dependencies:** S2 (Strapi), S3 (RAG KB), S4 (Jira MCP), S6 (Regulatory Corpus)

### Cluster 2: Evidence Collection & Extraction

**7 plans** — parallel (each plan handles a different evidence type).

| Plan | Evidence type | Input | Output |
|---|---|---|---|
| document-evidence-extraction | PDF/scanned policy docs | PDF file | Structured JSON (controls, gaps) |
| cli-audit-system-wrapper | AD/Splunk/SAP system data | CLI commands (allowlisted) | System query results |
| example-synthetic-access-review | IAM access data | CSV/JSON user list | Access review findings |
| koekenpan-ia-fieldwork-preparation | Jira tickets + policies | Jira MCP + Confluence MCP | Fieldwork preparation pack |
| diyve-garg-pbc-assistant-isabelle | PBC email requests | Email templates | Evidence request tracker |
| grc-copilot-mindshift-agent | M365 data (Teams, SharePoint) | Copilot prompts | Meeting summaries, policy excerpts |
| mollie-group-x-evidence-audit | Evidence completeness | Evidence folder | Completeness analysis |

- **Common pattern:** Raw evidence in → structured data out → finding schema JSON
- **Previous contributors:** KOEKENPAN, Diyve Garg, Jurien Huisman, Schuberg Philis (GRC), Mollie Group X
- **Dependencies:** S1 (Finding Schema), S2 (Strapi)

### Cluster 3: Compliance & Regulatory Assessment

**7 plans** — parallel (each plan covers a different compliance framework).

| Plan | Framework | Key assessment |
|---|---|---|
| robeminem94-gdpr-ai-audit-agent | GDPR | Data subject rights, DPIAs, breach notification |
| johannesiv-policy-to-controls-extractor | ISO 27001 / GDPR | Policy → control mapping completeness |
| eu-ai-act-compliance-monitor | EU AI Act | AI system classification, ALTAI self-assessment, GPAI Art. 51–56 |
| icfcop-control-testing-agent | 12 frameworks | Cross-framework mega-control testing (IAM, Change, BC/DR, Incident, Data, Vendor) |
| robeminem94-vendor-guard | DORA | Vendor risk, SOC1/2 review, SLA monitoring |
| rohan-sobha-compliance-report-generator | Multiple | Multi-framework compliance report generation |
| ai-agent-visibility-scanner | Shadow AI | Enterprise AI inventory and risk assessment |

- **Common pattern:** Framework requirements → gap identification → finding with regulatory citation
- **Previous contributors:** robeminem94, JohannesIV, Rohan Sobha, Schuberg Philis (ICFCOP)
- **Dependencies:** S1 (Finding Schema), S3 (RAG KB), S6 (Regulatory Corpus)

### Cluster 4: Reporting & Visualization

**5 plans** — downstream consumers of findings from all other clusters.

| Plan | Output type | Input |
|---|---|---|
| audit-report-generator-from-work-program | Draft audit report (Markdown) | Completed work program JSON |
| audit-evidence-visualization | HTML visuals (heat maps, traffic lights) | Findings JSON |
| power-bi-audit-dashboard-mcp | Power BI dashboard | Findings JSON via MCP |
| anonymous-audit-rep-analysis | Repeating observation analysis | Finding history JSON |
| themontechristo-threewaysecurity | 3-way match results | P2P transaction data |

- **Key dependency:** This cluster needs **output from Clusters 1–3** (findings in schema format). Schedule this for the afternoon (after other tracks have produced findings).
- **Previous contributors:** Eduward (Mollie, report generator), TheMonteCristo, Anonymous

### Cluster 5: Agent Infrastructure & Orchestration

**8 plans** — builds the "engine room" that powers all agents.

| Plan | What it provides | Who uses it |
|---|---|---|
| audit-loop-orchestration-sdk | Task/Loop/Agent Python SDK | All batch agents |
| overnight-audit-batch-processing-agent | "Ralph loop" overnight execution | Any agent running >50 tasks |
| audit-subagent-coordination-framework | Multi-agent debate (3–5 agents) | High-stakes findings |
| always-on-audit-agent | 24/7 field auditor assistant | Field auditors |
| open-source-audit-agent-framework | Local LLM (GLM 4.7 + Ollama) | Orgs without cloud API budget |
| audit-agent-gamified-ui | Fleet manager dashboard | Audit leads monitoring agents |
| n8n-audit-workflow-migration | n8n → Claude agent migration | Orgs currently using n8n |
| on-premise-ai-compute-decision-framework | GPU vs API decision framework | Orgs evaluating hardware |

- **Note:** The SDK (plan 1) is Track 0 infra. The others are independent and can be demo'd standalone.
- **Previous contributors:** Mathijs Schouten (all plans in this cluster)

### Cluster 6: AI Governance & Quality

**5 plans** — cross-cutting validation layer. Tests output from all other tracks.

| Plan | What it validates | Method |
|---|---|---|
| ellert-van-der-vecht-llm-owasp | Agent security (OWASP LLM Top 10) | Codebase scan against 10 controls |
| owasp-ai-testing-agent | AI system security (250-page guide) | 12 operational test procedures (AT-01–AT-12) |
| llm-hallucination-detection-agent | Finding accuracy | 3-step claim extraction → RAG verification |
| ai-audit-explainability-framework | Finding transparency | CoT reasoning + 5-question explainability annex |
| ellert-van-der-vecht-multi-model-validation | Cross-model agreement | Same prompt through Claude + GPT + local LLM |

- **Key principle:** This cluster does NOT produce its own audit content. It validates and quality-checks output from Tracks 1–4.
- **Previous contributors:** Ellert van der Vecht (Schuberg Philis)

---

## 3. Dependency Graph

```
                    ┌─────────────────────────────────────────────┐
                    │          TRACK 0: INFRASTRUCTURE            │
                    │                                             │
                    │  S1 Finding Schema    S2 Strapi Sandbox     │
                    │  S3 RAG Knowledge     S4 Jira/Confluence    │
                    │  S5 Loop SDK                                │
                    │  ⏱ First 2 hours, then helpdesk             │
                    └────────────┬────────────────────────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ TRACK 1          │  │ TRACK 2          │  │ TRACK 3          │
│ GIAS Pipeline    │  │ Evidence         │  │ Compliance       │
│                  │  │ Extraction       │  │ Assessment       │
│ UC1→UC9          │  │                  │  │                  │
│ Needs: S2,S3,S4  │  │ PDF, CLI, IAM,  │  │ GDPR, EU AI Act, │
│        S6        │  │ M365, PBC       │  │ DORA, ICFCOP     │
│                  │  │ Needs: S1,S2     │  │ Needs: S1,S3,S6  │
│ Output: RCM +    │  │                  │  │                  │
│ Work Program     │  │ Output: Parsed   │  │ Output: Gap      │
│                  │  │ evidence JSON    │  │ reports, findings │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └──────────┬──────────┘                     │
                    │                                │
                    ▼                                │
         ┌──────────────────┐                        │
         │ TRACK 4          │◀───────────────────────┘
         │ Reporting        │
         │                  │
         │ Needs: Findings  │
         │ from Tracks 1-3  │
         │                  │
         │ Output: Reports, │
         │ dashboards,      │
         │ visualizations   │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ TRACK 5          │
         │ AI Quality       │
         │                  │
         │ Tests output     │
         │ from ALL tracks  │
         │                  │
         │ Output: Quality  │
         │ scores, OWASP    │
         │ audit reports    │
         └──────────────────┘
```

### Timing dependencies

| Time | Track 0 | Track 1 | Track 2 | Track 3 | Track 4 | Track 5 |
|---|---|---|---|---|---|---|
| 09:30–11:00 | Build S1–S5 | UC1–UC3 (can start with basic Claude calls) | PDF extraction, CLI wrapper (no infra needed) | Start EU AI Act classification (no infra needed) | Design report templates | Study OWASP procedures |
| 11:00 | **Infra ready** → helpdesk | Switch to RAG-dependent UCs (UC2, UC5) | Connect to Strapi for test data | Connect to RAG KB for regulatory lookup | Wait for findings from Tracks 1–3 | Prepare test harness |
| 11:00–13:00 | Support other tracks | UC4–UC7 | Full extraction pipeline | GDPR + ICFCOP assessments | Generate first reports from early findings | Run hallucination detection on early findings |
| 13:30–15:30 | Monitor, fix issues | UC8–UC9, quality checks | Cross-connect with Track 1 (evidence → RCM) | Vendor Guard, visibility scanner | Full reports from all tracks | OWASP audit on Track 1 agents |
| 15:30–16:30 | Demo prep | Demo: end-to-end pipeline | Demo: evidence extraction showcase | Demo: compliance dashboard | Demo: generated report | Demo: quality report on another track's agent |

---

## 4. Hackathon Day Tracks

### Track 0: Shared Infrastructure

> **Mission:** Build the foundation that all other tracks depend on. First 2 hours: build. Rest of day: helpdesk.

**Plans:**
- [`saaf-strapi-synthetic-data.md`](hackathon-3/saaf-strapi-synthetic-data.md)
- [`saaf-rag-knowledge-base.md`](hackathon-3/saaf-rag-knowledge-base.md)
- [`saaf-jira-confluence-mcp.md`](hackathon-3/saaf-jira-confluence-mcp.md)
- [`audit-loop-orchestration-sdk.md`](hackathon-3/audit-loop-orchestration-sdk.md)

**Concrete tasks (4–5h):**

| # | Task | Time | Output |
|---|---|---|---|
| 0.1 | Deploy Strapi Docker container, seed 5 content types (incidents, access reviews, vendor contracts, findings, policies) | 45 min | Running Strapi at localhost:1337 |
| 0.2 | Set up ChromaDB + ingest regulatory corpus (DORA, GDPR, ISO 27001, EU AI Act, GIAS, all 59 plan files) | 60 min | `query("DORA RTO requirements")` returns relevant chunks |
| 0.3 | Stand up Jira MCP server + Confluence MCP server, point at Strapi data | 45 min | `jira_search("critical incidents Q1")` returns results |
| 0.4 | Implement Loop SDK core: `Task`, `Loop`, `Agent` classes with JSON persistence | 60 min | Python package importable by other tracks |
| 0.5 | Validate Finding Schema: write a `validate_finding(finding)` function | 15 min | Function returns True/False + error messages |
| 0.6 | Helpdesk: assist other tracks integrating with S1–S5 | remaining | Other tracks successfully call infra components |

**Team:** 2–3 Engineers
**Skills needed:** Python, Docker, ChromaDB, MCP protocol
**Dependencies:** None (this IS the foundation)
**End-of-day deliverable:** All 5 shared components running and tested

---

### Track 1: GIAS Audit Planning Pipeline

> **Mission:** Run the full UC1→UC9 audit planning pipeline against synthetic data and produce a complete RCM + Work Program.

**Plans:**
- [`frank-van-dissel-uc1-policy-process-intake.md`](hackathon-2/frank-van-dissel-uc1-policy-process-intake.md)
- [`frank-van-dissel-uc2-previous-audit-intelligence.md`](hackathon-2/frank-van-dissel-uc2-previous-audit-intelligence.md)
- [`frank-van-dissel-uc3-incident-issue-intelligence.md`](hackathon-2/frank-van-dissel-uc3-incident-issue-intelligence.md)
- [`frank-van-dissel-uc4-fraud-risk-assessment.md`](hackathon-2/frank-van-dissel-uc4-fraud-risk-assessment.md)
- [`frank-van-dissel-uc5-regulatory-criteria.md`](hackathon-2/frank-van-dissel-uc5-regulatory-criteria.md)
- [`frank-van-dissel-uc6-it-dependency-identifier.md`](hackathon-2/frank-van-dissel-uc6-it-dependency-identifier.md)
- [`frank-van-dissel-uc7-rcm-builder.md`](hackathon-2/frank-van-dissel-uc7-rcm-builder.md) / [`the-control-freaks-uc7-rcm-builder.md`](hackathon-2/the-control-freaks-uc7-rcm-builder.md)
- [`frank-van-dissel-uc8-audit-work-program.md`](hackathon-2/frank-van-dissel-uc8-audit-work-program.md) / [`floris-stokkers-work-program-agent.md`](hackathon-2/floris-stokkers-work-program-agent.md)
- [`frank-van-dissel-uc9-quality-resource-guard.md`](hackathon-2/frank-van-dissel-uc9-quality-resource-guard.md)

**Concrete tasks (4–5h):**

| # | Task | Time | Waits for | Output |
|---|---|---|---|---|
| 1.1 | UC1: Ingest synthetic IAM policy (from Strapi or local PDF) → extract Context Brief + native control register | 45 min | — | `context_brief.json` |
| 1.2 | UC3: Query synthetic Jira incidents via MCP → classify and score for audit relevance | 45 min | S4 (Jira MCP) | `incident_intelligence.json` |
| 1.3 | UC4: Generate fraud scenarios for procure-to-pay process using fraud triangle prompts | 45 min | — | `fraud_risk_assessment.json` (20+ scenarios) |
| 1.4 | UC2+UC5: Query RAG KB for previous audit findings + applicable regulatory criteria | 45 min | S3 (RAG KB) | `previous_audits.json`, `regulatory_criteria.json` |
| 1.5 | UC7: Build RCM from outputs of 1.1–1.4. Test Control Freaks version and Frank version, compare | 90 min | Tasks 1.1–1.4 | `rcm.json` (30+ controls with risks mapped) |
| 1.6 | UC8: Generate work program from RCM. Assign test procedures per control | 45 min | Task 1.5 | `work_program.json` |
| 1.7 | UC9: Quality check entire pipeline output (completeness, consistency, coverage) | 30 min | Task 1.6 | `quality_report.json` |

**Team:** 2 Auditors + 1 Vaktechniek + 1 Analyst
**Skills needed:** Audit methodology, GIAS 13.2/13.6, Python basics, Claude prompting
**Previous contributors:** Frank van Dissel, Lauren Browne (Mollie), Control Freaks, Floris Stokkers, Inge Garretsen, RCM Rangers
**Dependencies:** Track 0 (Strapi, RAG KB, Jira MCP)
**End-of-day deliverable:** Complete RCM + Work Program for IAM audit domain, generated end-to-end

---

### Track 2: Evidence Collection & Extraction

> **Mission:** Build and test evidence extraction pipelines for 4 different evidence types. Prove that AI can reliably extract structured data from messy audit evidence.

**Plans:**
- [`document-evidence-extraction-agent.md`](hackathon-3/document-evidence-extraction-agent.md)
- [`cli-audit-system-wrapper.md`](hackathon-3/cli-audit-system-wrapper.md)
- [`example-synthetic-access-review.md`](hackathon-2/example-synthetic-access-review.md)
- [`koekenpan-ia-fieldwork-preparation.md`](hackathon-2/koekenpan-ia-fieldwork-preparation.md)
- [`diyve-garg-pbc-assistant-isabelle.md`](hackathon-2/diyve-garg-pbc-assistant-isabelle.md)
- [`grc-copilot-mindshift-agent.md`](hackathon-3/grc-copilot-mindshift-agent.md)
- [`mollie-group-x-evidence-audit.md`](alignment/mollie-group-x-evidence-audit.md)

**Concrete tasks (4–5h):**

| # | Task | Time | Output |
|---|---|---|---|
| 2.1 | OCR extraction: run `extract-evidence.py` on 3 synthetic PDFs (access policy, change policy, BCP) | 60 min | 3 structured JSON files with extracted controls + gaps |
| 2.2 | Access review: run synthetic access review agent on 200-record Strapi dataset | 45 min | Access review findings (orphan accounts, SoD violations) |
| 2.3 | CLI wrapper: test 3 allowlisted commands (AD inactive users, Splunk query, patch status) | 45 min | System query results in finding schema format |
| 2.4 | Fieldwork prep: generate fieldwork preparation pack for IAM audit from Jira + Confluence | 45 min | Fieldwork prep document (key contacts, open issues, prior findings) |
| 2.5 | M365 Copilot: test 4 cheat sheet prompts in real Copilot environment (if licensed) | 45 min | Validated prompt templates with actual Copilot output |
| 2.6 | Precision test: compare AI extraction vs. manual extraction on 1 policy document | 45 min | Precision/recall table: did the AI find all the controls? |

**Team:** 1 Auditor + 1 Analyst + 1 Engineer
**Skills needed:** Document processing, Python, Claude Vision API, audit evidence standards
**Previous contributors:** KOEKENPAN, Diyve Garg, Schuberg Philis (GRC), Mollie Group X
**Dependencies:** Track 0 (Strapi for test data, Finding Schema)
**End-of-day deliverable:** 4 working extraction pipelines + precision/recall benchmark

---

### Track 3: Compliance & Regulatory Assessment

> **Mission:** Run framework-specific compliance assessments against synthetic data. Produce gap reports with regulatory citations.

**Plans:**
- [`robeminem94-gdpr-ai-audit-agent.md`](hackathon-2/robeminem94-gdpr-ai-audit-agent.md)
- [`johannesiv-policy-to-controls-extractor.md`](hackathon-2/johannesiv-policy-to-controls-extractor.md)
- [`eu-ai-act-compliance-monitor.md`](hackathon-3/eu-ai-act-compliance-monitor.md)
- [`icfcop-control-testing-agent.md`](hackathon-3/icfcop-control-testing-agent.md)
- [`robeminem94-vendor-guard.md`](hackathon-2/robeminem94-vendor-guard.md)
- [`rohan-sobha-compliance-report-generator.md`](hackathon-2/rohan-sobha-compliance-report-generator.md)
- [`ai-agent-visibility-scanner.md`](hackathon-3/ai-agent-visibility-scanner.md)

**Concrete tasks (4–5h):**

| # | Task | Time | Waits for | Output |
|---|---|---|---|---|
| 3.1 | EU AI Act: classify 3 synthetic AI systems (chatbot, credit scorer, HR screening tool) per Annex III | 45 min | — | Classification report (prohibited/high/limited/minimal per system) |
| 3.2 | GDPR: run GDPR agent against synthetic DPIA document from Strapi | 60 min | S3 (RAG KB) | GDPR gap report with Article references |
| 3.3 | ICFCOP: test 1 mega-control domain (IAM) across 3 frameworks (ISO 27001, DORA, NIS2) | 60 min | S3 (RAG KB) | Cross-framework control test results |
| 3.4 | Vendor Guard: assess 2 synthetic vendor contracts (1 critical, 1 non-critical) | 45 min | S2 (Strapi) | Vendor risk ratings with DORA citations |
| 3.5 | Policy extractor: run policy-to-controls on synthetic ISO 27001 policy | 45 min | — | Control mapping with completeness score |
| 3.6 | Curate regulatory corpus: identify missing regulatory text needed by all tracks, add to RAG KB | ongoing | S3 (RAG KB) | Updated corpus with regulatory excerpts |

**Team:** 2 Vaktechniek + 1 Analyst + 1 Auditor
**Skills needed:** GDPR, DORA, EU AI Act, ISO 27001, GIAS, compliance methodology
**Previous contributors:** robeminem94, JohannesIV, Rohan Sobha, Schuberg Philis (ICFCOP), Patrick Chu (NOREA)
**Dependencies:** Track 0 (RAG KB, Strapi, Finding Schema)
**End-of-day deliverable:** 5 framework-specific gap reports + curated regulatory corpus

---

### Track 4: Reporting & Visualization

> **Mission:** Convert raw findings from Tracks 1–3 into polished audit reports and visual dashboards. This track starts later (needs findings as input).

**Plans:**
- [`audit-report-generator-from-work-program.md`](hackathon-3/audit-report-generator-from-work-program.md)
- [`audit-evidence-visualization.md`](hackathon-3/audit-evidence-visualization.md)
- [`power-bi-audit-dashboard-mcp.md`](hackathon-3/power-bi-audit-dashboard-mcp.md)
- [`anonymous-audit-rep-analysis.md`](hackathon-2/anonymous-audit-rep-analysis.md)
- [`themontechristo-threewaysecurity.md`](hackathon-2/themontechristo-threewaysecurity.md)

**Concrete tasks (4–5h):**

| # | Task | Time | Waits for | Output |
|---|---|---|---|---|
| 4.1 | Design report template: define sections (exec summary, findings, recommendations) | 45 min | — | Markdown report template |
| 4.2 | 3-way match: run TheMonteCristo's P2P matching on synthetic Strapi data | 60 min | S2 (Strapi) | Match results with exceptions flagged |
| 4.3 | Evidence visualization: generate 3 HTML visuals (heat map, traffic light, control matrix) from sample findings | 60 min | Findings from Track 1 or 3 | 3 standalone HTML files |
| 4.4 | Report generation: convert Track 1's work program output to draft audit report | 60 min | Track 1 output | Complete draft audit report (Markdown) |
| 4.5 | Power BI: push 10 findings to Power BI via MCP (or mock endpoint) | 45 min | Findings from any track | Power BI dataset populated |
| 4.6 | Repeating observation analysis: analyse 2 years of synthetic finding history for patterns | 45 min | S2 (Strapi) | Trend report (which findings keep recurring) |

**Team:** 1 Analyst + 1 Engineer + 1 Auditor (optional)
**Skills needed:** Data visualization, Python, report writing, Power BI (optional)
**Previous contributors:** Eduward (Mollie), TheMonteCristo, Anonymous
**Dependencies:** Findings from Tracks 1–3 (start design work in morning, generate reports in afternoon)
**End-of-day deliverable:** 1 complete draft audit report + 3 evidence visualizations + Power BI proof-of-concept

---

### Track 5: AI Governance & Quality Assurance

> **Mission:** Be the "second pair of eyes" for every other track. Test agents for security, validate findings for accuracy, and ensure everything is explainable.

**Plans:**
- [`ellert-van-der-vecht-llm-owasp.md`](hackathon-2/ellert-van-der-vecht-llm-owasp.md)
- [`owasp-ai-testing-agent.md`](hackathon-3/owasp-ai-testing-agent.md)
- [`llm-hallucination-detection-agent.md`](hackathon-3/llm-hallucination-detection-agent.md)
- [`ai-audit-explainability-framework.md`](hackathon-3/ai-audit-explainability-framework.md)
- [`ellert-van-der-vecht-multi-model-validation.md`](hackathon-2/ellert-van-der-vecht-multi-model-validation.md)

**Concrete tasks (4–5h):**

| # | Task | Time | Waits for | Output |
|---|---|---|---|---|
| 5.1 | Set up hallucination detection skill: implement claim extraction → RAG verification → risk scoring | 90 min | S3 (RAG KB) | Working `check_finding()` function |
| 5.2 | OWASP LLM audit: run Ellert's 10-control audit against 1 agent from Track 1 or Track 3 | 60 min | An agent from another track | OWASP LLM audit report (PASS/WARN/FAIL per control) |
| 5.3 | Hallucination check: run 5 findings from Tracks 1–3 through the hallucination detector | 45 min | Findings from other tracks | Hallucination risk scores (LOW/MEDIUM/HIGH per finding) |
| 5.4 | Explainability annex: generate chain-of-thought explainability annex for 2 high-risk findings | 45 min | High-risk findings | 2 completed explainability annexes with evidence anchoring |
| 5.5 | Multi-model validation: run the same audit prompt through Claude Sonnet + local LLM (Ollama), compare | 45 min | — | Comparison table (agreement %, divergence analysis) |

**Team:** 1 Engineer + 1 Vaktechniek
**Skills needed:** AI security (OWASP), prompt engineering, Python, critical review
**Previous contributors:** Ellert van der Vecht (Schuberg Philis)
**Dependencies:** Agents and findings from all other tracks (this track is the "quality gate")
**End-of-day deliverable:** OWASP audit report on 1 agent + hallucination scores for 5 findings + 2 explainability annexes

---

## 5. Plans Not Assigned to a Track

The following plans are reference/framework documents or strategic plans that do not require hackathon build time. They provide context and guidance for the tracks above.

| Plan | Type | Why no track |
|---|---|---|
| [`audit-automation-overview.md`](hackathon-3/audit-automation-overview.md) | Reference | Lifecycle overview — context for all tracks |
| [`audit-workflow-automation-levels.md`](hackathon-3/audit-workflow-automation-levels.md) | Reference | Level 1/2/3 maturity framework — guidance |
| [`audit-skills-transformation-curriculum.md`](hackathon-3/audit-skills-transformation-curriculum.md) | Reference | Skills framework — used for group formation |
| [`audit-memory-knowledge-system.md`](hackathon-3/audit-memory-knowledge-system.md) | Workflow | Obsidian vault — individual setup, not team task |
| [`saaf-skills-registry-and-matching.md`](hackathon-3/saaf-skills-registry-and-matching.md) | Workflow | Matching tool — used pre-hackathon, not on the day |
| [`saaf-intelligence-monitor.md`](hackathon-3/saaf-intelligence-monitor.md) | Agent | News monitoring — runs weekly, not a hackathon build |
| [`on-premise-ai-compute-decision-framework.md`](hackathon-3/on-premise-ai-compute-decision-framework.md) | Framework | Hardware decision — strategic, not a build task |
| [`n8n-audit-workflow-migration.md`](hackathon-3/n8n-audit-workflow-migration.md) | Workflow | Migration guide — for orgs using n8n |
| [`overnight-audit-batch-processing-agent.md`](hackathon-3/overnight-audit-batch-processing-agent.md) | Agent | Overnight execution — cannot demo in 4h |
| [`always-on-audit-agent.md`](hackathon-3/always-on-audit-agent.md) | Agent | 24/7 agent — long-running, not a sprint task |
| [`open-source-audit-agent-framework.md`](hackathon-3/open-source-audit-agent-framework.md) | Skill | Local LLM setup — individual, takes time to install |
| [`audit-agent-gamified-ui.md`](hackathon-3/audit-agent-gamified-ui.md) | Workflow | Fleet dashboard — needs running agents first |
| [`linda-nyvelius-team-hightable.md`](hackathon-2/linda-nyvelius-team-hightable.md) | Skill | TeamMate+ specific — vendor-dependent |
| [`auditflow-ai.md`](alignment/auditflow-ai.md) | Alignment | Strategic vision document |
| [`group-5-hackers-ai-audit-agents.md`](alignment/group-5-hackers-ai-audit-agents.md) | Alignment | Strategic vision document |
| [`team-67-intelligent-audit-agents.md`](alignment/team-67-intelligent-audit-agents.md) | Alignment | Strategic vision document |
| [`mollie-group-x-evidence-audit.md`](alignment/mollie-group-x-evidence-audit.md) | Alignment | Strategic vision document |

---

## 6. Merge Candidates

These plan groups cover the same domain and should be consolidated to avoid duplicate effort:

| Group | Current plans | Recommendation |
|---|---|---|
| **Work Programs** | `frank-van-dissel-uc8`, `floris-stokkers-work-program-agent`, `inge-garretsen-audit-work-program-agent`, `the-rcm-rangers-audit-work-program-agent` (4 plans) | Use Frank's UC8 as the canonical pipeline version. Floris adds the "autofill from RCM" feature. Inge and RCM Rangers become attribution stubs pointing to canonical. |
| **RCM Builders** | `frank-van-dissel-uc7-rcm-builder`, `the-control-freaks-uc7-rcm-builder` (2 plans) | Both valuable — Control Freaks version is more structured (GIAS-based). Run both at hackathon and compare outputs. |
| **News Monitors** | `yellowraptor-whats-the-news`, `saaf-intelligence-monitor` (2 plans) | Yellowraptor = v1 (RSS scraper). Intelligence Monitor = v2 (adds Claude classification + weekly digest). Keep both; label as v1/v2. |
| **OWASP Security** | `ellert-van-der-vecht-llm-owasp`, `owasp-ai-testing-agent` (2 plans) | Complementary: Ellert's plan audits an agent's codebase. OWASP AI Testing Agent runs operational tests on a live system. Both in Track 5. |
| **Compliance Reports** | `rohan-sobha-compliance-report-generator`, `anonymous-audit-rep-analysis` (2 plans) | Different scope: Rohan generates from scratch; Anonymous analyses existing report history. Both useful, keep separate. |

---

## 7. Group Formation Guide

### Skill requirements per track

| Track | Auditors | Vaktechniek | Analysts | Engineers | Total |
|---|---|---|---|---|---|
| Track 0: Infrastructure | 0 | 0 | 0 | 2–3 | 2–3 |
| Track 1: GIAS Pipeline | 2 | 1 | 1 | 0 | 4 |
| Track 2: Evidence Extraction | 1 | 0 | 1 | 1 | 3 |
| Track 3: Compliance Assessment | 1 | 2 | 1 | 0 | 4 |
| Track 4: Reporting | 1 | 0 | 1 | 1 | 3 |
| Track 5: AI Quality | 0 | 1 | 0 | 1 | 2 |
| **Total** | **5** | **4** | **4** | **5–6** | **18–19** |

> **Note:** The table above shows the minimum team for 6 tracks with ~19 people. With 80+ participants, multiply: run 2–3 parallel instances of Tracks 1–3 on different audit domains (e.g., Track 1a: IAM audit, Track 1b: Change Management audit, Track 1c: Vendor audit). Each instance follows the same tasks but uses different synthetic data.

### Scaling to 80+ participants

| Participants | Configuration |
|---|---|
| 20 | 6 tracks as above (minimum viable) |
| 40 | Track 0 (3), Track 1 ×2 (8), Track 2 ×2 (6), Track 3 ×2 (8), Track 4 ×2 (6), Track 5 ×2 (4), flex (5) |
| 60 | Track 0 (4), Track 1 ×3 (12), Track 2 ×2 (6), Track 3 ×3 (12), Track 4 ×2 (6), Track 5 ×3 (6), flex (14) |
| 80+ | Track 0 (5), Track 1 ×4 (16), Track 2 ×3 (9), Track 3 ×4 (16), Track 4 ×3 (9), Track 5 ×3 (6), flex (19+) |

### Previous contributor suggestions

Participants who previously worked on a plan get an "experienced" badge. They can lead their track or choose to explore a different track for fresh perspective.

| Person / Group | Previous work | Suggested track |
|---|---|---|
| Frank van Dissel & Lauren Browne | UC1–UC9 (all 9 use cases) | Track 1 (GIAS Pipeline) — lead |
| The Control Freaks (Ilona, Imane, Peter, Guus, Bart, Joey, Mourad) | UC7 RCM Builder | Track 1 (GIAS Pipeline) — RCM focus |
| Floris Stokkers | Work program agent | Track 1 (GIAS Pipeline) — UC8 focus |
| Inge Garretsen | Work program agent | Track 1 (GIAS Pipeline) — UC8 focus |
| Ellert van der Vecht | OWASP LLM + multi-model validation | Track 5 (AI Quality) — lead |
| robeminem94 | GDPR agent + Vendor Guard | Track 3 (Compliance) — lead |
| JohannesIV | Policy-to-controls extractor | Track 3 (Compliance) |
| Rohan Sobha | Compliance report generator | Track 4 (Reporting) |
| KOEKENPAN | Fieldwork preparation | Track 2 (Evidence) |
| Diyve Garg, Juriën, Karim, Mourad | PBC assistant | Track 2 (Evidence) |
| TheMonteCristo | 3-way match | Track 4 (Reporting) |
| Eduward (Mollie) | Audit report from work program | Track 4 (Reporting) — lead |
| Schuberg Philis team | ICFCOP + GRC Copilot | Track 3 (Compliance) — ICFCOP focus |
| Yellowraptor | WhatsTheNews RSS scraper | Not a hackathon track (monitoring) |
| RCM Rangers | Work program agent | Track 1 (GIAS Pipeline) — UC8 focus |

### Free choice process

1. **Before the hackathon:** Share this document + the plan overview with all participants
2. **At 09:00:** Present the 6 tracks (5 min each), show dependency graph
3. **At 09:20:** Participants sign up for a track (first come, first served; max per track shown above)
4. **Suggestion system:** Show previous contributors per track. "You worked on UC7 at Hackathon #2 — Track 1 continues that work."
5. **Flex rule:** If a track is oversubscribed, organizers suggest alternatives based on the skill matrix

---

## 8. Hackathon Day Schedule

| Time | Activity | Notes |
|---|---|---|
| 09:00–09:15 | Welcome + overview | Present this workstream decomposition |
| 09:15–09:30 | Track presentations | 5 min per track: mission, tasks, what you'll build |
| 09:30–09:45 | Group formation | Participants choose tracks. Organizers balance skill mix. |
| 09:45–11:00 | **Sprint 1** | Track 0 builds infra. Tracks 1–5 start independent tasks. |
| 11:00–11:15 | **Infra checkpoint** | Track 0 confirms S1–S5 available. Quick demo of RAG query + Strapi. |
| 11:15–13:00 | **Sprint 2** | All tracks integrate with infra. Track 1 runs UC4–UC7. |
| 13:00–13:30 | Lunch + standup | Each track: 2 min status update. What's working? What's blocked? |
| 13:30–15:30 | **Sprint 3** | Cross-track integration. Track 4 uses findings from Tracks 1–3. Track 5 audits agents from other tracks. |
| 15:30–16:00 | Demo preparation | Each track prepares a 5-min demo showing their end-of-day deliverable. |
| 16:00–16:45 | **Demo session** | 6 tracks × 5 min demo + 2 min Q&A = ~45 min |
| 16:45–17:00 | Wrap-up | Lessons learned, what worked, what to improve for Hackathon #4. Commit everything to main. |

---

## Appendix: All 59 Plans by Track Assignment

| Plan | Session | Track | Role in track |
|---|---|---|---|
| `saaf-strapi-synthetic-data` | H3 | 0 | Strapi setup |
| `saaf-rag-knowledge-base` | H3 | 0 | RAG KB setup |
| `saaf-jira-confluence-mcp` | H3 | 0 | MCP servers |
| `audit-loop-orchestration-sdk` | H3 | 0 | SDK build |
| `frank-van-dissel-uc1-policy-process-intake` | H2 | 1 | Pipeline step 1 |
| `frank-van-dissel-uc2-previous-audit-intelligence` | H2 | 1 | Pipeline step 2 |
| `frank-van-dissel-uc3-incident-issue-intelligence` | H2 | 1 | Pipeline step 3 |
| `frank-van-dissel-uc4-fraud-risk-assessment` | H2 | 1 | Pipeline step 4 |
| `frank-van-dissel-uc5-regulatory-criteria` | H2 | 1 | Pipeline step 5 |
| `frank-van-dissel-uc6-it-dependency-identifier` | H2 | 1 | Pipeline step 6 |
| `frank-van-dissel-uc7-rcm-builder` | H2 | 1 | Pipeline step 7a |
| `the-control-freaks-uc7-rcm-builder` | H2 | 1 | Pipeline step 7b |
| `frank-van-dissel-uc8-audit-work-program` | H2 | 1 | Pipeline step 8 |
| `floris-stokkers-work-program-agent` | H2 | 1 | Pipeline step 8 (alt) |
| `inge-garretsen-audit-work-program-agent` | H2 | 1 | Pipeline step 8 (alt) |
| `the-rcm-rangers-audit-work-program-agent` | H2 | 1 | Pipeline step 8 (alt) |
| `frank-van-dissel-uc9-quality-resource-guard` | H2 | 1 | Pipeline step 9 |
| `document-evidence-extraction-agent` | H3 | 2 | PDF/OCR extraction |
| `cli-audit-system-wrapper` | H3 | 2 | System queries |
| `example-synthetic-access-review` | H2 | 2 | IAM access review |
| `koekenpan-ia-fieldwork-preparation` | H2 | 2 | Fieldwork prep |
| `diyve-garg-pbc-assistant-isabelle` | H2 | 2 | PBC requests |
| `grc-copilot-mindshift-agent` | H3 | 2 | M365 evidence |
| `mollie-group-x-evidence-audit` | Align | 2 | Evidence analysis |
| `robeminem94-gdpr-ai-audit-agent` | H2 | 3 | GDPR assessment |
| `johannesiv-policy-to-controls-extractor` | H2 | 3 | Policy → controls |
| `eu-ai-act-compliance-monitor` | H3 | 3 | EU AI Act |
| `icfcop-control-testing-agent` | H3 | 3 | Multi-framework |
| `robeminem94-vendor-guard` | H2 | 3 | DORA vendor risk |
| `rohan-sobha-compliance-report-generator` | H2 | 3 | Compliance reports |
| `ai-agent-visibility-scanner` | H3 | 3 | Shadow AI discovery |
| `audit-report-generator-from-work-program` | H3 | 4 | Report from WP |
| `audit-evidence-visualization` | H3 | 4 | HTML visuals |
| `power-bi-audit-dashboard-mcp` | H3 | 4 | Power BI MCP |
| `anonymous-audit-rep-analysis` | H2 | 4 | Repeat findings |
| `themontechristo-threewaysecurity` | H2 | 4 | 3-way match |
| `ellert-van-der-vecht-llm-owasp` | H2 | 5 | OWASP LLM Top 10 |
| `owasp-ai-testing-agent` | H3 | 5 | OWASP AI Testing Guide |
| `llm-hallucination-detection-agent` | H3 | 5 | Hallucination check |
| `ai-audit-explainability-framework` | H3 | 5 | Explainability annex |
| `ellert-van-der-vecht-multi-model-validation` | H2 | 5 | Multi-model compare |
| `audit-automation-overview` | H3 | — | Reference |
| `audit-workflow-automation-levels` | H3 | — | Reference |
| `audit-skills-transformation-curriculum` | H3 | — | Reference |
| `audit-memory-knowledge-system` | H3 | — | Reference |
| `saaf-skills-registry-and-matching` | H3 | — | Pre-hackathon |
| `saaf-intelligence-monitor` | H3 | — | Weekly job |
| `on-premise-ai-compute-decision-framework` | H3 | — | Strategic |
| `n8n-audit-workflow-migration` | H3 | — | Migration guide |
| `overnight-audit-batch-processing-agent` | H3 | — | Overnight (not sprint) |
| `always-on-audit-agent` | H3 | — | Long-running |
| `open-source-audit-agent-framework` | H3 | — | Local LLM setup |
| `audit-agent-gamified-ui` | H3 | — | Needs running agents |
| `audit-subagent-coordination-framework` | H3 | — | Enhancement (v2) |
| `linda-nyvelius-team-hightable` | H2 | — | Vendor-specific |
| `yellowraptor-whats-the-news` | H2 | — | v1 of monitor |
| `auditflow-ai` | Align | — | Vision doc |
| `group-5-hackers-ai-audit-agents` | Align | — | Vision doc |
| `team-67-intelligent-audit-agents` | Align | — | Vision doc |
