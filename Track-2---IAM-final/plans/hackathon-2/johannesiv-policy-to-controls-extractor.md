# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of JohannesIV) |
| **Organisation** | Kouters Van Der Meer |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Policy documents contain dozens of normative requirements buried in dense prose. Identifying, extracting, and translating these into testable audit controls is a manual, time-consuming task that is done inconsistently across engagements and organizations. The Policy-to-Controls Extractor automates this: it reads a PDF or DOCX policy document, detects every normative statement (using modal verbs in Dutch and English), and produces structured, testable controls with full traceability back to the source text. Each control is expressed in a consistent "shall" form with the 6 W's (Who, What, Why, When, Where, How) and an open-questions list where the policy is ambiguous.

---

## 3. Use-Case Type and Scope

**Audit domain:** Policy Compliance / Control Framework Design

**Applicable standards:**

- ISO 27001 (A.5 — Information security policies; A.18 — Compliance)
- Any framework whose controls are expressed in a policy document (NIS2, DORA, BIO2, internal policies)

**In scope:**

- Ingesting PDF and DOCX policy documents
- Detecting normative statements (must, shall, only, required, prohibited — Dutch and English)
- Generating structured controls with 6W's (Who/What/Why/When/Where/How), source anchor, and open questions
- Deduplication and clustering of overlapping controls
- Quality gate (critic check) flagging vague terms and untestable controls
- Output to JSON and XLSX

**Out of scope:**

- Automated testing of controls against evidence
- Gap analysis against existing control frameworks (ISMS, SOC 2 etc.)
- Continuous re-processing as policies change

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | 6-step extraction system prompt (in `prompts.py` of the [Policy-to-Controls-Extractor repo](https://github.com/SAAF-Project/Policy-to-Controls-Extractor)); reusable in `prompts/audit-use-cases/policy-to-controls.md` |
| **Tools** | Python agent in the repo: `agent.py` (pipeline orchestration), `models.py` (Control + ExtractionResult), `prompts.py` (system prompt) |
| **Regulatory** | Applicable to any policy-based framework; reuse `regulatory/control-mappings/` for cross-referencing extracted controls |
| **Outputs** | JSON + XLSX control register with fields: control ID, Who, What, Why, When, Where, How, source_anchor, open_questions |

---

## 5. Prompts

### System prompt (draft)

```
You are the Policy-to-Controls Extractor. You analyse policy documents and derive
concrete, testable controls from them.

Extraction pipeline:
1. Segment — process paragraph by paragraph; detect modal verbs
   (must/shall/only/required/prohibited/unless — Dutch and English)
2. Identify normative statements — filter sentences with an obligation, prohibition,
   or condition. Skip informative or descriptive sentences.
3. Generate control candidates — rewrite into testable "shall" form:
   actor + action + object + constraint
4. Fill the 6 W's — Who, What, Why, When, Where, How.
   Use "TBD" + open question where the policy does not specify.
5. Deduplicate and cluster — merge controls with the same intent;
   split if one sentence contains distinct requirements.
6. Quality gate (critic check) — flag controls with vague terms
   (adequate, timely, appropriate) unless the policy makes them measurable.
   Mark every control with at least one source_anchor.

Control ID format: POL-{DOMAIN}-{NNN}
Never invent information not present in the source document.
```

### Example user prompts

**Prompt 1:**
```
Domain: ACCESS (Access Management)
Policy document: [contents of access-management-policy.pdf]
Extract all testable controls. Return a JSON array conforming to the Control schema.
```

**Prompt 2:**
```
Domain: CHANGE (Change Management)
Policy document: [contents of change-management-policy.docx]
Extract controls. Flag any vague terms with an open question.
```

**Intended file location:** `prompts/audit-use-cases/policy-to-controls.md`

---

## 6. Tools and Techniques

### Approach

The agent reads a directory of PDF/DOCX files (`todo_dir`), extracts text using `pdfplumber` and `python-docx`, sends the content to Claude with the 6-step extraction prompt, parses the returned JSON into typed `Control` objects, and writes the results to both JSON and XLSX.

Configuration is via `P2C.conf` (INI format): paths, domain, scope, API key, model.

### Example script or pseudocode

```python
# python agent.py  (reads P2C.conf for paths and settings)
from pathlib import Path
import anthropic, pdfplumber
from models import Control, ExtractionResult
from prompts import SYSTEM_PROMPT

client = anthropic.Anthropic()

for doc_path in Path(config["paths"]["todo_dir"]).iterdir():
    text = extract_text(doc_path)   # pdfplumber or python-docx
    response = client.messages.create(
        model=config["claude"]["model"],   # claude-opus-4-6
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Domain: {domain}\n\n{text}"}]
    )
    controls = parse_controls(response.content[0].text)
    write_json_and_xlsx(controls, output_dir)
```

**Tech stack used:** Python 3.9+, Claude API (claude-opus-4-6), `pdfplumber`, `python-docx`, `openpyxl`

**Intended file location:** `tools/scripts/policy-to-controls/` (reference [Policy-to-Controls-Extractor repo](https://github.com/SAAF-Project/Policy-to-Controls-Extractor))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISO 27001 | A.5.1 — Policies for information security; A.18.1 — Compliance |
| DORA | Any article whose requirements can be encoded as testable controls |
| NIS2 / CBW | Security measure requirements (Art. 21) expressible as controls |

### Claude / AI tool usage notes

Policy documents processed should not contain real personal data. If internal policies reference personal data (e.g. HR policies), anonymize before processing. Model is configurable via `P2C.conf` — defaults to `claude-opus-4-6`.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON + XLSX

**Schema reference:** Control ID follows `POL-{DOMAIN}-{NNN}` pattern. `risk_rating` field can be derived from the quality gate and maps to `outputs/schemas/finding-schema.json` for controls flagged as gaps.

### Synthetic example output

```json
{
  "id": "POL-ACCESS-001",
  "who": "System administrator",
  "what": "System administrators shall revoke user access within 24 hours of employment termination.",
  "why": "Reduces risk of unauthorized access by former employees",
  "when": "Within 24 hours of employment termination notification",
  "where": "All IT systems in scope",
  "how": "TBD — policy does not specify the revocation procedure",
  "source_anchor": "Section 4.2: 'Access rights of employees shall be removed immediately upon termination'",
  "open_questions": [
    "What does 'immediately' mean precisely — is 24 hours the agreed threshold?",
    "Which system is authoritative for employment termination notification?"
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6)
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional)

**Stretch goals:**

- [ ] Web UI for document upload and control review
- [ ] Gap analysis: cross-reference extracted controls against an existing control framework
- [ ] Diff mode: re-extract only changed paragraphs when a policy is updated

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The 6-step extraction system prompt (`prompts.py`) — directly reusable by any organization
- Full Python agent (`agent.py`, `models.py`, `prompts.py`)
- Control output schema (JSON + XLSX)

**What help I'm looking for:**

- Test with policy documents in languages other than Dutch and English
- Review of the 6W quality gate rules by experienced auditors
- Extension: domain-specific modal verb lists (e.g. sector-specific regulatory language)

**Cross-org interest:**

Every organization that audits against policy has the same problem: translating dense policy prose into testable controls. This skill is applicable to any audit domain and any framework whose requirements appear in a policy document. Strong candidate for shared adoption across the SAAF community.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Working prototype built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned: test against real internal policy documents |
| **Act** | Not started | Target: Hackathon 3 — share learnings and extend quality gate rules |

---

## 12. Open Questions

1. How should the agent handle policies that mix normative and informative text in the same paragraph — sentence-level or clause-level segmentation?
2. Should controls extracted from different sections of the same policy be clustered by topic, or kept in document order for traceability?
3. Is there interest in a shared library of domain-specific modal verb patterns (Dutch/English + sector-specific regulatory language) maintained by the SAAF community?
