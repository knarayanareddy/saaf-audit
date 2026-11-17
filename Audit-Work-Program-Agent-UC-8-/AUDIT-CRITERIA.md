## Metadata

| Field | Value |
|---|---|
| Agent | Audit-Work-Program-Agent-UC-8- |
| Repository | https://github.com/SAAF-Project/Audit-Work-Program-Agent-UC-8-/ |
| Maintainer(s) | Olaf de Vriend |
| Last reviewed | 2026-09-15 |
| Status | Draft — synthesized from the SAAF-Project plan/spec (see Sources below); not yet reviewed by someone with GIAS 13.5/13.6 expertise, per the plan's own open ask (§10) |

**Sources used to draft this document:** 
`SAAF-Project/AWPA - UC8/PLAN inge-garretsen-audit-work-program-agent.md` (problem statement, scope, system prompt, sufficiency-flag definitions), `SAAF-Project/AWPA - UC8/README.md` and `CLAUDE.md` (architecture, I/O formats), and one live Opus run's `work_program.json` (cited as evidence in §6; the file was removed from the working tree on 2026-10-04 and is only in git history).

## 1. What the agent does

UC8 (Audit Work Program Agent) transforms a Risk & Control Matrix — the hierarchical JSON an upstream UC7 (RCM Builder) agent produces — into a detailed, executable engagement work program compliant with GIAS 13.5 (resources) and GIAS 13.6 (tasks, methodologies, auditor assignments). For every control in the RCM it generates a control objective, a Test of Design step, one or more Tests of Effectiveness (population, sampling approach, methodology, CAAT opportunity where relevant), six independently-evaluated sufficiency QA flags, and an auditor assignment drawn from a resource directory of skills and available hours. Output is written as JSON, Markdown, and an Excel workbook (work program + resource summary), plus a full run log (prompts, raw responses, token usage) for traceability.

## 2. Control objectives & framework mapping (≥3)

These are control objectives **for the agent itself** — what must be true of its behavior for an internal auditor to trust its output as a planning aid — not the objectives of whatever business controls a given RCM happens to contain (those vary per engagement).

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| CO-1 — Resource planning is complete and realistic: every task carries estimated hours and required skill, rolled up per auditor, with overruns flagged against actual availability. | GIAS 13.5 — Resources (types and quantity: hours and skills per task) | This is the standard UC8 is explicitly built to satisfy; §5 of the plan requires `estimated_hours`/`skill_required` on every step and a resource-overrun alert. |
| CO-2 — Every control receives a complete, appropriately rigorous test plan: a Test of Design plus at least one Test of Effectiveness, with a methodology that isn't reflexively "inquiry only" for high-significance risks. | GIAS 13.6 — Work program (tasks, methodologies, tools, auditor assignments per control) | Directly the standard the work program's phase structure (Context → Design → Execution → Evaluation → Planning → QA) is designed against; the `INQUIRY_ONLY` flag exists specifically to catch under-tested high-risk controls. |
| CO-3 — Evidence-gathering plans are sufficient and independent before execution begins: populations are reconciled, samples are adequately sized and justified, evidence sources are specified, the period covers the full audit scope, and evidence isn't self-provided by the control owner with no corroboration. | IIA Standards — engagement planning / sufficiency of evidence (the six `sufficiency_check()` flags: `EVIDENCE_MISSING`, `SAMPLE_TOO_SMALL`, `POPULATION_NOT_RECONCILED`, `PERIOD_INCOMPLETE`, `INDEPENDENCE_GAP`, plus `INQUIRY_ONLY` under CO-2) | This is the agent's own stated QA layer — six flags "each checked separately, no early-exit between checks" per `CLAUDE.md` — and the natural anchor for "did the agent actually catch a bad plan before an auditor executed it." |
| CO-4 — The agent never fabricates facts about a control it wasn't given, and every generated field is traceable back to the RCM input and the exact model call that produced it. | EU AI Act Art. 13 & 14 (transparency, human oversight) | The system prompt explicitly instructs "Never fabricate control descriptions, owners, or frequencies... If a field is not in the input, set it to null," and the full run log (`work_program_log.json`) exists specifically to make every output traceable — a transparency property, not a testing property, which is why it's split from CO-1–CO-3. |

Framework menu: ISO 27001 · GDPR · DORA · NIS2 · EU AI Act · COSO · COBIT · SOx (ICFR) · IIA Standards · OWASP (LLM/AI). Full catalogue: `docs/reference/domains-and-frameworks.md`.

## 3. Acceptance criteria (testable, pass/fail)

### CO-1 — Resource planning (GIAS 13.5)

- Given a control with a Test of Design and one or more Tests of Effectiveness, the agent assigns a non-null `estimated_hours` and `skill_required` to every single step — none are left blank.
- Given a resource directory and a work program where an auditor's total assigned hours exceed their `available_hours`, the agent's resource summary marks that auditor `OVERRUN` with the correct `delta` (assigned − available).
- Given the resource directory, every auditor in it appears in the resource summary — including auditors with zero assigned hours — not just auditors who received work.
- The agent does not assign a step to an auditor whose `skills` don't include the step's `skill_required`.

### CO-2 — Work program completeness & methodology rigor (GIAS 13.6)

- Given any control in the RCM, the agent generates exactly one `test_of_design` entry and at least one entry in `tests_of_effectiveness`.
- Given a control with `significance: High` (or `Key`), the agent does not use "inquiry" as the sole methodology across all of that control's Test of Effectiveness steps — doing so must instead raise the `INQUIRY_ONLY` flag (see CO-3).
- Given a control flagged `control_type: Automated` or `execution_type: IT-Dependent` with a plausible CAAT opportunity (e.g. a bulk/systematic check over a full population), the agent proposes a non-null `caat_tool` and `caat_pseudocode`; for a control with no such opportunity, both are `null` (not omitted from the schema).
- Given a `sampling_approach`, the agent always states both `method` (judgmental / random / full population / stratified / exception-based) and, when `method` isn't "full population," a non-null `sample_size`.

### CO-3 — Evidentiary sufficiency & independence (sufficiency_check flags)

- Given a test step with no evidence source specified, the agent raises `EVIDENCE_MISSING` for that step.
- Given a population greater than 100 items tested with a sample size below 25 and no stated rationale, the agent raises `SAMPLE_TOO_SMALL`.
- Given a population definition with no tie-out to a system record or report, the agent raises `POPULATION_NOT_RECONCILED`.
- Given an evidence period narrower than the full `AUDIT_SCOPE_PERIOD`, the agent raises `PERIOD_INCOMPLETE`.
- Given a control whose `control_owner` is also the sole evidence provider with no independent corroboration, the agent raises `INDEPENDENCE_GAP`.
- Given a control whose assigned auditor's name (from `distribute_assignments()`) matches its `control_owner`, the agent raises `INDEPENDENCE_GAP` — checked by `check_assignment_independence()`, run after assignment since `assigned_to` isn't known at `sufficiency_check()` time. **Limitation, stated honestly:** this only catches a literal name match; it cannot resolve a role-to-person link (e.g. `control_owner: "Finance Manager"` = auditor Jan Bakker), since the resource directory carries no role/title field to match against — see the function's own docstring.
- Given a control where none of the six conditions above are true, the agent returns an empty `sufficiency_flags` list — not an omitted field, and not a short-circuited partial check (all six are evaluated independently, per `CLAUDE.md`).

### CO-4 — No fabrication & traceability

- Given an RCM entry with a missing `control_owner` (or any other optional field), the agent sets that field to `null` rather than inventing a plausible-sounding value.
- Given any completed run, `work_program_log.json` contains, for every control processed, the exact system prompt, the exact user prompt sent, the raw model response, and token usage — sufficient to reconstruct why any single field has the value it does.
- Given a generated `control_objective`, its wording is traceable to the specific `risk`/`control` description supplied for that entry in the input RCM — it does not introduce risk language absent from the input.

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ `control_objective`, `control_frequency`, `control_owner` for every control — `null` where genuinely unknown from the input, never omitted | ✕ Invent facts, control owners, or frequencies not present in the input RCM |
| ✓ A `sufficiency_flags` list on every control (possibly empty), reflecting all six checks independently evaluated | ✕ Present the generated work program as audit-ready without a human-review / QA gate — UC9 (QA review by the CAE) is a separate, still-required step |
| ✓ `estimated_hours`, `skill_required`, and `assigned_to` on every Test of Design and Test of Effectiveness step | ✕ Run commands outside the allowlist — no `rm`, `sudo`, `curl`, `wget`, `ssh`; no runtime `pip install`; scripts run only from `tools/scripts/` |
| ✓ A resource summary listing every auditor from the resource directory, flagged `OK`/`OVERRUN` against their `available_hours` | ✕ Hard-code credentials or secrets — `ANTHROPIC_API_KEY` from the environment only, `.env` excluded from Claude's own reads via `.claudeignore` |
| ✓ `control_id` values that a downstream finding (`outputs/schemas/finding-schema.json`) can key back to via `control_objective` | ✕ Actually execute the CAAT scripts it proposes — `caat_pseudocode` is a proposal for a human/analyst to run, not something this agent runs itself |

## 5. Coverage gaps

Honest gaps, mostly carried directly from the plan's own "Out of scope" section (§3) — this is where the next iteration starts, not a hidden defect list:

- **No CAAT execution.** The agent proposes tool + pseudocode for a systematic/analytical test but never runs it — an auditor or data analyst still has to execute it and feed the result back in as `observed_exceptions` by hand.
- **No independent QA review.** UC9 (QA review by the CAE) is explicitly out of scope; a generated work program is a planning draft, not a signed-off engagement plan.
- **No ticketing integration.** Task/hour tracking lives only inside the generated output — nothing syncs to Jira, ServiceNow, or similar, so status drifts the moment real fieldwork starts.
- ~~Independence checking is evidence-only, not assignment-only.~~ **Closed 2026-09-15:** `check_assignment_independence()` now also raises `INDEPENDENCE_GAP` when the assigned auditor's name matches `control_owner`. Still only a literal name match — a role-to-person conflict (e.g. `control_owner: "Finance Manager"` who happens to be auditor Jan Bakker) isn't caught, since the resource directory has no role/title field to resolve that against. Closing *that* would need a richer resource directory schema, not a bigger check.
- **No re-ingestion loop.** If the upstream RCM (UC7) changes after a work program has been generated, there's no detection or partial-regeneration — a full manual re-run is the only path, which risks silently stale plans on longer engagements.
- **Single fixed system prompt, no per-domain tuning.** The same prompt handles every audit domain (financial, IT, operational); domain-specific testing conventions (e.g. IT general controls vs. revenue-recognition controls) aren't distinguished.

## 6. Status / validation

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-1 — resource overrun correctly flagged with `delta` | ☑ | Opus run `work_program.json` (git history) → `resource_alert.resource_summary`: e.g. Jan Bakker 130h assigned / 40h available → `OVERRUN`, delta 90 |
| CO-1 — all auditors appear in resource summary, including unassigned | ☑ (partially — all *assigned* auditors observed; a zero-hour auditor case wasn't present in this particular run's resource directory) | Same file — 4 auditors (Jan Bakker, Sara Li, Mehmet Yilmaz, Priya Nair) all listed with status |
| CO-2 — every control has ≥1 ToD + ≥1 ToE | ☑ | Same file — spot-checked control #1 of 9; both `test_of_design` and `tests_of_effectiveness` populated |
| CO-2 — `INQUIRY_ONLY` avoided/raised appropriately | ☐ | Not spot-checked against a specific High-significance, inquiry-only case — needs a targeted test RCM |
| CO-3 — `PERIOD_INCOMPLETE` fires correctly | ☑ | Same file — control #1's `sufficiency_flags` includes `PERIOD_INCOMPLETE` |
| CO-3 — `INDEPENDENCE_GAP` fires correctly (evidence-provider case) | ☑ | Same run — flag observed present across the 9-control output |
| CO-3 — `INDEPENDENCE_GAP` fires correctly (assigned-auditor-is-owner case) | ☑ | `check_assignment_independence()`, added 2026-09-15 — verified with a synthetic unit test (own name → flagged; role-only owner → correctly not flagged; existing flags on other entries left untouched; error entries skipped without crashing). Not yet exercised against a real Claude-generated run. |
| CO-3 — `EVIDENCE_MISSING` / `SAMPLE_TOO_SMALL` / `POPULATION_NOT_RECONCILED` fire correctly | ☐ | Not observed in this run — needs a test RCM deliberately constructed to trigger each, since a clean run naturally won't exercise every flag |
| CO-4 — no fabrication on missing fields | ☐ | Not yet spot-checked field-by-field against the source RCM |
| CO-4 — run log traceability | ☐ | `work_program_log.json` exists per run (confirmed present) but its contents weren't cross-checked against the JSON output for this document |

Next step per the plan's own §10: review by someone with GIAS 13.5/13.6 expertise, plus a deliberately adversarial test RCM constructed to exercise all six sufficiency flags (only 2 of 6 have been observed firing in the one real run inspected so far).

## 7. Observability

Logged today: every run writes `work_program_log.json` (timestamps, API entrypoint, model, system prompt, per-request user prompts, raw responses, token usage) next to the JSON/Markdown/Excel outputs. Missing: no error/retry logging beyond that file, no alerting, no log integrity protection (plain local file), and no retention policy — the log can contain real RCM data. `.gitignore` covers `outputs/*.json|md|xlsx`; the formerly tracked per-model example folders were removed on 2026-10-04, but earlier sample logs remain in git history and any new committed run folder must never hold real engagement data.
