# `agents/data/`

Input files the agents read: fixtures, sample fieldwork documents, reference
tables, checklists, and any loader helpers around them.

## What to add

A subfolder per agent, named after the agent slug, plus `shared/` for input used
by more than one agent:

```
data/
  shared/               # reference data several agents use
  <agent_name>/         # input files for that one agent
    sample_report.md
    checklist.json
  loaders.py            # optional helpers to read the files above
```

## Conventions

- Prefer plain, diffable formats: `.md`, `.json`, `.csv`, `.yaml`.
- These are **inputs**, not outputs. Nothing a run produces gets written back
  here — send run artifacts somewhere gitignored.
- **No real client or engagement data, no personal data, no credentials.**
  Anonymize before committing; if a file cannot be anonymized, keep it out of
  the repo and load it from a local path instead.
- Keep files small enough to review. If a fixture is large, trim it to the part
  that actually exercises the agent.
- Agents read these through a path relative to this package, not a hardcoded
  absolute path — put shared reading logic in `loaders.py`.
