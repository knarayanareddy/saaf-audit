# AI Agents in the Audit Practice — Overview and Applications

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Workflow |
| **Status** | Draft |

---

## 2. Problem Statement

There is no practical, practitioner-facing overview of how AI agents can be deployed across the audit lifecycle — one that connects directly to the daily reality of internal auditors.

English-language sources (IIA, ISACA, Big4) exist, but:

- They are often too abstract or too vendor-specific for practitioners
- They are not linked to the concrete SAAF plans that participants have already built
- The translation from "AI can do this" to "here is how you do it tomorrow in your audit" is missing
- Specific workflows across the audit lifecycle (planning → execution → reporting → follow-up) have not been mapped per AI technology

This plan documents all agent, skill, and workflow concepts for AI in the audit practice — linked to existing SAAF plans — organized by phase of the audit lifecycle.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — AI Automation (overarching)

**Applicable standards:**

- IIA IPPF — Standard 1200 (Proficiency), 2100 (Nature of Work)
- EU AI Act — Art. 4 (AI Literacy)
- IIA — AI in Internal Audit guidelines

**In scope:**

- Overview of AI applications per phase of the audit lifecycle (planning, execution, reporting, follow-up)
- Linking each application to relevant SAAF plans
- Distinction: agents by design (AI built into audit processes) vs. agents on demand (AI deployed during a specific audit)
- Distinction: local models (Ollama, Whisper) vs. cloud API (Claude, OpenAI, Gemini)
- Do's, don'ts, and lessons learned from the first two SAAF hackathons

**Out of scope:**

- Technical implementation guides (those live in the individual SAAF plans)
- Legal advice on AI use in the audit practice
- Product recommendations (this is a methodology overview, not a vendor selection)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Example prompts per audit phase; links to existing SAAF prompts |
| **Tools** | No new tools — this is a reference document describing and linking existing tools |
| **Regulatory** | IIA IPPF and EU AI Act as normative framework; summary of relevant requirements |
| **Outputs** | Reference document in Markdown, stored as `docs/reference/audit-ai-workflow.md` |

---

## 5. AI Applications per Audit Phase

### Phase 1: Planning & Scoping

| Application | Type | SAAF plan |
|---|---|---|
| **Risk assessment based on historical audit data** | Agent | `frank-van-dissel-uc2-previous-audit-intelligence.md` |
| **Fraud risk assessment** | Agent | `frank-van-dissel-uc4-fraud-risk-assessment.md` |
| **Automated audit programme generation** | Agent | `frank-van-dissel-uc8-audit-work-program.md`, `floris-stokkers-work-program-agent.md` |
| **Retrieve regulatory criteria (DORA, GDPR, ISO)** | Skill | `frank-van-dissel-uc5-regulatory-criteria.md` |
| **Analyse previous audit findings** | Skill | `anonymous-audit-rep-analysis.md` |

**When AI by design (structurally embedded):**

A Risk Assessment Agent runs automatically each week based on new incident data, changes in the business environment, and findings from previous audits. The audit manager receives a ranked risk list — without manual dossier research.

**When AI on demand (per audit):**

During scoping of a specific audit, the auditor enters a prompt with the audit mandate and relevant context. The agent generates a draft audit programme that the auditor then refines.

---

### Phase 2: Evidence Collection

| Application | Type | SAAF plan |
|---|---|---|
| **Automated evidence collection via APIs** | Skill | `frank-van-dissel-uc6-it-dependency-identifier.md`, `saaf-jira-confluence-mcp.md` |
| **Evidence integrity check** | Agent | `mollie-group-x-evidence-audit.md` |
| **Evidence request drafting (PBC assistant)** | Agent | `diyve-garg-pbc-assistant-isabelle.md` |
| **Fieldwork preparation** | Workflow | `koekenpan-ia-fieldwork-preparation.md` |

**Local models vs. cloud API:**

For evidence collection via APIs (Jira, Active Directory, AWS logs) the Claude API is suitable — data is synthetic or anonymised. For transcription of Teams recordings, **Whisper locally** is the right choice: audit conversations contain confidential information that must not pass through an external API.

---

### Phase 3: Analysis & Testing

| Application | Type | SAAF plan |
|---|---|---|
| **100% population test: user access rights** | Agent | `example-synthetic-access-review.md` |
| **Change management analysis (Jira ↔ GitHub)** | Agent | `frank-van-dissel-uc3-incident-issue-intelligence.md` |
| **Financial 3-way match (OI/PO/GRN)** | Agent | `themontechristo-threewaysecurity.md` |
| **Policy review (GDPR, EU AI Act)** | Agent | `johannesiv-policy-to-controls-extractor.md`, `robeminem94-gdpr-ai-audit-agent.md` |
| **Classify AI systems (EU AI Act)** | Agent | `ellert-van-der-vecht-llm-owasp.md`, `group-5-hackers-ai-audit-agents.md` |
| **DORA ICT risk assessment** | Agent | `frank-van-dissel-uc5-regulatory-criteria.md`, `rohan-sobha-compliance-report-generator.md` |
| **Build RCM (Risk & Control Matrix)** | Workflow | `the-control-freaks-uc7-rcm-builder.md`, `the-rcm-rangers-audit-work-program-agent.md` |
| **ICFCOP multi-framework testing** | Agent | `icfcop-control-testing-agent.md` |

---

### Phase 4: Reporting

| Application | Type | SAAF plan |
|---|---|---|
| **Draft findings (Condition/Criterion/Cause/Effect)** | Agent | `mollie-group-x-evidence-audit.md`, `anonymous-audit-rep-analysis.md` |
| **Generate compliance report** | Agent | `rohan-sobha-compliance-report-generator.md` |
| **M365 Copilot for reporting** | Skill | `grc-copilot-mindshift-agent.md` |

---

### Phase 5: Follow-Up & Monitoring

| Application | Type | SAAF plan |
|---|---|---|
| **Automated reminders (Audit Chaser)** | Agent | `diyve-garg-pbc-assistant-isabelle.md` |
| **Regulatory monitoring (Intelligence Monitor)** | Agent | `saaf-intelligence-monitor.md` |
| **Track action point progress** | Workflow | `yellowraptor-whats-the-news.md` |

---

## 6. Agents by Design vs. Agents on Demand

| Dimension | Agents by Design | Agents on Demand |
|---|---|---|
| **When** | Structurally embedded in audit processes | Deployed for specific audits or questions |
| **Trigger** | Automatic (schedule, event, data change) | Manual (auditor starts the agent) |
| **Governance** | Requires formal validation, audit trail, change control | Lower governance threshold; auditor is responsible for output |
| **Example** | Weekly risk scan runs automatically every Monday | Auditor asks agent to assess a policy document against DORA |
| **SAAF phase** | Hackathon #3+: after agents have been validated | Hackathon #1 and #2: first prototypes, run manually |

---

## 7. Local Models vs. Cloud API

| Criterion | Local (Ollama, Whisper) | Cloud API (Claude, OpenAI) |
|---|---|---|
| **Data privacy** | Ideal for confidential audit data | Acceptable for synthetic/anonymised data |
| **Cost** | No API costs; compute required | Per token; scalable |
| **Quality** | Lower for smaller models; Whisper base = good for transcription | Claude Sonnet = highest quality for reasoning |
| **Setup** | ffmpeg + ollama installation required | API key + 1 pip install |
| **When to use** | Transcription of Teams recordings; confidential documents | Reasoning over synthetic data; prompt development |
| **SAAF usage** | Whisper: 88 video transcriptions; Ollama: local tests | Claude API: all agent analyses, image descriptions |

---

## 8. Prompts

### System prompt (draft)

```
You are an AI audit assistant for [organisation name].
Your task is [describe the audit objective].
You always work with synthetic or anonymised data.
You always indicate when you draw a conclusion that requires verification by an auditor.
You always cite the specific standard or control framework on which you base your assessment.
Never express certainty that is not supported by the data provided.
```

### Example prompts

**Prompt 1 — Evidence analysis:**
```
Analyse the attached user access rights export (CSV).
Identify: (1) dormant accounts (>90 days since last login), (2) former employees
with active access rights, (3) SoD conflicts in the 'roles' column.
Produce an exception list in Markdown format with a risk classification per item.
```

**Prompt 2 — Standard testing:**
```
Test the attached change management document against the requirements of ISO 27001 A.8.32
(Change Management) and ITIL Change Management.
For each requirement indicate: Compliant / Partially compliant / Non-compliant / Not assessable.
Justify each assessment in no more than two sentences.
```

---

## 9. Do's, Don'ts, and Lessons Learned

### Do's

- Always validate the output of an AI agent before including it in an audit dossier
- Use synthetic data for development and testing — never real audit data
- Document which model you used and which version (reproducibility)
- Combine AI analysis with human judgment for high-risk findings
- Use Whisper locally for transcription of confidential conversations
- Start small: automating one audit phase is more valuable than a complete pipeline that never works

### Don'ts

- Do not blindly trust AI output for compliance conclusions (EU AI Act Art. 9 — human oversight)
- Do not send real personal data to external AI APIs (GDPR Art. 28)
- Do not use AI for high-impact decisions without traceable reasoning (explainability)
- Do not treat an AI agent as "the auditor" — the auditor remains responsible for the judgment

### Lessons Learned (Hackathon #1 and #2)

1. **Prompt quality determines output quality** — Plans with the best prompts produced the best demo outcomes
2. **Synthetic data is essential** — Teams without test data could not demonstrate their agent
3. **Building agents is faster than expected; integrating is harder** — Most time was spent on data access, not AI logic
4. **The IIA has a Prompt Library** — See [`docs/reference/iia-prompt-library.md`](../../docs/reference/iia-prompt-library.md)
5. **RAG > one-off context** — Agents with a knowledge base outperformed agents with only a long system prompt

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- This reference document (broadly shareable)
- Example prompts
- Do's/don'ts/lessons learned

**Help requested:**

- Auditors and technical specialists: add to lessons learned and do's/don'ts
- Organisations: add own experiences (anonymous contributions welcome)

**Cross-organisation interest:**

This is intended as the starting point for auditors who want to deploy AI in their audit practice. Broadly shareable beyond SAAF via IIA communities.

**Related SAAF plans:**

- All plans in `plans/hackathon-2/` and `plans/hackathon-3/` — this document is their overview page
- [`docs/reference/skills-and-agents.md`](../../docs/reference/skills-and-agents.md) — agent/skill definitions per audit phase
- [`plans/gap-analysis.md`](../gap-analysis.md) — coverage of 53 domains

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Overview documented; linked to existing plans |
| **Do** | In progress | Supplement based on Hackathon #3 experience |
| **Check** | Not started | Validate: is this document useful for auditors outside SAAF? |
| **Act** | Not started | Target: publish via IIA channels for broader distribution |

---

## 12. Open Questions

1. Should this document be translated into additional languages for international SAAF community members, or remain English-only?
2. How does this document relate to the IIA's own AI guidelines? Should we explicitly seek alignment?
3. Are there regulatory requirements (beyond GDPR) that specifically apply to AI use in the audit practice in certain jurisdictions?
4. How do we keep this document current as new SAAF plans are added?
