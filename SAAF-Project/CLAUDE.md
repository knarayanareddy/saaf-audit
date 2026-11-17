# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

SAAF (Shared Audit Agents Framework) is a shared workspace for 45+ organizations building AI audit agents together. The repo holds reusable components organized around four pillars: **Prompts**, **Tools**, **Regulatory**, and **Outputs**. There is no application runtime — the repo is a content and scripting library.

## Python scripts

Scripts live in `tools/scripts/` and run standalone with Python 3.9+ (system Python on macOS). No package manager or build step is needed unless a `requirements.txt` is present.

```bash
# Run from the repo root (paths are relative to there)
python3 tools/scripts/scrape_hackathon_repos.py
python3 tools/scripts/analyze_overlaps.py
python3 tools/scripts/generate_recap.py
```

Scripts require `gh` CLI authenticated with `repo` + `read:org` scopes to access the SAAF-Project GitHub org.

## Hackathon recap pipeline

Three scripts in `tools/scripts/` form a sequential pipeline:

1. `scrape_hackathon_repos.py` — fetches all org repos via `gh` CLI → writes `hackathon-recap/repo_data.json` and per-repo files in `hackathon-recap/repo_data_raw/`
2. `analyze_overlaps.py` — keyword-classifies repos by audit domain and tech stack → writes `hackathon-recap/overlap_analysis.json`
3. `generate_recap.py` — produces `hackathon-recap/recap-session-1.md` from the two JSON files

To convert the Markdown to PDF (requires `pandoc` + `typst`):

```bash
pandoc "hackathon-recap/recap-session-1.md" \
  --output "hackathon-recap/recap-session-1.pdf" \
  --pdf-engine=typst \
  --table-of-contents --toc-depth=3
```

`repo_data.json`, `repo_data_raw/`, and `overlap_analysis.json` are gitignored (private repo data). Only the generated Markdown and PDF are committed.

## Coding conventions (from Copilot instructions)

- Python: PEP 8, type hints, `pathlib` over `os.path`, `logging` at INFO level
- Use `Optional[X]` from `typing` (not `X | None`) — codebase runs on Python 3.9
- SQL: explicit column names, no `SELECT *`, comment complex joins
- Credentials from environment variables only, never hardcoded
- Scripts write output files relative to their own location using `Path(__file__).parents[N]`

## Finding schema

All agent outputs should conform to `outputs/schemas/finding-schema.json`. Required fields: `id` (pattern `F-\d{2,4}`), `title`, `risk_rating` (High/Medium/Low/Informational), `observation`, `recommendation`.

## Prompt conventions

New audit-use-case prompts go in `prompts/audit-use-cases/` and must follow the template in `prompts/conventions/prompt-template.md`: metadata header (use case, applicable standards, intended AI tool), system context block, user prompt template with `[placeholder]` syntax, and notes on limitations.

## Agent guardrails

When configuring MCP servers or Claude Code tool permissions for audit agent work, follow `regulatory/guardrails/allowed-commands.md`: allowlist-only, no `rm`/`sudo`/`curl`/`wget`/`ssh`, no runtime `pip install`. Python scripts run only from `tools/scripts/`.

## Audit criteria & controls (per agent)

Every agent repo must carry an `AUDIT-CRITERIA.md` **next to its `README.md`**. The README says what the agent does and how to run it; `AUDIT-CRITERIA.md` says what the agent must be judged against as an auditee: control objectives mapped to frameworks, testable pass/fail acceptance criteria, a "good output / never do" list, and known coverage gaps. Copy and fill in `docs/conventions/audit-criteria-template.md`. This is the output of the **A2 — Audit Criteria & Controls** track; **A1** stress-tests verify against these criteria.

## Quality standards (the car wash)

Since Session 11 every agent repo and shared service goes through nine standards: `README.md`, `agent.yaml`, `AUDIT-CRITERIA.md`, `SECURITY.md`, `LICENSE` (MIT), tests, pinned dependencies, CI on pull requests and `CODEOWNERS`. The list, what each must contain, how it is checked and the three layers of control (always on, every pull request, every quarter) are in `docs/conventions/quality-standards.md`. The `harden-agent-repo` skill walks a repo through all nine. Use `docs/conventions/security-md-template.md` for `SECURITY.md`.

## Language

All content in this repository must be written in **English**. This applies to:
- Plan documents (`plans/`)
- Reference documents (`docs/reference/`)
- Transcriptions (`docs/transcriptions/`)
- Prompts (`prompts/`)
- Code comments and docstrings
- Commit messages and PR descriptions

Do not commit Dutch, French, German, or any other non-English content. If source material (e.g. Drive documents, slides) is in Dutch, translate it to English before committing.

## Git workflow

Branch naming: `your-name/feature-description`. PRs require at least one review. Never commit real audit evidence, personal data, or credentials — use synthetic or anonymized data.
