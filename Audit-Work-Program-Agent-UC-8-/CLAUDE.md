# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UC8 — Audit Work Program Agent, part of the Standard Audit Agent Framework (SAAF). Transforms a Risk & Control Matrix (RCM) into a detailed, executable engagement work program compliant with GIAS 13.5 (resources) and GIAS 13.6 (tasks, methodologies, auditor assignments).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
```

## Running the Agent

```bash
python work_program_generator.py \
    --rcm Input/rcm_output.json \
    --resources Input/resource_directory.json \
    --output outputs/work_program.json
```

Produces four files in `outputs/`: `.json`, `.md`, `.xlsx`, `_log.json`.

## Architecture

The entire agent lives in `work_program_generator.py`. The pipeline is:

1. **`flatten_rcm()`** — normalises the UC7 hierarchical RCM input (`risks[].stage2.controls[]`) into a flat list of control dicts. Maps `inherent_risk_rating` → `significance` and surfaces IT-dependency fields as enrichment.
2. **`call_claude_batch()`** — submits all controls in a single Anthropic Messages Batch (50% token discount). Polls until `processing_status == "ended"`, parses each result via `_parse_raw_json()`, and returns `(results_by_id, run_log)`. The run log captures timestamps, the system prompt, per-request user prompts, raw responses, and token counts.
3. **`sufficiency_check()`** — called per control, right after its batch result is parsed (inside `generate_work_program()`'s loop, before assignment). Independently evaluates 5 of the 6 GIAS QA flags across every ToE step (`INQUIRY_ONLY`, `EVIDENCE_MISSING`, `SAMPLE_TOO_SMALL`, `POPULATION_NOT_RECONCILED`, `PERIOD_INCOMPLETE`, and the evidence-provider half of `INDEPENDENCE_GAP`). Each flag is checked separately — no early-exit between checks.
4. **`distribute_assignments()`** — proportional skill-based assignment across the full work program, run once all controls have been processed. Steps are grouped by `skill_required`; within each skill group each step is assigned to the matching auditor with the highest remaining capacity, seeded from `available_hours`. Auditors with more available hours receive proportionally more work.
5. **`check_assignment_independence()`** — runs immediately after `distribute_assignments()`, since it needs `assigned_to` (not known during step 3). Adds the other half of `INDEPENDENCE_GAP`: fires when the auditor assigned to test a control shares a name with that control's `control_owner`. Literal name match only — see the function's own docstring for why it can't resolve a role-to-person link (e.g. `control_owner: "Finance Manager"` who happens to be a named auditor).
6. **`check_resource_totals()`** — aggregates hours per auditor across all controls, flags overruns vs `available_hours`. All auditors appear in the summary, including those with zero assigned hours.
7. **`to_markdown()` / `to_excel()`** — render the JSON output. Excel has two sheets: "Work Program" (one row per test step, freeze pane, colour-coded) and "Resource Summary" (all auditors shown, green/red by status).

`SYSTEM_PROMPT` (constant in the script, also documented in `work-program-agent.md`) defines the exact JSON schema Claude must return per control.

## Key Data Files

- `Input/rcm_output.json` — live UC7 RCM output (primary input, hierarchical format)
- `Input/resource_directory.json` — auditor pool with skills and available hours
- `Input/rcm-schema.json` — UC7 JSON schema reference

## SAAF Pipeline Context

- **Upstream:** UC7 (RCM Builder) produces `Input/rcm_output.json`
- **Downstream:** UC9 (QA Review) consumes `control_id` → `control_objective` from the output

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Anthropic API access |
| `AUDIT_SCOPE_PERIOD` | `Jan-Dec 2025` | Injected into prompts and used in PERIOD_INCOMPLETE sufficiency check |

## Behavioral Guidelines

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### Think Before Coding

Before implementing: state assumptions explicitly, surface tradeoffs, ask when unclear.

### Simplicity First

Minimum code that solves the problem. No speculative features, no single-use abstractions, no error handling for impossible scenarios.

### Surgical Changes

Touch only what the request requires. Match existing style. Mention unrelated dead code but don't delete it. Remove only imports/variables that YOUR changes made unused.

### Goal-Driven Execution

Transform tasks into verifiable goals. For multi-step tasks, state a brief plan with success criteria before starting.
