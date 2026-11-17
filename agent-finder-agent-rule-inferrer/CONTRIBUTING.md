# Contributing

## Adding an inferred rule

1. Create `rules/<ID>.json` (next free `RFIR` number) following
   `schema/inferred-rule.schema.json`.
2. Copy the `Quote` exactly as written in the source. Never paraphrase or
   soften it ("must" stays "must").
3. Give the source as `<path> (L<start>-<end>)`, prefixed with `owner/repo:`
   when the file lives in another repository.
4. Run `python tools/validate_rules.py` and `pytest -q`.

## Enforcing a rule

Follow the five-step method in the README. The guard and its tests go in the
repository that owns the governed code. For data-use rules, start from the
synthetic-data guard template in the
[Agent Rogue-Risk Assessor](https://github.com/SAAF-Project/agent-rogue-risk-assessor)
(`skills/agent-rogue-risk-assessor/assets/guards/synthetic_data_guard.py`).
Update the record's `Status` and `PR` as the rule moves along.

## Ground rules

- Never put real audit evidence, interviewee data or secrets in records,
  fixtures, tests or PR text.
- Changes go through a branch and a pull request, reviewed by someone other
  than the author.
- Delete the prose rule only after the enforcing PR is merged; leave a one-line
  pointer to the guard.
