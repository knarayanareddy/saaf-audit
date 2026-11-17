# Observability Notes — Access Review Agent
SAAF Hackathon Submission · Leon Wiendels · 19 May 2026

---

## 1. Purpose
The access-review agent ingests two batch CSV exports — an Active Directory (AD) user export and an HR active-employee list — compares them, and produces a structured list of access-control exceptions (orphaned accounts, stale accounts, role mismatches) in the SAAF finding format for auditor review. It does not modify any system; it is read-only and advisory.

---

## 2. Users & Stakeholders
The primary user is the IT Auditor, who reviews the findings output. The IT / IAM team receives the resulting remediation list. The CISO or Risk Owner audits the quality of the agent's output. Data subjects (employees) are indirectly involved — their data is processed — and face a privacy risk if PII leaks into the output. Failure to catch a High finding exposes the CISO to liability; false positives cause unnecessary disruption for the IAM team.

---

## 3. Workflow
The agent runs in seven observable steps.

Step 1 — Ingest: Load AD CSV and HR CSV; log row counts and column names for both files.

Step 2 — Match: Inner-join on username; log match count and unmatched count per side.

Step 3 — Classify: Categorise each exception as orphaned, stale, or role-mismatch; log category counts.

Step 4 — Anonymise: Replace usernames with USER-NNN tokens before any API call; log token map hash (not the map itself).

Step 5 — LLM call: Send each exception to the Claude API with the system prompt; log request ID, token usage, latency, and model version.

Step 6 — Parse & validate: Parse JSON response; validate against finding-schema.json; log any schema violations.

Step 7 — Output: Write findings to outputs/; log file path, finding count, and risk-rating distribution.

---

## 4. Critical Decisions
Risk-rating assignment is the highest-risk decision point — the agent assigns High/Medium/Low without human override at this step, so miscalibration propagates to every downstream remediation action.

The staleness threshold is hardcoded at 90 days; if organisation policy differs, findings will be systematically wrong.

Match key selection assumes username is unique; shared or recycled usernames produce false negatives.

Anonymisation completeness is a hard gate — if PII survives Step 4 it reaches the external Claude API, breaching data minimisation obligations.

---

## 5. Failure Modes
Missed orphaned account: a shared username reused after termination returns a match on the inner-join, so the high-risk account stays active.

False positive on active user: export timing skew (HR list lags AD by hours) causes a live account to appear orphaned, leading to unnecessary access revocation.

PII in API payload: if the anonymisation step is skipped or partial, a GDPR / privacy breach occurs.

Schema-invalid output: if the LLM produces free text instead of JSON, findings are silently discarded or unparseable.

Hallucinated account detail: if the LLM infers missing fields, findings cannot be reproduced from source data.

Stale threshold mismatch: if the organisation policy differs from 90 days, the wrong Low/Medium population is flagged.

---

## 6. Observability Fields
Every run must emit a structured JSON log record containing at minimum: run_id (UUID), timestamp_utc (ISO-8601), ad_row_count, hr_row_count, match_count, orphaned_count, stale_count, role_mismatch_count, anonymisation_token_count (confirms all accounts were tokenised), api_request_id (Claude message ID for replay), model_version (exact model string, e.g. claude-sonnet-4-6), prompt_tokens, completion_tokens, latency_ms (per API call), schema_validation_pass (boolean, finding count if pass), finding_risk_distribution ({ High: N, Medium: N, Low: N }), output_file_path, and output_file_sha256 (integrity anchor).

---

## 7. Controls
Tool allowlist: read CSV only; no subprocess, no network except the Claude API; no write outside the outputs/ directory.

Policy gate: anonymisation is verified before each API call — if token_count is less than exception_count, the run aborts and raises an alert.

Human approval: all findings are advisory; no automated remediation actions are permitted.

Sampling: 100% of exceptions are sent to the LLM at current volume. For future scale, implement stratified sampling with a random seed logged per run.

Rate-limiting: Claude API calls are throttled with exponential back-off; all retries are logged.

---

## 8. Audit Evidence
An immutable run log (JSONL, append-only) must be retained for a minimum of three years per ISO 27001 A.5.33.

Source CSV hashes (SHA-256) are stored alongside the run log and enable a data-completeness challenge.

The full system prompt version is pinned by git commit SHA in each log record.

The raw LLM response (before schema validation) is archived per run to support challenge of any individual finding.

The output finding file is stored with its SHA-256, allowing detection of post-generation tampering.

Chain-of-thought note: the agent does not use extended thinking. The full request/response pairs serve as the audit substitute for reasoning transparency.

---

## 9. Alerts & Triggers
Zero findings on a large AD export (more than 500 AD rows producing zero findings): halt and require manual review.

Anonymisation gap (token_count less than exception_count): abort run and raise a P1 alert immediately.

Schema validation failure (any finding fails the schema): log the error, exclude the finding from output, and alert the auditor.

Latency spike (any API call exceeding 30 seconds): warn, retry with back-off, and log.

Risk distribution shift (more than 20% change in any rating tier versus the prior quarter): flag the run for auditor review.

Old source data (export date more than 24 hours before run time): surface a warning in the output file header.

Model version change (model_version does not match the expected pinned value): block the run and require explicit sign-off before proceeding.

---

## 10. Success Metrics
Engineering — schema validation pass rate: 100% per run. End-to-end run latency: under 5 minutes for 1,000 accounts. Anonymisation coverage: 100%, zero PII in any API payload.

Audit — false negative rate on orphaned accounts: 0% validated on the synthetic test set. Finding reproducibility: same inputs must produce the same findings (deterministic). Auditor review time saved: more than 60% versus manual process, targeting under one hour per entity.

Business — findings actioned within SLA: more than 90% of High findings remediated within 5 business days. Audit coverage: 100% of entities reviewed every quarter.
