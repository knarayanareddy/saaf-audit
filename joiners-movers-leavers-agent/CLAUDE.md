# CLAUDE.md

Guidance for Claude Code in this repository.

## What this is

A SAAF audit agent: deterministic joiner-mover-leaver (JML) access tests over HR, directory, entitlement and Jira exports, plus a Claude Code step that drafts findings from pseudonymised exceptions. See `README.md` (what and how) and `AUDIT-CRITERIA.md` (what it is judged against).

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                                  # tests (must pass before a PR)
.venv/bin/python -m engine.cli [--sources sources.yaml] [--draft] [--lang en|nl]
.venv/bin/python run.py [--sources sources.yaml] [--lang nl]   # web UI on 127.0.0.1:8765
.venv/bin/python tools/generate_sample_data.py                 # regenerate synthetic data
.venv/bin/python -m ai.claude_runner --prepare --lang en       # refresh prepared fallback (also nl)
```

If you regenerate the sample data, the fingerprint changes: refresh both prepared results and run the tests.

## Rules when acting as the JML agent (skill `/jml-audit`)

- Read source exports only through the engine. Never edit files in `sample_data/` or the user's exports.
- Read `runs/<stamp>/model_input.json` (pseudonymised). Do not read `review_local.json` or the source exports into the conversation: they contain names.
- Cite only identifiers that exist in the input (EX-.., ticket ids, USER-NNN, file:line). Findings follow `schemas/finding-schema.json`, `status: Open`, `ai_assisted: true`.
- Never present findings as final. The auditor signs off.
- Commands follow SAAF-Project `regulatory/guardrails/allowed-commands.md`: no `rm`, `sudo`, `curl`, `wget`, `ssh`, no runtime `pip install`.

## Conventions

- Python 3.9 compatible (macOS system Python): `from __future__ import annotations`, `Optional[X]`, no `X | None` at runtime, no `match`.
- PEP 8, type hints, `pathlib`, `logging` at INFO, paths from `Path(__file__).parents[N]`.
- All content in English. Dutch only in `web/i18n/nl.json`; keep its keys identical to `en.json` (a test checks this).
- UI follows the SAAF Light style (TAG x SAAF design system): `--sl-*` tokens, Geist, no emoji, no em dashes, no spinners (the loader is filling squares), human glyphs for people and robot glyphs for agents.
- `engine/access_review.py` is the Track 2 engine by Bart van den Broek. Keep changes minimal and list them in its header.
- Synthetic data only. Never commit real exports, personal data or credentials.
- Branch `your-name/feature-description`, reference an issue in each commit, PR with at least one review.
