# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Rohan Sobha |
| **Organisation** | Auditdienst Rijk |
| **Session** | Hackathon 4 (Session 5) |
| **Type** | Agent |
| **Status** | Finalised |
| **Claimed By** | Rohan Sobha |

---

## 2. Problem Statement

Policy-to-controls extractors (such as the upstream [johannesiv-policy-to-controls-extractor](plans/hackathon-2/johannesiv-policy-to-controls-extractor.md)) use LLMs to derive structured control objects from raw policy PDFs or DOCX documents. This creates a well-known reliability problem: the extractor can hallucinate controls that do not appear in the source document, silently merge or split clauses, or misattribute a control to the wrong section. Today an auditor who wants to rely on the extracted control set must manually re-read the entire policy document to verify each item — a process that can take hours for a 50-page document and that is itself error-prone under time pressure.

Without an automated validation step, extracted controls flow into audit workpapers with no grounding evidence, inflating the risk of issuing findings or sign-offs based on misread policy text.

This plan introduces a **judge-as-LLM** agent that acts as a second opinion: for every control produced by the extractor it re-reads the source policy text and returns a machine-readable verdict (`found: yes/no`), the page number, and the verbatim paragraph that supports the control. Auditors can then spot-check only the `found: no` items, reducing manual review effort while creating a documented audit trail of grounding evidence.

---

## 3. Use-Case Type and Scope

**Audit domain:** Policy Compliance / Control Validation

**Applicable standards:**

- ISO 27001:2022 — Annex A.5 (Organisational Controls) and A.18 (Compliance)
- DORA (EU 2022/2554) — Art. 9 ICT Risk Management Framework requirements
- NIS2 Directive (EU 2022/2555) — Art. 21 cybersecurity risk-management measures

**In scope:**

- Validating whether each control extracted by the upstream extractor is actually present (explicitly or by clear normative implication) in the source policy document
- Returning a structured verdict per control: found status, page number, and supporting verbatim paragraph
- Operating on the output JSON of `johannesiv-policy-to-controls-extractor` and the corresponding source PDF

**Out of scope:**

- Generating new controls that are present in the policy but were missed by the extractor (gap detection — a separate agent concern)
- Assessing the quality or completeness of controls against a standard
- Performing gap analysis between the policy and a regulatory framework
- Processing policy documents that have not first been through the upstream extractor

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New judge system prompt to be created at `prompts/audit-use-cases/judge-found-controls.md` |
| **Tools** | New Python script to be created at `tools/scripts/judge-found-controls/agent.py` |
| **Regulatory** | Reuses the control schema produced by `johannesiv-policy-to-controls-extractor` — no new regulatory file needed |
| **Outputs** | JSON array of verdict objects (control_id, found, page_no, paragraph); a downstream agent can convert `found: "no"` verdicts into findings conforming to `outputs/schemas/finding-schema.json` |

---

## 5. Prompts

### System prompt (draft)

```
You are a rigorous audit evidence examiner. Your sole task is to determine whether a
structured control object is actually grounded in a supplied policy document.

## Context you will receive

The user message will contain two parts, clearly delimited:

1. POLICY TEXT — the full text of the source policy document, with page boundaries marked
   as "--- PAGE <n> ---". Treat page numbers as authoritative.
2. CONTROL JSON — a single control object extracted from that policy by an automated tool.
   It has the following fields: id, who, what, why, when, where, how, source_anchor,
   open_questions.

## Your task

Read the POLICY TEXT carefully. Then decide whether the normative requirement described in
the CONTROL's `what` field is actually stated in, or clearly and unambiguously implied by,
a specific passage in the POLICY TEXT.

Apply the following decision rules:

FOUND = "yes" if and only if:
  - The policy contains explicit normative language (shall, must, is required to, will) that
    directly supports the control's `what` field, OR
  - The policy contains language that unambiguously implies the requirement with no
    reasonable alternative interpretation.

FOUND = "no" if:
  - The control's `what` describes a requirement not mentioned in the policy at all.
  - The policy mentions the topic but only in an informative, explanatory, or aspirational
    way (e.g. "it is recommended", "may", "should consider") — normative intent is absent.
  - The control combines two separate policy statements whose combination creates a new
    requirement not individually stated.
  - The source_anchor reference in the control JSON points to a section that does not
    contain the claimed language.

PARTIAL SUPPORT: There is no "partial" verdict. If the policy partially supports the
control but key normative elements are missing (e.g. the 24-hour deadline is absent from
the text), return `found: "no"` and use the `paragraph` field to quote the closest
matching passage so the auditor can see what is actually there.

## Output format — STRICT

Return ONLY a single valid JSON object. Do not include any prose, markdown, code fences,
or explanation outside the JSON object. The object must have exactly these three keys:

{
  "found": "yes" | "no",
  "page_no": <integer — the page number of the supporting paragraph, or 0 if not found>,
  "paragraph": "<verbatim quote from the policy text, or empty string if no relevant text exists>"
}

Rules for the `paragraph` field:
- Copy the text exactly as it appears in the source, including punctuation and
  capitalisation. Do not paraphrase.
- If `found` is "yes", this must be the passage that provides the normative grounding.
- If `found` is "no" but a related passage exists, include that passage here so the
  auditor can investigate.
- If `found` is "no" and there is no related passage at all, return an empty string "".
- Keep the quote to the single most relevant sentence or clause.

## What you must never do

- Never invent or paraphrase policy text.
- Never return found: "yes" because the control seems reasonable or standard practice —
  your judgment must be anchored exclusively in the supplied POLICY TEXT.
- Never return prose outside the JSON object.
- Never omit a key or add extra keys.
```

### Example user prompts

**Prompt 1 — control is clearly present:**
```
POLICY TEXT:
--- PAGE 1 ---
1. Introduction
This policy establishes the information security requirements for all employees and
contractors of Acme Corporation.

--- PAGE 4 ---
4.2 Access Management
Access rights of employees shall be removed immediately upon termination of employment,
contract, or agreement. The IT Security team is responsible for revoking all system
credentials within 24 hours of receiving a formal termination notification from Human
Resources.

CONTROL JSON:
{
  "id": "POL-ACCESS-001",
  "who": "System administrator",
  "what": "System administrators shall revoke user access within 24 hours of employment termination.",
  "why": "Reduces risk of unauthorized access by former employees",
  "when": "Within 24 hours of employment termination notification",
  "where": "All IT systems in scope",
  "how": "TBD",
  "source_anchor": "Section 4.2",
  "open_questions": []
}
```

Expected output:
```json
{
  "found": "yes",
  "page_no": 4,
  "paragraph": "The IT Security team is responsible for revoking all system credentials within 24 hours of receiving a formal termination notification from Human Resources."
}
```

**Prompt 2 — control over-specifies the policy (hallucinated deadline):**
```
POLICY TEXT:
--- PAGE 4 ---
4.2 Access Management
When an employee leaves the organisation, their access rights should be reviewed and
removed in a timely manner in accordance with the organisation's HR processes.

CONTROL JSON:
{
  "id": "POL-ACCESS-001",
  "who": "System administrator",
  "what": "System administrators shall revoke user access within 24 hours of employment termination.",
  "why": "Reduces risk of unauthorized access by former employees",
  "when": "Within 24 hours of employment termination notification",
  "where": "All IT systems in scope",
  "how": "TBD",
  "source_anchor": "Section 4.2",
  "open_questions": []
}
```

Expected output:
```json
{
  "found": "no",
  "page_no": 4,
  "paragraph": "When an employee leaves the organisation, their access rights should be reviewed and removed in a timely manner in accordance with the organisation's HR processes."
}
```

`found` is "no" because (a) "should" is not normative, and (b) the 24-hour deadline in the extracted control does not appear in the policy text. The closest passage is quoted so the auditor can assess whether the extractor over-specified.

**Intended file location:** `prompts/audit-use-cases/judge-found-controls.md`

---

## 6. Tools and Techniques

### Approach

The script loads two inputs: the extractor's JSON output file (an array of control objects) and the source policy PDF. It pages through the PDF using `pdfplumber`, assembling a single string where each page's text is preceded by a `--- PAGE <n> ---` marker. For each control it builds a user prompt containing the full paged policy text and the control JSON, then calls the Claude API using the judge system prompt. The returned JSON is parsed and a verdict object is assembled by merging the control's `id` with the three returned fields. After all controls are processed the full verdict array is written to `judge_verdicts.json`.

Errors (e.g. malformed model response) are recorded as `found: "error"` rather than crashing the run, so auditors can see exactly which controls were not evaluated.

### Example script or pseudocode

```python
"""
judge-found-controls/agent.py

Validates that each control in an extractor output JSON is grounded in
the source policy PDF. Writes judge_verdicts.json to the working directory.

Usage:
    python agent.py --controls controls.json --policy policy.pdf

Environment variables required:
    ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
import pdfplumber

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 512

SYSTEM_PROMPT_PATH = (
    Path(__file__).parents[3] / "prompts" / "audit-use-cases" / "judge-found-controls.md"
)


def load_system_prompt(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_controls(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "controls" in data:
        return data["controls"]
    raise ValueError(f"Unrecognised controls JSON structure in {path}")


def build_paged_policy_text(pdf_path: str) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(f"--- PAGE {i} ---\n{text}")
    return "\n\n".join(pages)


def judge_control(
    client: anthropic.Anthropic,
    system_prompt: str,
    policy_text: str,
    control: dict,
) -> dict:
    user_prompt = (
        f"POLICY TEXT:\n{policy_text}\n\n"
        f"CONTROL JSON:\n{json.dumps(control, indent=2, ensure_ascii=False)}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text.strip()
    verdict = json.loads(raw)
    missing = {"found", "page_no", "paragraph"} - verdict.keys()
    if missing:
        raise ValueError(f"Verdict missing keys: {missing}")
    return verdict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", required=True)
    parser.add_argument("--policy",   required=True)
    parser.add_argument("--output",   default="judge_verdicts.json")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Error: ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)
    controls = load_controls(args.controls)
    policy_text = build_paged_policy_text(args.policy)

    results = []
    for control in controls:
        control_id = control.get("id", "UNKNOWN")
        print(f"  Judging {control_id} ...", end=" ", flush=True)
        try:
            verdict = judge_control(client, system_prompt, policy_text, control)
            result = {"control_id": control_id, **verdict}
            print(f"found={verdict['found']}")
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"ERROR — {exc}")
            result = {
                "control_id": control_id,
                "found": "error",
                "page_no": 0,
                "paragraph": str(exc),
            }
        results.append(result)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    found   = sum(1 for r in results if r["found"] == "yes")
    missing = sum(1 for r in results if r["found"] == "no")
    errors  = sum(1 for r in results if r["found"] == "error")
    print(f"\nDone. {len(results)} controls judged: {found} found, {missing} not found, {errors} errors.")
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
```

**Tech stack used:** Python 3.9+, Claude API (`claude-sonnet-4-6`), `anthropic`, `pdfplumber`

**Intended file location:** `tools/scripts/judge-found-controls/agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISO 27001:2022 | A.5.1 — Policies for information security (policy text must be normative and traceable) |
| ISO 27001:2022 | A.18.1.1 — Identification of applicable legislation and contractual requirements |
| ISO 27001:2022 | A.18.2.2 — Compliance with security policies and standards |
| DORA Art. 9 | ICT risk management framework must be documented and verifiably implemented |
| NIS2 Art. 21 | Cybersecurity measures must be proportionate and documented |

### Claude / AI tool usage notes

No real audit evidence, personal data, or credentials will be sent to the Claude API during testing — a synthetic policy document and synthetic controls will be used. In production use, organisations must ensure appropriate DPA / data-sharing agreements with Anthropic before passing real policy documents. The model is called with `max_tokens=512` to prevent verbose responses; the script only reads files and writes `judge_verdicts.json`.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only (`ANTHROPIC_API_KEY`)

---

## 8. Output Format and Examples

**Format:** JSON array

**Schema reference:** Custom verdict schema (see below). Does not directly conform to `outputs/schemas/finding-schema.json` — a downstream agent can convert `found: "no"` verdicts into findings.

### Verdict schema

```json
[
  {
    "control_id": "string — matches the id field from the extractor output",
    "found":      "yes | no | error",
    "page_no":    0,
    "paragraph":  "string — verbatim quote or empty string"
  }
]
```

### Synthetic example output

```json
[
  {
    "control_id": "POL-ACCESS-001",
    "found": "yes",
    "page_no": 4,
    "paragraph": "The IT Security team is responsible for revoking all system credentials within 24 hours of receiving a formal termination notification from Human Resources."
  },
  {
    "control_id": "POL-ACCESS-002",
    "found": "no",
    "page_no": 4,
    "paragraph": "When an employee leaves the organisation, their access rights should be reviewed and removed in a timely manner in accordance with the organisation's HR processes."
  },
  {
    "control_id": "POL-CRYPTO-001",
    "found": "no",
    "page_no": 0,
    "paragraph": ""
  }
]
```

The three cases illustrate the meaningful outcomes: grounded control, over-specified control (closest passage quoted), and hallucinated control (topic absent entirely).

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (`claude-sonnet-4-6`)
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [x] `pdfplumber` — page-aware PDF text extraction

**Stretch goals:**

- [ ] DOCX input support via `python-docx`
- [ ] Confidence score: ask the model to return a 0–1 confidence and surface controls where confidence < 0.7 for mandatory human review
- [ ] Batch mode: group multiple controls per API call to reduce round-trips for large control sets
- [ ] HTML report: colour-coded table (green = found, red = not found) for auditor sign-off

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The judge system prompt (`prompts/audit-use-cases/judge-found-controls.md`)
- The Python script (`tools/scripts/judge-found-controls/agent.py`)
- A synthetic test fixture: 5-page dummy policy PDF and matching controls JSON with 3 found, 2 not found, and 1 hallucinated control

**What help I'm looking for:**

- Feedback from anyone who has run the upstream extractor on real policy documents — what are the most common hallucination patterns?
- Review of the normative-vs-informative decision rules in the system prompt from an ISO 27001 / DORA audit practitioner
- Input on whether `pdfplumber` handles scanned (OCR'd) PDFs reliably enough, or whether a fallback to `pytesseract` is needed

**Cross-org interest:**

Yes. Any organisation that uses the upstream policy-to-controls extractor benefits directly from this validation step. Interested in connecting with other SAAF participants building on top of the extractor — this could be generalised into a shared "extractor quality assurance" module in the SAAF repo.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Template filled in at Hackathon 4; system prompt and pseudocode finalised |
| **Do** | Complete | Python script implemented and tested against synthetic fixtures; see [judging-found-controls](https://github.com/SAAF-Project/judging-found-controls) |
| **Check** | Not started | Planned: run against a real government policy document (after DPA review) and measure precision/recall of `found` verdicts vs manual baseline |
| **Act** | Not started | Target: integrate as a post-processing step in the upstream extractor pipeline before Hackathon 5 |

---

## 12. Open Questions

1. **Multi-page paragraphs**: `pdfplumber` extracts text page by page, but normative clauses sometimes span two pages. Should the verdict report the page where the text starts, or the page where the normative verb appears?
2. **Partial-match scoring**: The current design is binary (found / not found). Should a `partial` verdict be introduced, or is returning `no` with the closest passage sufficient for auditors to make that call themselves?
3. **Extractor quality metric**: Given the full verdict array, what is the right aggregate metric — percentage of controls found, precision treating the policy as ground truth, or a weighted score that penalises hallucinated controls more heavily than over-specified ones?
4. **Scanned PDFs**: `pdfplumber` relies on embedded text layers. Should the script fail fast with a clear error for scanned PDFs, or silently fall back to an OCR library (`pytesseract`)?
5. **Token limits for large policies**: A 100-page policy at ~500 tokens/page × 80 controls = 4M input tokens per run. Should the policy text be pre-filtered to sections plausibly relevant to each control (using the `source_anchor` field), and if so, how do we avoid accidentally excluding the supporting paragraph?
