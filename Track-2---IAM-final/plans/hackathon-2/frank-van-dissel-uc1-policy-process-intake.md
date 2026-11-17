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

The first step of any audit is understanding the "official" way a process is intended to function. Today, auditors read policy documents, SOPs, and process manuals manually — extracting process steps, objectives, and controls by hand. This is slow, inconsistent, and produces unstructured notes that cannot be fed into downstream audit tools. The Policy-to-Process Intake Agent acts as a specialized Document Parser: it takes unstructured policy documents and transforms them into a structured Process Map and Initial Risk/Control Register, satisfying GIAS 13.2's requirement to understand how processes are intended to operate.

This is **Use Case 1 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It produces the foundational Context Brief that all subsequent agents (UC2–UC9) depend on.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Process Understanding (GIAS 13.2)

**Applicable standards:**

- GIAS 13.2 — Understanding the activity: "Internal auditors must identify and gather reliable, relevant, and sufficient information regarding the governance, risk management, and control processes of the activity under review."
- GIAS 13.2 — "Internal auditors must review the gathered information to understand how processes are intended to operate."

**In scope:**

- Parsing PDF, Word, and text policy documents / SOPs / process manuals
- Extracting Sub-Processes, Activities, and their stated Objectives
- Identifying native controls and risks mentioned in the policy text ("Risk & Control Bycatch")
- Grounding every extracted element to a specific paragraph or page (traceability)
- Producing a structured JSON Context Brief consumable by UC2–UC9
- Completeness guard for documents over 5 pages

**Out of scope:**

- Live process observation or stakeholder interviews
- Assessing whether the documented process reflects actual practice
- Detailed risk scoring (handled in UC4 and UC7)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | System prompt for document segmentation, normative statement detection, and structured extraction — reuse pattern from [`prompts/audit-use-cases/policy-to-controls.md`](../../prompts/audit-use-cases/) (related: [Policy-to-Controls-Extractor plan](johannesiv-policy-to-controls-extractor.md)) |
| **Tools** | Python agent: PDF/DOCX text extractor → Claude → structured JSON; Completeness Guard agent for documents >5 pages |
| **Regulatory** | GIAS 13.2 compliance checklist; reuse `regulatory/control-mappings/` for cross-referencing extracted controls |
| **Outputs** | Context Brief JSON: Process Map (Process IDs, Names, Activities), Mapped Objectives, Native Risk/Control Register with source quotes |

---

## 5. Prompts

### System prompt (draft)

```
You are a Document Parser specialised in internal audit process understanding.
Given a policy document (SOP, process manual, or procedure), extract:
1. Sub-Processes: hierarchical list of process names and underlying activities
2. Objectives: the stated purpose for each sub-process
3. Native Controls: sentences defining a control (e.g. "Must be approved by...")
4. Native Risks: sentences defining an explicit risk (e.g. "To prevent unauthorized access...")

For every extracted element, include a Source Quote — the exact paragraph or
sentence from the source document. Never infer or invent content not present
in the document. Mark ambiguous elements as "TBD: requires clarification."

Output a valid JSON object conforming to the Context Brief schema.
```

### Example user prompts

**Prompt 1:**
```
Audit Topic: "Procure-to-Pay Audit 2026"
Document: [15-page PDF — Invoice Processing and Payment Policy]

Parse this document. Extract all sub-processes, activities, objectives,
and native risks/controls. Include source quotes for every element.
```

**Prompt 2 — Completeness Guard:**
```
Table of contents of the source document:
[section headings list]

Generated JSON Process Map:
[extracted JSON]

Identify any sections from the table of contents that have no
corresponding process steps in the JSON. Flag them as gaps.
```

**Intended file location:** `prompts/audit-use-cases/uc1-policy-process-intake.md`

---

## 6. Tools and Techniques

### Approach

Two-agent pipeline:

1. **Parser Agent** — reads the policy document, segments it into contextual prose vs. actionable requirements, extracts process map, objectives, and native risk/control register with source quotes, outputs JSON Context Brief.
2. **Completeness Guard Agent** (for documents >5 pages) — compares the document's table of contents / headings against the generated JSON. If a section exists in the document but has no corresponding process steps in the JSON, it flags the gap and re-processes the missing section.

### Quality Safeguards

**Safeguard 1 — Traceability Check:** Every outputted process step or control must include a `source_quote` field from the policy text. Items without a source quote are flagged as unverified.

**Safeguard 2 — Anti-Focus-Loss (Completeness Guard):** For documents over 5 pages, a second agent performs a "Missing Element Scan" comparing headings to JSON output. Gaps are flagged and re-processed.

### Example script or pseudocode

```python
def run_intake_agent(document_path: str, audit_topic: str) -> dict:
    text = extract_text(document_path)        # PDF/DOCX parser
    context_brief = parse_with_claude(text, audit_topic)   # Parser Agent
    if len(text) > FIVE_PAGE_THRESHOLD:
        gaps = completeness_guard(text, context_brief)     # Completeness Guard
        context_brief["gaps"] = gaps
    return context_brief  # JSON: process_map, objectives, native_rcr
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), `pdfplumber`, `python-docx`

**Intended file location:** `tools/scripts/uc1-policy-process-intake/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2 | Understanding governance, risk management, and control processes of the activity under review |
| GIAS 13.2 | Identifying management's criteria for measuring objective achievement |

### Claude / AI tool usage notes

Policy documents processed should not contain real personal data. All test runs use synthetic or publicly available process documentation. Source quotes are extracted verbatim — no paraphrasing — to maintain auditability.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (Context Brief)

**Schema reference:** Custom schema; output consumed by UC2–UC9. Native risk/control register fields map to `outputs/schemas/finding-schema.json`.

### Test Scenario — Accounts Payable SOP Parse

- **Input:** 15-page PDF — "Invoice Processing and Payment Policy"
- **Expected:** Complete list of sub-processes covering all sections; native controls identified from beginning, middle, and end of document
- **Validation:** Completeness Guard confirms Section 5.4 (often missed by AI) is captured in the output

### Synthetic example output

```json
{
  "audit_topic": "Procure-to-Pay Audit 2026",
  "process_map": [
    {
      "process_id": "P-01",
      "name": "Invoice Receipt",
      "activities": ["Receive invoice via email or portal", "Log invoice in ERP system"],
      "objective": "Ensure all invoices are recorded completely and in a timely manner",
      "source_quote": "Section 2.1: All invoices must be registered in the ERP within 24 hours of receipt."
    }
  ],
  "native_rcr": [
    {
      "type": "control",
      "description": "Invoices above €10,000 must be approved by the Finance Director",
      "process_id": "P-01",
      "source_quote": "Section 3.4: Invoices exceeding €10,000 require Finance Director approval."
    }
  ],
  "completeness_gaps": []
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional for test documents)

**Stretch goals:**

- [ ] Support for structured process modelling formats (BPMN XML)
- [ ] Interactive gap review UI for auditors to confirm or dismiss completeness gaps

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Parser agent system prompt and completeness guard prompt
- JSON Context Brief schema (consumed by all downstream agents)
- Python pipeline

**What help I'm looking for:**

- Review of the JSON schema by auditors who will build downstream agents (UC2–UC9)
- Test documents in Dutch and other EU languages (policy parsing in multiple languages)
- Feedback from organizations using different document formats (SharePoint, Confluence exports)

**Cross-org interest:**

The foundational Context Brief produced by UC1 is the input for eight downstream agents. Any SAAF organization building an audit planning pipeline needs this first step. Strongly related to the [Policy-to-Controls-Extractor](johannesiv-policy-to-controls-extractor.md) — both share the same document parsing approach; the two teams should align on the JSON schema.

**Related SAAF plans:**

- [UC2 — Previous Audit Intelligence](frank-van-dissel-uc2-previous-audit-intelligence.md) — consumes Context Brief from UC1
- [UC3 — Incident Intelligence](frank-van-dissel-uc3-incident-issue-intelligence.md) — consumes Context Brief from UC1
- [UC4 — Fraud Risk Assessment](frank-van-dissel-uc4-fraud-risk-assessment.md) — consumes Context Brief from UC1
- [UC5 — Regulatory Criteria](frank-van-dissel-uc5-regulatory-criteria.md) — consumes Context Brief from UC1
- [UC6 — IT Dependency Identifier](frank-van-dissel-uc6-it-dependency-identifier.md) — consumes Context Brief from UC1
- [UC7 — RCM Builder](frank-van-dissel-uc7-rcm-builder.md) — aggregates all Phase 1–2 outputs
- [UC8 — Work Program Agent](frank-van-dissel-uc8-audit-work-program.md) — end product of the pipeline
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates entire pipeline
- [Policy-to-Controls-Extractor](johannesiv-policy-to-controls-extractor.md) — closely related skill; align on schema

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie internal audit policy documents |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What is the optimal JSON schema for the Context Brief to ensure all downstream agents (UC2–UC9) can consume it without transformation?
2. How should the agent handle policy documents that define processes implicitly (narrative style) rather than with explicit numbered steps?
3. Should the Completeness Guard run automatically or only when triggered by the auditor?
4. How do we align this agent's output schema with the [Policy-to-Controls-Extractor](johannesiv-policy-to-controls-extractor.md) — which produces a similar but differently structured control register?
