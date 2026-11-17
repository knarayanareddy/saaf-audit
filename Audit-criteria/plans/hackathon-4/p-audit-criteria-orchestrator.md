# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | TBD |
| **Organisation** | TBD |
| **Session** | Hackathon 4 (Session 7 — Repo Hardening & Audit Criteria) |
| **Type** | Agent |
| **Status** | Draft |
| **Claimed By** | TBD |

---

## 2. Problem Statement

Session 7 makes an `AUDIT-CRITERIA.md` mandatory next to every repo's
`README.md`. It must contain at least three control objectives tied to named
frameworks, testable pass/fail acceptance criteria, a good-output and never-do
list, and honest coverage gaps. Written by hand in a single pass, such a
document asserts more than it proves. When this repo's own criteria were
checked against the source, five of nine criteria failed when executed. The
most serious failure: in the live LLM path, the No-Go retry bound is
enforced only by the prompt. A model that ignored the escalation flag produced
10 No-Go verdicts in 12 turns. A single-pass process has no structural way to
catch that.

This plan builds an **Audit Criteria Orchestrator**. It drafts the document
from the PR's source and a short Q&A, reviews and stress-tests it in parallel,
executes every criterion, revises, and blocks placement until the text matches
the executed results.

---

## 3. Use-Case Type and Scope

**Audit domain:** IT audit of AI agents: assurance documentation for agent repositories.

**Applicable standards:** IIA Standards (GIAS 2024) 12.3 and 14.6 for supervision
and documentation; ISO 27001 (2022) A.8.15 and A.8.28; OWASP Top 10 for LLM
Applications (2025) LLM05, LLM06 and LLM10. The EU AI Act Art. 12 and 14 serve
as design references only, with no high-risk claim.

**In scope:**

- read the PR from a local checkout, a zip, or the GitHub API (read-only);
- live Q&A with the human;
- draft, review, stress test, revise, gate, and place the file in the local PR checkout;
- a soft block with human retry/override/abort, bounded in code;
- a per-run audit trail.

**Out of scope:** pushing or committing to GitHub; judging the substantive
audit quality of the target agent; sandboxing beyond the allowlist and
environment stripping described in §7.

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Five sub-agent prompts sharing one format spec (`prompts.py`) |
| **Tools** | `tools/scripts/audit_criteria_orchestrator/`, plus `audit_planning_orchestrator/criteria_checks.py`, which backs this repo's own criteria |
| **Regulatory** | Fixed framework starter list used by the gate: ISO 27001, GDPR, DORA, NIS2, EU AI Act, COSO, COBIT, SOx/ICFR, IIA Standards, OWASP LLM/AI |
| **Outputs** | `AUDIT-CRITERIA.md`, `pr_comment.md`, `runs/<run_id>/log.jsonl` |

---

## 5. Prompts

See `tools/scripts/audit_criteria_orchestrator/prompts.py`. The shared
`FORMAT_SPEC` is what makes the output machine-checkable:

- control objectives use `### CO-n` headings, each with a `**Frameworks:**` line;
- acceptance criteria use table rows `| AC-n | CO-n | criterion | \`command\` | result |`;
- every failing AC must be named under *Known deviations*.

---

## 6. Tools and Techniques

| # | Stage | Kind | Gate |
|---|---|---|---|
| 1 | `read_pr` | deterministic (dir / safe zip extraction / GitHub REST, read-only) | `validate_pr` |
| 2 | `qa` | LLM asks, human answers (interactive or `--answers`) | `validate_questions` |
| 3 | `draft` | LLM (`claude-opus-5`) | `validate_document` |
| 4a | `review` | LLM (`claude-sonnet-5`), in parallel with 4b | `validate_review` |
| 4b | `stress_test` | **real subprocess execution** of every AC, plus LLM adversarial pass | `validate_stress` |
| 5 | `revise` | LLM (`claude-opus-5`) | `validate_revision` |
| 6 | gate | deterministic: DoD parse plus re-execution of every AC on the revised text | `dod_check` |
| 7 | place | write to the local PR checkout, plus `pr_comment.md` | human commits |

**Design choices agreed with the group:**

- a No-Go triggers a soft block with human intervention, not a hard block;
- the GitHub connector is the primary source, with zip upload as fallback;
- `MAX_RETRIES = 2`, matching the existing orchestrator;
- the same `runs/<run_id>/log.jsonl` convention;
- review and stress testing run in parallel;
- Q&A is live.

**Deliberate fixes, carried over from this repo's `AUDIT-CRITERIA.md`:**

| Existing finding | Fix built in |
|---|---|
| D-3 retry bound prompt-only | Control flow is code; `_retry_options()` removes `retry` past the budget, and requests beyond it are refused and logged |
| D-1 gate fails open on unknown tools | `schemas.validate()` fails closed |
| D-4 trail not closed on exception | `finally: finalize()`, with an `error` event |
| D-5 run-id collisions | Microseconds plus a random suffix; directory created with `exist_ok=False` |
| Gap 4: no digests / model attribution | Each call logs input/output sha256, model and prompt hash |

**Deviation from the existing pattern (for the group to confirm):** the existing
orchestrator lets the LLM choose the order of tool calls. Here the order is
fixed in code. This settles that plan's Open Question 3 in favour of a
deterministic, reviewable control flow, at the cost of flexibility.

---

## 7. Regulatory and Policies

All bundled inputs are synthetic. Q&A answers and PR content are sent to the
model, so do not run it on repos containing real audit evidence or personal
data.

**Execution risk:** the stress tester runs PR code. The mitigations, and their
limits, are described in the package README. Live runs with `--allow-exec` are
intended for CI or a disposable container.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget` or `ssh` in scripts (verified by `criteria_checks --check guardrails`)
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials or personal data committed
- [x] API keys from environment only, and stripped from executed child processes

---

## 8. Output Format and Examples

The outputs are `AUDIT-CRITERIA.md`, `pr_comment.md` (an executed-results
table plus the changelog) and `summary.json`. The real example is this repo's
own [`AUDIT-CRITERIA.md`](../../AUDIT-CRITERIA.md): when the orchestrator's gate
is run against it, all 9 ACs are re-executed (4 pass, 5 fail, all disclosed)
and the verdict is **Go**.

---

## 9. Tech Stack

- [x] Python 3.9+, standard library only for `--simulate`
- [x] Claude API (`claude-opus-5` / `claude-sonnet-5`)
- [x] GitHub REST, read-only via `urllib`

**Stretch goals:** a GitHub Action wrapper (CI sandbox, PR comment posted by
the workflow); and a resume-from-run-id option, so a long Q&A is not repeated
after an abort.

---

## 10. Collaboration and Knowledge Sharing

The format spec and `criteria_checks.py` pattern are reusable by every SAAF
repo. Each repo ships one stdlib check script, and its `AUDIT-CRITERIA.md`
becomes executable.

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | This document |
| **Do** | Complete | Package built; all decision branches executed offline |
| **Check** | In progress | Offline: retry → Go, override, abort, budget exhaustion, crash-trail, fail-closed gate, exec blocklist all verified. No live API run yet. |
| **Act** | Not started | Run on the other SAAF-Project repos before they go public |

---

## 12. Open Questions

1. Should an override require a second approver (four-eyes) before placement?
2. Should the `Result` column in `AUDIT-CRITERIA.md` be generated by CI instead
   of written by hand, so it cannot go stale?
3. Is the fixed framework starter list right for repos outside audit planning,
   for example DORA register tooling?
