# Plan: LLM Finding Fact-Check Agent

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `frank-heldens-llm-finding-fact-check-agent.md` |
| **Submitter** | Frank Heldens |
| **Organization** | SAAF |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Skill |
| **Primary domain** | Evidence quality / AI risk management |
| **Source** | Hackathon session April 21, 2026 |

---

## 2. Problem Statement

AI-generated audit findings can contain hallucinations: plausible-sounding statements that are factually incorrect, unsupported by source documents, or internally inconsistent. When these findings are reported, they create audit quality failures that are difficult to detect after the fact.

**Concrete risks:**
1. Findings are reported for controls that were not in scope of the audit.
2. Findings are reported without supporting evidence or documentation in the audit file — the auditor must have substantively documented the finding in at least one work program; a mere reference is not sufficient.

The key distinction from generic hallucination detection is that this agent fact-checks findings against the **auditor's own work programs** — the primary source of truth for what was actually tested and observed during the engagement. If a finding appears in the audit report but cannot be substantively traced back to the work program documentation, it must be flagged regardless of whether the finding sounds plausible.

---

## 3. Use-Case Type & Scope

**Type:** Skill (reusable component callable as a post-processing step before audit report sign-off)

**Scope:**
- Read findings from the audit report (Word or PDF)
- Read all work programs for the same audit from a designated SharePoint folder (Word, PDF, Excel — mixed formats)
- Per finding: locate and assess substantive documentation in the work programs
- Score each finding using four gradations (see §5)
- Return an annotated finding with a fact-check verdict and an explanation of what is missing or unverified
- Block entry to the final report if verdict = HALLUCINATED; warn auditor if LIKELY_HALLUCINATED or UNVERIFIED

**Out of scope:**
- Cross-checking findings against external regulatory sources (see `llm-hallucination-detection-agent.md` for that)
- Re-generating missing work program content
- Replacing auditor judgment — the agent flags, humans decide

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | Finding extraction prompt; work program content extraction prompt; per-finding verification prompt; risk aggregation prompt |
| **Tools** | Claude API (extraction and verification), SharePoint (source documents via Graph API or local sync), `finding-schema.json` (output format) |
| **Regulatory** | IIA Standard 2310 (sufficient, reliable, relevant, useful information), IIA Standard 2330 (documenting information — auditors must document sufficient information to support findings and conclusions), EU AI Act Art. 13 (transparency of high-risk AI outputs) |
| **Outputs** | Annotated finding JSON with `fact_check` field per finding; JSONL audit log per validation run |

---

## 5. Verdict Gradations

Each finding is assigned one of four verdicts:

| Verdict | Meaning |
|---|---|
| **SUPPORTED** | The finding is clearly and substantively documented in one or more work programs. The auditor has recorded observations, test results, or evidence that directly supports the finding as stated in the report. |
| **LIKELY_HALLUCINATED** | The finding topic or control appears in the work programs, but the documentation is too thin or vague to substantiate the finding as reported. The auditor recorded something, but not enough to justify the specific claim. |
| **HALLUCINATED** | The finding as stated in the audit report cannot be traced back to any work program. No substantive documentation of this control, observation, or conclusion was found. |
| **UNVERIFIED** | The relevant work program content could not be read, parsed, or matched with sufficient confidence (e.g., document format issue, ambiguous scope boundary, or the work program structure does not allow a clear determination). |

---

## 6. Prompts

### Prompt 1 — Finding Extraction from Audit Report
```
System: You are an audit document parser. Your task is to extract all audit findings from an audit report.

A "finding" is any reported observation, conclusion, or recommendation that identifies a control deficiency, gap, or risk. Findings are typically structured with a title, observation, risk rating, and recommendation.

User: Extract all findings from the following audit report content. For each finding, output a JSON object with:
- "id": sequential identifier (F-001, F-002, ...)
- "title": the finding title as stated
- "control_reference": any control ID, domain, or process area mentioned (null if absent)
- "observation": the core observation text
- "risk_rating": as stated (High / Medium / Low / null)
- "recommendation": the recommendation text

Audit report content:
[AUDIT_REPORT_TEXT]
```

### Prompt 2 — Work Program Content Extraction
```
System: You are an audit work program parser. Your task is to extract the substantive audit observations, test results, and evidence descriptions from a work program document.

Focus on content that records what the auditor actually did and found — not just procedure headers or control descriptions. Ignore blank fields and template boilerplate.

User: Extract all substantive audit documentation from the following work program content. For each documented item, output a JSON object with:
- "control_reference": control ID, name, or domain this item relates to (infer from context if not explicit)
- "observation": what the auditor observed or found
- "evidence_description": what evidence was reviewed (document name, system, interview, etc.)
- "conclusion": pass / fail / finding / not tested / other (as stated or inferred)
- "source_file": [FILENAME]

Work program content:
[WORK_PROGRAM_TEXT]
```

### Prompt 3 — Per-Finding Verification
```
System: You are an audit quality control reviewer. Your task is to determine whether an audit finding reported in the audit report is substantively supported by the auditor's work program documentation.

Substantive support means the auditor has recorded observations, test steps, evidence reviewed, or conclusions that directly correspond to the finding as reported. A mere mention of the control name is not sufficient.

Apply the following verdict definitions:
- SUPPORTED: the finding is clearly traceable to substantive work program documentation
- LIKELY_HALLUCINATED: the control or topic appears in the work programs but documentation is too thin or vague to justify the finding as reported
- HALLUCINATED: no substantive documentation of this finding can be found in any work program
- UNVERIFIED: the work program content could not be matched with sufficient confidence due to format, scope ambiguity, or document structure

User: Assess whether the following audit finding is supported by the provided work program content.

Finding:
Title: [FINDING_TITLE]
Control reference: [CONTROL_REFERENCE]
Observation: [FINDING_OBSERVATION]

Relevant work program content:
[WORK_PROGRAM_EXCERPTS]

Respond with a JSON object:
{
  "verdict": "SUPPORTED | LIKELY_HALLUCINATED | HALLUCINATED | UNVERIFIED",
  "confidence": "High | Medium | Low",
  "supporting_excerpt": "the specific work program text that supports this verdict (null if HALLUCINATED)",
  "missing": "what is absent or insufficient — be specific (null if SUPPORTED)",
  "source_file": "filename(s) where supporting content was found (null if HALLUCINATED)"
}
```

### Prompt 4 — Aggregation & Report Summary
```
System: You are an audit quality gate. Based on individual finding verification results, determine the overall fact-check status of the audit report.

Rules:
- If ANY finding is HALLUCINATED → overall_status = BLOCKED (report must not be signed off)
- If ANY finding is LIKELY_HALLUCINATED or UNVERIFIED → overall_status = WARNING (auditor review required)
- If all findings are SUPPORTED → overall_status = CLEAR

User: Aggregate the following finding verification results into an overall fact-check assessment.

[FINDING_RESULTS_JSON]

Output a JSON object:
{
  "overall_status": "BLOCKED | WARNING | CLEAR",
  "total_findings": <number>,
  "supported": <number>,
  "likely_hallucinated": <number>,
  "hallucinated": <number>,
  "unverified": <number>,
  "summary": "two sentences for the engagement manager summarising what was found",
  "blocked_findings": [list of finding IDs with verdict HALLUCINATED],
  "warning_findings": [list of finding IDs with verdict LIKELY_HALLUCINATED or UNVERIFIED]
}
```

---

## 7. Tools & Techniques

| Tool | Role |
|---|---|
| Claude API (Sonnet) | Finding extraction, work program parsing, per-finding verification |
| SharePoint (Graph API or local sync folder) | Source location for audit report and work programs |
| `outputs/schemas/finding-schema.json` | Output format for annotated findings |
| Python `pathlib` + `json` | File handling and output writing |
| `python-docx`, `pdfplumber`, `openpyxl` | Parsing Word, PDF, and Excel work programs |
| JSONL logger | Audit trail of all fact-check runs |

**Key pattern — document-first extraction:**
1. Parse all work programs into a structured in-memory index (control → observations)
2. Extract findings from the audit report
3. For each finding, retrieve relevant work program excerpts by control reference or semantic similarity
4. Run the verification prompt per finding against those excerpts

This avoids asking the model to reason over raw, full-length documents and keeps each verification prompt focused.

---

## 8. Regulatory Framework

| Standard | Requirement |
|---|---|
| **IIA Standard 2310** | Auditors must identify sufficient, reliable, relevant, and useful information to support engagement conclusions |
| **IIA Standard 2330** | Auditors must document sufficient information to support the engagement results and conclusions |
| **IIA Standard 2400** | Audit communications must be accurate and supported — reported findings must reflect what was actually observed |
| **EU AI Act Article 13** | Transparency obligation: high-risk AI outputs must be interpretable and traceable to their basis |

**Audit trail requirement:** Every fact-check run must be logged (audit report name, work program files read, findings checked, per-finding verdict, timestamp, model used). This log is retained as part of the audit dossier.

---

## 9. Output Format

### Annotated Finding (JSON)
```json
{
  "id": "F-003",
  "title": "Privileged access reviews not performed quarterly",
  "control_reference": "AC-5",
  "observation": "The organisation did not perform quarterly privileged access reviews as required by policy.",
  "risk_rating": "High",
  "recommendation": "Implement a quarterly access review process with documented sign-off.",
  "fact_check": {
    "run_at": "2026-04-21T15:10:00Z",
    "model": "claude-sonnet-4-6",
    "verdict": "LIKELY_HALLUCINATED",
    "confidence": "Medium",
    "supporting_excerpt": "Work program notes mention 'access reviews discussed with IT manager' but no test results or evidence of review execution are recorded.",
    "missing": "No evidence of actual access review testing was found. The work program lacks documentation of the review population, sample tested, and results.",
    "source_file": "WP-Access-Control.docx"
  }
}
```

### Validation Log (JSONL)
One line per run appended to `outputs/logs/fact-checks.jsonl`:
```json
{"timestamp": "2026-04-21T15:10:00Z", "audit_report": "AuditReport-Q1-2026.docx", "work_programs_read": 5, "findings_checked": 8, "supported": 5, "likely_hallucinated": 2, "hallucinated": 0, "unverified": 1, "overall_status": "WARNING"}
```

---

## 10. Tech Stack

```
Language:     Python 3.9+
Dependencies: anthropic (Claude API), python-docx, pdfplumber, openpyxl
Config:       ANTHROPIC_API_KEY from environment; SHAREPOINT_FOLDER path
Input:        SharePoint folder containing audit report + work programs (Word/PDF/Excel)
Output:       Annotated finding JSON per finding + JSONL log
```

---

## 11. Collaboration & Cross-References

**Dependencies (this skill consumes):**
- SharePoint folder (audit report + work programs — path configured per engagement)
- `outputs/schemas/finding-schema.json` — output format

**Related plans:**
- `llm-hallucination-detection-agent.md` — complementary: that plan checks findings against external regulatory sources; this plan checks findings against the auditor's own work programs. Both can run in sequence.
- `saaf-rag-knowledge-base.md` — could supplement work program search with semantic retrieval if work programs are ingested into the shared RAG index
- `document-evidence-extraction-agent.md` — upstream: extracts structured content from documents, which could feed the work program parsing step

---

## 12. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | Not started | Build `tools/scripts/finding_fact_check.py` |
| **Check** | Not started | Validate against synthetic audit report + work programs from Hackathon #2 submissions |
| **Act** | Not started | Tune verdict thresholds and missing-evidence descriptions based on false-positive rate |

---

## 13. Open Questions

1. **SharePoint access**: Should the agent use the Microsoft Graph API to read files directly from SharePoint, or work against a locally synced folder? Graph API is more robust for production; local sync is simpler for the hackathon prototype.
2. **Semantic matching**: When a finding has no explicit control reference, how should the agent locate relevant work program sections? Options: keyword search, embedding-based retrieval, or asking the model to reason over all work program content (expensive).
3. **Work program structure variance**: Work programs differ in structure across engagements. Should the extraction prompt be tuned per template, or kept generic?
4. **Threshold for LIKELY_HALLUCINATED vs SUPPORTED**: How much auditor documentation is "enough"? This is a professional judgment call — consider letting the engagement manager configure a strictness level (strict / standard / lenient).
5. **Combination with `llm-hallucination-detection-agent.md`**: Should both fact-check agents run in a single pipeline, or remain independently callable skills?
