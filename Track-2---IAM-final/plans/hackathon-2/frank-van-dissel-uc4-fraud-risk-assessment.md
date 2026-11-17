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

Fraud risk assessment is a mandatory component of every internal audit's risk assessment under GIAS 13.2, yet it is one of the most inconsistently performed steps. Auditors rely on generic fraud typologies or personal experience, rarely apply the full fraud triangle rigorously, and often miss industry-specific fraud scenarios. The Fraud Risk Assessment Agent performs a systematic, reproducible fraud risk assessment: it generates a fraud scenario library specific to the audit scope, evaluates each scenario against the fraud triangle (Pressure, Opportunity, Rationalization), assesses inherent and residual fraud risk, and produces a prioritized list of fraud risks with red flags and indicators.

This is **Use Case 4 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It consumes the Context Brief from [UC1](frank-van-dissel-uc1-policy-process-intake.md) and incident data from [UC3](frank-van-dissel-uc3-incident-issue-intelligence.md), and feeds its output into the [RCM Builder (UC7)](frank-van-dissel-uc7-rcm-builder.md).

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Fraud Risk Assessment (GIAS 13.2)

**Applicable standards:**

- GIAS 13.2 — "Considering specific risks related to fraud."
- GIAS 13.2 — Evaluating the significance of risks and prioritizing them for review
- IIA Practice Guide — Fraud and Internal Audit

**In scope:**

- Generating a fraud scenario library relevant to the audit scope and industry
- Evaluating scenarios against the fraud triangle (Pressure, Opportunity, Rationalization)
- Assessing inherent fraud risk (likelihood × impact) per scenario
- Evaluating mitigating controls and residual fraud risk
- Generating fraud-focused red flags and indicators per scenario
- Producing a prioritized fraud risk register

**Out of scope:**

- Forensic investigation of suspected fraud cases
- Real-time transaction monitoring for fraud detection
- Legal assessment of fraud scenarios

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Fraud scenario generation prompt; fraud triangle evaluation prompt; Red Team adversarial agent prompt |
| **Tools** | Python pipeline: fraud scenario generator → triangle evaluator → control effectiveness assessor → red team agent |
| **Regulatory** | GIAS 13.2 fraud mandate; ACFE fraud tree typologies as knowledge base; reuse `regulatory/control-mappings/` |
| **Outputs** | Fraud Risk Assessment Report: scenario inventory, fraud triangle analysis per scenario, inherent/residual risk ratings, red flags and indicators |

---

## 5. Prompts

### System prompt (draft — Fraud Scenario Generator)

```
You are an internal audit specialist in fraud risk assessment.
Given an audit scope, industry type, and process description, generate a comprehensive
library of fraud scenarios relevant to this specific context.
For each scenario, apply the fraud triangle:
- Pressure: what motivation exists for this fraud?
- Opportunity: what control weakness or access enables it?
- Rationalization: what reasoning might a perpetrator use?

Also identify: inherent risk rating (High/Medium/Low), primary red flags,
and any fraud indicators that would be observable in audit data.

Reference ACFE fraud typologies where applicable.
Do not name specific individuals. Use role-based descriptions only.
```

### System prompt (draft — Red Team Agent)

```
You are an adversarial agent taking the perspective of a potential fraudster.
Given a set of proposed controls for the audit scope, identify:
1. How each control could be bypassed
2. What combination of control weaknesses creates the greatest fraud opportunity
3. Which red flags would be hardest for an auditor to detect

Output a "bypass analysis" for each control. Be specific about the method.
This analysis is for audit planning purposes — to strengthen the audit program.
```

### Example user prompts

**Prompt 1 — scenario generation:**
```
Audit scope: Accounts Payable / Procure-to-Pay process.
Industry: Financial services (payment processor).
Context Brief: [from UC1]
Incident data: [from UC3]
Organizational fraud case history: [if available]

Generate a comprehensive fraud scenario library (target: 20+ scenarios).
For each scenario: apply fraud triangle, rate inherent risk, list red flags.
```

**Prompt 2 — Red Team:**
```
Proposed controls for Procure-to-Pay:
- Dual approval required for invoices >€10,000
- System-generated duplicate payment check
- Vendor master data change approval workflow

For each control: identify bypass methods and residual fraud risk.
```

**Intended file location:** `prompts/audit-use-cases/uc4-fraud-risk-assessment.md`

---

## 6. Tools and Techniques

### Approach

Two-agent pipeline with quality gates:

1. **Fraud Scenario Generator:** Produces fraud scenario library with fraud triangle analysis, inherent risk ratings, and red flags — referenced against ACFE fraud typologies
2. **Control Effectiveness Assessor:** Evaluates mitigating controls against each scenario; produces residual risk rating
3. **Red Team Agent:** Adversarial agent that evaluates control bypass methods from a fraudster's perspective
4. **Fraud Triangle Completeness Check:** Validates that every scenario has documented analysis of all three triangle elements

### Quality Safeguards

**Safeguard 1 — Red Team Agent:** Adversarial agent takes the perspective of a potential fraudster to evaluate control bypass methods — stress-testing the control assessment.

**Safeguard 2 — Fraud Triangle Completeness Check:** Automated validation that every fraud scenario has documented analysis of Pressure, Opportunity, and Rationalization. Incomplete scenarios are flagged and returned for completion.

### Example script or pseudocode

```python
def run_fraud_assessment(audit_scope: str, context_brief: dict, incidents: dict) -> dict:
    scenarios = generate_fraud_scenarios(audit_scope, context_brief, incidents)
    
    # Validate completeness of fraud triangle for each scenario
    for scenario in scenarios:
        validate_fraud_triangle(scenario)   # Completeness check
    
    # Assess controls and residual risk
    assessed = assess_control_effectiveness(scenarios, context_brief["native_rcr"])
    
    # Red team evaluation
    red_team_findings = red_team_agent(context_brief["native_rcr"])
    
    return generate_fraud_report(assessed, red_team_findings)
```

**Tech stack used:** Python 3.9+, Claude API (claude-opus-4-6 for fraud scenarios, claude-sonnet-4-6 for red team)

**Intended file location:** `tools/scripts/uc4-fraud-risk-assessment/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2 | "Considering specific risks related to fraud" — mandatory for every audit |
| ACFE Fraud Tree | Reference typology for fraud scenario generation |
| IIA Practice Guide | Fraud and Internal Audit — methodology for fraud risk assessment |

### Claude / AI tool usage notes

No real names, transaction data, or personal information should be included in prompts. All fraud scenarios are hypothetical. Organizational fraud case history should be anonymized before processing.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (Fraud Risk Assessment Report)

**Schema reference:** Fraud scenarios map to `outputs/schemas/finding-schema.json` (risk_rating field corresponds to inherent/residual fraud risk)

### Test Scenario — High-Risk Fraud Process

- **Input:** Cash handling or procurement process
- **Expected:** Comprehensive list of 20+ plausible fraud scenarios
- **Validation:** Compare against ACFE fraud tree typologies; review by fraud specialist

### Synthetic example output

```json
{
  "fraud_scenarios": [
    {
      "id": "FR-001",
      "title": "Ghost vendor — fictitious supplier invoice scheme",
      "fraud_triangle": {
        "pressure": "Finance employee under personal financial stress",
        "opportunity": "Vendor master data changes require only one approver; no periodic vendor validation",
        "rationalization": "Employee feels underpaid relative to peers"
      },
      "inherent_risk": "High",
      "mitigating_controls": ["Dual approval for new vendors", "Annual vendor validation exercise"],
      "residual_risk": "Medium",
      "red_flags": ["Vendor with no website or phone number", "Invoices just below approval threshold", "Payments to personal bank accounts"]
    }
  ],
  "red_team_findings": [
    {
      "control": "Dual approval for invoices >€10,000",
      "bypass_method": "Split single large invoice into multiple invoices below threshold",
      "bypass_risk": "High"
    }
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6)
- [x] Python 3.9+
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] ACFE fraud tree knowledge base as structured RAG input
- [ ] Industry-specific fraud scenario libraries (financial services, healthcare, government)

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Fraud scenario generation prompt with fraud triangle structure
- Red Team adversarial agent prompt
- Fraud triangle completeness validator
- Sample fraud scenario library for Procure-to-Pay

**What help I'm looking for:**

- Fraud specialists to validate scenario coverage against ACFE typologies
- Organizations willing to share anonymized fraud case history for scenario calibration

**Video Transcription Insights (Hackathon #3 analysis):**

AI has a structural advantage in fraud pattern detection: it processes the full transaction population simultaneously, without anchoring bias or fatigue. Video analysis identified the following pattern from a presentation on AI pattern detection:

- Human auditors test samples (typically 25-60 records) and extrapolate. AI can test 100% of the population and identify patterns that only emerge at scale — e.g., a specific vendor–approver pair that appears in 0.3% of transactions but accounts for 40% of overrides.
- The fraud agent should be prompted to look for **population-level patterns**, not just individual anomalies: "Are there combinations of fields (vendor + approver + amount range + day of week) that appear more frequently than expected?"
- Benchmarking: compare the fraud scenario library generated by this agent against the ACFE Occupational Fraud Report 2024 typologies. If the agent misses a common ACFE category, the scenario generation prompt needs calibration.

**AI as a New Fraud Risk Category (April 2026):**

The Anthropic Mythos incident (April 2026, NCSC NL directive) introduces a new category of AI-enabled fraud risk that this agent should model:

- **AI-enabled social engineering**: Mythos achieved 73% on the hardest CTF challenges and autonomously found a 27-year-old OpenBSD vulnerability. Applied to fraud, this capability level means AI agents can autonomously craft spear-phishing content, impersonate executives in email chains (bypassing traditional detection), and generate synthetic invoices that pass automated validation checks.
- **Glasswing** (Anthropic research, April 2026): a frontier AI capability for analyzing large codebases and financial datasets autonomously. In a fraud context, Glasswing-class AI can scan transaction datasets for fraud patterns — but also, in adversarial use, identify exploit patterns (control weaknesses) at scale that a human fraudster would miss.

**Implication for fraud scenario generation:** The fraud scenario library should now include an "AI-enabled fraud" category:

```json
{
  "fraud_category": "AI-Enabled Social Engineering",
  "scenarios": [
    "AI-generated deepfake voice call impersonating CFO to authorize wire transfer",
    "AI agent autonomously crafting and sending phishing emails targeting finance team",
    "AI-generated synthetic invoices with plausible vendor details that bypass matching controls"
  ],
  "detection_controls": [
    "Out-of-band verification for wire transfers above threshold",
    "Voice authentication protocols for high-value authorizations",
    "AI-generated content detection on incoming invoices"
  ]
}
```

The fraud risk assessment agent should be updated to include a dedicated "AI-enabled fraud" prompt that generates scenarios using the current frontier AI capability level as the threat actor capability baseline.

**Related SAAF plans:**

- [UC1 — Policy-to-Process Intake](frank-van-dissel-uc1-policy-process-intake.md) — provides Context Brief and native control register
- [UC3 — Incident Intelligence](frank-van-dissel-uc3-incident-issue-intelligence.md) — provides incident data as fraud signal input
- [UC7 — RCM Builder](frank-van-dissel-uc7-rcm-builder.md) — consumes fraud scenarios as risk input
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates fraud risk coverage
- [`plans/hackathon-3/audit-subagent-coordination-framework.md`](../hackathon-3/audit-subagent-coordination-framework.md) — multi-agent debate is recommended for high-stakes fraud risk ratings
- [`plans/hackathon-3/owasp-ai-testing-agent.md`](../hackathon-3/owasp-ai-testing-agent.md) — AI security testing; AI-enabled fraud scenarios require AI security controls as mitigations

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie fraud risk assessment process |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. Should the Red Team Agent run before or after the control effectiveness assessment — and does the order affect the quality of the bypass analysis?
2. How do we incorporate organizational fraud case history without sending sensitive data to the API?
3. Should the fraud scenario library be seeded with a pre-built ACFE typology knowledge base, or generated fresh per audit scope?
