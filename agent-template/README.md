# [Agent name]

> Starter template for a SAAF agent. All nine quality standards are already in place. Replace every `[placeholder]`, delete this note, and the standards check on your pull request turns green.

## What it does

[Two or three sentences: the audit task this agent supports, for whom, and what it deliberately does not do.]

## Input and output

| | What | Format |
|---|---|---|
| Input | [for example: a user access list] | [CSV, columns ...] |
| Output | [for example: findings] | JSON that follows the SAAF finding schema (`id`, `title`, `risk_rating`, `observation`, `recommendation`) |

## Prerequisites

- Python 3.9 or newer.
- Keys come from environment variables, never from the code. [List the variable names, for example `ANTHROPIC_API_KEY`, or write "none: this agent makes no model calls".]

## Install and run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 src/agent.py samples/input.csv
```

The demo runs on the synthetic file in `samples/`. It needs no keys.

## Guardrails

[What the agent may and may not do. Keep it in line with the `mandate` block in `agent.yaml`.]

## Model and data residency

[Which model and provider the agent calls, and where the data goes. Or: "No model calls. All data stays on the machine that runs it."]

## Limitations and human review

[What the agent gets wrong or does not cover, and which step a human must sign off before the output is used.]

## Tests

```bash
python3 -m pytest
```

## Licence, contact and plan

- Licence: MIT, see `LICENSE`.
- Security: the [SAAF security policy](https://github.com/SAAF-Project/.github/blob/main/SECURITY.md) covers this repo. Put what is specific to this agent, such as its scope, under a "Security notes" heading in this README.
- Owner: see `CODEOWNERS`.
- LLM checks: `llm_checks.yaml` holds one check for every criterion tagged `[llm]` in `AUDIT-CRITERIA.md`, under the same number. The file explains the format.
- Plan: [link to the plan in SAAF-Project/plans].
