# Agent finder Agent: rule inferrer

**Quotations are the new code.**

AI agents, and the people who run them, write their intent as prose: in code
comments, docs, plans and prompts. That intent can be captured and quoted back
with file and line. But a sentence has no leverage on its own: nothing stops the
next run, or the next person, from ignoring it.

This repository holds the **Agent finder Agent**: a method and a Claude Code
agent that find rules stated only in prose and turn them into checks that run.

> Less prose, more code. It's called vibecoding, not vibe prosing.

## The method

| Step | What happens | Output |
|---|---|---|
| 1. Find the agents | Given a repo, identify its agents, prompts, tools and calls to outside AI services | Agent inventory |
| 2. Extract prose rules | Quote every rule that exists only as text, with file and line | A record in `rules/` |
| 3. Triage, open a PR | Add a guard in code at the point the rule governs, keeping its original intent | Pull request |
| 4. Test durability | Prove the guard blocks the forbidden action even when the input says it's allowed | Tests, scanner re-score |
| 5. Merge, delete the prose | After independent review, the code and its test become the rule | Prose replaced by a pointer to the guard |

## Rule records

Each inferred rule is one JSON file in [`rules/`](rules/), named after its id and
checked against [`schema/inferred-rule.schema.json`](schema/inferred-rule.schema.json):

```json
{
  "Inferred_Rule": "RFIR042",
  "Quote": "no real audit evidence or interviewee data may be used.",
  "Tool": "Read",
  "Parameters": "SAAF-Project/Audit-criteria:plans/hackathon-4/p-papen-uc7-voice-rcm-walkthrough.md (L197-198)",
  "Outcome": "Operator instruction for the voice component (audio goes to ElevenLabs). Not enforced in code. …",
  "Status": "pr-open",
  "PR": "https://github.com/SAAF-Project/agent-rogue-risk-assessor/pull/3"
}
```

`Status` follows the method: `prose-only` → `pr-open` → `enforced` → `prose-deleted`.

Validate (Python ≥ 3.9, standard library only):

```bash
python tools/validate_rules.py
```

## Using the agent

Copy [`.claude/agents/agent-finder-agent.md`](.claude/agents/agent-finder-agent.md)
into the target repo's `.claude/agents/`, then ask Claude Code:
*"Use the agent-finder-agent on this repo"*, or hand it a rule record.

It builds on the [Agent Rogue-Risk Assessor](https://github.com/SAAF-Project/agent-rogue-risk-assessor):
its scanner flags prose-only rules (red flag RF3), and its
`assets/guards/synthetic_data_guard.py` is the template for data-use rules.

## First case: RFIR042

The UC7 voice walkthrough sends audio to ElevenLabs, and its plan says no real
audit evidence or interviewee data may be used. Nothing in code checked that.
[agent-rogue-risk-assessor#3](https://github.com/SAAF-Project/agent-rogue-risk-assessor/pull/3)
adds a reusable synthetic-data guard with adversarial tests and teaches the
scanner to find rules like this one. Still open: wiring the voice script to the
guard, then deleting the prose.

## Repository layout

```
.claude/agents/   the Agent finder Agent definition
rules/            one JSON record per inferred rule
schema/           JSON schema for rule records
tools/            validator
tests/            pytest suite
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
