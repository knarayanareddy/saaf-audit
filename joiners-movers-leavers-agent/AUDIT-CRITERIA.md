# `AUDIT-CRITERIA.md` — Joiners-Movers-Leavers Access Audit Agent

> Copied and filled in from `docs/conventions/audit-criteria-template.md` in the main SAAF-Project repo (SAAF A2 standard).
> It sits next to `README.md`: the README says what the agent does and how to run it; this document says what the agent must be judged against as an auditee.
> Sources used to draft it: the code in this repository, the test suite (`tests/test_agent.py`), three live Claude Code runs on the sample data (2 November 2026), and the Track 2 IAM work it is a spin-off of (`SAAF-Project/Track-2---IAM-final`).

---

## Metadata

| Field | Value |
|---|---|
| **Agent** | Joiners-Movers-Leavers (JML) Access Audit Agent |
| **Repository** | https://github.com/SAAF-Project/joiners-movers-leavers-agent |
| **Maintainer(s)** | Mathijs Schouten (SAAF Project). Baseline engine: Bart van den Broek (Track 2) |
| **Last reviewed** | 2026-11-02 |
| **Status** | Draft |

## 1. What the agent does

The agent tests whether access rights follow the joiner, mover and leaver lifecycle in one audit period. It reads HR master data, directory accounts, entitlement exports per system (Active Directory groups, ERP roles), a Jira export of access-request and removal tickets, and an access policy (SLAs, role model, SoD rules, privileged roles). A deterministic engine runs twelve JML tests plus five baseline account checks and returns each exception with the source rows it rests on. Claude Code, run headless with every tool disabled, then assesses each exception and drafts grouped findings in the SAAF finding schema from a pseudonymised copy of the exceptions. Every draft is validated against the input, and nothing is final until an auditor signs off.

The agent makes model calls at runtime (Claude Code). AI-specific frameworks below are therefore in scope. The twelve tests themselves are deterministic and do not use a model.

## 2. Control objectives & framework mapping

The first three objectives are about the agent's own trustworthy behaviour; CO-2 also covers the audit domain it tests.

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| **CO-1** — Every exception and every finding is traceable to specific source records (file and line), and nothing is reported without a source | IIA Global Internal Audit Standards 2024, Standard 14.6 (Documenting engagements) and 14.2 (Analyses and potential engagement findings); ISAE 3000 (sufficient appropriate evidence) | An exception an auditor cannot trace back to a record is an opinion, not evidence. Reviewers and A1 stress testers must be able to re-perform each one. |
| **CO-2** — The JML tests are complete and correct for the stated population: every grant, transfer and termination in the period is tested, planted exceptions are found, and correct records pass | ISO/IEC 27001:2022 A.5.18 (Access rights), A.5.3 (Segregation of duties), A.8.2 (Privileged access rights); SOC 2 CC6.2 and CC6.3; COBIT 2019 DSS05.04 | These are the access controls the agent claims to test. A missed exception or a false positive directly misleads the auditor. |
| **CO-3** — The model fabricates nothing: it cites only identifiers present in its input, every finding follows the SAAF finding schema, and anything that fails these checks is rejected visibly | OWASP Top 10 for LLM Applications 2025, LLM09 (Misinformation); EU AI Act Art. 13 (transparency), applied voluntarily; SAAF `outputs/schemas/finding-schema.json` | Language models can produce plausible but unsupported statements. The agent must catch this deterministically, not rely on the model's good behaviour. |
| **CO-4** — A human auditor reviews and signs off before any output is final, and the auditor can always see whether findings came from a live model call, a prepared result or a deterministic draft | EU AI Act Art. 14 (human oversight), applied voluntarily; IIA Global Internal Audit Standards 2024 (engagement supervision and review); COSO 2013 Principle 10 | Audit conclusions are the auditor's. The agent drafts; it must not present a draft as a conclusion or hide which path produced it. |
| **CO-5** — Personal data is minimised before the model call and the model has no capabilities beyond reading its input | GDPR Art. 5(1)(c) (data minimisation), Art. 25 (data protection by design); OWASP LLM 2025 LLM02 (Sensitive information disclosure) and LLM06 (Excessive agency); SAAF `regulatory/guardrails/allowed-commands.md` | Access reviews are full of names and roles. The model only needs the facts, and an agent with tools could act outside its mandate. |

*Framework menu: ISO 27001 · GDPR · DORA · NIS2 · EU AI Act · COSO · COBIT · SOx (ICFR) · IIA Standards · OWASP (LLM/AI). Full catalogue: `docs/reference/domains-and-frameworks.md` in SAAF-Project.*

## 3. Acceptance criteria (testable, pass/fail)

Test names refer to `tests/test_agent.py`. Run them with `python3 -m pytest -q`.

**CO-1 — Traceability**
- **CO-1.1** Given the sample data, every exception carries at least one evidence item. (`test_every_exception_traces_to_source_rows`)
- **CO-1.2** Given an evidence reference `file.csv:N`, line N of that file is the row for the same user, or for the cited ticket. (`test_every_exception_traces_to_source_rows`)
- **CO-1.3** Given any test, the agent names the control references it maps to, and every exception has a risk rating. (`test_each_exception_has_a_risk_and_controls`)
- **CO-1.4** Given a UI session, the run folder holds the inputs' SHA-256 hashes, the review, the exact model input, the raw model output, the validated draft and the sign-off. *Verified by a manual run (section 6); no automated test yet.*

**CO-2 — Completeness and correctness of the JML tests**
- **CO-2.1** Given the sample data, the agent returns exactly the 15 planted exceptions (5 joiner, 4 mover, 4 leaver, 2 baseline), no more and no fewer. (`test_planted_exceptions_found_exactly`)
- **CO-2.2** Given the clean joiner, mover and leaver cases and existing staff, the agent returns no exception for them, and service accounts matching the exclusion patterns are excluded. (`test_clean_records_pass`, `test_service_account_excluded`)
- **CO-2.3** Given the same inputs twice, the agent returns identical results apart from the generation timestamp, and the sample data generator reproduces the committed files byte for byte. (`test_review_is_deterministic`, `test_sample_data_is_reproducible`)
- Limitation, stated honestly: the population is what the exports contain. The agent does not prove the exports are complete (see Coverage gaps).

**CO-3 — No fabrication**
- **CO-3.1** Given a draft finding that cites an identifier not present in the model input, the agent rejects that finding and names the identifier. (`test_finding_citing_unknown_record_is_rejected`)
- **CO-3.2** Given a draft finding whose text mentions an exception or ticket id that is not in the input, the agent rejects it. (`test_finding_mentioning_unknown_id_in_text_is_rejected`)
- **CO-3.3** Given a finding with an invalid id, an unknown risk rating, a field outside the schema or a title over 100 characters, the agent rejects it; the deterministic fallback findings always pass the schema. (`test_finding_outside_schema_is_rejected`, `test_deterministic_findings_follow_schema`)
- **CO-3.4** Given a draft that leaves exceptions unassessed or not covered by any finding, the agent reports this as a failed check instead of passing silently. (`test_uncovered_exceptions_are_reported`)
- Limitation, stated honestly: the check proves that every cited identifier exists, not that the model's reasoning about it is right. That is what CO-4 is for.

**CO-4 — Human review gate and transparency of the path taken**
- **CO-4.1** Given no sign-off, the report states "Draft. Not signed off by an auditor." (`test_web_flow_requires_signoff_before_final`)
- **CO-4.2** Given a sign-off request without a reviewer name, or before a draft exists, the agent refuses it. (`test_web_flow_requires_signoff_before_final`)
- **CO-4.3** Given that Claude Code is unavailable, the agent falls back to the prepared result only when its fingerprint matches the exact data set, and otherwise to a deterministic draft; the UI and the report state which path was used. Every model finding has `status: Open` and `ai_assisted: true`. (`test_fallback_without_claude_uses_prepared`, `test_fallback_on_other_data_is_deterministic`, `test_prepared_results_match_sample_and_pass_checks`)

**CO-5 — Data minimisation and confinement**
- **CO-5.1** Given the sample data, the model input contains no username or full name of any person; people appear only as USER-NNN. (`test_payload_contains_no_names`)
- **CO-5.2** Given a model output with USER-NNN references, names are restored only locally for the auditor's display. (`test_reveal_restores_names_locally`)
- **CO-5.3** Given a model call, Claude Code is started with `--tools ""`, `--strict-mcp-config` and `--no-session-persistence`, and never with permission bypass flags. (`test_model_call_has_no_tools`)
- **CO-5.4** Given the web UI, the server listens on 127.0.0.1 only. *Verified by code read (`run.py`).*

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ Each exception with its test id, risk rating, the person's lifecycle and its source rows (`file:line`) | ✕ Invent facts, people, tickets or citations that are not in the input |
| ✓ Findings that conform to `finding-schema.json`, with `evidence_references` listing exception and ticket ids | ✕ Present output as final or audit-ready without the auditor's sign-off |
| ✓ A visible statement of the path used: live Claude Code (with model and duration), prepared result, or deterministic draft | ✕ Use a prepared result for a data set other than the one it was recorded on |
| ✓ The result of every validation check, including rejected findings and uncovered exceptions | ✕ Hide a rejected finding or a failed check |
| ✓ The data set fingerprint and file hashes, so the result can be tied to its inputs | ✕ Send names or usernames to the model, or give the model tools, file access or network access |
| ✓ A "Needs follow-up" conclusion when the records allow a legitimate explanation | ✕ Run commands outside the allowlist (`regulatory/guardrails/allowed-commands.md`) or bind the web UI to a public interface |
| ✓ Root causes marked as to be confirmed with management | ✕ Hard-code credentials or secrets (none exist: Claude Code uses the auditor's own login) |

## 5. Coverage gaps

- **Synthetic data only.** All data is fictional. The agent has not been run on a real directory, ERP or Jira export. Column names are fixed (see `engine/sources.py`); real exports will need mapping.
- **No connectors.** The agent reads CSV/XLSX exports, not Entra ID, AD, SAP or Jira APIs. Completeness of the exports (record counts against the source system, extraction parameters) is not verified by the agent and remains an auditor procedure.
- **Approver authority is not tested.** J4 checks that requester and approver differ. It does not check that the approver is the line manager or an authorised system owner.
- **History depends on the export.** Removal timing (M1, L2) relies on `removed_date` in the entitlement export. Many systems do not keep this; audit logs would be needed.
- **One transfer per person per period.** HR data holds one `transfer_date` and `previous_role`. Multiple moves, rehires, contractors and external identities are not modelled as lifecycles (externals only surface as orphaned accounts, B1).
- **Login evidence is directory-only.** L3 uses the directory's last login. Application logins are not tested.
- **No test on removal tickets.** Leaver removal tickets are shown as evidence but not tested (for example a removal ticket that is still open).
- **Model output varies between runs.** The tests are deterministic; the model's grouping is not (live runs on the same data produced four and five findings). The prepared fallback makes a presentation predictable, but each live run needs its own review.
- **Pseudonymisation is name-based.** Names, usernames and unique first names are replaced, including in ticket text. Nicknames, e-mail addresses or employee numbers inside free text would not be caught. Review real exports before use.
- **Data leaves the machine in pseudonymised form.** Claude Code sends the model input to Anthropic under the auditor's own account. Organisations need to confirm this is acceptable for their data.
- **Sign-off is not authenticated.** The reviewer types a name; the event log is local and append-only by convention, not tamper-evident.
- **Dutch interface text has not been reviewed by a second Dutch-speaking auditor.**
- **No CI pipeline yet.** Tests run locally; there is no GitHub Actions workflow.
- **Presentation pacing.** The UI reveals test results one by one for readability. The results are computed in full before the reveal; nothing is simulated.

## 6. Status / validation

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-1.1, CO-1.2, CO-1.3 | ☑ | `pytest` on Python 3.9.6 (macOS system Python), 2026-11-02: 21 passed |
| CO-1.4 run folder contents | ☑ | Manual UI run 2026-11-02 (`runs/<stamp>-ui/`: `events.jsonl`, `review_local.json`, `model_input.json`, `model_output_raw.json`, `draft.json`, `signoff.json`) |
| CO-2.1, CO-2.2, CO-2.3 | ☑ | `pytest`, 2026-11-02 |
| CO-3.1 to CO-3.4 | ☑ | `pytest`, 2026-11-02. Also seen live: the first live run had one finding rejected because the validator did not yet accept approver references (USER-NNN in ticket fields). The validator was corrected; the rejection itself showed the check works. |
| CO-4.1, CO-4.2, CO-4.3 | ☑ | `pytest` and a manual UI run with sign-off, 2026-11-02 |
| CO-5.1 to CO-5.3 | ☑ | `pytest`, 2026-11-02 |
| CO-5.4 | ☑ | Code read (`run.py`, `uvicorn.run(host="127.0.0.1")`) |
| Live model quality | ☐ | Three live runs passed every check (2026-11-02). Not yet reviewed by an A1 stress-test team. |

## 7. Observability

**Logged today:**
- Each UI session writes a run folder under `runs/` (gitignored): `events.jsonl` (append-only: sources loaded with SHA-256 hashes and fingerprint, tests run with counts per test, draft requested and returned with mode, model, duration, error and checks, sign-off, report viewed), `review_local.json`, `model_input.json` (exactly what the model received), `model_output_raw.json`, `draft.json` and `signoff.json`.
- The CLI (`python3 -m engine.cli`) writes the same review files plus `summary.txt`.
- Python `logging` at INFO for source loading, exclusions and fallbacks.

**Missing:**
- No tamper evidence (hash chain or signature) on the event log.
- No record of the operating system user or machine.
- No central collection; logs stay on the auditor's machine.
- Claude Code's own session is not persisted (`--no-session-persistence`); the envelope's session id and cost are kept in `draft.json` only.
