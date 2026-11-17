# Compliance Q&A Portal — Track 2

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Edwin |
| **Organisation** | SAAF |
| **Session** | Hackathon 4 (Session 5) |
| **Type** | Agent |
| **Status** | Draft |
| **Claimed By** | Edwin |

---

## 2. Problem Statement

Auditors spend hours reading long policy documents to answer a single compliance question ("Is MFA enforced for all users?", "Are privileged accounts reviewed quarterly?"). The document is often scanned, has complex multi-column layouts, and contains tables and exceptions that are easy to miss. The result: every compliance question requires manual close-reading, quoting, and judgement — and the audit trail of *why* a question was judged compliant or not often lives only in the auditor's head.

This plan builds on the Hackathon 3 concept [`document-evidence-extraction-agent.md`](../hackathon-3/document-evidence-extraction-agent.md) and proposes a concrete, demo-ready **Compliance Q&A portal**: upload one PDF, ask one question, receive a structured verdict with evidence and a confidence score, then add your auditor judgement on top. Vertical-slice complete in one hackathon day, extensible to multi-document and multi-question batch workflows afterwards.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Compliance Q&A on Policy Documents

**Applicable standards:**

- IIA IPPF — Standard 2310 (Identifying Information)
- ISO 27001 — A.5.31 (Legal, statutory, regulatory and contractual requirements), A.9.2 (User access management)
- DORA — Art. 11 (ICT business continuity management)

**In scope (MVP, day 1 — one PDF, one question):**

- Upload **one PDF** policy document (digital or scanned)
- Auditor types **one compliance question** in a free-text prompt
- Agent reads the document through the lens of that question and returns:
  - **Status**: `Voldaan` / `Niet voldaan` / `Niet van toepassing` / `Geen antwoord`
  - **Confidence score** (0–100 or High/Medium/Low)
  - **Evidence**: verbatim quotes with page numbers (may be zero if `Geen antwoord`)
  - **AI reasoning**: short explanation of how the status follows from the evidence
- Auditor adds a **free-text judgement** on top of the AI output (their professional opinion)
- Dashboard view showing all of the above side-by-side with the source PDF

**Out of scope (for this hackathon):**

- Multiple questions or multiple documents in one run (stretch: batch mode)
- CLI output parsing, access-review Excel, M365 configuration exports
- Audio/video transcription
- Real-time DMS ingestion
- Encrypted / password-protected documents
- Production use with real client data — MVP uses synthetic PDFs only

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What will be produced or reused |
|---|---|
| **Prompts** | New compliance-Q&A system prompt with prompt-caching; user-prompt template wrapping the auditor's question + document text (intended location: `prompts/audit-use-cases/compliance-qa/`) |
| **Tools** | `tools/scripts/compliance_qa.py` — PDF-in, verdict-out pipeline. Reuses pipeline pattern from `GDPR-AI-Audit-Agent`. Streamlit portal as UI layer |
| **Regulatory** | Optional ISO 27001 / DORA framework hints in the prompt so the model can cite the right control when evidence is found |
| **Outputs** | JSON verdict conforming to a new `compliance-qa-schema.json` (question, status, confidence, evidence[], ai_reasoning, auditor_judgement) + finding-seed via `to_findings()` adapter |

---

## 5. Prompts

### System prompt (draft — cached)

```
You are a compliance audit assistant. An auditor will give you:
1. The full text of a policy document (with page markers)
2. ONE compliance question about that document

Your job: answer the question using ONLY evidence from the document. Never
use outside knowledge. Never paraphrase — always quote source text exactly.
Never extract or output any PII (GDPR).

Return strictly valid JSON with the following fields:

{
  "status": "Voldaan" | "Niet voldaan" | "Niet van toepassing" | "Geen antwoord",
  "confidence": integer 0–100,
  "evidence": [
    {"exact_quote": "...", "page": 3, "section": "4.2 Access Management"}
  ],
  "ai_reasoning": "One paragraph explaining how the evidence supports the status."
}

Status decision rules:
- "Voldaan"             — document explicitly states the control/requirement is met
- "Niet voldaan"        — document explicitly states it is NOT met, or the absence
                          of the control is explicitly acknowledged
- "Niet van toepassing" — the question does not apply to the scope of this document
- "Geen antwoord"       — the document does not contain enough information to decide

Confidence rules:
- 90–100 = multiple explicit, unambiguous quotes
- 70–89  = one explicit quote, or several implicit statements pointing the same way
- 40–69  = indirect evidence requiring interpretation
- 0–39   = weak or conflicting evidence; prefer "Geen antwoord" below ~40

If evidence is zero, return evidence: [] and status "Geen antwoord" or
"Niet van toepassing" as appropriate.
```

### Example user prompts

**Prompt 1 — Access control question:**
```
<document>
{full_pdf_text_with_page_markers}
</document>

Question: Wordt multi-factor authenticatie afgedwongen voor alle gebruikers
met toegang tot kritische systemen?

Return JSON matching the compliance-qa schema.
```

**Prompt 2 — Business-continuity question (likely "Geen antwoord"):**
```
<document>
{full_pdf_text_with_page_markers}
</document>

Question: Hoe vaak wordt het business continuity plan getest?

Return JSON matching the compliance-qa schema.
```

**Intended file location:** `prompts/audit-use-cases/compliance-qa/system-prompt.md`

---

## 6. Tools and Techniques

### Approach

Simple four-component portal:

```
┌──────────────────────────────────────────────────────────┐
│  UI (Streamlit portal)                                    │
│   • PDF upload                                            │
│   • Question text box ("What would you like to check?")   │
│   • Verdict dashboard (status / confidence / evidence     │
│     quotes with pages / AI reasoning / auditor note)      │
├──────────────────────────────────────────────────────────┤
│  Orchestrator   compliance_qa.py                          │
│   1. Ingest PDF → text with page markers                  │
│   2. Ask Claude (system prompt + question + document)     │
│   3. Validate JSON against Pydantic schema                │
│   4. Return verdict to UI; append to audit log            │
├──────────────────────────────────────────────────────────┤
│  LLM             Claude Sonnet 4.5 + prompt caching       │
│                  (system prompt cached across questions)  │
├──────────────────────────────────────────────────────────┤
│  Storage         JSONL audit log per session              │
│                  Uploaded PDFs in `.gitignore`d tmpdir    │
└──────────────────────────────────────────────────────────┘
```

Pipeline steps:

1. **Ingest** — digital PDF → `pdfplumber` extracts text, preserves page numbers; scanned PDF → `pdf2image` + Claude Vision (one call, whole document, with page markers embedded)
2. **Ask** — the system prompt (cached) + user prompt wrapping the document text and the auditor's question are sent to Claude Sonnet 4.5
3. **Validate** — response parsed into `ComplianceVerdict` Pydantic model; on parse failure, one automatic retry with a stricter reminder
4. **Render** — verdict shown in a dashboard card with colour-coded status and clickable evidence quotes
5. **Auditor note** — auditor writes their own judgement in a free text area; on "Save" the full record (AI + auditor) is appended to the audit log
6. **Export** — optional "Download as JSON" / "Download as finding" buttons for the current verdict

### Example script or pseudocode

```python
# tools/scripts/compliance_qa.py
from pathlib import Path
from pydantic import BaseModel, Field
from anthropic import Anthropic
import pdfplumber

class EvidenceQuote(BaseModel):
    exact_quote: str
    page: int
    section: str | None = None

class ComplianceVerdict(BaseModel):
    question: str
    status: str = Field(pattern="^(Voldaan|Niet voldaan|Niet van toepassing|Geen antwoord)$")
    confidence: int = Field(ge=0, le=100)
    evidence: list[EvidenceQuote] = []
    ai_reasoning: str
    auditor_judgement: str | None = None

def extract_pdf_text(pdf_path: Path) -> str:
    """Return full document text with [Page N] markers."""
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            parts.append(f"[Page {i}]\n{page.extract_text() or ''}")
    return "\n\n".join(parts)

def ask(pdf_path: Path, question: str, client: Anthropic) -> ComplianceVerdict:
    doc_text = extract_pdf_text(pdf_path)

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},   # 90% cheaper on repeat calls
        }],
        messages=[{
            "role": "user",
            "content": f"<document>\n{doc_text}\n</document>\n\nQuestion: {question}\n\n"
                       "Return JSON matching the compliance-qa schema.",
        }],
    )

    raw_json = response.content[0].text
    verdict = ComplianceVerdict.model_validate_json(raw_json)
    verdict.question = question
    return verdict
```

### Key technical choices

| Choice | Rationale |
|---|---|
| **One PDF + one question per run** | Matches the auditor mental model; trivial UI; measurable accuracy |
| **Full document in one prompt** (not per-page) | Simpler, lets the model reason across pages for "Niet voldaan" cases where absence is the signal |
| **Pydantic v2** for the verdict schema | JSON-schema auto-export, validation errors point at the exact field |
| **Prompt caching** on system prompt | Same system prompt on every question → 90% cost reduction after the first call |
| **pdfplumber-first, vision-fallback** | Digital PDFs: cheap, fast, deterministic. Only fall back to Vision if `extract_text()` returns empty |
| **Streamlit portal** | Same stack as existing SAAF agents; <1 hour to a working dashboard |
| **JSONL audit log** | Every AI verdict + auditor note appended; immutable trail per session |
| **Auditor judgement as a separate field** | The AI never overwrites or influences the auditor's own conclusion; clear split in the final record |

**Tech stack used:** Python 3.12, Claude API (claude-sonnet-4-5 with prompt caching), Pydantic v2, pdfplumber, pdf2image (fallback), Streamlit, pytest

**Intended file location:** `tools/scripts/compliance_qa.py` + `tools/scripts/compliance_qa_app.py` (Streamlit UI)

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2310 | Identifying information — all extractions are quoted + page-cited |
| ISO 27001 A.5.31 | Legal, statutory, regulatory and contractual requirements — mapper links extracted controls to obligations |
| ISO 27001 A.9.2 | User access management — scope for access-review stretch extractor |
| DORA Art. 11 | ICT business continuity — extractor can identify BCP/DR coverage in policy documents |

### Claude / AI tool usage notes

- Documents are sent to the Claude API. **MVP uses synthetic data only.**
- Before any organisation tests with real policy documents: legal/compliance must sign off on the sensitivity classification.
- Stretch: Ollama + LLaVA fallback path for confidential documents — selected via `--local-vision` flag on the CLI.
- No PII, credentials, client data, or real audit evidence is to be committed to the repo.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only (`ANTHROPIC_API_KEY`)
- [x] Uploaded documents scanned against `.gitignore`; raw uploads never committed
- [x] Audit log redacts quoted text when `sensitivity: confidential` is flagged in metadata

---

## 8. Output Format and Examples

**Format:** JSON (structured extraction) + Markdown (auditor summary) + JSONL (audit log)

**Schema reference:** new schema `outputs/schemas/compliance-qa-schema.json`; `to_findings()` adapter emits records conforming to `outputs/schemas/finding-schema.json` when status is `Niet voldaan`.

### Dashboard view (what the auditor sees)

```
┌────────────────────────────────────────────────────────────────┐
│  Question: Wordt MFA afgedwongen voor alle gebruikers?         │
│  Document: InfoSec Policy v2.3.pdf                             │
├────────────────────────────────────────────────────────────────┤
│  Status:      ✅ VOLDAAN                                        │
│  Confidence:  ████████░░ 85 / 100                              │
├── Evidence ────────────────────────────────────────────────────┤
│  📄 p.5 §4.3 "All users must authenticate via MFA when          │
│     accessing systems classified as Critical."                  │
│  📄 p.6 §4.3.1 "MFA is enforced via Azure AD Conditional        │
│     Access Policy 'MFA-All-Critical'."                          │
├── AI Reasoning ────────────────────────────────────────────────┤
│  The policy explicitly requires MFA for all users accessing     │
│  critical systems (p.5) and names the technical enforcement     │
│  mechanism (p.6). Two direct quotes support the verdict.        │
├── Auditor Judgement (free text) ───────────────────────────────┤
│  [ Policy is clear, but need to verify in fieldwork whether ]   │
│  [ the Conditional Access Policy is actually enabled and     ]   │
│  [ covers all 'Critical' classified systems.                ]   │
├────────────────────────────────────────────────────────────────┤
│  [ Save verdict ]  [ Export as finding ]  [ New question ]      │
└────────────────────────────────────────────────────────────────┘
```

### Synthetic example output (JSON)

```json
{
  "question": "Wordt MFA afgedwongen voor alle gebruikers met toegang tot kritische systemen?",
  "document": "InfoSec Policy v2.3.pdf",
  "status": "Voldaan",
  "confidence": 85,
  "evidence": [
    {
      "exact_quote": "All users must authenticate via MFA when accessing systems classified as Critical.",
      "page": 5,
      "section": "4.3 Authentication"
    },
    {
      "exact_quote": "MFA is enforced via Azure AD Conditional Access Policy 'MFA-All-Critical'.",
      "page": 6,
      "section": "4.3.1 Technical implementation"
    }
  ],
  "ai_reasoning": "The policy explicitly requires MFA for all users accessing critical systems (p.5) and names the technical enforcement mechanism (p.6). Two direct quotes support the verdict.",
  "auditor_judgement": "Policy is clear, but need to verify in fieldwork whether the Conditional Access Policy is actually enabled and covers all 'Critical' classified systems.",
  "timestamp": "2026-04-21T13:14:22Z",
  "model": "claude-sonnet-4-5",
  "session_id": "2026-04-21-edwin-infosec-v2.3"
}
```

### Accuracy target (MVP)

- ≥ 80% correct status on a test set of ~10 questions (mix of Voldaan / Niet voldaan / N.v.t. / Geen antwoord) against 3 synthetic PDFs with known ground truth
- 0% hallucinated quotes — every `exact_quote` must be a verbatim substring of the source document (validated automatically)
- Confidence score roughly calibrated: High-confidence correct verdicts > 90%; when wrong, confidence should be < 70%

---

## 9. Tech Stack

**MVP scope (day 1 demo):**

- [x] Claude API — claude-sonnet-4-5 with vision + prompt caching
- [x] Python 3.12
- [x] GitHub (fork + PR into `SAAF-Project/SAAF-Project` via `tools/scripts/` + `plans/hackathon-4/`)
- [x] Pydantic v2 (schema validation)
- [x] pdfplumber + pdf2image (PDF handling)
- [x] Streamlit (UI + side-by-side inspection)
- [x] pytest (accuracy regression tests)
- [ ] Strapi (if a synthetic-document API saves us generation time)

**Stretch goals:**

- [ ] Multi-question mode: upload 1 PDF, paste a list of questions, get a dashboard with one row per question
- [ ] Multi-document mode: run the same question across a folder of policies
- [ ] Evidence highlighting: render the PDF with the returned quotes highlighted in-page
- [ ] "Explain why not Voldaan": second-pass prompt asking what evidence *would* flip the status
- [ ] Ollama + local vision model for confidential documents
- [ ] Export current verdict directly to a SAAF `finding-schema.json` record
- [ ] MCP adapter to pull source documents from Confluence and push findings to Jira

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `tools/scripts/compliance_qa.py` (portal backend)
- `tools/scripts/compliance_qa_app.py` (Streamlit UI)
- Compliance-Q&A system prompt
- `outputs/schemas/compliance-qa-schema.json`
- 3 synthetic policy PDFs + a question-set of ~10 Q's with known ground truth (Voldaan / Niet voldaan / N.v.t. / Geen antwoord mix)
- pytest regression suite with verdict-accuracy assertions and hallucination check

**Help requested:**

- **Auditors (2x):** draft the synthetic policy content and the question set with ground-truth verdicts; validate that the AI reasoning + evidence would be acceptable in a real dossier.
- **Vaktechniek (1x):** review that the `status` wording (Voldaan / Niet voldaan / N.v.t. / Geen antwoord) matches audit terminology.
- **Analysts (2x):** measure accuracy against ground truth; design the ~10-question test set so all four status values are represented.
- **Engineers (1x):** co-build the Streamlit portal + PDF text extraction + audit log.

**Cross-org interest:**

Compliance questioning of policy documents is universal audit work. A shared portal + question-library + ground-truth dataset lets organisations benchmark verdict quality consistently and feed verdicts into the SAAF shared-outputs library. Aligns with `saaf-jira-confluence-mcp` (source docs) and `saaf-rag-knowledge-base` (questions and verdicts as indexed knowledge).

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | This document; builds on hackathon-3 predecessor plan |
| **Do** | In progress | Hackathon 4: Streamlit Q&A portal + 3 synthetic PDFs + ~10-question test set |
| **Check** | Not started | Target: auditor review of verdict + evidence quality in the 2 weeks after hackathon; benchmark verdict accuracy against manual judgement at ≥ 1 participating org |
| **Act** | Not started | Target: Hackathon 5 — multi-question / multi-document batch mode based on Check feedback; Hackathon 6 — MCP integration |

---

## 12. Open Questions

1. **Status taxonomy** — does `Voldaan / Niet voldaan / Niet van toepassing / Geen antwoord` match how auditors actually classify? Or add a fifth like `Gedeeltelijk voldaan`?
2. **Confidence scale** — 0–100 integer, or named bucket (High / Medium / Low)? Which does the auditor trust more at a glance?
3. **Max document size** — what do we do if the PDF exceeds Claude's context (~200k tokens)? Chunk + map-reduce, or hard-limit with a UI warning for the MVP?
4. **Multi-language policies (NL + EN)** — ask in NL but let evidence be quoted in either source language? Or force single-language per session?
5. **Auditor judgement vs. AI verdict mismatch** — if the auditor disagrees with the AI, do we capture that as a separate field, overwrite the status, or both (with a flag)?
6. **Privacy boundary for cloud API** — is synthetic-only sufficient for hackathon demo, or do we need an Ollama path working on day 1 as a credibility signal?
7. **Ground truth generation** — author the 3 synthetic PDFs by hand, or use an LLM to generate them (with the risk of the same model acing its own generated data)?
