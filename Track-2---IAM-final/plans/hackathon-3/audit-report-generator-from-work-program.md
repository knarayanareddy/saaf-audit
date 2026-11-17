# Plan: Automated Audit Report Generator from Work Program

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `audit-report-generator-from-work-program.md` |
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organization** | SAAF |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Agent |
| **Primary domain** | Audit Reporting / Audit Workflow |
| **Source** | WhatsApp: "AI Innovators: Hub • General" (April 2026) — Eduward (Mollie, internal audit) explicitly mentioned: "automatisch rapporteren met AI uit werkprogramma" (automatic reporting from audit work programs). This is a live use case being actively built at Mollie. It fills the downstream gap in the existing work-program plans: those plans generate the work program; this plan converts a completed work program into a draft audit report. |

---

## 2. Problem Statement

A completed audit work program contains all the raw material for an audit report: test procedures executed, evidence referenced, observations made, and conclusions drawn per test step. Translating this into a formal audit report is currently a manual process that takes 3-5 days per audit engagement.

**The gap in the existing SAAF portfolio:**
- `floris-stokkers-work-program-agent.md` — generates an audit work program from an audit objective
- `frank-van-dissel-uc8-audit-work-program.md` — same
- `inge-garretsen-audit-work-program-agent.md` — same

None of these plans address what happens after the work program is executed. The downstream step — converting completed work program steps into a structured audit report — is missing.

**Live validation:** Eduward at Mollie is already building this. The SAAF plan formalizes the approach, makes it reusable, and documents the prompts and output schema.

---

## 3. Use-Case Type & Scope

**Type:** Agent

**Scope:**
- Accept a completed audit work program as input (structured JSON or annotated Markdown)
- For each completed test step with observations: extract the finding or conclusion
- Synthesize related observations into consolidated findings (avoiding repetition)
- Draft each finding in the SAAF finding schema format (F-XXXX: title, risk rating, observation, recommendation)
- Draft the overall audit report structure: scope, methodology, executive summary, findings, management response template
- Apply consistent IIA-standard language: "based on our procedures", "in our opinion", etc.
- Flag low-confidence findings for auditor review before finalizing

**Out of scope:**
- Management response (this is written by the auditee, not the auditor)
- Sign-off and distribution (administrative steps outside agent scope)
- Replacing audit judgment — the agent drafts; the auditor finalizes

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | Observation extraction prompt; finding synthesis prompt; report structure generator; executive summary prompt |
| **Tools** | Claude API (Sonnet), `outputs/schemas/finding-schema.json`, `llm-hallucination-detection-agent.md` (post-draft check) |
| **Regulatory** | IIA Standard 2410 (criteria for communicating audit results), IIA Standard 2420 (quality of communications — accurate, objective, clear, concise, constructive, complete, timely), IIA Standard 2430 (engagement disclosure of non-conformance) |
| **Outputs** | Draft audit report (Markdown), finding list JSON (F-XXXX format), executive summary, management response template |

---

## 5. Prompts

### Prompt 1 — Observation Extraction from Work Program Steps
```
System: You are extracting audit observations from completed audit work program steps.

For each completed test step, extract:
1. OBSERVATION: What did you find? (factual, not interpretive)
2. CRITERION: What was the expected state? (policy, standard, or control)
3. CONDITION: What is the actual state found?
4. CAUSE: Why does the gap exist? (if determinable from evidence)
5. EFFECT: What is the risk or impact of this gap?
6. EVIDENCE: What evidence supports this? (document name, date, record count)
7. CONCLUSION: Pass / Fail / Not tested

Use only information present in the work program step. Do not infer or add information not in the source.

User: Extract observations from the following completed work program steps:

[WORK_PROGRAM_STEPS_JSON]
```

### Prompt 2 — Finding Synthesis (Multiple Steps → One Finding)
```
System: You are synthesizing multiple related audit observations into a single consolidated finding.

IIA finding structure:
- Title: concise, action-oriented (e.g., "Insufficient segregation of duties in payment processing")
- Risk rating: High / Medium / Low / Informational (per SAAF risk matrix)
- Observation: 2-4 sentences describing what was found; factual; quantified where possible
- Recommendation: 1-3 actionable steps the auditee should take to remediate

Rules:
- One finding covers one control objective or one risk theme — do not bundle unrelated observations
- Every factual claim must trace to an evidence source from the work program
- Risk rating is based on: data sensitivity × likelihood of exploitation × impact if materialized

User: Synthesize these related observations into a single consolidated finding:

[OBSERVATIONS_JSON]

Output in finding-schema.json format: {id, title, risk_rating, observation, recommendation}
```

### Prompt 3 — Report Structure Generation
```
System: You are drafting the structure of an internal audit report following IIA Standards.

Standard report structure:
1. Report header: engagement title, entity audited, period, report date, auditor signature
2. Executive summary: overall assessment, number of findings by risk rating, key message (3 bullets)
3. Scope and methodology: what was audited, what was not, how (interviews, data analysis, document review)
4. Findings: ordered High → Medium → Low → Informational; each finding in full
5. Summary of management actions: table with finding, agreed action, responsible owner, deadline
6. Appendix: work program reference, population and sample sizes, limitations

User: Draft the report structure from the following engagement data:

Engagement title: [TITLE]
Entity: [ENTITY]
Period: [PERIOD]
Audit objective: [OBJECTIVE]
Findings: [FINDINGS_JSON]
Scope inclusions: [IN_SCOPE]
Scope exclusions: [OUT_OF_SCOPE]
Methodology: [METHODS_USED]

Draft each section with placeholder text where auditor input is needed.
```

### Prompt 4 — Executive Summary
```
System: You are writing an executive summary for an internal audit report.
Target reader: audit committee member who will not read the full report.

Requirements:
- 3-5 sentences maximum
- State overall conclusion: "Based on our work, [entity]'s [control area] is [adequate / partially adequate / inadequate]"  
- Reference the most significant finding and its business impact
- Note the most important recommended action
- Avoid technical jargon; use business language

User: Write an executive summary for an audit engagement with the following findings:

[FINDINGS_JSON]
```

---

## 6. Tools & Techniques

| Tool | Role |
|---|---|
| Claude API (Sonnet) | Observation extraction, finding synthesis, report drafting |
| `outputs/schemas/finding-schema.json` | Standard finding format |
| `llm-hallucination-detection-agent.md` | Verify factual claims in draft findings against work program evidence |
| `floris-stokkers-work-program-agent.md` | Upstream: the work program this agent consumes |
| Python `json` + `pathlib` | Input parsing and report file generation |

**Workflow integration:**
```
[Audit Objective]
      ↓
floris-stokkers-work-program-agent → work_program.json
      ↓
[Auditor executes test steps, records observations in work_program.json]
      ↓
audit-report-generator-from-work-program → draft_report.md + findings.json
      ↓
llm-hallucination-detection-agent → validated_findings.json
      ↓
[Auditor reviews, edits, finalizes, publishes]
```

---

## 7. Regulatory Framework

| Standard | Requirement |
|---|---|
| **IIA Standard 2410** | Criteria for communicating — engagement results must include: objective, scope, conclusions, recommendations, and action plans |
| **IIA Standard 2420** | Quality of communications — accurate (no errors), objective (fair), clear (easily understood), concise (no unnecessary elaboration), constructive (helps auditee), complete (nothing omitted), timely (issued promptly) |
| **IIA Standard 2330** | Documenting information — the work program is the record; the report is derived from it; both must be retained |
| **IIA Standard 2060** | Reporting to senior management — findings must be communicated with risk ratings and management responses |

---

## 8. Output Format

### Draft Audit Report (Markdown)
Complete report with all 6 standard sections, findings formatted in observation/criterion/condition/cause/effect/recommendation structure.

### Findings List (JSON)
```json
[
  {
    "id": "F-0041",
    "title": "Incomplete segregation of duties in purchase-to-pay process",
    "risk_rating": "High",
    "observation": "Testing of 150 purchase orders identified 12 instances (8%) where the same user requested, approved, and received a purchase order. This violates the organization's P2P policy Section 3.2 requiring three separate approvers. The 12 transactions have a combined value of €340,000.",
    "recommendation": "Implement system-enforced role separation in the ERP system preventing the same user from performing more than one of: request, approve, receive. Complete system controls by September 1, 2026.",
    "evidence_sources": ["PO export 2026-Q1 (150 records)", "P2P Policy v4.2 Section 3.2"],
    "work_program_steps": ["WP-3.1", "WP-3.2", "WP-3.4"]
  }
]
```

### Management Response Template
Pre-formatted table for auditee to fill in: agreed action, responsible owner, target completion date.

---

## 9. Tech Stack

```
Language:     Python 3.9+
Dependencies: anthropic (Claude API)
Config:       ANTHROPIC_API_KEY from environment
Input:        Completed work program JSON (from floris-stokkers or inge-garretsen plan)
Output:       Draft audit report Markdown + findings JSON + management response template
```

---

## 10. Collaboration & Cross-References

**Upstream (provides input):**
- `floris-stokkers-work-program-agent.md` — generates the work program this agent consumes
- `frank-van-dissel-uc8-audit-work-program.md` — same
- `inge-garretsen-audit-work-program-agent.md` — same

**Downstream (consumes output):**
- `llm-hallucination-detection-agent.md` — validates factual claims in draft findings
- `power-bi-audit-dashboard-mcp.md` — findings JSON can be pushed to Power BI
- `audit-evidence-visualization.md` — generates heat maps / risk matrices from findings list

**WhatsApp source attribution:**
> This plan originated directly from **Eduward's** message in the **"AI Innovators: Hub • General"** WhatsApp group (April 2026): "automatisch rapporteren met AI uit werkprogramma" — automated reporting from audit work programs with AI. Eduward is a member of Mollie's internal audit team and is actively building this capability. This plan formalizes that use case and makes it reusable for the SAAF community. Eduward is a natural contributor and potential reviewer for this plan.

---

## 11. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | In progress | Eduward at Mollie is actively building this; Hackathon #3 demo opportunity |
| **Check** | Not started | Compare AI-generated draft to human-written draft on same engagement; measure edits required |
| **Act** | Not started | Refine based on actual auditor edit patterns (what does the auditor always change?) |

**Hackathon #3 task (Auditor role):**
Take a completed (or partially completed) work program from a past audit. Run the report generator against it. Count: how many findings did the agent produce? How many matched what you would have written? How many required significant editing? Record the edit rate.

---

## 12. Open Questions

1. **Work program format**: The agent requires a structured JSON input. Most work programs are in Excel or Word. Should this plan include a conversion sub-agent (Excel/Word → JSON)?
2. **Multi-engagement reports**: Some organizations produce combined reports covering multiple audit areas. Should the agent support merging multiple work program outputs into one report?
3. **Language**: Should the report be generated in Dutch or English? IIA guidance is English; many Dutch organizations report in Dutch. Language parameter in the config?
4. **Audit trail**: IIA Standard 2330 requires that the derivation from work program to report is traceable. The `work_program_steps` field in the finding schema provides this — but should it be more explicit (include the actual work program text, not just step IDs)?
