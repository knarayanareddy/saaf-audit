# SAAF AI Control Assessment

A lightweight web portal that lets an internal auditor **upload policy documents, ask one compliance question, and receive a structured verdict with evidence, reasoning and confidence** — in under a minute.

Built during **SAAF Hackathon 4** as the vertical-slice MVP for **Track 2 — Evidence Collection & Extraction**.

![Status](https://img.shields.io/badge/status-MVP-blue) ![Tests](https://img.shields.io/badge/tests-13%2F13%20passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.12%2B-blue) ![License](https://img.shields.io/badge/license-SAAF%20community-lightgrey)

---

## What it does (in plain language)

Every audit engagement has hundreds of compliance questions ("Is MFA enforced for all users?", "Are quarterly access reviews documented?", "Does the BCP cover our cloud provider?"). Answering each question means **reading a stack of policy PDFs line by line**, finding the exact sentence that proves — or disproves — the control is in place, and writing it up defensibly.

**SAAF AI Control Assessment** automates the slow middle part of that workflow, without taking away the auditor's judgement:

1. **You upload one or more PDFs** (policies, procedures, test reports)
2. **You type one compliance question** in natural language (Dutch or English)
3. **The AI reads the documents through the lens of that question** and gives you:
   - A verdict: **Voldaan / Niet voldaan / Niet van toepassing / Geen antwoord**
   - A confidence score (0–100) and a short explanation of why it's this high or low
   - A list of **concrete additional information** that would raise the score
   - The **exact quotes** from the documents that support the verdict, with page numbers
   - An **8-step GIAS reasoning trail** so another auditor can reproduce the conclusion
4. **You add context** (a procedure document you have offline, a verbal CISO confirmation, an extra PDF) → the AI re-evaluates with the new evidence
5. **You decide**: accept the AI verdict or override it. Everything is written to an append-only, read-only audit log on disk.

The auditor is always in the loop. The AI is a research assistant, not the decision-maker.

---

## Why this is defensible to auditors

The reasoning model is aligned with the **Global Internal Audit Standards (GIAS) v2024, effective January 2025**. Every verdict the AI produces is built from an 8-step reasoning trail that a senior auditor can inspect and reproduce:

| # | GIAS Step | Reference |
|---|---|---|
| 1 | Define Objective & Scope | GIAS 13.3 |
| 2 | Identify Risk Context | — |
| 3 | Gather Evidence (relevant · reliable · sufficient) | — |
| 4 | Apply Professional Skepticism | — |
| 5 | Perform Analysis (risk · design · operating effectiveness) | — |
| 6 | Evaluate Evidence Sufficiency | — |
| 7 | Form Conclusion | GIAS 14.5 |
| 8 | Create Audit Trail (Conclusion → Finding → Evidence) | — |

A small **🧭 GIAS v2024-aligned** badge in the top bar signals this to every user of the tool.

---

## Key features

| Feature | What it gives the auditor |
|---|---|
| **Multi-document upload** | Combine several PDFs (policy + procedure + appendix) into one assessment |
| **Natural-language question** | Type the control in your own words — no canned checklists |
| **Verbatim evidence quotes** | Every claim comes with an exact quote + page number |
| **Soft hallucination guard** | Quotes that don't match the source are flagged (⚠️ *unverified*) rather than silently accepted |
| **Confidence reasoning** | The AI explains *why* the score is 65 vs 90 and what would raise it |
| **Auditor context re-evaluation** | Paste additional text and/or upload extra PDFs → new verdict |
| **Accept / Override buttons** | One click to accept the AI's status, or pick your own from a dropdown |
| **GIAS Reasoning Trail** | Collapsible panel with all 8 steps, per verdict |
| **NL / EN language switch** | Flag-dropdown in the top-right; AI reasoning follows your choice |
| **Append-only read-only audit log** | Every AI verdict, re-evaluation, accept and override is logged outside the repo (`~/saaf-audit-log/audit-log.jsonl`, chmod 444) |

---

## Quick start

### 1. Install

```bash
git clone https://github.com/SAAF-Project/Track-2-Evidence-Collection-Extraction.git
cd Track-2-Evidence-Collection-Extraction

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set your Claude API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Never commit your key.** The repo's `.gitignore` blocks `.env*` / `*.key` / `credentials*` / `anthropic*key*` as a belt-and-braces default, but please don't paste keys in chat or files.

### 3. Run the portal

```bash
streamlit run compliance_qa_app.py
```

Opens on [http://localhost:8501](http://localhost:8501).

### 4. Run the tests

```bash
pytest tests/ -v
```

Expect **13/13 passing** in under a second — tests mock the Claude client, so you can run them without an API key.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  UI  (Streamlit portal — compliance_qa_app.py)            │
│   • Sidebar: 1. Control question  2. Upload PDFs          │
│   • Dashboard: status · confidence · GIAS trail · evidence│
│   • Auditor context box + Save & re-assess button         │
│   • Final judgement + Accept / Override buttons           │
├──────────────────────────────────────────────────────────┤
│  Orchestrator   compliance_qa.py                          │
│   1. extract_pdf_text() via pdfplumber                    │
│   2. ask(): build user message, call Claude               │
│   3. Validate response against Pydantic ComplianceVerdict │
│   4. Normalised substring check on every evidence quote   │
│   5. Append verdict to read-only audit log                │
├──────────────────────────────────────────────────────────┤
│  LLM           Claude Sonnet 4.5 + prompt caching         │
│                (system prompt cached → 90% cost reduction)│
├──────────────────────────────────────────────────────────┤
│  Storage       ~/saaf-audit-log/audit-log.jsonl (chmod 444│
│                after every append, outside any git repo)  │
└──────────────────────────────────────────────────────────┘
```

### Key technical choices

| Choice | Rationale |
|---|---|
| **Pydantic v2** schemas | Single source of truth for the verdict shape; clear validation errors |
| **Prompt caching** on system prompt | Same system prompt on every question → 90% cost saving after first call |
| **pdfplumber** | Deterministic text extraction for digital PDFs; page markers preserved |
| **Streamlit** | <1 hour to a working UI; fits the hackathon time-budget |
| **JSONL audit log** | Append-only, greppable, schema-free |
| **Read-only file mode (444)** | Prevents accidental tampering between appends; the app flips to 600 for the write then back to 444 |
| **Soft-flagging instead of blocking** | Quotes that don't match the source are marked ⚠️ *unverified*, not rejected — auditors keep control |

---

## Verdict JSON shape

See [`schemas/compliance-qa-schema.json`](schemas/compliance-qa-schema.json) for the full JSON Schema.

```json
{
  "question": "Wordt MFA afgedwongen voor alle gebruikers?",
  "documents": ["InfoSec-Policy-v2.3.pdf"],
  "status": "Voldaan",
  "confidence": 85,
  "confidence_reasoning": "Één expliciete quote die de control benoemt; geen operationele evidence.",
  "information_needed": [
    "Azure AD Conditional Access export",
    "Kwartaalrapport MFA-dekking van de CISO"
  ],
  "evidence": [
    {
      "exact_quote": "All users must authenticate via MFA when accessing systems classified as Critical.",
      "page": 5,
      "section": "4.3 Authentication",
      "verified": true
    }
  ],
  "reasoning_trail": {
    "objective_scope": "...",
    "risk_context": "...",
    "evidence_gathering": "...",
    "professional_skepticism": "...",
    "analysis": "...",
    "evidence_sufficiency": "...",
    "conclusion": "Design effective.",
    "audit_trail": "Conclusion -> Finding F-001 -> Evidence p.5."
  },
  "ai_reasoning": "The policy explicitly requires MFA on p.5 and names the enforcement mechanism on p.6.",
  "auditor_judgement": null,
  "auditor_override_status": null,
  "log_stage": "initial_ai",
  "timestamp": "2026-04-21T13:14:22Z",
  "model": "claude-sonnet-4-5"
}
```

---

## Repo layout

```
Track-2-Evidence-Collection-Extraction/
├── README.md                   # this file
├── plan.md                     # the original concept plan (hackathon submission)
├── requirements.txt
├── .gitignore                  # hardened — blocks .env, *.key, credentials*
├── compliance_qa.py            # backend: Pydantic models + ask() + audit log
├── compliance_qa_app.py        # Streamlit UI
├── prompts/
│   └── system-prompt.md        # the GIAS-aligned system prompt
├── schemas/
│   └── compliance-qa-schema.json
└── tests/
    └── test_compliance_qa.py   # 13 offline tests, no API key needed
```

---

## Status value semantics

| Status | When |
|---|---|
| **Voldaan** (Compliant) | Document explicitly states the control is met |
| **Niet voldaan** (Non-compliant) | Document explicitly states it is NOT met, or absence is explicitly acknowledged |
| **Niet van toepassing** (Not applicable) | The question does not apply to the scope of this document |
| **Geen antwoord** (No answer) | The document does not contain enough information to decide |

Status enum values stay **Dutch** in the JSON regardless of UI language — this keeps all entries in the audit log consistently parseable across teams and languages.

---

## Security and privacy

- Documents are sent to the Claude API. **Use synthetic or anonymised content while evaluating the tool.**
- Production use with real policy documents requires legal / compliance sign-off per organisation.
- The audit log lives at `~/saaf-audit-log/audit-log.jsonl` — **outside any git repo** — and is written read-only (444) to prevent accidental overwrite.
- The repo's `.gitignore` blocks common key / credential patterns so API keys cannot accidentally land in a commit.
- The hallucination guard is **soft**: it flags quotes that don't match the source but does not drop them — the auditor decides.

---

## Roadmap

- [ ] Multi-question mode: one PDF, a list of questions, a dashboard row per question
- [ ] Multi-document mode: run the same question across a folder of policies
- [ ] In-PDF evidence highlighting (render the uploaded PDF with quote spans highlighted)
- [ ] Ollama + local vision model for confidential documents
- [ ] Export a verdict directly to a SAAF `finding-schema.json` record
- [ ] MCP adapter to pull source documents from Confluence and push findings to Jira
- [ ] Batch accuracy benchmark vs. manual auditor judgement (≥ 1 org)

---

## Acknowledgements

- Built for **SAAF Hackathon 4**, Track 2 — Evidence Collection & Extraction
- Reasoning methodology: **Global Internal Audit Standards (GIAS) v2024**, effective January 2025
- Hackathon 3 predecessor plan by **Mathijs Schouten** ([`document-evidence-extraction-agent.md`](https://github.com/SAAF-Project/SAAF-Project/blob/main/plans/hackathon-3/document-evidence-extraction-agent.md)) was the starting point
- Skeleton and Streamlit wrapper built with **Claude Code** as pair programmer

---

## License

Follows the SAAF community license in the parent [SAAF-Project/SAAF-Project](https://github.com/SAAF-Project/SAAF-Project) repository. Contributions back to the community are encouraged via pull requests to the parent repo.
