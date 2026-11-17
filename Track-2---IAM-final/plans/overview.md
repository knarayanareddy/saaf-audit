# SAAF Plans — Central Overview

> **Last updated:** April 2026 (Hackathon #3 — post video transcription analysis)  
> **Total plans:** 60 (4 Alignment + 27 Hackathon 2 + 29 Hackathon 3)  
> **Quality score:** 1 (minimal) → 5 (production-ready template)  
> **See also:** [`plans/gap-analysis.md`](gap-analysis.md) | [`plans/meta-analysis.md`](meta-analysis.md)

---

## How to Read This Table

| Column | Meaning |
|---|---|
| **Score** | 1–5 quality score based on template completeness, prompts, tools, regulatory coverage, output schema |
| **Missing** | Sections not yet filled in or thin |
| **Overlap** | Other plans covering similar ground |
| **Tool suggestion** | From `docs/reference/ai-tools-and-techniques.md` — recommended tech additions |

---

## Alignment Session Plans

| File | Type | Submitter / Org | Domain | Score | Missing / Notes | Overlaps |
|---|---|---|---|---|---|---|
| [`auditflow-ai.md`](alignment/auditflow-ai.md) | Workflow | SAAF / Unknown | Overall audit lifecycle | 3 | Limited tool code; no output schema | Overlaps with all hackathon plans — this is the umbrella |
| [`group-5-hackers-ai-audit-agents.md`](alignment/group-5-hackers-ai-audit-agents.md) | Agent | Group 5 / Multi-org | AI Governance — auditing AI systems | 3 | Regulatory section light; EU AI Act mapping shallow | `robeminem94-gdpr-ai-audit-agent.md`, `johannesiv-policy-to-controls-extractor.md` |
| [`mollie-group-x-evidence-audit.md`](alignment/mollie-group-x-evidence-audit.md) | Agent | Mollie Group X / Mollie | Evidence collection & analysis | 4 | Needs Strapi synthetic data hookup for demo | `diyve-garg-pbc-assistant-isabelle.md`, `koekenpan-ia-fieldwork-preparation.md` |
| [`team-67-intelligent-audit-agents.md`](alignment/team-67-intelligent-audit-agents.md) | Agent | Team 67 / Multi-org | Multi-domain (risk, compliance, ops) | 3 | Very broad scope; tool section underspecified | `frank-van-dissel-uc2`, `frank-van-dissel-uc4`, `rohan-sobha-compliance-report-generator` |

---

## Hackathon 2 Plans

| File | Type | Submitter / Org | Domain | Score | Missing / Notes | Overlaps |
|---|---|---|---|---|---|---|
| [`anonymous-audit-rep-analysis.md`](hackathon-2/anonymous-audit-rep-analysis.md) | Agent | Anonymous | Audit reporting — finding analysis | 3 | Output schema not linked to `finding-schema.json`; needs synthetic data example | `rohan-sobha-compliance-report-generator.md` |
| [`diyve-garg-pbc-assistant-isabelle.md`](hackathon-2/diyve-garg-pbc-assistant-isabelle.md) | Agent | Diyve Garg / Unknown | Evidence request (PBC assistant) | 4 | Needs email integration spec | `mollie-group-x-evidence-audit.md`, `koekenpan-ia-fieldwork-preparation.md` |
| [`ellert-van-der-vecht-llm-owasp.md`](hackathon-2/ellert-van-der-vecht-llm-owasp.md) | Workflow | Ellert van der Vecht / Schuberg Philis | AI Security — OWASP LLM Top 10 | 5 | Complete; Gandalf cross-ref added | None — unique domain |
| [`ellert-van-der-vecht-multi-model-validation.md`](hackathon-2/ellert-van-der-vecht-multi-model-validation.md) | Workflow | Ellert van der Vecht / Schuberg Philis | AI output validation (multi-model) | 4 | Benchmark dataset not yet specified | `ellert-van-der-vecht-llm-owasp.md` (same author, complementary) |
| [`immistyle-cuec-crosscheck-agent.md`](hackathon-2/immistyle-cuec-crosscheck-agent.md) | Agent | immistyle / Anonymous | Third-party risk — CUEC crosscheck & gap flagging | 4 | Strong use case; matching logic would benefit from RAG over org control library | `robeminem94-vendor-guard.md` |
| [`example-synthetic-access-review.md`](hackathon-2/example-synthetic-access-review.md) | Agent | Anonymous | IAM — user access review (100% population) | 4 | Finding format could align more tightly with `finding-schema.json` | `frank-van-dissel-uc6-it-dependency-identifier.md` (IAM data source) |
| [`floris-stokkers-work-program-agent.md`](hackathon-2/floris-stokkers-work-program-agent.md) | Agent | Floris Stokkers / Unknown | Audit planning — work program generation | 4 | Prompts strong; tool code thin | `frank-van-dissel-uc8-audit-work-program.md`, `inge-garretsen-audit-work-program-agent.md`, `the-rcm-rangers-audit-work-program-agent.md` |
| [`frank-van-dissel-uc1-policy-process-intake.md`](hackathon-2/frank-van-dissel-uc1-policy-process-intake.md) | Agent | Frank van Dissel / Unknown | Information Security Policy — intake & gap | 4 | Missing: automated policy retrieval from SharePoint/Confluence | `johannesiv-policy-to-controls-extractor.md` |
| [`frank-van-dissel-uc2-previous-audit-intelligence.md`](hackathon-2/frank-van-dissel-uc2-previous-audit-intelligence.md) | Agent | Frank van Dissel / Unknown | Audit planning — historical audit analysis | 4 | Needs RAG hookup for large audit dossier search | `saaf-rag-knowledge-base.md` (RAG infrastructure consumer) |
| [`frank-van-dissel-uc3-incident-issue-intelligence.md`](hackathon-2/frank-van-dissel-uc3-incident-issue-intelligence.md) | Agent | Frank van Dissel / Unknown | IT Ops — incident & change intelligence (Jira/GitHub) | 5 | Complete; primary consumer of `saaf-jira-confluence-mcp.md` | `saaf-jira-confluence-mcp.md` (infrastructure) |
| [`frank-van-dissel-uc4-fraud-risk-assessment.md`](hackathon-2/frank-van-dissel-uc4-fraud-risk-assessment.md) | Agent | Frank van Dissel / Unknown | Fraud Risk Assessment | 4 | Needs synthetic fraud scenario data in Strapi | `frank-van-dissel-uc2-previous-audit-intelligence.md` |
| [`frank-van-dissel-uc5-regulatory-criteria.md`](hackathon-2/frank-van-dissel-uc5-regulatory-criteria.md) | Skill | Frank van Dissel / Unknown | Compliance — regulatory criteria retrieval (DORA, GDPR, ISO) | 4 | Strong RAG candidate; corpus hookup to `saaf-rag-knowledge-base.md` missing | `saaf-rag-knowledge-base.md` (would be a primary consumer) |
| [`frank-van-dissel-uc6-it-dependency-identifier.md`](hackathon-2/frank-van-dissel-uc6-it-dependency-identifier.md) | Agent | Frank van Dissel / Unknown | IT Ops — IT dependency mapping (cloud, APIs) | 3 | Tool code thin; needs real API target (AWS Config, Azure Resource Graph) | `saaf-jira-confluence-mcp.md` (evidence collection) |
| [`frank-van-dissel-uc7-rcm-builder.md`](hackathon-2/frank-van-dissel-uc7-rcm-builder.md) | Agent | Frank van Dissel / Unknown | RCM (Risk & Control Matrix) building | 4 | Near-duplicate of `the-control-freaks-uc7-rcm-builder.md` — **merge candidate** | `the-control-freaks-uc7-rcm-builder.md`, `the-rcm-rangers-audit-work-program-agent.md` |
| [`frank-van-dissel-uc8-audit-work-program.md`](hackathon-2/frank-van-dissel-uc8-audit-work-program.md) | Agent | Frank van Dissel / Unknown | Audit planning — work program generation | 4 | Near-duplicate of `floris-stokkers-work-program-agent.md` — **merge candidate** | `floris-stokkers-work-program-agent.md`, `inge-garretsen-audit-work-program-agent.md` |
| [`frank-van-dissel-uc9-quality-resource-guard.md`](hackathon-2/frank-van-dissel-uc9-quality-resource-guard.md) | Agent | Frank van Dissel / Unknown | Audit quality — resource management | 3 | Scope underspecified; quality criteria not defined | Unique |
| [`inge-garretsen-audit-work-program-agent.md`](hackathon-2/inge-garretsen-audit-work-program-agent.md) | Agent | Inge Garretsen / Unknown | Audit planning — work program (UC 8) | 4 | Another work program variant; differentiation from Frank UC8 unclear | `frank-van-dissel-uc8-audit-work-program.md`, `floris-stokkers-work-program-agent.md` |
| [`johannesiv-policy-to-controls-extractor.md`](hackathon-2/johannesiv-policy-to-controls-extractor.md) | Agent | Johannes IV / Unknown | GDPR + EU AI Act — policy-to-controls extraction | 4 | Strong prompts; could add DORA + ISO 27001 in addition to GDPR/AI Act | `robeminem94-gdpr-ai-audit-agent.md`, `frank-van-dissel-uc1-policy-process-intake.md` |
| [`koekenpan-ia-fieldwork-preparation.md`](hackathon-2/koekenpan-ia-fieldwork-preparation.md) | Workflow | Koekenpan team / Unknown | Fieldwork preparation — evidence gathering | 4 | Confluence retrieval would benefit from `saaf-jira-confluence-mcp.md` | `diyve-garg-pbc-assistant-isabelle.md`, `mollie-group-x-evidence-audit.md` |
| [`linda-nyvelius-team-hightable.md`](hackathon-2/linda-nyvelius-team-hightable.md) | Agent | Linda Nyvelius / Unknown | TeamMate+ knowledge reuse | 3 | Very tool-specific (TeamMate+); limited generalizability; RAG approach would generalize it | `saaf-rag-knowledge-base.md` (architectural parallel) |
| [`robeminem94-gdpr-ai-audit-agent.md`](hackathon-2/robeminem94-gdpr-ai-audit-agent.md) | Agent | robeminem94 / Unknown | GDPR + EU AI Act audit | 4 | Strong regulatory; needs Strapi synthetic DPIA data | `johannesiv-policy-to-controls-extractor.md`, `group-5-hackers-ai-audit-agents.md` |
| [`robeminem94-vendor-guard.md`](hackathon-2/robeminem94-vendor-guard.md) | Agent | robeminem94 / Unknown | Third-party & vendor risk | 4 | SLA breach detection underdeveloped; Strapi vendor data hookup missing | `frank-van-dissel-uc9-quality-resource-guard.md` |
| [`rohan-sobha-compliance-report-generator.md`](hackathon-2/rohan-sobha-compliance-report-generator.md) | Agent | Rohan Sobha / Unknown | Compliance reporting — multi-framework | 4 | Strong output format; `finding-schema.json` alignment not explicit | `anonymous-audit-rep-analysis.md` |
| [`the-control-freaks-uc7-rcm-builder.md`](hackathon-2/the-control-freaks-uc7-rcm-builder.md) | Agent | The Control Freaks / Unknown | RCM Builder (UC 7) | 5 | Best-in-class for RCM; **merge target** for frank UC7 | `frank-van-dissel-uc7-rcm-builder.md` (merge candidate), `icfcop-control-testing-agent.md` |
| [`the-rcm-rangers-audit-work-program-agent.md`](hackathon-2/the-rcm-rangers-audit-work-program-agent.md) | Agent | The RCM Rangers / Unknown | RCM + work program (combined) | 3 | Combines two concerns (RCM + work program); section 6 thin | `the-control-freaks-uc7-rcm-builder.md`, `frank-van-dissel-uc8-audit-work-program.md` |
| [`themontechristo-threewaysecurity.md`](hackathon-2/themontechristo-threewaysecurity.md) | Agent | TheMonteChristo / Unknown | Financial — P2P/O2C 3-way match | 4 | Unique domain; needs synthetic ERP data in Strapi | Unique |
| [`yellowraptor-whats-the-news.md`](hackathon-2/yellowraptor-whats-the-news.md) | Skill | Yellowraptor / Anonymous | Regulatory monitoring — RSS aggregation | 4 | 30-source feed list added; Claude summarization stretch goal | `saaf-intelligence-monitor.md` (H3 successor) |

---

## Hackathon 3 Plans

_Session 1 batch (pre-video analysis — 8 plans):_

| File | Type | Submitter / Org | Domain | Score | Missing / Notes | Overlaps |
|---|---|---|---|---|---|---|
| [`audit-automation-overview.md`](hackathon-3/audit-automation-overview.md) | Workflow | Mathijs Schouten / SAAF | Meta — AI audit lifecycle overview | 4 | Living document; needs update after Hackathon #3 | Covers all domains — umbrella document |
| [`grc-copilot-mindshift-agent.md`](hackathon-3/grc-copilot-mindshift-agent.md) | Agent | Mathijs Schouten / Schuberg Philis | GRC — M365 Copilot adoption | 4 | PDF rendering not yet tested | `rohan-sobha-compliance-report-generator.md` |
| [`icfcop-control-testing-agent.md`](hackathon-3/icfcop-control-testing-agent.md) | Agent | Mathijs Schouten / Schuberg Philis | Multi-framework control testing (12 frameworks) | 5 | Complete; ICFCOP crosswalk JSON to build | `the-control-freaks-uc7-rcm-builder.md`, `frank-van-dissel-uc7` |
| [`saaf-intelligence-monitor.md`](hackathon-3/saaf-intelligence-monitor.md) | Agent | Mathijs Schouten / SAAF | Intelligence monitoring — 30 AI/audit sources | 4 | GitHub Actions deploy not yet built | `yellowraptor-whats-the-news.md` (predecessor) |
| [`saaf-jira-confluence-mcp.md`](hackathon-3/saaf-jira-confluence-mcp.md) | Skill | Mathijs Schouten / SAAF | IT infrastructure — MCP for Jira + Confluence | 5 | Complete; n8n and CLI alternatives documented | `frank-van-dissel-uc3` (consumer) |
| [`saaf-rag-knowledge-base.md`](hackathon-3/saaf-rag-knowledge-base.md) | Skill | Mathijs Schouten / SAAF | Shared RAG infrastructure | 4 | Enriched: content injection vs RAG; Obsidian pattern; harness layer insight | `linda-nyvelius-team-hightable.md`, `frank-van-dissel-uc5` |
| [`saaf-skills-registry-and-matching.md`](hackathon-3/saaf-skills-registry-and-matching.md) | Workflow | Mathijs Schouten / SAAF | SAAF meta — skills matching | 4 | 5-step skill creation workflow added | Unique |
| [`saaf-strapi-synthetic-data.md`](hackathon-3/saaf-strapi-synthetic-data.md) | Skill | Mathijs Schouten / SAAF | Shared synthetic data sandbox | 5 | Complete; Docker Compose + 5 content types | `saaf-jira-confluence-mcp.md` (consumer) |

_Session 2 batch (from video transcription analysis — 14 plans):_

| File | Type | Submitter / Org | Domain | Score | Missing / Notes | Overlaps |
|---|---|---|---|---|---|---|
| [`ai-agent-visibility-scanner.md`](hackathon-3/ai-agent-visibility-scanner.md) | Agent | Mathijs Schouten / SAAF | AI Governance — shadow AI discovery & inventory (Akto 2025: 21% visibility) | 4 | Sourced from WhatsApp; NCSC NL directive angle; requires IT cooperation for log scan | `eu-ai-act-compliance-monitor.md` (classification), `cli-audit-system-wrapper.md` |
| [`ai-audit-explainability-framework.md`](hackathon-3/ai-audit-explainability-framework.md) | Framework | Mathijs Schouten / SAAF | AI Governance — audit finding explainability & challenge response | 4 | Sourced from WhatsApp (AI Innovators Hub, AI als tool voor audit); EU AI Act Art. 13 anchoring | `ellert-van-der-vecht-llm-owasp.md`, `audit-subagent-coordination-framework.md` |
| [`always-on-audit-agent.md`](hackathon-3/always-on-audit-agent.md) | Agent | Mathijs Schouten / SAAF | Agent Infrastructure — 24/7 field assistant (Clawdbot) | 4 | Telegram integration and Ollama fallback need testing | `saaf-intelligence-monitor.md` (different pattern) |
| [`audit-report-generator-from-work-program.md`](hackathon-3/audit-report-generator-from-work-program.md) | Agent | Mathijs Schouten / SAAF | Audit Reporting — auto-draft audit report from completed work program | 4 | Sourced from Eduward (Mollie) building this live; needs work program JSON format spec | `floris-stokkers-work-program-agent.md` (upstream), `llm-hallucination-detection-agent.md` |
| [`audit-agent-gamified-ui.md`](hackathon-3/audit-agent-gamified-ui.md) | Workflow | Mathijs Schouten / SAAF | Agent Infrastructure — fleet manager dashboard | 4 | MVP HTML dashboard; WebSocket stretch | `audit-loop-orchestration-sdk.md` (state files source) |
| [`audit-evidence-visualization.md`](hackathon-3/audit-evidence-visualization.md) | Skill | Mathijs Schouten / SAAF | Reporting — HTML audit visual generation | 4 | 5 visual types to implement; PDF export stretch | `power-bi-audit-dashboard-mcp.md` (complementary) |
| [`audit-loop-orchestration-sdk.md`](hackathon-3/audit-loop-orchestration-sdk.md) | Workflow | Mathijs Schouten / SAAF | Agent Infrastructure — Python loop orchestration SDK | 4 | Core Task/Loop/Agent primitives; async stretch | `overnight-audit-batch-processing-agent.md` (primary consumer) |
| [`audit-memory-knowledge-system.md`](hackathon-3/audit-memory-knowledge-system.md) | Workflow | Mathijs Schouten / SAAF | Knowledge Management — Obsidian vault + ChromaDB | 4 | Vault watcher script; Obsidian plugin stretch | `saaf-rag-knowledge-base.md` (complementary layer) |
| [`audit-skills-transformation-curriculum.md`](hackathon-3/audit-skills-transformation-curriculum.md) | Reference | Mathijs Schouten / SAAF | Talent — AI audit reskilling (4 stages) | 4 | Validate with CAEs; IIA alignment stretch | `saaf-skills-registry-and-matching.md` (skills taxonomy) |
| [`audit-subagent-coordination-framework.md`](hackathon-3/audit-subagent-coordination-framework.md) | Workflow | Mathijs Schouten / SAAF | Agent Infrastructure — multi-agent debate & consensus | 4 | 3-round debate orchestrator; parallel execution stretch | `frank-van-dissel-uc4-fraud-risk-assessment.md` (use case) |
| [`audit-workflow-automation-levels.md`](hackathon-3/audit-workflow-automation-levels.md) | Workflow | Mathijs Schouten / SAAF | AI Strategy — automation maturity (Level 1→3) | 4 | Reference document; SAAF plan tagging stretch | `audit-automation-overview.md` (complementary) |
| [`cli-audit-system-wrapper.md`](hackathon-3/cli-audit-system-wrapper.md) | Skill | Mathijs Schouten / SAAF | Evidence Collection — CLI wrapper for legacy systems | 4 | Allowlist config for AD/Splunk/ServiceNow; MCP wrapper stretch | `saaf-jira-confluence-mcp.md` (complementary) |
| [`document-evidence-extraction-agent.md`](hackathon-3/document-evidence-extraction-agent.md) | Agent | Mathijs Schouten / SAAF | Evidence Collection — OCR + document extraction | 4 | pdf2image + Claude Vision pipeline; DOCX/XLSX extension stretch | `johannesiv-policy-to-controls-extractor.md` (text-based parallel) |
| [`llm-hallucination-detection-agent.md`](hackathon-3/llm-hallucination-detection-agent.md) | Skill | Mathijs Schouten / SAAF | Evidence Quality — hallucination detection for audit findings | 4 | Sourced from WhatsApp (AI Innovators Hub); RAG integration placeholder; blocking threshold TBD | `ellert-van-der-vecht-llm-owasp.md` (LLM06), `saaf-rag-knowledge-base.md` (consumer) |
| [`n8n-audit-workflow-migration.md`](hackathon-3/n8n-audit-workflow-migration.md) | Workflow | Mathijs Schouten / SAAF | Agent Infrastructure — n8n to Claude migration | 4 | PBC reminder example; migration tool stretch | `diyve-garg-pbc-assistant-isabelle.md` (PBC use case) |
| [`eu-ai-act-compliance-monitor.md`](hackathon-3/eu-ai-act-compliance-monitor.md) | Agent | Mathijs Schouten / SAAF | Compliance — EU AI Act continuous monitoring (GPAI Aug 2026 deadline, ALTAI) | 4 | Sourced from WhatsApp; needs EU AI Act corpus in RAG; feeds from intelligence monitor | `saaf-intelligence-monitor.md` (regulatory feed), `saaf-rag-knowledge-base.md` |
| [`on-premise-ai-compute-decision-framework.md`](hackathon-3/on-premise-ai-compute-decision-framework.md) | Framework | Mathijs Schouten / SAAF | AI Infrastructure — on-premise GPU vs. cloud API decision (NVIDIA DGX/RTX, TCO, GDPR Art. 28) | 4 | Hardware prices and model recommendations should be updated annually | `open-source-audit-agent-framework.md` (software complement) |
| [`owasp-ai-testing-agent.md`](hackathon-3/owasp-ai-testing-agent.md) | Agent | Mathijs Schouten / SAAF | AI Security — OWASP AI Testing Guide v1.0 operational agent (250 pages) | 4 | Sourced from WhatsApp; OWASP guide must be ingested into RAG; extends ellert plan | `ellert-van-der-vecht-llm-owasp.md` (AT-01 subset), `saaf-rag-knowledge-base.md` |
| [`open-source-audit-agent-framework.md`](hackathon-3/open-source-audit-agent-framework.md) | Skill | Mathijs Schouten / SAAF | Agent Infrastructure — local LLM stack (GLM 4.7 + router) | 4 | Router config; quality benchmark vs Claude Sonnet | `always-on-audit-agent.md` (Ollama fallback) |
| [`overnight-audit-batch-processing-agent.md`](hackathon-3/overnight-audit-batch-processing-agent.md) | Agent | Mathijs Schouten / SAAF | Agent Infrastructure — overnight batch (Ralph loop) | 4 | Orchestrator script; GitHub Actions cron stretch | `audit-loop-orchestration-sdk.md` (SDK variant) |
| [`power-bi-audit-dashboard-mcp.md`](hackathon-3/power-bi-audit-dashboard-mcp.md) | Skill | Mathijs Schouten / SAAF | Reporting — Power BI MCP integration | 4 | MCP server + Strapi mock; .pbix template stretch | `saaf-jira-confluence-mcp.md` (same MCP pattern) |

---

## Plans by Type

| Type | Count | Plans |
|---|---|---|
| **Agent** | 27 | Most H2 plans, icfcop, grc-copilot, saaf-intelligence-monitor, alignment plans, always-on-audit-agent, document-evidence-extraction-agent, overnight-audit-batch-processing-agent |
| **Skill** | 13 | frank-uc5, yellowraptor, saaf-jira-confluence, saaf-rag, saaf-strapi, audit-evidence-visualization, cli-audit-system-wrapper, open-source-audit-agent-framework, power-bi-audit-dashboard-mcp, llm-hallucination-detection-agent, (mollie skills) |
| **Workflow** | 12 | ellert-llm-owasp, ellert-multi-model, koekenpan, audit-automation-overview, auditflow-ai, saaf-skills-registry, audit-agent-gamified-ui, audit-loop-orchestration-sdk, audit-memory-knowledge-system, audit-subagent-coordination-framework, audit-workflow-automation-levels, n8n-audit-workflow-migration |
| **Framework** | 1 | ai-audit-explainability-framework |
| **Reference** | 1 | audit-skills-transformation-curriculum |

---

## Plans by Quality Score

| Score | Plans |
|---|---|
| **5 — Production-ready** | `ellert-van-der-vecht-llm-owasp.md`, `frank-van-dissel-uc3-incident-issue-intelligence.md`, `the-control-freaks-uc7-rcm-builder.md`, `icfcop-control-testing-agent.md`, `saaf-jira-confluence-mcp.md`, `saaf-strapi-synthetic-data.md` |
| **4 — Good, minor gaps** | Most H2 plans; all H3 agent plans |
| **3 — Needs work** | `auditflow-ai.md`, `group-5-hackers-ai-audit-agents.md`, `team-67-intelligent-audit-agents.md`, `frank-van-dissel-uc6`, `frank-van-dissel-uc9`, `linda-nyvelius-team-hightable.md`, `the-rcm-rangers-audit-work-program-agent.md` |
| **1–2 — Placeholder only** | None |

---

## Merge Candidates

The following plan pairs address the same problem and should be consolidated before Hackathon #4:

| Plan A | Plan B | Recommended Action |
|---|---|---|
| `frank-van-dissel-uc7-rcm-builder.md` | `the-control-freaks-uc7-rcm-builder.md` | Merge into `the-control-freaks-uc7-rcm-builder.md` (higher quality); Frank's UC7 becomes a cross-reference |
| `frank-van-dissel-uc8-audit-work-program.md` | `floris-stokkers-work-program-agent.md` + `inge-garretsen-audit-work-program-agent.md` | Consolidate into one canonical work program agent plan; keep best prompts from all three |
| `yellowraptor-whats-the-news.md` | `saaf-intelligence-monitor.md` | Yellowraptor = MVP; Intelligence Monitor = v2; keep both but update cross-references |

---

## Infrastructure Plans (Cross-Cutting)

These plans are not domain-specific but support all other plans:

| Plan | What it provides | Which plans consume it |
|---|---|---|
| `saaf-strapi-synthetic-data.md` | Shared synthetic test data (5 content types) | All agent plans needing realistic data for demos |
| `saaf-rag-knowledge-base.md` | Shared regulatory knowledge base (ChromaDB + Nomic) | `frank-van-dissel-uc5`, `frank-van-dissel-uc2`, `johannesiv`, `robeminem94-gdpr` |
| `saaf-jira-confluence-mcp.md` | MCP servers for Jira + Confluence | `frank-van-dissel-uc3`, `koekenpan-ia-fieldwork-preparation`, `saaf-strapi-synthetic-data` |
| `saaf-skills-registry-and-matching.md` | Participant → plan matching algorithm | Used at hackathon day for task assignment |
| `saaf-intelligence-monitor.md` | Weekly AI/audit news digest (30 sources) | Reference for all plans needing regulatory updates |
| `audit-automation-overview.md` | Meta-overview of all AI audit use cases across the audit lifecycle | Navigator document for auditors new to SAAF |
| `audit-loop-orchestration-sdk.md` | Python SDK (Task, Loop, Agent, Mailbox primitives) for multi-step workflows | `overnight-audit-batch-processing-agent.md`, `audit-subagent-coordination-framework.md` |
| `audit-memory-knowledge-system.md` | Obsidian vault + ChromaDB: past findings and precedents | `always-on-audit-agent.md`, `frank-van-dissel-uc2-previous-audit-intelligence.md` |
| `open-source-audit-agent-framework.md` | Local LLM stack (GLM 4.7 + Claude router) — zero API cost | `always-on-audit-agent.md`, `overnight-audit-batch-processing-agent.md` |
| `cli-audit-system-wrapper.md` | Allowlisted CLI wrapper for legacy audit systems (AD, Splunk, SAP) | `frank-van-dissel-uc6-it-dependency-identifier.md`, `example-synthetic-access-review.md` |
| `audit-workflow-automation-levels.md` | Level 1→3 automation maturity framework; maps all SAAF plans to levels | Navigator for automation strategy decisions |
| `audit-agent-gamified-ui.md` | Browser dashboard for fleet monitoring of parallel agent runs | `audit-loop-orchestration-sdk.md`, `overnight-audit-batch-processing-agent.md` |
