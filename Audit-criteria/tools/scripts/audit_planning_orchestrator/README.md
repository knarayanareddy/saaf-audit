# Audit Planning Orchestrator

An LLM **"command" agent** that runs and commands the Mollie audit-planning
sub-agents as tools:

```
UC7 RCM Builder  ->  UC8 Work Program  ->  UC9 Quality & Resource Guard (Go / No-Go)
```

The orchestrator (Claude, `claude-opus-5`) decides which sub-agent to call and
when. This loop enforces the parts that must not be left to chance:

- **Schema gates** — every hand-off is validated ([`schemas.py`](schemas.py))
  before it can reach the next stage. Bad output is never passed downstream.
- **Bounded No-Go recovery** — when UC9 returns *No-Go*, the orchestrator reads
  the gap and re-runs UC7 (risk/scoping gap) or UC8 (procedure/resourcing gap),
  up to `MAX_RETRIES` cycles, then escalates to a human.
- **Audit trail** — each run writes `runs/<run_id>/` with the JSON hand-off
  artifacts, an append-only `log.jsonl` (IIA 2340 supervision trail), and a
  combined `summary.json`.

Design rationale and the SAAF 4-pillar mapping:
[`plans/hackathon-4/p-papen-audit-planning-orchestrator.md`](../../../plans/hackathon-4/p-papen-audit-planning-orchestrator.md).

## Run it

All commands run from the **repo root**.

### Offline — no API key, proves the wiring (start here)

```bash
python -m tools.scripts.audit_planning_orchestrator.orchestrator --simulate
```

A deterministic controller drives the same order, gates and recovery loop as the
LLM, using mock sub-agents. The sample bundle seeds a scoping gap (the "Payment"
sub-process has no risk), so you see UC9 return **No-Go**, the orchestrator
re-run UC7 + UC8, and UC9 then return **Go** — all recorded in the run log.

### Real orchestrator, cheap sub-agents

```bash
export ANTHROPIC_API_KEY=sk-ant-...          # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
python -m tools.scripts.audit_planning_orchestrator.orchestrator --mock-subagents
```

The real Claude orchestrator makes the tool decisions; UC7/UC8/UC9 return
fixtures so you spend tokens only on the orchestration reasoning.

### Full run

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m tools.scripts.audit_planning_orchestrator.orchestrator \
    --input tools/scripts/audit_planning_orchestrator/sample_data/accounts_payable.json
```

Every stage calls Claude (`claude-opus-5` for UC7/UC8 synthesis,
`claude-sonnet-5` for UC9 validation).

## Inputs

`--input` points at a risk-input bundle (see
[`sample_data/accounts_payable.json`](sample_data/accounts_payable.json)):
`engagement`, `process_map` (sub-processes + objectives, from UC1–UC6),
`risks` (tagged by source), `auditor_directory`, and `available_hours`.

## Files

| File | Role |
|---|---|
| `orchestrator.py` | Agentic loop, tool dispatch, schema gates, retry budget, CLI |
| `sub_agents.py` | UC7/UC8/UC9 tool wrappers (one Claude call each) + offline fixtures |
| `prompts.py` | System prompts for the orchestrator and the three sub-agents |
| `schemas.py` | Dependency-free structural validators (the quality gate) |
| `run_logger.py` | Per-run artifacts + `log.jsonl` audit trail |
| `criteria_checks.py` | Executable checks behind the repo-root `AUDIT-CRITERIA.md` |
| `sample_data/` | Synthetic Accounts Payable input bundle |

## Notes

- `--simulate` uses only the Python standard library. The `anthropic` SDK
  (see `requirements.txt`) is needed only for the API-backed paths.
- `runs/` is gitignored — it holds generated planning output.
- No real audit evidence or personal data: inputs are synthetic planning data,
  API keys come from the environment only.
