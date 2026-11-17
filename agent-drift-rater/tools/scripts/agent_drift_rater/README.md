# Agent Drift Rater

Static design review that rates each AI agent in the SAAF-Project org on its susceptibility to
**drift** — acting outside its approved mandate without anyone changing that mandate (from the
"Drift Watch" talk, Agents Gone Rogue, Amsterdam, 6 Oct 2026).

Results are **design evidence, not certification**: they describe design risk from code and
docs at a pinned commit, not runtime behaviour.

## Quick start

```bash
# Offline self-test against synthetic fixtures (no gh, no API key):
python -m tools.scripts.agent_drift_rater.cli selftest

# Rate the fixtures end to end (deterministic + mock judge):
python -m tools.scripts.agent_drift_rater.cli rate --simulate

# Rate a single local repository, deterministic only:
python -m tools.scripts.agent_drift_rater.cli rate --path path/to/repo --no-llm

# Rate specific org repos (needs `gh` authenticated with repo + read:org):
python -m tools.scripts.agent_drift_rater.cli rate --repo APM-Writer --repo python-mcp-framework
```

## Two-stage mandate flow

Drift is defined against the agent's mandate, so rate against a reviewed mandate:

```bash
python -m tools.scripts.agent_drift_rater.cli extract-mandates --repo APM-Writer   # writes mandates/<unit>.json
# review and edit the mandate file, then:
python -m tools.scripts.agent_drift_rater.cli confirm-mandate --unit APM-Writer --reviewer "P. Papen"
python -m tools.scripts.agent_drift_rater.cli rate --repo APM-Writer
python -m tools.scripts.agent_drift_rater.cli publish --run <run_id> --dry-run
```

A unit with an unconfirmed mandate is rated **provisional**; `publish` refuses provisional units
unless `--allow-provisional` is given.

## Approved fixes → GitHub issues

Suggestions the reviewer approves in the dashboard can be filed as issues in each analyzed repo.
Export the approved ids from the dashboard ("Copy IDs for issues") into a JSON file, then:

```bash
# Dry run — prints the issues it would create, posts nothing:
python -m tools.scripts.agent_drift_rater.cli create-issues --run <run_id> --approved approved.json

# Create them for real — requires an explicit per-repo whitelist (safety):
python -m tools.scripts.agent_drift_rater.cli create-issues --run <run_id> --approved approved.json \
    --yes --repo <repo-name>
```

Issue bodies carry the agent, its rating, the raised red flags, and the fix (why/how) — citing
file paths and line numbers only, never code. Existing issues with the same title are skipped.

## What it measures

- **Drivers** D1 proxy pressure · D2 self-editing · D3 context loss · D4 untrusted input · D5 permission creep.
- **Controls** C1 hard rules in code · C2 versioning · C3 independent review · C4 oversight/rollback · C5 replayable log.
- **Red flags** RF1–RF6 from the talk's auditor slide.
- Residual = inherent (drivers) × control strength, with red-flag floors, conditioned on whether the agent takes actions.

See `regulatory/control-mappings/agent-drift-red-flags.md` for the framework mapping and
`prompts/audit-use-cases/agent-drift-rater.md` for the system prompts.

## Privacy

`cache/`, `runs/` and `mandates/` are gitignored — fetched private code, excerpts and draft
mandates stay local. Only templated ratings and findings are published (via `publish`, after a
leak check), and they cite `path#line`, never verbatim code.
