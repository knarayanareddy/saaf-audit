# Document Evidence Extraction Agent

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Auditors spend hours manually extracting relevant clauses, dates, and control statements from policy PDFs, system configuration screenshots, and compliance documents. These documents are often scanned (not machine-readable), have complex multi-column layouts, or contain embedded tables that basic PDF parsers mangle.

The result: evidence extraction is a bottleneck in every audit fieldwork phase. Important information is missed or mis-transcribed. Linking evidence to specific control criteria requires additional manual effort.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Evidence Collection / Document Analysis

**Applicable standards:**

- IIA IPPF — Standard 2310 (Identifying Information)
- ISO 27001 — A.5.31 (Legal, statutory, regulatory and contractual requirements)
- DORA — Art. 11 (ICT business continuity management)

**In scope:**

- OCR + layout understanding for scanned policy PDFs, configuration exports, and compliance documents
- Extraction of structured fields: policy name, version, effective date, owner, control statements, exceptions
- Mapping extracted controls to audit criteria (e.g., ISO 27001 clauses, DORA articles)
- Output as structured JSON finding inputs, compatible with `finding-schema.json`

**Out of scope:**

- Audio/video transcription (covered by Whisper-based plans)
- Real-time document ingestion from DMS systems (future: MCP integration)
- Extraction from encrypted or password-protected documents

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Document extraction system prompt; control-mapping prompt |
| **Tools** | `tools/scripts/extract-evidence.py` — OCR + Claude Vision extraction pipeline |
| **Regulatory** | IIA 2310 (identifying information) — extraction agent produces structured, citable evidence |
| **Outputs** | Structured JSON per document: extracted fields + control mappings + finding seed |

---

## 5. Prompts

### System prompt (draft)

```
You are an audit document extraction specialist.
Given a document image or PDF page, extract all audit-relevant information.
For each extracted item, provide:
1. The exact quoted text from the document
2. The page number and section where it appears
3. The control criterion it relates to (if identifiable)
4. A confidence score (High / Medium / Low) for each extraction

Extract: policy name, version number, effective date, responsible owner,
control statements, exceptions, approval signatures, and review dates.
Do not paraphrase — always quote directly. Flag any sections that are
illegible or ambiguous.
```

### Example user prompts

**Prompt 1 — Policy extraction:**
```
Extract all control statements and their owners from the attached Information Security Policy (pages 3-8).
Map each statement to the relevant ISO 27001 A-control.
Format output as JSON with fields: control_id, iso_ref, statement, owner, page.
```

**Prompt 2 — Configuration screenshot:**
```
This is a screenshot of a firewall rule configuration export.
Extract all rules that allow inbound traffic on port 22 (SSH) or port 3389 (RDP).
For each rule: source IP range, destination, protocol, port, action, rule name.
Flag any rules with source = "0.0.0.0/0" (open to internet).
```

**Intended file location:** `prompts/audit-use-cases/document-evidence-extraction.md`

---

## 6. Tools and Techniques

### Approach

The agent uses Claude's vision capability (base64-encoded page images) to extract structured information from documents. For scanned PDFs, each page is rendered to PNG (via `pdf2image`). For digital PDFs, `pdfplumber` extracts text and table structures first; Claude handles remaining layout complexity.

The extraction pipeline:
1. Convert document to page images (if scanned) or extract text+tables (if digital)
2. Send each page to Claude with the extraction system prompt
3. Merge per-page extractions into a unified structured document
4. Map extracted control statements to the relevant framework using a reference lookup
5. Generate finding seeds for any gaps detected between stated controls and framework requirements

### Example script or pseudocode

```python
import anthropic
import base64
from pathlib import Path
from pdf2image import convert_from_path
import json

client = anthropic.Anthropic()

def extract_document(pdf_path: Path, framework: str = "ISO27001") -> dict:
    pages = convert_from_path(pdf_path, dpi=200)
    extractions = []

    for i, page_img in enumerate(pages):
        # Encode page as base64 PNG
        import io
        buf = io.BytesIO()
        page_img.save(buf, format="PNG")
        img_b64 = base64.standard_b64encode(buf.getvalue()).decode()

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
                    },
                    {
                        "type": "text",
                        "text": f"Extract all audit-relevant information from page {i+1}. "
                                f"Map to {framework} controls where applicable. "
                                "Return JSON with fields: extractions[], gaps[], page."
                    }
                ]
            }]
        )
        extractions.append(json.loads(response.content[0].text))

    return merge_extractions(extractions)

def merge_extractions(pages: list[dict]) -> dict:
    merged = {"policy_metadata": {}, "controls": [], "gaps": []}
    for page in pages:
        merged["controls"].extend(page.get("extractions", []))
        merged["gaps"].extend(page.get("gaps", []))
    return merged
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6 with vision), pdf2image, pdfplumber, base64

**Intended file location:** `tools/scripts/extract-evidence.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2310 | Identifying information — extraction agent produces quoted, page-cited evidence |
| ISO 27001 A.5.31 | Legal requirements — agent maps extracted controls to regulatory obligations |
| DORA Art. 11 | Business continuity — agent can extract BCP/DR coverage from policy documents |

### Claude / AI tool usage notes

Document images are sent to the Claude API. Use synthetic or anonymized documents only during testing. For production use with real policy documents: confirm with legal/compliance whether the document's sensitivity classification allows cloud API processing. Consider running Claude locally via Ollama for confidential documents.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (extracted document structure) + Markdown (human-readable summary)

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "document": "Information Security Policy v2.3",
  "effective_date": "2025-01-01",
  "owner": "CISO — J. de Vries",
  "controls": [
    {
      "control_id": "ISP-AC-01",
      "statement": "All user accounts must be reviewed quarterly by the account owner.",
      "iso_ref": "ISO 27001 A.9.2.5",
      "page": 4,
      "confidence": "High"
    },
    {
      "control_id": "ISP-AC-02",
      "statement": "Privileged accounts require dual approval for provisioning.",
      "iso_ref": "ISO 27001 A.9.2.3",
      "page": 4,
      "confidence": "High"
    }
  ],
  "gaps": [
    {
      "iso_ref": "ISO 27001 A.9.2.6",
      "description": "No control found for removal of access rights on termination",
      "risk": "High"
    }
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6 with vision)
- [x] Python 3.9+
- [x] pdf2image (scanned PDF → PNG)
- [x] pdfplumber (digital PDF text/table extraction)
- [x] Strapi (synthetic policy documents for testing)

**Stretch goals:**

- [ ] Local vision model (LLaVA via Ollama) for confidential document processing
- [ ] Batch processing: extract an entire evidence folder overnight
- [ ] Auto-link extracted evidence to Jira/Confluence via MCP

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `extract-evidence.py` extraction script
- Extraction system prompt
- Synthetic test policy PDFs (3 domains: access management, change management, BCP)

**Help requested:**

- Auditors: provide synthetic policy documents with known control gaps for quality testing
- Vaktechniek: validate that quoted extractions meet IIA evidence standards
- Engineers: extend to handle Word (.docx) and Excel (.xlsx) documents

**Cross-org interest:**

Every audit team processes policy documents. A shared extraction pipeline reduces per-team effort and enables benchmarking of extraction quality across organizations.

**XAI Evidence Types for Audit Dossiers (April 2026):**

Explainable AI (XAI) outputs are a new category of audit evidence that this extraction agent should handle. As AI systems are increasingly deployed in audited processes (credit scoring, transaction monitoring, risk classification), auditors need to extract and interpret XAI outputs from AI system documentation:

- **SHAP (SHapley Additive exPlanations)**: output is a table of feature contributions to a model's decision. The extraction agent should recognize SHAP waterfall charts (as images) and SHAP summary tables (as structured data) and extract: model name, decision, top 5 contributing features with direction and magnitude.
- **LIME (Local Interpretable Model-agnostic Explanations)**: output is a local approximation showing which features drove a specific prediction. Extraction: model, instance ID, predicted class, confidence, top features.
- **Attention maps / saliency maps**: visual XAI outputs showing which parts of an input (text, image) the model attended to. Extraction: model type, input type, highlighted regions (described in text).

These XAI outputs are relevant to:
- Auditing AI-assisted underwriting or credit decisions (DORA Art. 10, EU AI Act Annex III item 5)
- Evidence for AI audit explainability findings (see [`ai-audit-explainability-framework.md`](ai-audit-explainability-framework.md))
- Bias and fairness assessments under OWASP AT-11

**Recommended implementation**: add a `--evidence-type xai` flag to `extract-evidence.py` that activates XAI-specific extraction prompts and output schema fields (`feature_contributions`, `confidence_score`, `xai_method`).

**Related SAAF plans:**

- [`saaf-jira-confluence-mcp.md`](saaf-jira-confluence-mcp.md) — source of policy documents via Confluence
- [`saaf-rag-knowledge-base.md`](saaf-rag-knowledge-base.md) — extracted controls can be indexed in the RAG KB
- [`johannesiv-policy-to-controls-extractor.md`](../hackathon-2/johannesiv-policy-to-controls-extractor.md) — related plan (text-based)
- [`ai-audit-explainability-framework.md`](ai-audit-explainability-framework.md) — XAI outputs extracted by this agent feed into the explainability annex

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Pipeline designed; extraction schema defined |
| **Do** | In progress | Hackathon #3: extract from 3 synthetic policy PDFs, validate output |
| **Check** | Not started | Target: compare extraction output against manual extraction by auditor |
| **Act** | Not started | Target: production integration with Confluence policy library |

---

## 12. Open Questions

1. For scanned documents with poor OCR quality, should we fall back to Whisper-style audio description, or accept lower extraction confidence?
2. How do we handle multi-language policy documents (Dutch + English)? Translate first or extract in source language?
3. What is the confidence threshold below which an extraction should be flagged for manual review?
4. Should extracted evidence be auto-linked to the audit dossier, or always reviewed by the auditor before linking?
