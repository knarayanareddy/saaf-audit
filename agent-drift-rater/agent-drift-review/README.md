# Agent Drift Review

Published drift ratings for SAAF agents, produced by `tools/scripts/agent_drift_rater`. This
folder holds only committed, templated output — ratings, red flags, findings and advice. Raw
fetched code, excerpts and draft mandates stay local (gitignored under the tool's package).

## What a rating means

A rating is **design evidence from static review, not certification**. It describes how
susceptible an agent's *design* is to drift — acting outside its approved mandate without anyone
changing it — based on code and documentation at a pinned commit. It does not show how the agent
behaved at runtime. EU AI Act articles are used as a good-practice benchmark; most agents here
are unlikely to be high-risk systems under Annex III.

## Layout

- `reports/<date>/findings.json` — findings conforming to `outputs/schemas/finding-schema.json`.
- `reports/<date>/scorecard.md` — the ranked scorecard.
- `reports/<date>/dashboard.html` — a self-contained dashboard.

## How owners confirm a mandate

Each agent is rated against an approved *mandate profile* (purpose, hard rules, approval points).
Until an owner or reviewer confirms that profile, the rating is marked **provisional**. To
confirm: run `extract-mandates` for your unit, review the generated `mandates/<unit>.json`,
correct it, then run `confirm-mandate --unit <id> --reviewer "<name>"`. A `management_response`
field is available on every finding for right of reply.
