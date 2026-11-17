# Black Knight

*None shall pass without proof.*

A small, deterministic guard for audit tooling that stops a bad actor (or plain bad input) from getting a green tick
by staying silent. No LLM, no network, no runtime dependencies. The rule it enforces is called **No Silent Pass**:
the Python package is `no_silent_pass`, the commands are `black-knight` and `no-silent-pass` (same thing).

**Rule:** "nothing detected", "could not parse", "input ambiguous" and "check never ran" are
never a pass. They produce `NOT_ASSESSED`.

Built by team **Dungeon Dwellers** on the SAAF red team day, after finding the same
fail-open pattern in several audit agents. How it is judged: see [AUDIT-CRITERIA.md](AUDIT-CRITERIA.md).

## Verdicts and exit codes

| Verdict | Meaning | Exit code |
|---|---|---|
| `PASS` | At least one check ran, none failed, coverage is 100% (configurable), nothing recorded as unassessable | 0 |
| `FAIL` | An executed check found a violation | 1 |
| `NOT_ASSESSED` | Everything else, including empty input and zero checks | 2 |

## Use

```python
from no_silent_pass import Guard

with Guard("three-way-match") as g:
    for i, row in enumerate(rows, 1):
        item = f"row {i}"
        qty = g.require_unique(row, ("quantity", "qty", "quantity_billed"), "quantity", item)
        if qty is None:
            continue                      # reason recorded, row counted as skipped
        g.within("qty_vs_po", qty, po_qty, tol, item)   # rejects NaN/inf/ambiguous numbers
        g.mark_assessed(item)

g.claim("verified", requires=["qty_vs_po"])   # label only if that check really ran and passed
g.write("report.json")
```

```bash
black-knight gate report.json      # exit 0 / 1 / 2; a missing, malformed, inconsistent or stale report is 2
black-knight demo                  # fail-open vs fail-closed side by side
python -m no_silent_pass demo      # the same, without installing the command
```

### The gate does not trust a report's own verdict

A report is a claim by an earlier run. `gate` recomputes the verdict from the report's data and returns the
stricter of the two: a `PASS` with no check run, with coverage below the threshold, with reasons left over or with a
failed check is not a pass (a failed check makes it `FAIL`). A field it cannot verify counts against the report.

In CI, also tie the report to the run, so a report left over from a crashed run cannot stand in for today's:

```bash
export NO_SILENT_PASS_RUN_ID="$GITHUB_RUN_ID"      # the tool stamps it into the report; gate checks it
rm -f report.json                                  # belt and braces: start without an old report
python my_audit_tool.py --report report.json
black-knight gate report.json --max-age 3600       # refuse a report older than an hour, or without a timestamp
```

`--min-coverage` and `--min-checks` can make the gate stricter than the report's own thresholds, never laxer.
`--allow-not-assessed` only relaxes an honest "nothing was assessed": it never relaxes a `FAIL`, nor a report that is
inconsistent, stale or from another run.

## What it addresses

Each row is a pattern found on the red team day, replayed as a regression test in
`tests/test_regressions.py`. The adapters re-implement the *shape* of the pattern; they are
illustrations, not patches to anyone's repository. The tools the patterns came from are left
out on purpose: the patterns are what this guard addresses, not the teams.

| Kind of tool | Fail-open behaviour found | Guard behaviour |
|---|---|---|
| invoice matching | First matching column alias wins; decoy columns hide a mismatch | Disagreeing alias columns: `NOT_ASSESSED` |
| invoice matching | `1,234.56` parsed as 1.23456, and `1,000` as 1.0 | Ambiguous numbers: `NOT_ASSESSED` |
| invoice matching | NaN passes `abs(a-b) > tol`, so nothing is flagged | Non-finite numbers: `NOT_ASSESSED` |
| invoice matching | Invoice without goods receipt is only a warning | Executed check fails: `FAIL` |
| readiness scanner | No detected signals (or nothing could be scanned) gives verdict "yes" | `not assessed` |
| manifest collector | Fetch error falls back to seed data, build stays green | Visible skip, `NOT_ASSESSED` |

`Guard.claim()` covers a related pattern: a label such as "verified" is only granted when the check it depends on really ran and passed.

## Limits

* It cannot detect that an upstream check is wrong, only that it did not run, did not cover
  the input, or ran on untrustworthy data.
* The gate is not a signature. It catches empty, inconsistent, stale and foreign reports; someone who forges a
  complete, consistent, fresh report with the right run id is out of scope.
* Adapters are examples. To protect a real tool, wire its checks through `Guard`.
* Not yet packaged as a GitHub Action; use the CLI in a CI step.

## Judged against

[AUDIT-CRITERIA.md](AUDIT-CRITERIA.md) lists the control objectives, the testable acceptance criteria and the known gaps of this tool, per the SAAF convention.

## Security notes

Report a weakness as the [SAAF security policy](https://github.com/SAAF-Project/.github/blob/main/SECURITY.md) describes, never in a public issue. What is specific to this repository:

- A guard that returns PASS when it should return FAIL or NOT_ASSESSED is treated as a security bug.
- The library has no runtime dependencies, makes no network calls and executes no external input.

## Develop

```bash
python -m pip install pytest
python -m pip install -e .   # optional: installs the black-knight command
python -m pytest
```
