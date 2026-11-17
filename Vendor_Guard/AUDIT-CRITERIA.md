# AUDIT-CRITERIA.md — SAAF Vendor Risk Audit Agent

> What this agent must be judged against **as an auditee**. The [README](README.md) says what it does and how to run it.
> Based on the SAAF template [`docs/conventions/audit-criteria-template.md`](https://github.com/SAAF-Project/SAAF-Project/blob/main/docs/conventions/audit-criteria-template.md) (A2 — Audit Criteria & Controls). Closes #4.

## Metadata

| Field | Value |
|---|---|
| **Agent** | SAAF Vendor Risk Audit Agent (Vendor Guard) |
| **Repository** | https://github.com/SAAF-Project/Vendor_Guard |
| **Maintainer(s)** | *to be filled in by the registered developer + auditor team* |
| **Last reviewed** | 2026-10-06 |
| **Status** | **Draft** — developer-written; control objectives and framework clauses await auditor review |

## 1. What the agent does

A command-line agent that performs a first-pass third-party (vendor) risk assessment. **Input:** a vendor questionnaire plus supporting documents (SOC 2 reports, ISO certificates, DORA self-assessments) as PDF, DOCX, XLSX or TXT. Claude models profile the vendor, assess the documents against ISO 27001, NIS2, CBW, DORA, BIO2 (Dutch government vendors) and the EU AI Act / ALTAI / EC Ethics Guidelines (AI vendors), and extract document dates; Python code checks document currency and computes the ratings. **Output:** a RAG scorecard, a gap register and an audit memo, in both Office (xlsx/docx) and Google Workspace (csv/html) formats. **Audit task supported:** vendor due diligence and third-party assurance review, as a *draft for a qualified auditor*, not as a final opinion.

## 2. Control objectives & framework mapping

The objectives below concern the **agent's own trustworthy behaviour**: the qualities an auditor needs before relying on its output.

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| **CO-1** — Reported findings are complete; irregular model output never lowers the reported risk or silently drops findings. | IIA Global Internal Audit Standards 14.2 (Analyses and potential findings) & 14.6 (Engagement documentation); COBIT 2019 APO10 (Managed vendors) | A vendor assessment that under-reports gaps gives false assurance, which is the worst failure for an audit tool. |
| **CO-2** — Risk ratings are deterministic, rule-based and conservative. | IIA GIAS 14.3 (Evaluation of findings); DORA Art. 28 (ICT third-party risk management) | The rating must be reproducible and explainable to the auditee and regulator; it must not depend on the model's mood. |
| **CO-3** — Third-party assurance is relied on only while it is current. | ISAE 3402 / AICPA SOC 2 (report period); ISO/IEC 17021-1 & IAF MD 5 (certificate validity, surveillance audits); EBA/GL/2019/02 (outsourcing — ongoing monitoring) | Expired certificates or stale SOC reports provide no assurance; reliance on them is a classic TPRM finding. |
| **CO-4** — Untrusted vendor input cannot steer the assessment. | OWASP Top 10 for LLM Applications 2025 — LLM01 (Prompt injection); EU AI Act Art. 15 (Accuracy, robustness and cybersecurity) | The documents are written by the party under audit, which has an incentive to influence the outcome. |
| **CO-5** — Outputs are safe to open and do not compromise the reviewer's environment. | OWASP LLM05:2025 (Improper output handling); OWASP CSV Injection; ISO/IEC 27001:2022 Annex A 8.28 (Secure coding) | Finding text derives from vendor input and lands in spreadsheets and HTML opened by auditors. |
| **CO-6** — Outputs are presented as drafts under human oversight; uncertain results are flagged for review. | EU AI Act Art. 14 (Human oversight); IIA GIAS 15.1 (Final engagement communication) | An AI-generated memo must not reach management looking like a signed-off audit opinion. |

*Framework clause references were drafted by the developer and must be confirmed by the team's auditor.*

## 3. Acceptance criteria (testable, pass/fail)

Every criterion is automated in [`tests/test_regression.py`](tests/test_regression.py) (test names prefixed `test_acNN_`), using synthetic data and a mocked model. Run with `python -m pytest tests/ -v`.

**CO-1 — Completeness, fail-safe normalisation** (AC-01, AC-04, AC-08)
- AC-01 · Given a model finding with an unrecognised status (e.g. "Fail"), the agent records it as **Gap** and appends `[HUMAN REVIEW REQUIRED]` with the raw value to the evidence.
- AC-01 · Given an unrecognised severity (e.g. "Extreme"), the agent records **High** and flags it the same way.
- AC-01 · Given a known synonym ("Non-Compliant", "Informational", "n/a"), the agent maps it to the canonical value **without** a review flag.
- AC-01 · Given a finding with a missing field or a non-text status/severity, the agent rejects it (validation error) rather than inventing a value.
- AC-04 · Given a model response cut off mid-array, the agent keeps the complete findings **and logs a warning** that later findings are missing.
- AC-04 · Given a response that is not JSON at all, the agent raises an error; it does not return an empty, "clean" result.
- AC-04 · Given a single JSON object instead of an array, every agent still returns that finding.
- AC-08 · Given a full run, every finding from every agent appears in both gap registers (CSV and XLSX row counts match), and all six output files are written.
- AC-08 · Given that any agent fails (e.g. API outage), the run aborts and **no** partial report is written.

**CO-2 — Deterministic, conservative ratings** (AC-02, AC-08)
- AC-02 · Given any Critical finding with status Gap **or Partial**, or any High Gap, the framework is rated **Red**.
- AC-02 · Given only Medium/Low Gaps or non-Critical Partials, the framework is rated **Amber**; given only Compliant / Not Applicable, **Green**.
- AC-02 · Given findings across several frameworks, each framework is rated independently and the worst finding determines its rating.
- AC-02 · Given model output with unrecognised status *and* severity, the framework cannot be rated Green.
- AC-08 · Given a vendor profile, security and resilience agents always run; BIO2 runs only for Dutch government vendors; AI-trust runs only for AI systems; document validity always runs.

**CO-3 — Current assurance only** (AC-03)
- AC-03 · Given a SOC 2 Type II period end ≤ 365 days ago, the agent rates it Compliant; at 366 days, **Gap / High**.
- AC-03 · Given a document date in the future, the agent does **not** rate it Compliant (Partial / Medium, "verify the date").
- AC-03 · Given an ISO certificate expired yesterday → Gap / High; expiring within 90 days (including today) → Partial / Medium; later → Compliant.
- AC-03 · Given an unparseable or missing date, the agent never rates the document Compliant.
- AC-03 · Given an ISO surveillance audit older than 365 days, the agent reports a Gap / High (existing test `test_iso_surveillance_audit_overdue`).

**CO-4 — Untrusted input** (AC-06, AC-07, AC-11)
- AC-06 · Given any set of vendor documents, the model input starts with a notice that the documents are untrusted evidence, and each document is enclosed in its own `<vendor_document>` tags.
- AC-06 · Given a document containing `</vendor_document>` or a forged opening tag, it cannot close or forge a delimiter; its text is kept but neutralised.
- AC-06 · Given a filename containing quotes or markup, it cannot break out of the tag attribute.
- AC-06 · Given any agent call, vendor text is sent only in the user message, **never** in the system prompt.
- AC-07 · Given a legacy `.xls` or unsupported file, the agent stops with a clear error before any model call.
- AC-11 · Given the `claude-code` backend, every model call runs Claude Code with **no built-in tools, no MCP servers, none of the user's settings/hooks/CLAUDE.md, and one turn**, with vendor text only in the prompt, never in the system prompt; every agent, the orchestrator and the memo work through it.
- AC-11 · Given a Claude Code error (not signed in, rate limit, error result, empty answer) or a missing SDK, the run fails with an explanatory error rather than an empty result; the default backend never touches the Agent SDK.

**CO-5 — Safe outputs and local surface** (AC-05, AC-12)
- AC-05 · Given finding text starting with `=`, `+`, `-`, `@`, tab or carriage return, the CSV cell is prefixed with `'` and the XLSX cell is stored as text, not as a formula.
- AC-05 · Given HTML or script in vendor name, services, findings or memo text, the HTML memo contains no executable markup.
- AC-12 · Given the local web UI, it listens on 127.0.0.1 only; any API call without the per-session token, or with a non-local `Host` header, is refused (403), so another website cannot start a run or read results.
- AC-12 · Given an upload, filenames are reduced to safe basenames inside the run directory; only one questionnaire, PDF/DOCX/XLSX/TXT, ≤ 50 MB and one run at a time are accepted.
- AC-12 · Given a finished run, only the six whitelisted output files can be downloaded; given a failed run, the error is shown and **no** files are offered; warnings (e.g. truncation) reach the page.

**CO-6 — Human oversight** (AC-01, AC-10)
- AC-10 · Given any memo (DOCX or HTML), a notice that it is an AI-assisted draft requiring auditor review appears above the memo body.
- AC-01 · Given uncertain model output, the affected finding carries `[HUMAN REVIEW REQUIRED]` in the gap register.

**Test hygiene** (AC-09)
- AC-09 · Given the test suite, no test can reach the network or the real API: the API key is removed, an unmocked client raises, and outbound sockets are blocked.

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ One finding per assessed control with framework, control ID, status, severity, evidence and recommendation | ✕ Invent evidence, citations or controls not present in the vendor documents (instructed in every agent prompt; see gap G-3) |
| ✓ A RAG rating per framework that follows the documented rule in §3 / CO-2 | ✕ Downgrade a finding because the model's wording was unexpected |
| ✓ A Document Validity finding for every vendor document whose date could be extracted, or a Partial finding when it could not | ✕ Treat expired, stale or future-dated assurance as current |
| ✓ `[HUMAN REVIEW REQUIRED]` on every finding whose model output had to be coerced | ✕ Follow instructions embedded in vendor documents |
| ✓ The AI-assisted draft notice on every memo | ✕ Present the memo as audit-ready with no human-review gate |
| ✓ The same findings and ratings in the Office and Google Workspace versions of each output (CSV cells may carry a `'` injection guard) | ✕ Write spreadsheet formulas or executable HTML derived from model or vendor text |
| | ✕ Produce a partial report when an agent has failed |
| | ✕ Hard-code credentials; the API key is read only from `ANTHROPIC_API_KEY` |

## 5. Coverage gaps

Things an auditor would reasonably expect that the agent does **not** (yet) do.

- **G-1 · Findings do not conform to the SAAF [`finding-schema.json`](https://github.com/SAAF-Project/SAAF-Project/blob/main/outputs/schemas/finding-schema.json).** Proposed mapping for an export adapter: `control_id` + `control_name` → `control_objective`; `evidence` → `observation`; `recommendation` → `recommendation`; generated `F-NN` → `id`; `ai_assisted: true`. The SAAF scale has no *Critical*, so the mapping must state whether Critical → High; that is a rating decision for the auditor.
- **G-2 · Prompt-injection resistance is not verified against the live model.** AC-06 proves the defences are wired in (delimiting, untrusted-data notice, no vendor text in the system prompt); whether Claude actually ignores an embedded instruction needs an **A1 stress test** with adversarial vendor documents.
- **G-3 · Evidence is not traced back to source text.** Nothing checks that a finding's evidence actually occurs in the vendor documents, so a hallucinated citation would pass. A deterministic quote-match check would close this.
- **G-4 · No control-coverage reconciliation.** If the model skips controls listed in `prompts/*.md`, nothing notices; the framework can look Green because it was only partly assessed.
- **G-5 · The memo narrative is not checked against the findings.** The model-written memo could contradict the scorecard (e.g. call a Red framework "adequate").
- **G-6 · No audit trail of model interactions.** Raw prompts, responses, model IDs and run timestamps are not stored, so a run cannot be reproduced or independently re-performed.
- **G-7 · Scanned (image-only) PDFs yield no text**, without a warning. The vendor would then appear to have no evidence, which over-reports gaps.
- **G-8 · Personal data in vendor documents is sent to the Anthropic API unredacted.** Users must have a lawful basis and processor agreement (GDPR Art. 28) before uploading documents containing personal data.
- **G-9 · Single-run, non-deterministic model assessment.** No repeated-run consistency check; the same documents can yield different findings between runs.
- **G-10 · Model IDs are hard-coded** (`claude-opus-4-6`, `claude-sonnet-4-6`); deprecation will break runs and silently change assessment behaviour when updated.
- **G-11 · `aggregate_findings` is a pass-through**: overlapping controls across frameworks (e.g. ISO 27001 vs. NIS2 vs. BIO2) are not de-duplicated or cross-referenced.
- **G-12 · SOC 2 content is not assessed for exceptions or qualified opinions**, only for currency; complementary user entity controls (CUECs) are not extracted.
- **G-14 · No OS-level isolation.** The `claude-code` backend relies on Claude Code having no tools; the process itself runs with the user's normal permissions (no container). The web UI page's JavaScript is syntax-checked (gjs) but its behaviour is not covered by automated tests.
- **G-13 · The `claude-code` backend has no output-length cap** (the Agent SDK exposes no `max_tokens`), and it has not yet been run end-to-end against a live Claude login. Results may differ from the `api` backend for the same documents.

## 6. Status / validation

Verified on 2026-10-06 by the automated suite: **231 tests passing**, 0 failing (Python 3.14, pinned `requirements.txt`). The 40 regression tests for AC-01 to AC-07 were also run against the **pre-fix** code and failed there, confirming they detect the defects they guard against. No live-model run has been performed for this review.

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| AC-01 fail-safe normalisation & review flag | ☑ | `test_ac01_*` (automated, mocked) |
| AC-02 RAG rule | ☑ | `test_ac02_*` |
| AC-03 document currency | ☑ | `test_ac03_*`, `tests/test_document_validity_agent.py` |
| AC-04 robust parsing, no silent loss | ☑ | `test_ac04_*` |
| AC-05 formula / script injection | ☑ | `test_ac05_*` |
| AC-06 untrusted-input plumbing | ☑ | `test_ac06_*` |
| AC-06 live prompt-injection resistance | ☐ | Open; needs A1 stress test (G-2) |
| AC-07 input errors fail early | ☑ | `test_ac07_*` |
| AC-08 pipeline completeness & routing | ☑ | `test_ac08_*`, `tests/test_integration.py` |
| AC-09 tests cannot reach network | ☑ | `test_ac09_*`, `tests/conftest.py` |
| AC-10 draft notice on memos | ☑ | `test_ac10_*` |
| AC-11 backends (locked-down claude-code, loud errors) | ☑ | `tests/test_backends.py` (`test_ac11_*`, fake SDK) |
| AC-11 live run through a real Claude login | ☑ (partial) | Manual run 2026-10-06: profile, routing and document validity completed via the user's own login |
| AC-12 local web UI access control, uploads, downloads | ☑ | `tests/test_webui.py` (`test_ac12_*`, real loopback server, fake pipeline) |
| End-to-end run on sample documents with the real API | ☐ | Open; needs an API key and auditor review of the output |
| Framework clause mappings in §2 | ☐ | Open; auditor to confirm |
