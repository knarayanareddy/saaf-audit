# SAAF Hackathon Submission – Draft Plan

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Alex Zwijnenburg & Bas Rovers|
| **Organisation** | Kouters Van der Meer |
| **Session** | Hackathon 4 (Session 5) |
| **Type** | Agent |
| **Status** | Draft |
| **Claimed By** | Alex Zwijnenburg & Bas Rovers |

---

## 2. Problem Statement

Organizations often maintain large amounts of Governance, Risk & Compliance (GRC) information across multiple departments, processes, and reporting layers. This includes internal controls, effectiveness assessments, risks, risk rationales, and process documentation.

Transforming this information into consistent tactical and executive-level reporting is currently highly manual and lacks standardization. Different departments and risk managers may interpret and present risk information differently, resulting in inconsistent board reporting and reduced comparability over time.

In addition, creating management and board reports is time-consuming and requires significant manual analysis to identify trends, correlations, and key risk themes.

The proposed AI agent improves both standardization and efficiency by:

- Standardizing the interpretation and presentation of GRC data
- Supporting consistent reporting structures across organizations
- Automatically analyzing uploaded GRC datasets
- Identifying trends and correlations between ineffective controls and elevated risks
- Generating tactical and executive-level reports with visualizations and recommendations
- Allowing risk managers and department managers to interact with and refine reports before executive publication

The solution enables organizations to produce faster, more consistent, and more actionable risk reporting for management and board-level stakeholders.

---

## 3. Use-Case Type and Scope

**Audit domain:**  
Governance, Risk & Compliance Reporting / Enterprise Risk Management

**Applicable standards:**

- ISO 27001
- SOC 2
- ISAE 3402
- NIS2
- DORA
- COSO ERM
- Any governance, risk, compliance, or audit framework applicable to the organization

**In scope:**

- Analysis of uploaded GRC datasets
- Analysis of controls and effectiveness assessments
- Analysis of risks, risk scores, and rationales
- Correlation analysis between controls and risks
- Tactical-level reporting for risk and department managers
- Board-level reporting with visualizations and recommendations
- Human interaction loop before final board report generation
- Standardized reporting structures and terminology

**Out of scope:**

- Direct integration with or extraction from GRC tools
- Fully autonomous decision-making
- Real-time operational monitoring
- Automatic remediation execution
- Direct modification of source data
- Regulatory filing automation

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | System prompts for tactical and executive reporting agents |
| **Tools** | Data analysis and visualization scripts for uploaded GRC datasets |
| **Regulatory** | Reuse of standard control and risk frameworks where applicable |
| **Outputs** | Structured tactical and board-level reports including visualizations, findings, and recommendations |

---

## 5. Prompts

### System prompt (draft)

```text
You are an AI governance, risk, and compliance reporting assistant.

Your role is to analyze uploaded governance, risk, and internal control datasets and transform this information into clear tactical and executive-level reporting.

You must:
- Identify trends, anomalies, and correlations between ineffective controls and elevated risks
- Standardize reporting language and structure
- Explain findings in language suitable for board members and senior management
- Generate concise recommendations and mitigation actions
- Distinguish between operational, tactical, and strategic perspectives
- Ask clarifying questions when context is insufficient

You must never:
- Invent data or unsupported conclusions
- Present assumptions as facts
- Provide legal or regulatory guarantees
- Modify source data
```

### Example user prompts

**Prompt 1:**

```text
Analyze the uploaded control effectiveness assessments and identify trends between ineffective controls and high residual risks. Generate a tactical report for the risk manager including recommendations for remediation.
```

**Prompt 2:**

```text
Generate a board-level summary of the current risk posture based on the uploaded GRC dataset. Include visualizations, key risk themes, and strategic recommendations.
```

**Intended file location:**  
`prompts/audit-use-cases/grc-board-reporting-agent.md`

---

## 6. Tools and Techniques

### Approach

The solution consists of a multi-stage AI agent workflow.

1. Users upload structured GRC datasets containing:
   - Controls
   - Effectiveness assessments
   - Risks and risk scores
   - Processes
   - Risk rationales

2. A preprocessing layer normalizes and structures the uploaded data.

3. Analytical logic identifies:
   - Ineffective controls
   - Risk clusters
   - Trend developments
   - Correlations between risks and controls

4. The first AI agent generates a tactical-level report aimed at risk managers or department managers.

5. Users can interact with the tactical report and provide additional context or guidance.

6. A second AI agent translates the information into an executive board-level report with simplified explanations and strategic recommendations.

7. Visualizations are generated automatically based on the analyzed data.

### Example script or pseudocode

```python
# Load uploaded GRC data
controls = load_uploaded_controls()
risks = load_uploaded_risks()

# Identify ineffective controls
ineffective_controls = [
    c for c in controls if c.effectiveness == "ineffective"
]

# Correlate risks with ineffective controls
correlations = correlate(risks, ineffective_controls)

# Generate tactical report
tactical_report = tactical_agent.generate(correlations)

# Human feedback loop
feedback = collect_manager_feedback()

# Generate executive report
executive_report = executive_agent.generate(
    tactical_report,
    feedback
)
```

**Tech stack used:**  
Python 3.11, Claude API / OpenAI API, Power BI or Plotly for visualizations, LangChain or agent orchestration framework

**Intended file location:**  
`tools/scripts/grc-board-reporting-agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISO 27001 | Risk management and control effectiveness |
| SOC 2 | Internal control monitoring |
| DORA | ICT risk management and resilience |
| NIS2 | Cybersecurity governance and risk reporting |
| COSO ERM | Enterprise risk governance |

### Claude / AI tool usage notes

- No production personal data will be used during development
- Synthetic or anonymized datasets preferred during testing
- Human validation remains mandatory before board publication
- Executive outputs must remain explainable and traceable to source data

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:**  
Markdown + PDF + Visualization Dashboard

### Synthetic example output

```json
{
  "report_type": "Board Risk Report",
  "overall_risk_posture": "Elevated",
  "key_findings": [
    {
      "risk": "Third-party vendor access",
      "risk_rating": "High",
      "related_control_status": "Ineffective",
      "trend": "Increasing over last 2 quarters"
    }
  ],
  "recommendations": [
    "Implement quarterly vendor access recertification",
    "Increase monitoring on privileged third-party accounts"
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Desktop
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [x] Visualization tooling (Power BI / Plotly)
- [x] Uploaded structured datasets (CSV / Excel / JSON)

**Stretch goals:**

- [ ] Interactive conversational reporting interface
- [ ] Multi-language reporting
- [ ] Industry benchmarking capabilities
- [ ] Multi-framework compliance mapping

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- System prompts
- Synthetic GRC datasets
- Reporting logic examples
- Visualization templates
- Correlation analysis methods

**What help I'm looking for:**

- Feedback on executive reporting quality
- Expertise in visualization best practices
- Additional regulatory mapping validation
- Feedback from audit and risk professionals

**Cross-org interest:**

This use case is broadly applicable across organizations using GRC processes and performing risk reporting. Collaboration is welcome, especially around standardization of executive risk reporting and explainable AI outputs.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | In progress | Initial concept and architecture defined |
| **Do** | Not started | Prototype development planned during hackathon |
| **Check** | Not started | Validation with risk professionals planned |
| **Act** | Not started | Potential expansion after pilot feedback |

---

## 12. Open Questions

1. What is the most effective visualization approach for executive-level risk communication?
2. How can explainability and traceability of AI-generated recommendations be validated?
3. Which uploaded dataset structures should be standardized first?
4. What level of human approval should be mandatory before report publication?
5. How can multi-framework reporting be standardized effectively?
