# Plan — Mollie Group X: AI-Assisted Audit Evidence Collection and Analysis

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mollie Group X (anonymous) |
| **Organisation** | Mollie |
| **Session** | Alignment (Session 1) |
| **Type** | Agent |
| **Status** | Presented |

---

## 2. Problem Statement

Internal auditors spend significant time on repetitive, low-judgment tasks: collecting evidence from various systems, cross-referencing it against control objectives, assessing whether the evidence is sufficient and appropriate, and drafting findings and conclusions. These tasks are time-consuming and error-prone when done manually.

Mollie Group X proposes building a pipeline of agents covering the core audit execution workflow: collecting evidence, analyzing it against control objectives, checking the quality of the analysis, and producing structured findings conclusions.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Fieldwork — Evidence Collection and Analysis

**Applicable standards:**

- IIA International Standards — evidence sufficiency and appropriateness
- AI Act — applicable to AI tools used in the audit process
- ISO 27001 / COBIT — as relevant control frameworks for evidence assessment
- NIST Cybersecurity Framework — applicable control objectives
- CIS Controls — technical control benchmarks

**In scope:**

- Automated collection of audit evidence from relevant systems and sources
- Analysis of evidence against predefined control objectives
- Quality check of AI-generated analysis outputs (self-review / second-agent review)
- Drafting structured findings conclusions (effective / not effective)

**Out of scope:**

- Audit planning and risk assessment (separate from fieldwork execution)
- CAE approval and reporting (post-fieldwork)
- Network or infrastructure penetration testing

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Evidence collection prompt; evidence analysis prompt (vs. control objective); quality check prompt; findings conclusion prompt |
| **Tools** | Python evidence collection scripts; multi-agent pipeline (collect → analyze → check → conclude); Claude Code for analysis |
| **Regulatory** | AI Act; ISO 27001; COBIT; NIST; CIS Controls loaded as reference framework |
| **Outputs** | Structured findings: control objective, evidence collected, analysis, quality verdict, conclusion (effective / not effective) |

---

## 5. Prompts

### System prompt (draft — Evidence Analysis Agent)

```
You are an internal audit evidence analyst.
Given a control objective and a set of collected evidence items:

1. Assess whether the evidence is sufficient: does it cover the full population or an appropriate sample?
2. Assess whether the evidence is appropriate: is it reliable, relevant, and from a credible source?
3. For each control objective: determine whether the evidence supports a conclusion of Effective or Not Effective
4. If the evidence is insufficient or inappropriate: specify what additional evidence is required

Do not draw conclusions beyond what the evidence explicitly supports.
Flag any inference that requires auditor judgment rather than direct evidence.
```

### System prompt (draft — Quality Check Agent)

```
You are an audit quality reviewer.
Given an evidence analysis produced by an AI agent:

1. Check that every conclusion is directly supported by the cited evidence — flag unsupported conclusions
2. Check that the analysis covers the full scope of the control objective — flag scope gaps
3. Check that the language is clear, professional, and audit-appropriate
4. Assign a quality verdict: Pass / Requires Revision / Fail

A "Pass" verdict requires: all conclusions supported, full scope covered, professional language.
```

### Example user prompts

**Prompt 1 — Evidence analysis:**
```
Control objective: "All user access to the payment system is reviewed and certified by the access owner on a quarterly basis."

Evidence collected:
- Access review log Q4 2025 (system export): 342 users reviewed, 12 revoked
- Access review sign-off email from access owner dated 2026-01-15
- 8 users identified in the system with no review record

Assess evidence sufficiency and appropriateness. Conclude: Effective or Not Effective?
```

**Prompt 2 — Quality check:**
```
Analysis produced by Evidence Analysis Agent:
"The access review was completed and the control is effective."

Evidence cited: access review log (342 users reviewed).

Quality check: is the conclusion fully supported? Are there gaps?
```

**Intended file location:** `prompts/audit-use-cases/mollie-groupx-evidence-analysis.md`, `prompts/audit-use-cases/mollie-groupx-quality-check.md`

---

## 6. Tools and Techniques

### Approach

Sequential four-stage agent pipeline — each stage feeds into the next:

1. **Evidence Collection Agent** — Collects evidence from relevant systems and sources based on the control objective; organises evidence by type and source
2. **Evidence Analysis Agent** — Assesses collected evidence against the control objective; determines whether it is sufficient and appropriate; draws a preliminary conclusion
3. **Quality Check Agent** — Reviews the analysis output for unsupported conclusions, scope gaps, and language quality; assigns Pass / Requires Revision / Fail
4. **Findings Conclusion Agent** — Drafts the structured finding (if Not Effective) or confirms effective conclusion; produces output in standard finding format

Agents proceed from simple to complex: start with well-defined control objectives and structured evidence before tackling ambiguous or unstructured sources.

### Example script or pseudocode

```python
def run_evidence_audit_pipeline(control_objective: str, evidence_sources: list) -> dict:
    # Stage 1: Collect
    evidence = evidence_collection_agent(control_objective, evidence_sources)

    # Stage 2: Analyze
    analysis = evidence_analysis_agent(control_objective, evidence)

    # Stage 3: Quality check
    quality_result = quality_check_agent(analysis)

    if quality_result["verdict"] == "Requires Revision":
        analysis = evidence_analysis_agent(control_objective, evidence,
                                           feedback=quality_result["feedback"])
        quality_result = quality_check_agent(analysis)

    # Stage 4: Conclude
    finding = findings_conclusion_agent(control_objective, analysis, quality_result)

    return {"evidence": evidence, "analysis": analysis,
            "quality": quality_result, "finding": finding}
```

**Tech stack used:** Python 3.9+, Copilot, Gemini, Claude (Claude Code for evidence analysis), GitHub

**Intended file location:** `tools/scripts/mollie-groupx-evidence-audit/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA Standards | Evidence sufficiency and appropriateness; workpaper requirements |
| AI Act | Requirements applicable to AI tools used in audit decision-making |
| ISO 27001 | Information security controls as audit subject matter |
| COBIT | IT governance controls as audit subject matter |
| NIST CSF | Cybersecurity controls as audit subject matter |
| CIS Controls | Technical security benchmarks as audit subject matter |

### Claude / AI tool usage notes

Evidence collected from live systems may contain confidential or personal data. Use anonymised or synthetic evidence during development and testing. Define clear data handling procedures before connecting to production systems.

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (structured finding) + Markdown (analysis narrative)

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "control_objective": "All user access to the payment system is reviewed and certified quarterly",
  "evidence_collected": [
    {"type": "System export", "source": "Payment system access log", "reliability": "High"},
    {"type": "Sign-off email", "source": "Access owner", "reliability": "Medium"}
  ],
  "analysis": {
    "sufficient": false,
    "appropriate": true,
    "gaps": "8 users have no review record — not covered by the evidence provided"
  },
  "quality_verdict": "Requires Revision",
  "quality_feedback": "Conclusion of 'Effective' is unsupported — 8 users were not reviewed",
  "finding": {
    "id": "F-001",
    "title": "Incomplete quarterly access review — 8 users not certified",
    "risk_rating": "Medium",
    "observation": "8 active users in the payment system have no record of quarterly access certification for Q4 2025, contrary to the access management policy.",
    "recommendation": "Access owner to review and certify all 8 users immediately; implement automated completeness check on the access review process."
  }
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Code
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [x] Copilot / Gemini (supporting tools)

**Stretch goals:**

- [ ] Integration with audit management system for automatic workpaper population
- [ ] Automated evidence collection connectors for common systems (ERP, IAM, ITSM)

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Evidence Analysis Agent prompt
- Quality Check Agent prompt
- Four-stage pipeline pseudocode

**What help I'm looking for:**

- Auditors to validate the quality check criteria — what makes an analysis "Pass" vs. "Requires Revision"?
- Organizations to contribute anonymised control objectives and evidence samples for testing

**Cross-org interest:**

The evidence analysis and quality check pattern is applicable across audit domains. Other SAAF participants building fieldwork agents should align on the finding schema and quality gate approach.

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

1. How should the pipeline handle evidence that is partially relevant — some items support the objective, others are inconclusive? When is the overall conclusion Effective vs. Not Effective?
2. How many Quality Check cycles are acceptable before escalating to a human auditor?
3. Which AI model combination is most appropriate for each stage — Claude for analysis and quality check, Gemini or Copilot for evidence collection?
