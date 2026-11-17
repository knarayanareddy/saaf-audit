# Plan — Group 5 Hackers: Auditing AI Agents in Financial Services

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Group 5 Hackers (anonymous) |
| **Organisation** | Anonymous |
| **Session** | Alignment (Session 1) |
| **Type** | Agent |
| **Status** | Presented |

---

## 2. Problem Statement

AI agents are being deployed across financial services at speed — for credit scoring, fraud detection, customer service, and trading. Yet internal audit teams lack systematic tools to audit these AI systems. Key risks go undetected: model bias, unexplained decisions, regulatory non-compliance with the EU AI Act, and absence of audit trails.

Group 5 Hackers proposes a suite of five specialised audit agents — each targeting a distinct AI governance risk — to give internal audit teams the capability to assess AI systems with the same rigour applied to traditional financial controls.

---

## 3. Use-Case Type and Scope

**Audit domain:** AI Security — Auditing AI Agents in Financial Services (EU AI Act, NIST AI RMF, IIA)

**Applicable standards:**

- EU AI Act — High-risk AI classification, FRIA (Fundamental Rights Impact Assessment) requirements
- NIST AI RMF — Map, Measure, Manage, Monitor framework
- IIA Standards — Three-line audit model applied to AI governance
- CEN/CENELEC guidance on AI quality management (PrEN 18286)
- ISO AI Standards (80+ applicable standards)

**In scope:**

- Policy compliance scanning for AI systems against EU AI Act and internal policies
- High-risk AI classification and FRIA flagging
- Bias and discrimination testing across model outputs
- Audit trail analysis for AI decision logging and governance
- Model performance monitoring — drift detection and retraining trigger identification

**Out of scope:**

- Active penetration testing of AI systems
- Training or retraining of AI models
- Statutory or external audit of AI systems

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Compliance scan prompt (policy vs. EU AI Act); FRIA assessment prompt; bias detection prompt; audit trail analysis prompt; drift detection prompt |
| **Tools** | LLM frameworks (Anthropic, OpenAI, Llama, Mistral); agent platforms (LangChain, AutoGen, CrewAI); compliance tools (Ethyca, Fiddler, Modelbit) |
| **Regulatory** | EU AI Act (full text); NIST AI RMF; IIA Three-Line Model; CEN/CENELEC PrEN 18286; `regulatory/control-mappings/` |
| **Outputs** | AI compliance report; FRIA flag list; bias testing results; audit trail gaps; performance drift alerts |

---

## 5. Prompts

### System prompt (draft — Compliance Scanner Agent)

```
You are an AI compliance auditor specialised in the EU AI Act and financial services AI governance.
Given a description of an AI system (its purpose, inputs, outputs, and deployment context)
and the relevant policy text:

1. Classify the AI system under the EU AI Act (Unacceptable Risk / High Risk / Limited Risk / Minimal Risk)
2. For High-Risk systems: identify all applicable requirements from Annex III and assess compliance
3. Flag any requirements that are not met or not evidenced: specify the gap and the relevant article
4. Identify whether a Fundamental Rights Impact Assessment (FRIA) is required

Never classify a system as compliant if any mandatory requirement is unaddressed.
```

### System prompt (draft — Fairness Monitor Agent)

```
You are an AI fairness and bias auditor.
Given model output data (predictions, scores, or decisions) and the protected attributes
relevant to financial services (age, gender, nationality, disability):

1. Test for statistical disparity in outcomes across demographic groups
2. Apply fairness metrics: demographic parity, equalized odds, individual fairness
3. Flag any metric that exceeds acceptable thresholds
4. Produce an explainability summary: what features drive outcomes for each group?

Outputs must be interpretable by a non-technical audit committee.
```

### Example user prompts

**Prompt 1 — EU AI Act classification:**
```
AI system: Credit scoring model used in retail lending decisions.
Inputs: transaction history, income data, credit bureau data.
Outputs: approval/rejection decision + score.
Deployed by: a regulated financial institution in the EU.

Classify under EU AI Act. List all applicable Annex III requirements.
Assess whether a FRIA is required.
```

**Prompt 2 — Bias detection:**
```
Model output sample (n=10,000 loan applications):
- Approval rate by gender: Male 68%, Female 54%
- Approval rate by nationality: EU national 71%, Non-EU national 49%

Apply demographic parity and equalized odds metrics.
Flag if thresholds are exceeded. Draft audit finding if bias is detected.
```

**Intended file location:** `prompts/audit-use-cases/group5-compliance-scanner.md`, `prompts/audit-use-cases/group5-fairness-monitor.md`

---

## 6. Tools and Techniques

### Approach

Five specialised audit agents — each targeting a distinct AI governance risk:

1. **Compliance Scanner Agent** — Scans AI system documentation against EU AI Act and internal policies; flags non-compliance; classifies risk level
2. **Risk Classifier Agent** — Identifies High-Risk AI systems under EU AI Act Annex III; flags systems requiring FRIA; prioritises audit attention
3. **Fairness Monitor Agent** — Tests model outputs for bias and discrimination across protected attributes; applies standard fairness metrics
4. **Audit Trail Analyzer Agent** — Analyses AI decision logs for completeness, governance coverage, and explainability gaps
5. **Performance Validator Agent** — Detects model drift over time; identifies when retraining is triggered; validates that performance monitoring controls exist

### Quality Safeguards

- **Decision logging:** All agent outputs include reasoning chains — no black-box verdicts
- **Role-based access:** Agent outputs restricted to audit team; no model modification capability
- **Version control:** All agent logic committed to private GitHub with mandatory 2-reviewer policy (dev + audit team)

### Example script or pseudocode

```python
def audit_ai_system(system_description: dict, policy_docs: list, output_data: dict) -> dict:
    # Agent 1: Compliance
    compliance_report = compliance_scanner(system_description, policy_docs)

    # Agent 2: Risk classification
    risk_classification = risk_classifier(system_description)

    # Agent 3: Fairness
    fairness_results = fairness_monitor(output_data, protected_attributes=["gender", "nationality", "age"])

    # Agent 4: Audit trail
    trail_gaps = audit_trail_analyzer(system_description.get("decision_logs"))

    # Agent 5: Performance
    drift_alerts = performance_validator(system_description.get("monitoring_data"))

    return {
        "compliance": compliance_report,
        "risk": risk_classification,
        "fairness": fairness_results,
        "audit_trail": trail_gaps,
        "performance": drift_alerts
    }
```

**Tech stack used:** Python 3.9+, Claude API (Anthropic), OpenAI / Llama / Mistral, LangChain / AutoGen / CrewAI, Ethyca / Fiddler / Modelbit (compliance tooling)

**Intended file location:** `tools/scripts/group5-ai-audit-agents/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| EU AI Act | High-risk classification (Annex III); FRIA requirements; transparency obligations |
| NIST AI RMF | Map (risk identification), Measure (testing), Manage (controls), Monitor (ongoing) |
| IIA Standards | Three-line audit model; evidence requirements; reporting standards |
| CEN/CENELEC PrEN 18286 | AI quality management system requirements |

### Claude / AI tool usage notes

AI system descriptions and model output data may be commercially sensitive. Anonymise or use synthetic data during development. No real model weights or training data should be committed to the repo.

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (findings) + Markdown (compliance report, FRIA flag list)

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "compliance_scan": {
    "system": "Retail credit scoring model",
    "eu_ai_act_classification": "High Risk (Annex III — creditworthiness assessment)",
    "fria_required": true,
    "gaps": [
      {
        "article": "Article 13 — Transparency",
        "requirement": "High-risk AI systems must provide information enabling meaningful human oversight",
        "status": "Gap",
        "detail": "No explainability output available for rejection decisions"
      }
    ]
  },
  "fairness_results": {
    "demographic_parity_gap": {"gender": 0.14, "nationality": 0.22},
    "threshold": 0.10,
    "finding": "Nationality demographic parity gap (0.22) exceeds acceptable threshold (0.10). High risk of discriminatory outcome."
  }
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (Anthropic)
- [x] Python 3.9+
- [x] GitHub (private repo, 2-reviewer policy)
- [ ] Ethyca / Fiddler / Modelbit (compliance tooling)

**Stretch goals:**

- [ ] Integration with existing model monitoring platforms
- [ ] Automated FRIA report generation
- [ ] Continuous monitoring dashboard for deployed AI systems

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- EU AI Act compliance scan prompt
- Fairness Monitor prompt with metric definitions
- Audit Trail Analyzer prompt

**What help I'm looking for:**

- Legal/compliance experts to validate EU AI Act classification logic
- Data scientists to review fairness metric thresholds
- Financial services firms willing to test against real (anonymised) model output data

**Cross-org interest:**

Multiple SAAF organizations are likely deploying AI systems subject to the EU AI Act. A shared AI audit agent framework could serve as a community-maintained compliance tool.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Presented at Hackathon 1, March 10, 2026 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | TBD |
| **Act** | Not started | Target: future hackathon |

---

## 12. Open Questions

1. How should the Compliance Scanner handle AI systems that partially meet EU AI Act requirements — what threshold triggers a "Non-compliant" verdict vs. "Partially compliant"?
2. What fairness metric thresholds are appropriate for financial services — are there regulatory benchmarks from the EBA or ECB?
3. How do we handle proprietary model architectures where the audit team cannot access the model internals — is a black-box testing approach sufficient for EU AI Act compliance?
