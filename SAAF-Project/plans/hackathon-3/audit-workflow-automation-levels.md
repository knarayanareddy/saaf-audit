# Audit Workflow Automation Levels

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Workflow |
| **Status** | Draft |

---

## 2. Problem Statement

Audit teams implementing AI lack a framework for choosing the right level of automation for a given task. They either automate too much (agents taking actions without oversight) or too little (just using ChatGPT for spell-checking). There is no clear progression model from "no AI" to "fully autonomous agents."

The result: teams build ad-hoc solutions, miss the middle ground of practical automation, and struggle to justify AI investment to management without a framework for measuring progress.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — AI Strategy / Automation Maturity

**Applicable standards:**

- IIA IPPF — Standard 1200 (Proficiency), 2010 (Planning), 2100 (Nature of Work)
- EU AI Act — Art. 9 (Risk management), Art. 14 (Human oversight)
- ISO 42001 — AI management systems maturity

**In scope:**

- Three-level automation framework: Level 1 (Rules-based triage) → Level 2 (AI in steps) → Level 3 (Adaptive agents)
- Mapping of all existing SAAF plans to automation levels
- Per-level governance requirements and human-oversight controls
- Decision guide: when to use each level for a given audit task
- Progression roadmap: how to move from Level 1 to Level 3

**Out of scope:**

- Level 4 (fully autonomous, no human oversight) — outside IIA ethical framework
- Technical implementation of specific agents (those are in individual plans)
- Vendor selection or product recommendations

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Automation level classifier prompt; governance requirement checklist per level |
| **Tools** | No new tools — this is a reference document |
| **Regulatory** | EU AI Act Art. 14 (human oversight) as the normative ceiling for each level |
| **Outputs** | Reference document + automation level assessment template for new SAAF plans |

---

## 5. Automation Level Framework

### Level 1: Rules-Based Triage

**Definition:** Pre-programmed rules automatically classify, route, or flag items. No generative AI. Human makes all decisions.

**Examples:**
- Exception flag: user accounts inactive >90 days → flagged automatically
- Risk threshold: vendor contract value >€500K → escalated for manual review
- Keyword match: incident ticket contains "data breach" → routed to security audit queue

**Governance requirements:**
- Rule documentation (what triggers the flag)
- False positive rate monitoring
- Annual rule review

**SAAF plans at this level:**
- `example-synthetic-access-review.md` (threshold flagging)
- `yellowraptor-whats-the-news.md` (RSS keyword filter)

---

### Level 2: AI in Steps

**Definition:** AI assists with specific steps in the audit workflow. A human initiates each AI step and reviews the output before proceeding.

**Examples:**
- Auditor uploads vendor contract → AI extracts key clauses → auditor reviews and approves extraction
- AI drafts a finding in C/C/C/E format → auditor edits and approves before adding to dossier
- AI generates a work program → auditor selects which steps to execute

**Governance requirements:**
- Human approval gate at each AI-assisted step
- AI output logged with model version and timestamp
- Auditor annotates: "AI-assisted, reviewed by [name]"
- Accuracy spot-check: monthly review of AI vs. auditor judgment on 10% of outputs

**SAAF plans at this level (most current plans):**
- `frank-van-dissel-uc4-fraud-risk-assessment.md`
- `johannesiv-policy-to-controls-extractor.md`
- `robeminem94-gdpr-ai-audit-agent.md`
- `the-control-freaks-uc7-rcm-builder.md`
- `document-evidence-extraction-agent.md`

---

### Level 3: Adaptive Agents

**Definition:** AI agents autonomously execute multi-step workflows, adapt based on intermediate results, and produce complete outputs. Human reviews the final output, not each step.

**Examples:**
- Overnight batch: agent builds RCMs for 30 control domains while auditor sleeps; auditor reviews next morning
- Always-on agent: agent monitors regulatory feeds, classifies relevant articles, drafts alerts — auditor approves before sending
- Multi-agent debate: 5 agents independently assess a vendor contract, debate disagreements, produce consensus finding

**Governance requirements:**
- Documented agent design (system prompt, tools, model version — versioned in git)
- Complete audit trail of all agent actions (checkpoints, tool calls, intermediate outputs)
- Mandatory human review of all final outputs before use in audit dossier
- Incident response plan for agent errors
- Periodic validation: compare agent outputs against expert judgment on 5% of cases

**SAAF plans at this level (target for H3+):**
- `overnight-audit-batch-processing-agent.md`
- `always-on-audit-agent.md`
- `audit-subagent-coordination-framework.md`
- `saaf-intelligence-monitor.md`

---

## 6. Prompts

### System prompt (draft — automation level classifier)

```
You are an audit automation advisor.
Given a description of an audit task, classify it to the most appropriate automation level:
- Level 1: Rules-based triage (deterministic, no AI reasoning)
- Level 2: AI in steps (AI assists, human reviews each step)
- Level 3: Adaptive agents (AI executes multi-step workflow, human reviews final output)

For each classification, state:
1. Recommended level and rationale
2. Key governance requirements for this level
3. The biggest risk if the team skips to a higher level prematurely
4. The SAAF plan most relevant to this task
```

### Example user prompts

**Prompt 1 — Level classification:**
```
Task: We want to use AI to check all purchase orders against our vendor master list
for SoD conflicts (same person who approved the PO also approved the vendor).
What automation level is appropriate and why?
```

**Prompt 2 — Progression roadmap:**
```
We are currently at Level 1 for our access review process (threshold flagging).
What are the 3 specific steps to move to Level 2 AI-assisted access reviews?
What governance artifacts do we need to produce before moving to Level 2?
```

**Intended file location:** `prompts/audit-use-cases/automation-level-advisor.md`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| EU AI Act Art. 9 | Risk management — automation level framework is a risk management tool for AI deployment |
| EU AI Act Art. 14 | Human oversight — Level 3 still requires human review of final outputs; Level 4 (no oversight) is out of scope |
| IIA IPPF 2010 | Planning — automation level should be documented in the audit plan |
| ISO 42001 | AI management systems — this framework maps to ISO 42001 maturity dimensions |

### Claude / AI tool usage notes

This plan is primarily a reference document. The automation level classifier prompt uses synthetic task descriptions. No audit data is processed by this plan itself.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown reference document + JSON assessment template

**Schema reference:** Not applicable (reference document)

### Synthetic example output (automation level assessment)

```markdown
## Automation Level Assessment — Access Review (Acme B.V.)

**Task:** Quarterly user access review for 2,000 accounts across 5 systems

**Current state:** Manual (Level 0 — spreadsheet review)

**Recommended level:** Level 2 (AI in steps)

**Rationale:** Access reviews are high-volume but require auditor judgment for exceptions.
AI should flag anomalies; auditor decides on each flagged account.

**Progression path:**
1. Level 1 (Month 1): Implement threshold rules (>90 days inactive, terminated employees)
2. Level 2 (Month 3): Add AI-powered SoD conflict detection; auditor reviews AI findings
3. Level 3 (Month 9): Autonomous overnight access review run; auditor reviews summary

**Governance artifacts needed before Level 2:**
- [ ] System prompt documented and version-controlled
- [ ] False-positive rate baseline established from Level 1 run
- [ ] Auditor review log template prepared
- [ ] Model version documented in audit working papers
```

---

## 9. Tech Stack

**MVP scope:**

- [x] This is a reference document (no tech stack required)
- [x] Markdown (stored in `docs/reference/`)
- [x] Claude API for the automation level classifier prompt (optional demo)

**Stretch goals:**

- [ ] Interactive web tool: input audit task description → get automation level recommendation
- [ ] SAAF plan tagging: update all plan metadata with automation level field
- [ ] Maturity assessment: 10-question quiz that places an audit team at their current level

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- This reference document
- Automation level classifier prompt
- Per-level governance checklist templates

**Help requested:**

- Audit directors and CAEs: validate that the Level 3 governance requirements are realistic
- Vaktechniek: map automation levels to IIA IPPF standards formally
- Legal/compliance: validate that Level 3 meets EU AI Act Art. 14 (human oversight) requirements

**Cross-org interest:**

This framework is broadly applicable — any organization implementing AI in audit can use it. Intended for sharing via IIA Nederland channels.

**Related SAAF plans:**

- [`audit-automation-overview.md`](audit-automation-overview.md) — complementary overview by audit lifecycle phase
- [`overnight-audit-batch-processing-agent.md`](overnight-audit-batch-processing-agent.md) — Level 3 example
- [`always-on-audit-agent.md`](always-on-audit-agent.md) — Level 3 candidate
- All SAAF plans — each should declare its automation level in metadata

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Three-level framework defined; SAAF plans mapped |
| **Do** | In progress | Hackathon #3: validate level assignments with auditors in the room |
| **Check** | Not started | Survey: do audit teams agree with the level assignment for their plans? |
| **Act** | Not started | Add automation level field to plan template for H4 submissions |

---

## 12. Open Questions

1. Should the framework have 3 levels or 5 (more granular distinction between types of Level 2)?
2. How does this framework align with ISACA's AI audit maturity model (if one exists)?
3. Should "automation level" be a required field in the SAAF plan template from H4 onwards?
4. Who in an audit organization is responsible for approving a move from Level 2 to Level 3?
