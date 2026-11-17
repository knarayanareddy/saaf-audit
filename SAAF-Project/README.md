# SAAF Project — Shared Audit Agents Framework

A co-creative initiative where auditors from participating organizations build AI agents together. Over 10 hackathons and 2 alignment sessions, participants develop reusable components for AI-assisted auditing.

## Repository Structure

This repository is organized around four framework pillars:

| Pillar | Folder | Description |
|---|---|---|
| Prompts | [`prompts/`](prompts/) | Domain-specific audit prompts and system instructions |
| Tools | [`tools/`](tools/) | Scripts, APIs, and integrations powering agent capabilities |
| Regulatory | [`regulatory/`](regulatory/) | Control mappings, guardrails, and AI usage policies |
| Outputs | [`outputs/`](outputs/) | Standardized report formats and output templates |

Additional documentation lives in [`docs/`](docs/).

### Where agents live

Early on, everything lived in this one repo. In practice most teams build **standalone agents
that are deployed on their own**, so the recommended home is now a **dedicated repo per agent**
in the [SAAF-Project organisation](https://github.com/orgs/SAAF-Project/repositories). This repo
is the shared backbone — the four pillars above, shared utility scripts (e.g. transcription
tooling), submitted plans, and a **reference** to each agent repo (see the Agent Overview table
below).

- **In your own agent repo:** source code, tests, sample inputs/outputs, its own README and deploy config.
- **Stays here:** prompts, regulatory mappings, output schemas, shared utility scripts, your plan, and a reference row pointing to your repo.
- **Already built your agent inside this repo?** Migrate it to a dedicated repo — see
  [`docs/getting-started.md`](docs/getting-started.md#building-an-agent). You keep your contribution
  history and your agent also earns the Agent Builder bonus on the
  [portal leaderboard](https://saaf-portal.vercel.app/leaderboard).
- _Future direction:_ the agent repos may be wired together as a monorepo (e.g. Turborepo) so they
  can be spun up from here while each agent keeps its own home.

### Community Playbook

For anyone looking to run SAAF-style hackathons **inside their own organisation or as a regional chapter**, the [**SAAF Community Playbook**](https://github.com/SAAF-Project/SAAF-community-playbook) is the field guide. It covers the shared manifesto, the morning-keynotes / afternoon-hackathon day format, sponsor and champion engagement, value measurement and executive reporting, and the contribution flow back to the main SAAF Project — across 49 markdown files in 8 sections, plus pre-event / day-of / post-event checklists and ready-to-fill templates (chapter charter, speaker brief, manager brief, plan submission, retro).

## Hackathon #1 (Session 2) — Agents Built

> **10 AI audit agents in under 2 hours** — built by 80+ professionals from 45+ organizations on March 10, 2026 at Mollie, Amsterdam.
> Session 1 was the kick-off alignment session; Session 2 was the first build hackathon.
>
> Full recap: [`hackathon-recap/recap-session-1.md`](hackathon-recap/recap-session-1.md) &nbsp;·&nbsp; [PDF](hackathon-recap/recap-session-1.pdf)

### Agent Overview

Each row maps an agent archetype to its team repository, the AI and tools it uses, and which SAAF pillars it draws from.

| # | Agent | Use Case | Repository | AI / Tools used | SAAF Pillars |
|---|-------|----------|------------|-----------------|--------------|
| 1 | **EU AI Act Risk Assessment** | Finds applicable requirements, checks compliance status | [Compliance-Report-Generator](https://github.com/SAAF-Project/Compliance-Report-Generator) | Claude API · Python | Prompts · Regulatory · Outputs |
| 2 | **Control Testing Copilot** | Automates test steps and collects evidence | [IA-Fieldwork-Preparation](https://github.com/SAAF-Project/IA-Fieldwork-Preparation) | Claude API | Prompts · Tools · Outputs |
| 3 | **Policy to Control Generator** | Converts policy text into structured audit checks | [Policy-to-Controls-Extractor](https://github.com/SAAF-Project/Policy-to-Controls-Extractor) | Claude API · Python | Prompts · Regulatory |
| 4 | **Vendor Risk Manager** | Scores supplier security & compliance against 8 EU/NL frameworks | [Vendor\_Guard](https://github.com/SAAF-Project/Vendor_Guard) | Claude API · Azure · Python | Prompts · Tools · Regulatory · Outputs |
| 5 | **Audit Document Pre-Check** | Verifies PBC submissions for completeness and consistency | [PBC-Assistant-Isabelle](https://github.com/SAAF-Project/PBC-Assistant-Isabelle---IA-AI-Hackathon) | Claude API · Python | Prompts · Outputs |
| 6 | **Continuous Monitoring Agent** | Detects anomalies in operational/financial data | [Team-HighTable](https://github.com/SAAF-Project/Team-HighTable) | Python · TypeScript | Tools · Prompts |
| 7 | **Find Similar Issues & Draft Recommendations** | Retrieves historical findings and proposes remediation | [Team-HighTable](https://github.com/SAAF-Project/Team-HighTable) | Python | Prompts · Outputs |
| 8 | **Data Lineage Mapping** | Visualizes data flows for audit traceability | _(in progress)_ | MCP · Python | Tools · Outputs |
| 9 | **Regulatory Change Tracker** | Scours DNB/AFM feeds, maps new rules to existing controls | [WhatsTheNews](https://github.com/SAAF-Project/WhatsTheNews) | TypeScript · RSS feeds | Tools · Regulatory |
| 10 | **Risk & Compliance Workflow Automation** | Orchestrates multi-step audit tasks end-to-end | [Vendor\_Guard](https://github.com/SAAF-Project/Vendor_Guard) | Claude API · Azure | Tools · Regulatory · Outputs |
| 11 | **Fraud Risk Analysis → Podcast** | Performs a fraud risk analysis as a multi-voice podcast (NL/EN) so failing controls get heard, not filed | [fraude-risicoanalyse-podcast](https://github.com/SAAF-Project/fraude-risicoanalyse-podcast) | ElevenLabs `eleven_v3` · Python | Tools · Outputs |

### How Agents Use the SAAF Framework

```
Pillar          What the agent uses
──────────────────────────────────────────────────────────────────────
Prompts         System instructions + audit-use-case prompt templates
                → prompts/system-instructions/  prompts/audit-use-cases/
Tools           MCP servers, API connectors, Python scripts
                → tools/integrations/mcp-server-example.md
                → tools/apis/example_api_connector.py
Regulatory      ISO 27001 / NIS2 control mappings, guardrails, AI policy
                → regulatory/frameworks/  regulatory/guardrails/
Outputs         Structured findings (finding-schema.json), report templates
                → outputs/schemas/finding-schema.json
```

### Key Technologies Across Agents

| Technology | Used by |
|---|---|
| **Claude API (Anthropic)** | Vendor\_Guard, Compliance-Report-Generator, Policy-to-Controls-Extractor, PBC-Assistant, IA-Fieldwork-Preparation |
| **Python** | 6 of 10 agents — data extraction, scoring, classification |
| **TypeScript / JavaScript** | Team-HighTable, WhatsTheNews |
| **MCP (Model Context Protocol)** | Agents connecting to live data sources without custom connectors — see [`tools/integrations/mcp-server-example.md`](tools/integrations/mcp-server-example.md) |
| **Azure / Microsoft** | Vendor\_Guard (document processing, storage) |
| **RSS feeds (DNB, AFM)** | WhatsTheNews (regulatory news monitoring) |

### Overlap & Consolidation Opportunities

Three audit domains emerged across teams — the highest-overlap pairs are prime candidates for a shared reference implementation:

| Domain | Repositories |
|---|---|
| Compliance Monitoring | Compliance-Report-Generator · Vendor\_Guard |
| Vendor / Third-Party Risk | Vendor\_Guard |
| Regulatory Change Tracking | WhatsTheNews · Compliance-Report-Generator |

See the [overlap analysis](hackathon-recap/recap-session-1.md#overlap-analysis) section of the recap for scored pairing recommendations.

## Hackathon #2 (Session 3) — Submitted Plans

> **March 24, 2026 · Schuberg Philis**
> Plans submitted during and after the session are in [`plans/hackathon-2/`](plans/hackathon-2/).

See [`plans/hackathon-2/README.md`](plans/hackathon-2/README.md) for the index.

Plans can always be submitted — before, during, or after a hackathon. Only the template may change per session. For the full submission guide and current template see [`docs/getting-started.md`](docs/getting-started.md#hackathon-2--submitting-a-plan).

---

## Hackathon #3 (Session 4) — April 21, 2026

> **April 21, 2026 · Wolters Kluwer, Alphen aan den Rijn**  
> Theme: **Shared Infrastructure + Agents by Design**

Plans for Hackathon #3 are in [`plans/hackathon-3/`](plans/hackathon-3/). **29 plans** have been submitted across four themes:

- **Shared infrastructure**: RAG knowledge base, Strapi synthetic data sandbox, Jira/Confluence MCP, skills registry, intelligence monitor
- **Agent harness patterns**: loop orchestration SDK, always-on agent, overnight batch, multi-agent debate, fleet dashboard
- **Domain-specific agents**: EU AI Act compliance monitor, OWASP AI testing, AI agent visibility scanner, hallucination detection, explainability framework
- **Audit reporting**: report generator from work program, evidence extraction, evidence visualization, CLI legacy wrapper, Power BI MCP

See [`plans/hackathon-3/README.md`](plans/hackathon-3/README.md) for the full index with type, audit domain, and status per plan.

### Cross-Session Reference Documents

| Document | Description |
|---|---|
| [`plans/overview.md`](plans/overview.md) | Central overview of all 60 plans across all sessions with quality scores and overlap analysis |
| [`plans/gap-analysis.md`](plans/gap-analysis.md) | Coverage mapping of 53 audit domains — what's covered, what's missing |
| [`plans/meta-analysis.md`](plans/meta-analysis.md) | Cross-plan synthesis: hackathon assignments, lessons learned, SAAF governance direction |
| [`docs/reference/domains-and-frameworks.md`](docs/reference/domains-and-frameworks.md) | 53 audit domains across 12 categories with applicable frameworks |
| [`docs/reference/ai-sources-registry.md`](docs/reference/ai-sources-registry.md) | 30 curated AI/audit news sources with URLs |
| [`docs/reference/ai-tools-and-techniques.md`](docs/reference/ai-tools-and-techniques.md) | RAG ecosystem, agent layers, 22+ tools comparison |
| [`docs/reference/skills-and-agents.md`](docs/reference/skills-and-agents.md) | 12 agent/skill definitions per audit phase |
| [`docs/reference/infographics-catalog.md`](docs/reference/infographics-catalog.md) | Text descriptions of 10 AI infographics from the SAAF Drive |
| [`docs/reference/iia-prompt-library.md`](docs/reference/iia-prompt-library.md) | IIA AI Prompt Library reference and access guide |

---

## Hackathon #4 (Session 5) — TBD

Planning for the next session has started. Plans carry forward across sessions — submit yours now and let the community build on it.

See [`plans/hackathon-4/`](plans/hackathon-4/) to browse or submit a plan. The template is at [`docs/plans/plan-template.md`](docs/plans/plan-template.md).

### Agents built

| Agent | Repository | Audit Domain |
|---|---|---|
| **Judging Found Controls** | [judging-found-controls](https://github.com/SAAF-Project/judging-found-controls) | Policy Compliance / Control Validation |

---

### Hackathon Harness

The [`website/`](website/) folder is a static coordination website for browsing plans, registering for tracks, and facilitating the hackathon day.

```bash
cd website && python3 -m http.server 8080
# Open http://localhost:8080
```

| Page | Description |
|---|---|
| [`index.html`](website/index.html) | Participant harness: track browser, plan explorer, registration |
| [`facilitator.html`](website/facilitator.html) | Live dashboard — polls GitHub Issues for registrations |
| [`slides-hackathon3.html`](website/slides-hackathon3.html) | Opening presentation slide deck |
| [`print-table-signs.html`](website/print-table-signs.html) | Printable A4 table signs |
| [`leaderboard.html`](website/leaderboard.html) | Contribution leaderboard — scores from merged PRs, plans, claims |
| [`recap-hackathon3.html`](website/recap-hackathon3.html) | Post-hackathon #3 recap slide deck |

Data in `website/data/` is auto-generated from the plan Markdown files by [`tools/scripts/generate_dashboard.py`](tools/scripts/generate_dashboard.py).

---

## Getting Started

See [`docs/getting-started.md`](docs/getting-started.md) for onboarding instructions.

## Participating Organizations

45+ organizations from across the Dutch and international audit landscape. See the [project website](https://saafproject.com) for the full list.

## Organizers

Eduward van de Kamp, Mathijs Schouten

## Partners

NOREA, ISACA, IIA
