# Audit Skills Transformation Curriculum

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Reference |
| **Status** | Draft |

---

## 2. Problem Statement

AI is restructuring audit roles. Anthropic's white-collar exposure study estimates that 70-80% of audit tasks have at least partial AI automation potential within 3-5 years. Most audit teams have no structured reskilling path: they either ignore this and continue as before, or send people to one-day "AI for auditors" workshops that teach nothing practical.

The gap: there is no learning progression from "manual auditor" → "auditor who uses AI tools" → "agent configurator" → "agent overseer / AI audit lead." Without this progression, organizations either over-automate (AI without oversight) or under-invest (AI never adopted).

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Talent / AI Literacy / Change Management

**Applicable standards:**

- IIA IPPF — Standard 1200 (Proficiency and Due Professional Care), 1210 (Proficiency)
- EU AI Act — Art. 4 (AI Literacy) — organizations must ensure adequate AI literacy for AI system users
- Anthropic white-collar exposure study (2024) — audit profession exposure analysis

**In scope:**

- Four-role reskilling progression: Manual Auditor → AI Tool User → Agent Configurator → Agent Overseer
- Competency framework: what skills does each role require?
- Learning path: concrete activities, SAAF plans, and resources per stage
- Assessment: how to measure progression from one stage to the next
- Connection to EU AI Act Art. 4 compliance requirements for organizations deploying AI in audit

**Out of scope:**

- Individual development plans (this is a framework, not per-person coaching)
- Technical AI/ML training (focus is on audit-specific AI skills, not becoming an AI engineer)
- Certification programs (SAAF does not offer certifications)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Self-assessment prompts for each role level |
| **Tools** | No new tools — reference document |
| **Regulatory** | EU AI Act Art. 4 compliance mapping; IIA 1210 proficiency standard |
| **Outputs** | Curriculum document + competency assessment template |

---

## 5. Skills Transformation Framework

### Stage 1: Manual Auditor (Baseline)

**Profile:** Executes audit tasks manually. Uses Word, Excel, and GRC tools. May use ChatGPT for occasional text assistance but not systematically.

**Key skills:**
- Audit methodology (IIA IPPF)
- Domain expertise (1-3 audit domains)
- Interview and documentation skills
- Risk assessment framework knowledge

**AI exposure:** Passive (reads about AI, attends awareness sessions)

**Stage 1 → Stage 2 transition:**
- Complete 2 SAAF hackathon sessions as participant
- Use at least 3 existing SAAF agents on real audit tasks (with auditor oversight)
- Pass self-assessment: can articulate what prompt engineering is and why it matters

---

### Stage 2: AI Tool User

**Profile:** Uses existing AI tools and pre-built SAAF agents as part of regular audit workflow. Does not build agents but adapts prompts for their specific context.

**Key skills:**
- Prompt engineering basics (system prompts, user prompts, few-shot examples)
- Critical evaluation of AI output (spotting hallucinations, checking citations)
- Knowing when to use AI vs. manual approach
- Basic understanding of AI limitations (context windows, model biases)

**SAAF activities:**
- Use `grc-copilot-mindshift-agent.md` M365 Copilot prompts for reporting
- Adapt `frank-van-dissel-uc4-fraud-risk-assessment.md` prompts to own domain
- Run `the-control-freaks-uc7-rcm-builder.md` with own control domain

**Stage 2 → Stage 3 transition:**
- Build a modified version of an existing SAAF agent for own audit context
- Contribute a prompt improvement or new use case example to the SAAF repo
- Pass self-assessment: can write a clear system prompt from scratch for a new audit task

---

### Stage 3: Agent Configurator

**Profile:** Designs and builds new audit agents by following SAAF patterns. Can write Python scripts, configure MCP servers, and submit new plans to the SAAF repo.

**Key skills:**
- Python (basic scripting: API calls, CSV processing, file I/O)
- Claude API usage (messages, system prompts, tool use)
- MCP server configuration (reading existing MCP servers, adapting for new data sources)
- Template compliance (SAAF 12-section plan format, finding-schema.json)
- Basic testing (synthetic data, comparing AI output to expected output)

**SAAF activities:**
- Submit a new plan to `plans/hackathon-3/` following the 12-section template
- Build and demo a working agent at a hackathon session
- Review another team's plan and provide structured feedback

**Stage 3 → Stage 4 transition:**
- Successfully deploy an agent that runs without manual intervention for 1 month
- Mentor a Stage 2 auditor through their first agent build
- Pass self-assessment: can describe the governance requirements for a Level 3 agent

---

### Stage 4: Agent Overseer / AI Audit Lead

**Profile:** Leads the organization's AI audit capability. Responsible for agent governance, quality assurance, risk management, and organizational learning. Reports to CAE on AI audit maturity.

**Key skills:**
- Agent governance framework (IIA IPPF mapping, EU AI Act compliance)
- Multi-agent orchestration (batch processing, subagent coordination)
- AI risk management (model risk, bias detection, output quality monitoring)
- Change management (leading Stage 1-3 colleagues through transition)
- Strategic planning (AI audit roadmap, maturity assessment, budget)

**SAAF activities:**
- Lead an organization's full SAAF implementation (from hackathon to production agents)
- Contribute to SAAF governance framework discussions
- Design and run validation experiments for Level 3 agents (see `audit-workflow-automation-levels.md`)

---

## 6. Prompts

### System prompt (draft — self-assessment)

```
You are an AI audit skills advisor.
The user will describe their current audit activities and AI tool usage.
Based on their description, place them at Stage 1, 2, 3, or 4 of the AI audit skills framework.
Provide:
1. Current stage assessment with rationale
2. The most important skill gap to address to advance to the next stage
3. 3 specific SAAF activities they should complete next
4. Estimated time to reach the next stage (honest, not aspirational)
```

### Example user prompts

**Prompt 1 — Self-assessment:**
```
I have 8 years of internal audit experience focused on IT and cyber.
I've been to one SAAF hackathon and tried Claude for finding drafts.
I don't code but I want to build agents. Where am I in the framework?
```

**Prompt 2 — Team assessment:**
```
My team has 12 auditors: 6 IT audit, 4 financial, 2 data/analytics.
2 of us have used SAAF tools. None have built agents.
What is the most efficient 6-month reskilling plan for the team?
```

**Intended file location:** `prompts/audit-use-cases/skills-self-assessment.md`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 1200 | Proficiency and due professional care — AI skills are now part of audit proficiency |
| IIA IPPF 1210 | Proficiency — CAE must ensure team has skills sufficient for planned audit activities |
| EU AI Act Art. 4 | AI Literacy — organizations deploying AI systems must ensure adequate literacy for users and overseers |

### Claude / AI tool usage notes

The self-assessment prompt uses no confidential data — only job descriptions and skill inventories. Claude API is suitable.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown reference document + JSON competency assessment template

**Schema reference:** Not applicable

### Synthetic example output (self-assessment result)

```markdown
## AI Audit Skills Assessment — J. de Vries

**Current stage:** Stage 2 — AI Tool User (confident)

**Evidence:** 2 years of ChatGPT use for finding drafts, attended 1 SAAF hackathon,
has adapted 2 existing prompts for own audit domain. No Python experience.

**Most important skill gap:** Cannot build new agents or scripts — limited to adapting
existing SAAF tools.

**Recommended next activities:**
1. Complete `saaf-skills-registry-and-matching.md` questionnaire to find team matches
2. Pair with a Stage 3 colleague to build a modified version of `frank-van-dissel-uc4`
3. Complete Python basics course (Codecademy: 10 hours, focus on functions + file I/O)

**Estimated time to Stage 3:** 3-4 months with 2h/week dedicated practice
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Markdown reference document (no tech stack required)
- [x] Claude API for self-assessment prompts

**Stretch goals:**

- [ ] Interactive web assessment: 15-question quiz → stage placement + recommended next steps
- [ ] Integration with `saaf-skills-registry-and-matching.md` (skills taxonomy alignment)
- [ ] Progress tracking: each SAAF participant tracks stage progression over hackathon sessions

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- This curriculum document
- Self-assessment prompt
- Competency assessment template per stage

**Help requested:**

- CAEs and audit directors: validate that Stage 4 requirements are realistic and meaningful
- IIA Nederland: explore alignment with IIA professional development tracks
- HR/L&D professionals: review learning path design for adult learning principles

**Cross-org interest:**

This framework is applicable to any internal audit function considering AI adoption. Intended for sharing via IIA Nederland, ISACA Nederland, and NOREA channels.

**Empirical Evidence Base — Robert Worm Thesis (2025):**

Robert Worm's master's thesis *"The Impact of AI Literacy on IT Auditors' Risk Perception and Self-Assessed Capability"* (2025) provides the first empirical study of AI literacy levels in the Dutch IT audit profession. Key findings directly relevant to this curriculum:

- **Dunning-Kruger effect confirmed**: auditors with low AI literacy systematically overestimate their capability to assess AI risks. Auditors at Stage 1 of this framework typically assess themselves as Stage 2 — they do not know what they do not know.
- **Risk perception diverges with literacy**: as AI literacy increases, perceived risk from AI systems increases (not decreases) — contrary to the common assumption that familiarity breeds comfort. Stage 3-4 auditors are *more* concerned about AI risks than Stage 1 auditors.
- **Training intervention effect**: a 4-hour structured intervention (similar to Stage 1→2 in this curriculum) significantly improved both actual literacy scores and risk calibration. This validates the structured reskilling approach.
- **Self-assessment accuracy**: only 34% of IT auditors could accurately self-assess their AI literacy stage when given a blind questionnaire. This motivates the external stage assessment prompts in this plan — auditors cannot reliably self-place without structured guidance.

The Worm thesis is the empirical anchor for the "why" behind this curriculum. When presenting to CAEs or IIA Netherlands, cite it as evidence that ad-hoc AI training is insufficient and that structured stage progression is required.

**Professional Credential Alignment (ISACA & IIA, April 2026):**

Two credential tracks are newly relevant for Stages 2-4 of this curriculum:

*ISACA:*
- **AI Fundamentals Certificate** — 20-hour self-paced course covering AI concepts, generative AI, and responsible AI use. Suitable for Stage 1→2 transition. Available at isaca.org/ai.
- **Artificial Intelligence Auditing (AAIA) Certificate** — advanced credential covering AI audit methodology, risk assessment, and governance. Suitable for Stage 3→4 transition. Prerequisites: CISA or equivalent. ISACA Netherlands chapter is now offering the AAIA course in Dutch.

*IIA:*
- **From Prompts to Practice** podcast series (IIA, 2025): covers AI-driven innovation in internal audit. Recommended listening for Stage 1-2 auditors.
- **IIA AI Auditing Framework**: published 2025; provides a methodology for auditing AI systems. Directly maps to Stage 3 competencies in this curriculum.
- **IIA Netherlands training calendar**: new AI-related courses being added regularly. IIA.nl/evenementen is the authoritative source; the SAAF Intelligence Monitor should track new course announcements.

**Intended integration**: map each SAAF curriculum stage to the relevant ISACA/IIA credential to give auditors a recognized external validation pathway alongside their SAAF progress.

**Related SAAF plans:**

- [`saaf-skills-registry-and-matching.md`](saaf-skills-registry-and-matching.md) — skills taxonomy (complementary)
- [`audit-workflow-automation-levels.md`](audit-workflow-automation-levels.md) — Stage 4 overseer uses Level 3 governance framework
- [`open-source-audit-agent-framework.md`](open-source-audit-agent-framework.md) — Stage 2-3 transition tool
- [`saaf-intelligence-monitor.md`](saaf-intelligence-monitor.md) — tracks IIA/ISACA credential announcements and new training offerings

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Four-stage framework defined; competency descriptions complete |
| **Do** | In progress | Hackathon #3: validate stage assignments with participants in the room |
| **Check** | Not started | Survey: do auditors agree with their stage placement from the self-assessment? |
| **Act** | Not started | Align with IIA professional development tracks; explore formal recognition |

---

## 12. Open Questions

1. Should the framework have 4 stages or 5 (split Stage 3 into "agent user" and "agent builder")?
2. How does this map to existing IIA certifications (CIA, CISA)? Can SAAF stages be recognized formally?
3. At what stage does EU AI Act Art. 4 "adequate AI literacy" begin? Stage 2 or Stage 3?
4. How do we prevent the framework from becoming a box-ticking exercise rather than genuine skill development?
