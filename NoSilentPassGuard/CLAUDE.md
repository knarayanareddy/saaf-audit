# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Black Knight** (Python package `no_silent_pass`) is a small, deterministic guard for audit tooling. Its rule, called **No Silent Pass**: "nothing detected", "could not parse", "input ambiguous" and "check never ran" are never a pass. They give `NOT_ASSESSED`. It is not an AI agent: no LLM, no network, no runtime dependencies, Python 3.9+. It lives in the SAAF-Project org (`SAAF-Project/NoSilentPassGuard`) and came out of the SAAF red team day, after the same fail-open pattern was found in several audit agents.

Names: *Black Knight* is the guard, *No Silent Pass* is the rule, `no_silent_pass` is the package, and `black-knight` and `no-silent-pass` are the same command.

## Commands

```bash
python -m pip install pytest                 # only dev dependency
python -m pip install -e .                   # optional: installs the black-knight command
python -m pytest                             # all tests (tests/ via pyproject; pythonpath = src)
python -m pytest tests/test_gate.py -k stale # one area

black-knight demo                            # fail-open vs fail-closed side by side
python -m no_silent_pass demo                # the same without installing the command
black-knight gate report.json                # exit 0 PASS / 1 FAIL / 2 NOT_ASSESSED
black-knight gate report.json --max-age 3600 --run-id "$GITHUB_RUN_ID"
```

`gate` options: `--max-age SECONDS`, `--run-id` (default `$NO_SILENT_PASS_RUN_ID`), `--min-coverage`, `--min-checks` (stricter than the report, never laxer), `--allow-not-assessed` (relaxes only an honest "nothing assessed").

## Architecture (`src/no_silent_pass/`)

- `guard.py`: `Verdict` and `Guard`. A guard keeps a ledger of items (assessed or skipped), the checks that ran and the reasons a result cannot be trusted. Entry points: `mark_assessed`, `skip`, `not_assessed`, `check` (needs a real bool), `within` (tolerance check on finite numbers), `require_present`, `require_unique` (alias columns that disagree are refused), `require_finite`, `claim` (a label such as "verified" only if the checks behind it ran and passed). `verdict()`: any failed check is `FAIL`; else any reason is `NOT_ASSESSED`; else `PASS`. `report()` is the JSON report (schema_version 1, run_id, generated_at, thresholds, counts, reasons). `write()` replaces the file in one step.
- `numbers.py`: `parse_amount`. Ambiguous (`1,000` without a locale) or non-finite values raise `AmbiguousNumber` or `NonFiniteNumber`; it never guesses.
- `gate.py`: `assess_report`. Does not trust a report's own `verdict`: it recomputes it from the report's data, takes the stricter of the two, and refuses a report that is incomplete, inconsistent, too old or from another run. Returns `(verdict, reasons, problems)`; `problems` mean the report itself cannot be trusted and are never relaxed by `--allow-not-assessed`.
- `cli.py`: `gate` and `demo`. Exit codes 0, 1, 2. An unreadable, malformed or untrustworthy report is 2.
- `adapters/`: three illustrations (invoice matching, readiness scanner, manifest collector) showing how a fail-open pattern is rewritten with the guard. They are examples to copy from, not patches to anyone's repository.
- `tests/`: `test_guard.py`, `test_numbers.py`, `test_gate.py`, `test_cli.py`, `test_regressions.py` (replays the findings), `test_boundaries.py` (stdlib only, no network, nothing executed).

## Rules that must keep holding

- **PASS has to be earned.** A change that can turn an input that was `NOT_ASSESSED` or `FAIL` into `PASS` needs a test that shows why that is right. When in doubt, fail closed.
- `FAIL` dominates `NOT_ASSESSED`. `PASS` needs at least `min_checks` checks run, coverage at or above `min_coverage`, no failed check and no recorded reason.
- Never guess a number. Ambiguity is resolved by an explicit locale (`decimal`), not by a heuristic.
- `Guard.__exit__` records an exception as `NOT_ASSESSED` and never swallows it.
- The gate must not become easier to satisfy: no new way for a report to pass without data behind it. It is not a signature (a complete, consistent, fresh, forged report is out of scope; say so rather than imply otherwise).

## Conventions

- Python 3.9+: use `Optional[X]` from `typing`, not `X | None`; type hints; `from __future__ import annotations` is already used. Standard library only.
- `tests/test_boundaries.py` enforces an import allow-list, no network or process modules and no `eval`/`exec`/`compile`/`__import__`. Adding an import means adding it to `ALLOWED` on purpose.
- The report shape is `schema_version` 1. Add fields; do not remove or rename them without bumping the version and updating `gate.py`.
- Keep `README.md` (findings table, usage), `AUDIT-CRITERIA.md` (acceptance criteria and the "N passed" line in section 6) and the tests in sync. SAAF requires `AUDIT-CRITERIA.md` next to the README (template: `docs/conventions/audit-criteria-template.md` in SAAF-Project).
- All content in English: code, comments, docs, commit messages. Synthetic data only: no real audit evidence, personal data or credentials in tests or examples.
- The README names kinds of tools, not other teams' repositories. Keep it that way unless the findings have been reported and fixed.

## Git workflow

SAAF convention: branch `your-name/feature-description`, pull request to `main`, at least one review. Org members are read-only in the SAAF-Project org, so work from a fork. Run `python -m pytest` before every push.
