# AUDIT-CRITERIA.md — FieldworkOrchestration

## Metadata

| Field | Value |
|---|---|
| Agent | FieldworkOrchestration (orchestrator + fieldwork agents + demo webapp) |
| Repository | https://github.com/SAAF-Project/FieldworkOrchestration |
| Maintainer(s) | Olaf de Vriend |
| Last reviewed | 2026-09-29 |
| Status | Draft — synthesized from the repo's README, `agents/README.md`, `CLAUDE.md` and module docstrings; not yet validated by a live stress test |

**Sources used to draft this document:** `README.md`, `agents/README.md`, `webapp/README.md`, the `agents/audit_trail.py` and `agents/orchestrator.py` docstrings, and the structure of one real run under `runs/` (`audit_trail.jsonl`, `webapp_state.json`). Nothing here was re-run; items marked ☐ in §6 are unverified.

**Branch note:** `origin/main` is 3 commits ahead of `origin/develop`; `develop` has nothing `main` lacks. This document describes `main`.

## 1. What the agent does

FieldworkOrchestration runs a set of internal-audit fieldwork agents (PBC request creation/distribution/validation, evidence collection and analysis, findings drafting, document extraction) through one orchestrator. The orchestrator chains dependent agents, has an independent `quality_check` agent review any run, and refuses to treat results as final until a human auditor records an approval. Every Claude call is written to an append-only audit trail under `runs/<run_id>/`. A FastAPI demo webapp exposes the role-based flow (auditee delivers evidence → auditor reviews → final auditor finalizes). It makes live Claude calls, so AI-specific frameworks apply.

## 2. Control objectives & framework mapping (≥3)

Control objectives are for the orchestrator's own trustworthy behaviour, not for the audits it supports.

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| CO-1 — Human oversight: no agent output is treated as final without an explicit, attributed human decision. | EU AI Act Art. 14 (human oversight); IIA Standards 2340 (engagement supervision) | `require_approved` / `finalize_run` gate every "final" action; webapp attributes approvals to the engagement's named auditor server-side. |
| CO-2 — Traceability: for any output, the prompt, model, settings, raw response and timing that produced it can be reconstructed. | EU AI Act Art. 12/13 (record-keeping, transparency); IIA Standards 2330 (documenting information) | `AuditTrail` records every `ClaudeClient` call; quality verdicts and approvals are separate, entry-linked, append-only files. |
| CO-3 — Independent quality review: agent conclusions are challenged by a separate reviewer and weak ones are revised or failed, not passed through. | IIA Standards 2340/2050 (quality, reliance); ISO 27001 A.5.36-style review of outputs | `quality_check` reviews any agent's call (pass / requires_revision / fail); the evidence pipeline runs a bounded revision loop. |
| CO-4 — Constrained execution and data protection: the only code that runs commands is allowlisted and read-only, and real engagement data and secrets never reach git. | OWASP LLM06 (excessive agency) & LLM02 (sensitive information disclosure); GDPR Art. 5(1)(f); SAAF `allowed-commands.md` | `cli_runner.py` enforces `cli_allowlist.json` (Claude never picks the command); `runs/` and `.env` are gitignored. |
| CO-5 — No fabrication: findings and evidence conclusions rest on supplied evidence and say when it is insufficient. | EU AI Act Art. 13; IIA Standards 2310 (identifying information); OWASP LLM09 (misinformation) | `evidence_analysis` can conclude Inconclusive; `findings_conclusion` produces a finding only against the analysed evidence. |

## 3. Acceptance criteria (testable, pass/fail)

**CO-1**
- Given a run with no recorded approval, `finalize_run` raises and performs no finalizing action.
- Given an entry whose latest decision is "rejected", `require_approved` fails loudly for that entry.
- Given `entry_ids` passed to `finalize_run`, only those entries need approval; unrelated unapproved entries do not block it.
- Given a webapp approval request, the approver name comes from the engagement's `assigned` record, never from the request body.

**CO-2**
- Given any agent run through `ClaudeClient` with an `AuditTrail`, `audit_trail.jsonl` has an entry with system prompt, user prompt, model, settings, raw response, timing and token usage.
- Given a quality review or approval, it is appended to `quality.jsonl` / `approvals.jsonl` linked by `entry_id`, and the original trail entry is not modified.
- Given a whole pipeline call with no client passed, all stages land in a single `runs/<run_id>/`.

**CO-3**
- Given an `evidence_analysis` verdict of `requires_revision`, the pipeline re-runs analysis with the feedback, at most `max_revisions` times, then stops.
- Given a `fail` verdict, the pipeline does not silently pass the result on to `findings_conclusion` as if it had passed. **Limitation, stated honestly:** not yet checked against a real run (see §6).
- Given `review_run`, every entry in the run gets a `quality_check` verdict.

**CO-4**
- Given a command not in `cli_allowlist.json`, `run_command` refuses it; given a parameter that would extend the template beyond its declared parameters, it refuses that too.
- Given the shipped allowlist, every entry is read-only (currently only `echo_placeholder`).
- Given a fresh clone, `git ls-files` contains no `.env`, `runs/` content or `.venv`.

**CO-5**
- Given evidence that does not support a control objective, `evidence_analysis` concludes Inconclusive or Not Effective rather than Effective.
- Given an Effective conclusion, `findings_conclusion` confirms it and does not invent a finding.
- Given a produced finding, its fields cite the analysed evidence items. **Limitation, stated honestly:** conformance to `finding-schema.json` (`F-\d{2,4}` id, `risk_rating`) is not enforced by code, only prompted.

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ A `runs/<run_id>/` trail entry for every Claude call | ✕ Invent evidence, PBC items or findings not grounded in the inputs |
| ✓ A quality verdict and a recorded human decision before anything is treated as final | ✕ Present AI output as audit-ready without the human approval gate |
| ✓ Findings with `id`, `title`, `risk_rating`, `observation`, `recommendation` per `outputs/schemas/finding-schema.json` | ✕ Run a command outside `cli_allowlist.json`, or let the model choose the command |
| ✓ Approver names resolved server-side from the engagement | ✕ Commit `.env`, `runs/` or real client evidence |
| ✓ Explicit "Inconclusive" when evidence is insufficient | ✕ Send real client personal data to Claude without the engagement owner's approval |

## 5. Coverage gaps

- **No automated tests** for the orchestrator, gating logic or webapp (the repo documents none).
- **Concept-prototype webapp:** role selection is a UI picker, not authentication, so approval attribution is only as trustworthy as the engagement record. See `webapp/README.md` for its own list of unsolved items.
- **Finding-schema conformance is prompted, not validated** in code.
- **Delivery is mocked** (`pbc_distribution`, `pbc_reminder` draft emails; nothing is sent).
- **No data-minimisation step** before documents are sent to Claude; no PII redaction.
- **Ported code:** agents were copied from other SAAF repos on 2026-09-08 and can drift from the originals (e.g. UC8 in `Audit-Work-Program-Agent-UC-8-`).
- **Placeholder allowlist only:** no real read-only commands yet, so the CLI path has never been exercised against a real system.

## 6. Status / validation

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-1 finalize blocked without approval | ☐ | Behaviour documented in `orchestrator.py` docstrings; not run |
| CO-1 server-side approver attribution | ☐ | Documented in `webapp/README.md`; not run |
| CO-2 trail entry per Claude call | ☑ (partial) | `runs/20260914T155456Z-7a7f33fb/audit_trail.jsonl` exists with `webapp_state.json`; field contents not cross-checked |
| CO-2 quality/approval linked, append-only | ☐ | Not run |
| CO-3 bounded revision loop | ☐ | Not run |
| CO-4 allowlist enforcement | ☐ | Not run |
| CO-4 no secrets/runs tracked | ☑ | `git ls-files` shows only `.env.example`; a pattern scan for API keys and private keys found nothing (2026-09-29); `.env`, `.venv` and `runs/` are ignored |
| CO-5 Inconclusive on weak evidence | ☐ | Needs a deliberately weak-evidence test case |

Next step: write tests for the gating and allowlist logic (the two deterministic controls), then run an adversarial evidence set through the evidence pipeline.

## 7. Observability

Logged today: every Claude call (prompts, model, settings, raw response, thinking trace when enabled, timing, tokens) in `runs/<run_id>/audit_trail.jsonl`; quality verdicts in `quality.jsonl`; human decisions in `approvals.jsonl`; a local HTML status page via `agents/dashboard.py`. Missing: no application/error logging beyond that, no alerting, no log integrity protection (files are plain, locally writable), and no retention policy for `runs/`, which can hold real engagement data.
