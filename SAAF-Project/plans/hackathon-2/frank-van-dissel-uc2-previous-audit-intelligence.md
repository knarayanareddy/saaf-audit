# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Frank van Dissel & Lauren Browne) |
| **Organisation** | Mollie |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Internal audit departments accumulate valuable knowledge from previous audits, but this information is often scattered across reports, databases, and team members' memories. Before starting a new engagement, auditors must manually search past reports for relevant findings — a time-consuming process that is inconsistently done and relies heavily on institutional memory. The Previous Audit Intelligence & Lessons Learned Agent systematically analyzes previous audit reports to identify relevant risks, control deficiencies, and emerging patterns that should inform the current risk assessment, in full compliance with GIAS 13.2.

This is **Use Case 2 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It consumes the Context Brief from [UC1](frank-van-dissel-uc1-policy-process-intake.md) and feeds its Historical Risk Intelligence Report into the [RCM Builder (UC7)](frank-van-dissel-uc7-rcm-builder.md).

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Historical Risk Intelligence (GIAS 13.2)

**Applicable standards:**

- GIAS 13.2 — "When internal auditors have identified the relevant risks for an activity under review in past engagements, only a review and update of the previous engagement risk assessment may be necessary."
- GIAS 13.2 — Identifying and gathering reliable, relevant, and sufficient information

**In scope:**

- Searching and retrieving relevant previous audit reports (same process, related processes, same business unit)
- Extracting structured information: identified risks, findings, recommendations, management responses, follow-up status
- Analyzing patterns across multiple audits (recurring issues, systemic weaknesses)
- Assessing relevance to current audit based on: time elapsed, scope similarity, remediation status, environmental changes
- Generating a comparative analysis highlighting the evolution of the risk landscape
- Scoring historical findings for relevance to the current audit objective

**Out of scope:**

- Substantive testing of whether prior findings have been resolved (requires evidence)
- Accessing real-time operational data (batch analysis of stored reports only)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Relevance scoring prompt and pattern analysis prompt; Temporal Relevance Validator prompt |
| **Tools** | Semantic search across audit report database; named entity recognition; temporal analysis pipeline |
| **Regulatory** | GIAS 13.2 compliance; reuse `regulatory/control-mappings/` for risk taxonomy cross-reference |
| **Outputs** | Historical Risk Intelligence Report: ranked prior findings with relevance scores, recurring patterns, trend analysis, focus area recommendations |

---

## 5. Prompts

### System prompt (draft — Conservative Agent)

```
You are a conservative internal audit historian.
Given a set of previous audit reports and the current audit scope, identify
historical findings that are directly relevant to this engagement.
Include only findings with a relevance score above 7/10.
For each included finding: state the relevance score, explain why it is
still relevant given the time elapsed and any known remediation actions,
and note whether the risk is improving, stable, or deteriorating.
Never include findings without explicit justification for relevance.
```

### System prompt (draft — Comprehensive Agent)

```
You are a comprehensive internal audit historian.
Given a set of previous audit reports and the current audit scope, identify
all findings that could plausibly be relevant to this engagement.
Include findings with a relevance score above 4/10.
Flag each finding with: relevance score, rationale, remediation status
(open/closed/unknown), and whether the risk landscape has changed
since the finding was raised.
```

### Example user prompts

**Prompt 1 — relevance scoring:**
```
Current audit scope: Procure-to-Pay process, FY 2025.
Context Brief: [from UC1]

Previous audit reports (past 3 years):
- Procure-to-Pay Audit 2023: [report summary]
- Vendor Management Audit 2022: [report summary]

Score all previous findings for relevance to the current scope. Provide
trend analysis: is the risk landscape improving, stable, or deteriorating?
```

**Prompt 2 — Temporal Relevance Validator:**
```
Finding: "Duplicate payment controls in ERP not functioning correctly" (raised 2022, rated High)
Reported management response: "IT team will fix the ERP configuration by Q4 2022."
Time elapsed: 3 years.

Is this finding still relevant? Has the risk likely changed given the reported remediation?
Assign a current relevance score and explain.
```

**Intended file location:** `prompts/audit-use-cases/uc2-previous-audit-intelligence.md`

---

## 6. Tools and Techniques

### Approach

Multi-agent pipeline with a Judge:

1. **Agent A — Conservative:** Semantic search and relevance scoring; includes only high-similarity matches (>7/10)
2. **Agent B — Comprehensive:** Broader retrieval, includes all potentially relevant reports (>4/10)
3. **Judge Agent:** Evaluates the trade-off between comprehensiveness and precision; produces the final Historical Risk Intelligence Report with consensus relevance scores
4. **Temporal Relevance Validator:** Separate agent assesses whether risks identified in previous audits remain relevant given time elapsed or remediation actions

### Quality Safeguards

**Safeguard 1 — Multi-Model Consensus:** Agent A (conservative) and Agent B (comprehensive) independently score findings; the Judge Agent reconciles discrepancies and produces a final ranked list.

**Safeguard 2 — Temporal Relevance Validator:** For each historical finding, a specialist agent evaluates: time since finding was raised, documented management response, follow-up status, and whether the operating environment has changed materially.

### Example script or pseudocode

```python
def run_audit_intelligence(current_scope: str, prior_reports: list[str]) -> dict:
    material = embed_reports(prior_reports)          # Semantic search index
    
    scores_conservative = agent_conservative(current_scope, material)
    scores_comprehensive = agent_comprehensive(current_scope, material)
    consensus = judge_agent(scores_conservative, scores_comprehensive)
    
    validated = temporal_validator(consensus, follow_up_db)
    return generate_intelligence_report(validated)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6 for agents, claude-opus-4-6 for judge), sentence-transformers for semantic search

**Intended file location:** `tools/scripts/uc2-previous-audit-intelligence/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2 | Review and update of previous engagement risk assessment when prior risks have been identified |
| GIAS 13.2 | Identifying relevant risks, significant changes, and prior audit coverage |

### Claude / AI tool usage notes

Previous audit reports processed must be anonymized — no real personal data, client names, or confidential findings sent to the API. Use synthetic or anonymized versions for testing. The agent explicitly does not confirm whether findings have been resolved — it flags them for auditor follow-up.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (Historical Risk Intelligence Report) + Markdown summary

**Schema reference:** Prior findings conform to `outputs/schemas/finding-schema.json`; relevance scores and trend analysis are additional fields.

### Test Scenario 1 — Direct Repeat Audit

- **Input:** Audit of same process conducted 2 years ago
- **Expected:** High relevance scores (>80%) for most previous findings
- **Validation:** Compare agent output to manual historical analysis by experienced auditor

### Synthetic example output

```json
{
  "historical_findings": [
    {
      "id": "HIST-2023-F-003",
      "title": "Duplicate payment controls not functioning correctly",
      "original_risk_rating": "High",
      "relevance_score": 8.5,
      "relevance_rationale": "Same process in scope. Management response indicated fix by Q4 2022 but no evidence of closure in follow-up database.",
      "trend": "Stable — risk has not demonstrably improved",
      "recommendation": "Include in current RCM as priority risk; expand sample size for duplicate payment testing."
    }
  ],
  "recurring_patterns": ["Access management weaknesses recurring across 3 consecutive audits"],
  "focus_areas": ["Duplicate payment controls", "Vendor master data integrity"]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6, claude-opus-4-6)
- [x] Python 3.9+
- [x] sentence-transformers (semantic search)
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Direct integration with audit management systems (TeamMate+, AuditBoard) for automated report retrieval
- [ ] Continuous learning: update relevance scoring model based on auditor feedback

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Multi-agent relevance scoring pipeline (Conservative + Comprehensive + Judge)
- Temporal Relevance Validator prompt
- JSON output schema for Historical Risk Intelligence Report

**What help I'm looking for:**

- Auditors at organizations with large historical report databases to validate the semantic search quality
- Input on relevance scoring thresholds from experienced audit leads

**Cross-org interest:**

Prior findings review is a mandatory step under GIAS 13.2. This agent is immediately applicable to all 45+ SAAF organizations. Strongly related to the [AuditRepAnalysis plan](anonymous-audit-rep-analysis.md) — both address the same problem. The two teams should consider merging or aligning their approaches.

**Related SAAF plans:**

- [UC1 — Policy-to-Process Intake](frank-van-dissel-uc1-policy-process-intake.md) — provides Context Brief input
- [UC7 — RCM Builder](frank-van-dissel-uc7-rcm-builder.md) — consumes this agent's output
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates this output
- [AuditRepAnalysis](anonymous-audit-rep-analysis.md) — closely related prior findings review skill; consider alignment
- [Team-HighTable](linda-nyvelius-team-hightable.md) — semantic similarity approach applicable to this agent's search component

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie historical audit reports |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What is the optimal relevance threshold for the Conservative vs. Comprehensive agents — and should the threshold be configurable per engagement?
2. How should the agent handle findings where the management response claims resolution but no follow-up evidence is available?
3. How do we align this agent's approach with the [AuditRepAnalysis](anonymous-audit-rep-analysis.md) plan — should these become one shared skill?
4. What is the minimum historical report corpus size needed for the semantic search to produce useful results?
