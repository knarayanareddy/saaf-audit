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

Organizations capture operational incidents and control failures in systems like Jira or ServiceNow, but this data rarely makes its way into audit risk assessments in a structured way. Auditors either ignore this valuable signal or spend hours manually filtering and categorizing hundreds of incident tickets. The Incident & Issue Intelligence Agent automates this: it connects to incident management exports, filters incidents relevant to the audit scope, categorizes them by risk type and control failure mode, performs root cause analysis, identifies patterns and trends, and produces a structured Incident Intelligence Report — transforming raw operational data into actionable audit risk intelligence in compliance with GIAS 13.2.

This is **Use Case 3 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It consumes the Context Brief from [UC1](frank-van-dissel-uc1-policy-process-intake.md) and feeds its output into [UC4 (Fraud Risk Assessment)](frank-van-dissel-uc4-fraud-risk-assessment.md) and [UC7 (RCM Builder)](frank-van-dissel-uc7-rcm-builder.md).

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Incident Risk Intelligence (GIAS 13.2)

**Applicable standards:**

- GIAS 13.2 — "Identifying the potentially significant risks to the objectives of the activity under review."
- GIAS 13.2 — Identifying and gathering relevant information regarding governance, risk management, and control processes

**In scope:**

- Connecting to or evaluating exports from incident management systems (Jira, ServiceNow, etc.)
- Filtering incidents relevant to audit scope (by tags, business unit, incident type)
- Categorizing incidents by risk type, severity, and control failure mode
- Performing root cause analysis on incident descriptions
- Identifying patterns: frequency, clustering, escalation trends (past 12–24 months)
- Producing a heat map of risk concentration areas
- Flagging high-risk incidents requiring direct audit attention

**Out of scope:**

- Real-time incident monitoring (batch analysis of exported data only)
- Investigating individual incidents (audit team follow-up required)
- Integration with incident resolution workflows

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Dual classification prompts (rule-based Agent A + NLP Agent B) and Materiality Assessment Panel prompts |
| **Tools** | Python pipeline: incident export parser → dual classification agents → pattern analysis → heat map generation |
| **Regulatory** | GIAS 13.2 compliance; incident categorization taxonomy reusable in `regulatory/control-mappings/` |
| **Outputs** | Incident Intelligence Report: summary statistics, categorized incident inventory, root cause analysis, high-risk incident flags, risk heat map |

---

## 5. Prompts

### System prompt (draft — NLP Classification Agent)

```
You are an internal audit risk analyst specialised in incident data.
Given a list of operational incidents (from Jira/ServiceNow), and the current audit scope:
1. Filter incidents relevant to the audit scope
2. Categorize each relevant incident by: risk type (operational/financial/compliance/IT),
   severity (Critical/High/Medium/Low), and primary control failure mode
3. Identify root causes from incident descriptions (pattern: why did the control fail?)
4. Flag incidents that warrant direct audit attention

Output a structured JSON with: incident_id, relevance (yes/no), category, severity,
control_failure_mode, root_cause, audit_attention_flag.
Never include personally identifiable information about individuals named in incident tickets.
```

### Example user prompts

**Prompt 1 — incident classification:**
```
Audit scope: Procure-to-Pay process.
Context Brief: [from UC1]

Incident export (past 12 months, 847 incidents):
[incident data]

Filter relevant incidents, categorize by risk type and control failure mode,
and identify the top 10 risks by frequency and severity.
```

**Prompt 2 — root cause analysis:**
```
Top 5 incident clusters identified:
- Cluster 1: 42 incidents tagged "duplicate payment" — average severity: High
- Cluster 2: 28 incidents tagged "unauthorized approval" — average severity: Critical

For each cluster, perform root cause analysis. What underlying control failure
does this cluster point to?
```

**Intended file location:** `prompts/audit-use-cases/uc3-incident-issue-intelligence.md`

---

## 6. Tools and Techniques

### Approach

Dual-agent pipeline with a Materiality Panel:

1. **Agent A — Rule-based classification:** Filters and categorizes incidents using keyword rules and field-based logic (tags, business unit, incident type)
2. **Agent B — NLP classification:** Uses Claude to classify incidents semantically, identifying risk type and control failure mode from free-text descriptions
3. **Judge Agent:** Reconciles discrepancies between Agent A and Agent B; produces consensus categorization
4. **Materiality Assessment Panel:** Three specialized agents assess materiality from Financial, Operational, and Compliance perspectives; produces a combined materiality verdict per incident cluster
5. **Pattern Analyzer:** Time series analysis for trend detection; identifies frequency, clustering, and escalation trends over 12–24 months

### Quality Safeguards

**Safeguard 1 — Dual Classification:** Rule-based (Agent A) vs. NLP-based (Agent B) classification; Judge Agent reconciles discrepancies to prevent systematic misclassification.

**Safeguard 2 — Materiality Assessment Panel:** Specialized agents assess materiality from Financial, Operational, and Compliance angles — preventing over- or under-emphasis on any single dimension.

### Example script or pseudocode

```python
def run_incident_intelligence(audit_scope: str, incident_export: list[dict]) -> dict:
    # Dual classification
    classified_a = rule_based_agent(incident_export, audit_scope)
    classified_b = nlp_agent(incident_export, audit_scope)      # Claude
    consensus = judge_agent(classified_a, classified_b)
    
    # Materiality
    materiality = materiality_panel(consensus)   # Financial + Operational + Compliance agents
    
    # Pattern analysis
    patterns = analyze_trends(consensus)
    
    return generate_incident_report(consensus, materiality, patterns)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), `pandas` (time series analysis)

**Intended file location:** `tools/scripts/uc3-incident-issue-intelligence/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2 | Identifying potentially significant risks to the objectives of the activity under review |
| GIAS 13.2 | Gathering relevant information regarding control processes |

### Claude / AI tool usage notes

Incident data exported from Jira/ServiceNow must be anonymized before processing — remove names, email addresses, and any personally identifiable information from incident descriptions. The agent is explicitly instructed to suppress PII from its output.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (Incident Intelligence Report) + Markdown heat map summary

**Schema reference:** High-risk incident clusters map to `outputs/schemas/finding-schema.json`

### Test Scenario — High-Volume Incident Process

- **Input:** Process with 500+ incidents in past year
- **Expected:** Successful clustering into major categories; identification of top 10 risks
- **Validation:** Manual spot-check of 50 random incidents confirms accurate categorization

### Synthetic example output

```json
{
  "summary": {"total_incidents": 847, "relevant_to_scope": 143, "audit_attention_flags": 12},
  "risk_clusters": [
    {
      "cluster_id": "C-001",
      "label": "Duplicate payments",
      "count": 42,
      "severity": "High",
      "control_failure_mode": "Automated duplicate detection control not functioning",
      "root_cause": "ERP configuration error introduced during Q2 system upgrade",
      "materiality": {"financial": "High", "operational": "Medium", "compliance": "Low"},
      "audit_attention_flag": true
    }
  ],
  "heat_map": {"Duplicate Payments": 42, "Unauthorized Approvals": 28, "Missing GR": 19}
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.9+
- [x] `pandas` (trend analysis)
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Direct API integration with Jira / ServiceNow (rather than export-based)
- [ ] Real-time incident monitoring dashboard

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Dual-agent classification pipeline (rule-based + NLP + Judge)
- Materiality Assessment Panel prompts
- Incident Intelligence Report JSON schema

**What help I'm looking for:**

- Organizations willing to share anonymized incident export samples for testing
- Input on industry-specific risk categorization taxonomies

**Related SAAF plans:**

- [UC1 — Policy-to-Process Intake](frank-van-dissel-uc1-policy-process-intake.md) — provides Context Brief input
- [UC4 — Fraud Risk Assessment](frank-van-dissel-uc4-fraud-risk-assessment.md) — consumes incident data as fraud signal
- [UC7 — RCM Builder](frank-van-dissel-uc7-rcm-builder.md) — aggregates this output with UC2, 4, 5
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates pipeline output

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie incident data (anonymized) |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What incident fields are consistently available across Jira and ServiceNow exports — and what is the minimum viable data schema?
2. How should the agent handle incidents where the description is too vague for NLP classification — flag for auditor review or exclude?
3. What time window is most useful: 12 months, 24 months, or rolling based on audit frequency?
