# Plan — Team 67: Accelerating Internal Audit, Compliance & Risk with Intelligent Agents

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Team 67 (anonymous — five specialists in IT Audit, IT Risk, Compliance, and Data Management) |
| **Organisation** | Anonymous |
| **Session** | Alignment (Session 1) |
| **Type** | Agent |
| **Status** | Presented |

---

## 2. Problem Statement

The 2026 risk landscape presents three converging challenges for internal audit: cybersecurity and AI risks dominate audit priorities, regulatory complexity and supply chain vulnerabilities are accelerating, and organizations need continuous — not annual — risk monitoring.

Traditional audit workflows are too slow and too manual to keep pace. Team 67 proposes five intelligent agents that unify audit, compliance, and risk functions into always-on, data-driven workflows: continuous risk monitoring, instant compliance query handling, AI-powered risk assessment, program assurance from interviews, and ethical AI oversight for deployed AI systems.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Continuous Risk Monitoring, Compliance, AI Governance (cross-domain)

**Applicable standards:**

- IIA International Standards for the Professional Practice of Internal Auditing
- EU AI Act — AI governance and oversight requirements
- Applicable regulatory frameworks per organization (to be configured per deployment)

**In scope:**

- Continuous integration of IT systems, third-party vendor feeds, and regulatory data for risk monitoring
- AI chatbot for policy and compliance queries from employees and auditors
- Historical audit finding analysis for dynamic risk scoring and audit prioritisation
- Interview-to-report conversion for program assurance engagements
- Continuous monitoring of deployed AI systems for bias, compliance gaps, and explainability

**Out of scope:**

- Execution of fieldwork testing
- Legal advice or legally binding compliance determinations
- Model training or retraining of monitored AI systems

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Risk monitoring alert prompt; compliance query response prompt; risk scoring and prioritisation prompt; interview-to-report (Program Assurance RAG) prompt; AI oversight monitoring prompt |
| **Tools** | Data integration pipeline (IT systems + vendor feeds + regulatory feeds); policy RAG knowledge base; historical audit finding database; AI system monitoring hooks |
| **Regulatory** | IIA Standards; EU AI Act; organization-specific regulatory frameworks loaded as RAG knowledge base |
| **Outputs** | Risk alerts (prioritised by severity); compliance query responses; dynamic risk score rankings; program assurance reports; AI oversight findings |

---

## 5. Prompts

### System prompt (draft — Continuous Risk Monitoring Agent)

```
You are an internal audit risk monitoring specialist.
You have access to integrated data from IT systems, third-party vendor feeds, and regulatory update streams.

On each monitoring cycle:
1. Identify anomalies, emerging risks, and compliance gaps across connected data sources
2. Prioritise findings by risk severity (High / Medium / Low)
3. For High-priority findings: generate an immediate alert with: risk description, affected system/process, recommended action, and urgency level
4. For regulatory updates: flag any new requirements that affect the organization's current control framework

Never suppress a High-priority finding without explicit human approval.
```

### System prompt (draft — Program Assurance RAG Agent)

```
You are an internal audit report specialist.
Given transcripts or notes from audit interviews and a framework reference (e.g. IIA, ISO, COBIT):

1. Extract audit-relevant information: control descriptions, management representations, process deviations
2. Map findings to the applicable framework criteria
3. Draft structured audit observations in professional internal audit language
4. Identify gaps where additional evidence or interviews are needed

Output: framework-aligned audit report sections, ready for audit manager review.
```

### Example user prompts

**Prompt 1 — Risk monitoring alert:**
```
Integrated data update:
- Vendor "SupplierX" flagged in sanctions screening database (updated 2026-04-10)
- IT system "ERP Core" shows 15% spike in failed login attempts (last 24h)
- Regulatory update: NIS2 implementation deadline passed; organization has not yet completed gap assessment

Generate prioritised risk alerts. Flag High-priority items for immediate escalation.
```

**Prompt 2 — Compliance query:**
```
Employee query: "Our team wants to use an AI tool to automate invoice approvals. Do we need approval from compliance before deploying it? What policies apply?"

Answer based on our internal AI governance policy and the EU AI Act.
```

**Intended file location:** `prompts/audit-use-cases/team67-risk-monitor.md`, `prompts/audit-use-cases/team67-program-assurance-rag.md`

---

## 6. Tools and Techniques

### Approach

Five specialised intelligent agents:

1. **Continuous Risk Monitoring Agent** — Connects IT systems, third-party vendor feeds, and regulatory data; uses ML anomaly detection to identify emerging risks; sends prioritised alerts
2. **Automated Compliance Query Agent** — AI chatbot answering policy and compliance questions from employees and auditors 24/7, based on current regulations and internal policies
3. **Program Assurance RAG Agent** — Converts interview data and notes into framework-aligned audit reports using Retrieval-Augmented Generation against the relevant audit standard
4. **AI-Powered Risk Assessment Agent** — Reviews historical audit findings and control effectiveness; generates dynamic risk scores; recommends priority audit areas
5. **Ethical AI Oversight Agent** — Continuously monitors AI systems in business processes for bias, compliance gaps, and explainability issues; aligned with EU AI Act

### Quality Safeguards

- **Private collaboration, public results:** Private GitHub repo for agent logic; public repositories for shared industry best practices
- **Mandatory peer review:** All agent logic reviewed before deployment to ensure cross-industry standards alignment
- **Human escalation:** High-priority alerts and compliance determinations always routed to a human auditor

### Example script or pseudocode

```python
def run_team67_risk_pipeline(data_feeds: dict, query: str = None, interview_notes: str = None) -> dict:
    results = {}

    # Agent 1: Continuous risk monitoring
    results["risk_alerts"] = continuous_risk_monitor(data_feeds)

    # Agent 2: Compliance query (if query provided)
    if query:
        results["compliance_answer"] = compliance_query_agent(query, policy_kb=load_policy_kb())

    # Agent 3: Program assurance (if interview notes provided)
    if interview_notes:
        results["assurance_report"] = program_assurance_rag(interview_notes, framework="IIA")

    # Agent 4: Risk assessment
    results["risk_scores"] = risk_assessment_agent(data_feeds.get("historical_findings"))

    # Agent 5: AI oversight
    results["ai_oversight"] = ethical_ai_monitor(data_feeds.get("ai_system_logs"))

    return results
```

**Tech stack used:** Python 3.9+, Claude API / LLM of choice, RAG framework (vector database + retrieval), ML anomaly detection, GitHub (private repo with mandatory peer review)

**Intended file location:** `tools/scripts/team67-intelligent-agents/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA Standards | Evidence requirements; reporting; three-line model |
| EU AI Act | High-risk AI classification; transparency; ongoing monitoring requirements |
| NIS2 | Cybersecurity risk monitoring; incident reporting |

### Claude / AI tool usage notes

The Compliance Query Agent and Program Assurance RAG Agent process internal policies and interview notes — potentially containing commercially sensitive information. These must not be sent to external LLM APIs without data processing agreements. Synthetic data only for development and testing.

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (risk alerts, risk scores) + Markdown (compliance answers, assurance reports, AI oversight findings)

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "risk_alerts": [
    {
      "priority": "High",
      "risk": "Sanctioned vendor in active supply chain",
      "affected": "SupplierX — Accounts Payable",
      "action": "Immediately suspend payments and escalate to Legal and Procurement",
      "urgency": "Same business day"
    },
    {
      "priority": "Medium",
      "risk": "ERP login failure spike — potential brute force attempt",
      "affected": "ERP Core authentication",
      "action": "IT Security to investigate and review access logs within 48h"
    }
  ],
  "risk_scores": [
    {"audit_area": "Third-Party Risk", "score": 87, "trend": "Increasing", "recommendation": "Priority audit Q2 2026"},
    {"audit_area": "Cybersecurity", "score": 74, "trend": "Stable", "recommendation": "Include in annual plan"}
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / LLM of choice
- [x] Python 3.9+
- [x] RAG framework (vector store + retrieval)
- [x] GitHub (private repo, mandatory peer review)
- [ ] ML anomaly detection (scikit-learn / cloud ML)

**Stretch goals:**

- [ ] Real-time dashboard for risk monitoring alerts
- [ ] Integration with audit management system for automatic finding creation
- [ ] Continuous AI monitoring hooks for deployed AI systems

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Continuous Risk Monitoring prompt
- Program Assurance RAG prompt with IIA framework mapping
- Compliance Query Agent prompt

**What help I'm looking for:**

- Organizations with mature continuous monitoring setups to validate the data integration approach
- Compliance experts to review the EU AI Act classification logic in the Ethical AI Oversight Agent

**Cross-org interest:**

The Program Assurance RAG Agent overlaps with use cases across multiple SAAF organizations. A shared framework-aligned RAG knowledge base (IIA, ISO, COBIT) could be a community resource.

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

1. How do we handle the tension between real-time risk monitoring (which requires live data access) and the SAAF principle of not committing real audit data — should the monitoring agent operate on a separate, secured infrastructure?
2. For the Compliance Query Agent: how do we ensure responses stay within the bounds of the organization's actual policies and avoid hallucinating compliance positions?
3. Should the Ethical AI Oversight Agent be scoped to AI systems the organization uses internally, or also to AI systems embedded in third-party vendor products?
