# Plan — AuditFlow AI: Automating the Audit Lifecycle

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | AuditFlow AI team (anonymous) |
| **Organisation** | Anonymous |
| **Session** | Alignment (Session 1) |
| **Type** | Agent |
| **Status** | Presented |

---

## 2. Problem Statement

70% of audit time is spent on manual, repetitive work — leaving teams burned out and unable to focus on strategic risk analysis. Audit coverage is incomplete and fraud signals are missed because auditors are buried in documentation, scheduling, and evidence review.

AuditFlow AI proposes end-to-end AI-powered automation across the entire audit lifecycle: from risk planning through evidence collection, control testing, interview analysis, and stakeholder coordination. The goal is to free auditors to focus on high-value risk analysis and governance advisory — promising 3x audit coverage, 85% faster fraud detection, and 60% time savings.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Lifecycle — End-to-End Automation (Planning, Execution, Testing, Reporting)

**Applicable standards:**

- IIA International Standards for the Professional Practice of Internal Auditing
- SOC 2 — compliance and data governance requirements for the platform itself

**In scope:**

- Automated risk questionnaire generation and audit scope prioritisation
- Evidence document scanning, categorisation, and matching to test objectives
- Automated Tests of Operating Effectiveness with exception detection
- Interview transcription and conversion to formal audit language
- Stakeholder scheduling, agenda preparation, action item tracking

**Out of scope:**

- Deep IT General Controls testing
- Real-time continuous control monitoring beyond audit scope
- External audit / statutory audit workflows

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Risk questionnaire generation prompt; evidence categorisation prompt; interview-to-audit-language prompt; workpaper generation prompt |
| **Tools** | LLM-powered document analysis pipeline; pattern recognition for fraud signals; anomaly detection for control exceptions; stakeholder scheduling logic |
| **Regulatory** | IIA Standards; SOC 2 compliance requirements; audit trail requirements |
| **Outputs** | Risk-prioritised audit scope; categorised evidence with reliability scores; workpapers with test results; formal audit observations from interviews; stakeholder communication log |

---

## 5. Prompts

### System prompt (draft — Evidence Validator Agent)

```
You are an audit evidence specialist.
Given a set of uploaded documents and a list of test objectives:

For each document:
1. Categorise the document type (e.g. policy, system report, approval log, exception report)
2. Match it to the most relevant test objective(s) from the list provided
3. Assign a reliability score (High / Medium / Low) based on source credibility:
   - High: system-generated, tamper-evident, or independently verified
   - Medium: internally produced, reviewed by a second party
   - Low: self-reported, undated, or unverified
4. Flag any test objectives with no matching evidence

Never fabricate document content. Only assess what is explicitly present.
```

### System prompt (draft — Interview Analyst Agent)

```
You are an internal audit report writer.
Given a transcript of a stakeholder interview:

1. Extract key findings, control weaknesses, and management representations
2. Convert informal language into formal audit observation language (IIA standard)
3. Identify any statements that require corroboration with documentary evidence
4. Flag contradictions between different interviewees' statements

Output: structured list of audit observations with supporting quotes from the transcript.
```

### Example user prompts

**Prompt 1 — Evidence matching:**
```
Test objectives:
- TO-01: Verify that all purchase orders above €10,000 were approved by a manager
- TO-02: Verify that no payments were made to vendors not on the approved vendor list

Documents uploaded:
- "PO_approval_log_Q4_2025.xlsx" (system export)
- "Vendor_master_list_2025.pdf" (internal document)
- "Payment_run_December.csv" (ERP export)

Categorise each document, match to test objectives, assign reliability scores.
```

**Prompt 2 — Interview analysis:**
```
Interview transcript:
Auditor: "How do you ensure duplicate invoices are not paid?"
Controller: "We have a system check, but sometimes it flags false positives so we override it manually."
Auditor: "How often is the override used?"
Controller: "Maybe once or twice a week."

Extract findings and convert to formal audit language.
```

**Intended file location:** `prompts/audit-use-cases/auditflow-ai-evidence-validator.md`, `prompts/audit-use-cases/auditflow-ai-interview-analyst.md`

---

## 6. Tools and Techniques

### Approach

Four-workgroup pipeline (each owning one agent development track):

1. **Risk Intelligence Agent** — Analyses historical audit data, regulatory updates, and company news; generates risk questionnaires; prioritises audit scope
2. **Evidence Validator Agent** — Scans uploaded documents; matches to test objectives; assigns reliability scores based on source credibility
3. **Control Tester Agent** — Performs automated Tests of Operating Effectiveness; identifies exceptions; generates workpapers
4. **Interview Analyst Agent** — Transcribes stakeholder interviews; extracts key findings; converts to formal audit observations
5. **Stakeholder Coordinator Agent** — Schedules meetings; prepares agendas; tracks action items; sends reminders

### Example script or pseudocode

```python
def run_auditflow_pipeline(audit_scope: dict, documents: list, interviews: list) -> dict:
    # Phase 1: Planning
    risk_profile = risk_intelligence_agent(audit_scope)

    # Phase 2: Evidence
    evidence_results = evidence_validator_agent(documents, risk_profile["test_objectives"])

    # Phase 3: Testing
    test_results = control_tester_agent(evidence_results)

    # Phase 4: Reporting
    observations = interview_analyst_agent(interviews)
    workpapers = generate_workpapers(test_results, observations)

    return {"risk_profile": risk_profile, "test_results": test_results,
            "observations": observations, "workpapers": workpapers}
```

**Tech stack used:** LLM frameworks (OpenAI, Anthropic, Llama, Mistral), Agent platforms (LangChain, AutoGen, CrewAI), Audit tools (DataSnipper, Alteryx, UiPath), Python

**Intended file location:** `tools/scripts/auditflow-ai/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA Standards | Evidence sufficiency and reliability; workpaper requirements; reporting standards |
| SOC 2 | Data governance and security for the platform itself; audit trail requirements |

### Claude / AI tool usage notes

TBD — audit evidence documents may contain confidential information; data residency and anonymisation requirements to be confirmed. Synthetic data only during testing.

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (test results, evidence matching) + Markdown (workpapers, audit observations)

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "evidence_validation": [
    {
      "document": "PO_approval_log_Q4_2025.xlsx",
      "type": "System-generated approval log",
      "matched_objectives": ["TO-01"],
      "reliability": "High",
      "notes": "ERP system export — tamper-evident"
    }
  ],
  "test_results": [
    {
      "objective": "TO-01",
      "result": "Exception",
      "detail": "3 purchase orders above €10,000 approved by initiator — segregation of duties violation",
      "risk_rating": "High"
    }
  ],
  "observations": [
    {
      "source": "Controller interview",
      "finding": "Duplicate payment check override is used approximately twice per week without documented approval",
      "corroboration_required": true
    }
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Desktop
- [x] Python 3.9+
- [x] LangChain / AutoGen / CrewAI (agent orchestration)
- [ ] DataSnipper / Alteryx (audit tool integration)
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] SOC 2 compliant deployment with full audit trail
- [ ] Integration with TeamMate+ or other audit management systems
- [ ] Real-time stakeholder dashboard

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Evidence Validator prompt with reliability scoring rubric
- Interview Analyst prompt for audit language conversion
- Risk Intelligence questionnaire generation prompt

**What help I'm looking for:**

- Auditors to validate reliability scoring rubric for different evidence types
- Organizations willing to contribute anonymised interview transcripts for testing

**Cross-org interest:**

Multiple SAAF participants are working on overlapping lifecycle stages (planning, evidence, reporting). Coordination on shared schemas (test objectives, evidence, findings) would reduce duplication.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Presented at Hackathon 1, March 10, 2026 |
| **Do** | In progress | Prototype concept presented; individual agents to be built |
| **Check** | Not started | TBD |
| **Act** | Not started | Target: future hackathon |

---

## 12. Open Questions

1. How should evidence reliability scoring handle documents that are internally produced but reviewed by an external party (e.g. management representations confirmed by external auditor)?
2. Which agent orchestration framework is most appropriate for the sequential pipeline — LangChain, AutoGen, or CrewAI?
3. How do we ensure the Interview Analyst Agent does not hallucinate findings not present in the transcript?
