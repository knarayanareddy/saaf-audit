# Agent Drift Rater

Static design review that rates each AI agent in the **SAAF-Project** GitHub org on its
susceptibility to **drift** — an agent acting outside its approved mandate without anyone
changing that mandate (from the "Drift Watch" talk, Agents Gone Rogue, Amsterdam, 6 Oct 2026).

Results are **design evidence, not certification**: they describe design risk from code and
documentation at a pinned commit, not runtime behaviour.

> This is a standalone copy of the tool that also lives in the SAAF monorepo under
> `tools/scripts/agent_drift_rater/`. The internal layout is kept identical so the module runs
> the same way here.

## Quick start

Requires Python 3.9+ and (for org runs) the `gh` CLI authenticated with `repo` + `read:org`.

```bash
# Offline self-test against synthetic fixtures (no gh, no API key):
python -m tools.scripts.agent_drift_rater.cli selftest

# Rate the fixtures end to end (deterministic + mock judge):
python -m tools.scripts.agent_drift_rater.cli rate --simulate

# Rate a single local repository, deterministic only:
python -m tools.scripts.agent_drift_rater.cli rate --path path/to/repo --no-llm

# Rate the whole org (deterministic — no code sent to any API):
python -m tools.scripts.agent_drift_rater.cli rate --no-llm
```

The optional Claude pass (`anthropic` SDK, `ANTHROPIC_API_KEY`) runs by default; `--no-llm`
disables it. `--simulate` and `--no-llm` need only the standard library.

## Two-stage mandate flow

Drift is measured against the agent's approved mandate, so confirm it before rating:

```bash
python -m tools.scripts.agent_drift_rater.cli extract-mandates --repo <name>
# review and edit mandates/<unit>.json, then:
python -m tools.scripts.agent_drift_rater.cli confirm-mandate --unit <name> --reviewer "Your Name"
python -m tools.scripts.agent_drift_rater.cli rate --repo <name>
python -m tools.scripts.agent_drift_rater.cli report --run <run_id>
python -m tools.scripts.agent_drift_rater.cli publish --run <run_id> --dry-run
```

An unconfirmed mandate makes the rating **provisional**; `publish` refuses provisional units
unless `--allow-provisional` is given.

## What it measures

- **Drivers** D1 proxy pressure · D2 self-editing · D3 context loss · D4 untrusted input · D5 permission creep.
- **Controls** C1 hard rules in code · C2 versioning · C3 independent review · C4 oversight & rollback · C5 replayable log.
- **Red flags** RF1–RF6 from the talk's auditor slide.
- Residual = inherent (drivers) × control strength, with red-flag floors, conditioned on whether the agent takes actions.

The `report` command also writes an **interactive dashboard**: a reviewer approves a suggestion,
which becomes a fix request for the repo owner, who records *Will fix* / *Won't fix*.

## Layout

| Path | What |
|---|---|
| `tools/scripts/agent_drift_rater/` | The tool (run as `python -m tools.scripts.agent_drift_rater.cli`). |
| `prompts/audit-use-cases/agent-drift-rater.md` | System prompts (rating judge + mandate extraction). |
| `regulatory/control-mappings/agent-drift-red-flags.md` | RF/C ↔ OWASP LLM 2025 ↔ EU AI Act ↔ SAAF guardrails. |
| `outputs/schemas/finding-schema.json` | Finding schema the output conforms to. |
| `outputs/examples/` | Example findings, scorecard and dashboard (from synthetic fixtures). |
| `plans/hackathon-4/p-papen-agent-drift-rater.md` | The plan document. |

## Privacy

`cache/`, `runs/` and `mandates/` are gitignored — fetched private code, excerpts and draft
mandates stay local. Committed outputs cite `path#line` and the detected signal only, never
verbatim code (enforced by a leak check on `publish`).

## Frameworks

Drift Watch red flags & controls · OWASP Top 10 for LLM Applications 2025 · EU AI Act
(Art. 9, 11, 12, 14, 15 — as a good-practice benchmark) · SAAF guardrails.
