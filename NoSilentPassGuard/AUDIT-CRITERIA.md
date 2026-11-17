# AUDIT-CRITERIA.md: Black Knight

## Metadata

| Field | Value |
|---|---|
| **Agent** | Black Knight (package `no_silent_pass`): a deterministic guard library and CI gate, not an AI agent; it makes no model calls |
| **Repository** | https://github.com/SAAF-Project/NoSilentPassGuard |
| **Maintainer(s)** | Dungeon Dwellers (SAAF red team day team) |
| **Last reviewed** | 2026-11-10 |
| **Status** | Reviewed: every criterion below is covered by a unit test that passes (see section 6). Not yet stress-tested by an A1 team. |

**Branch note:** the repository has a single branch, `main`, and this document describes it.

## 1. What the agent does

Black Knight wraps the checks of an audit tool and turns what happened into one of three verdicts. `PASS` has to be earned: at least one check ran, none failed, the coverage of the input items meets the threshold, and nothing was recorded as unassessable. "Nothing detected", "could not parse", "input ambiguous" and "check never ran" give `NOT_ASSESSED`. The `gate` command turns a guard report into an exit code for CI, and does not trust the report's own verdict: it recomputes it from the report's data and checks that the report belongs to the run being gated. It has no LLM, no network access and no runtime dependencies, so the AI frameworks (EU AI Act, OWASP LLM) do not apply.

## 2. Control objectives & framework mapping (≥3)

The objectives describe the tool's own trustworthy behaviour, not the audits it is used in.

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| CO-1 — Fail closed: the absence of evidence is never reported as a pass. | IIA Standard 2310 (identifying information) and 2320 (analysis and evaluation); COSO 2013 principle 13 (relevant, quality information) | The tool exists to stop "nothing detected" from reading as "no problem". |
| CO-2 — Input integrity: ambiguous, unreadable or non-finite data is refused, not guessed. | IIA Standard 2310; COSO 2013 principle 13 | A wrong guess (`1,234.56` read as 1.23456, NaN passing a comparison) produces a confident wrong result. |
| CO-3 — Report integrity: a report is complete, consistent with its own data, and tied to the run that produced it, so a gate cannot be satisfied by an empty, contradictory or stale report. | IIA Standard 2330 (documenting information); ISO 27001 Annex A.8.15 (logging) | The gate is the control a pipeline relies on; a gate that believes any file saying "PASS" is not a control. |
| CO-4 — Determinism and data protection: no network, no model, no execution of input, and no data leaves the machine. | GDPR Art. 5(1)(f) (integrity and confidentiality); SAAF `allowed-commands.md` (no network egress, no runtime installs) | Audit input can be sensitive; the tool must be safe to run on it. |

## 3. Acceptance criteria (testable, pass/fail)

**CO-1**
- Given a guard with no input and no check, the verdict is `NOT_ASSESSED`.
- Given one item and no check, the verdict is `NOT_ASSESSED`; given one passing check and full coverage it is `PASS`.
- Given a skipped item, the verdict is `NOT_ASSESSED`, unless the coverage threshold was relaxed explicitly.
- Given a check that returns anything but a boolean (for example `None`), the verdict is `NOT_ASSESSED`.
- Given an executed check that fails, the verdict is `FAIL`, even when other items were not assessed.
- Given an unhandled exception inside the guard's `with` block, the verdict is `NOT_ASSESSED` and the exception is not swallowed.
- Given a label (`claim`) that requires a check that never ran, the label is refused and the verdict is `NOT_ASSESSED`; given a check that failed, the label is refused.

**CO-2**
- Given `1,000` or `12,345` without a stated locale, parsing raises `AmbiguousNumber`; with `decimal="."` or `","` it is read as stated.
- Given `1,234.56` and `1.234,56`, both are read as 1234.56.
- Given `nan`, `inf`, `-inf`, `Infinity` (text or float), parsing raises `NonFiniteNumber`.
- Given an empty value, `None`, a boolean or text such as `12abc`, parsing raises `NumberError`.
- Given a row whose alias columns disagree (`quantity` 10, `quantity_billed` 13), the field is refused and the row is counted as skipped.
- Given a column that holds `None` or only spaces, it is treated as empty, not as the text "None".
- Given a negative tolerance, the comparison is not made and the item is `NOT_ASSESSED`.

**CO-3**
- Given a report `{"verdict": "PASS"}` and nothing else, `gate` exits 2.
- Given a "PASS" with no checks run, coverage below the threshold, or reasons left over, `gate` exits 2.
- Given a "PASS" that lists a failed check, `gate` exits 1.
- Given a field the gate needs but that is missing, not a count, or not a finite number in range (for example `coverage` = NaN), the report is not a pass.
- Given `--min-coverage` or `--min-checks`, the gate can be stricter than the report's own thresholds, never laxer.
- Given `--max-age`, a report that is older, undated, dated without a time zone, or dated in the future is refused.
- Given a run id (`--run-id` or `NO_SILENT_PASS_RUN_ID`), a report from another run, or without one, is refused.
- Given `--allow-not-assessed`, an honest `NOT_ASSESSED` exits 0, but a `FAIL`, an inconsistent report, a stale report and a foreign report do not.
- Given a missing, unreadable or malformed report file, `gate` exits 2.
- Given a report written by the guard, the file is replaced in one step and no temporary file is left behind.

**CO-4**
- Given the source of the package, it imports only allow-listed standard-library modules and no network or process module, and declares no runtime dependency.
- Given the source of the package, it never calls `eval`, `exec`, `compile` or `__import__`, so no input is executed.

## 4. Good output / never do

| A correct output MUST contain | The tool must NEVER |
|---|---|
| ✓ A verdict that follows from the recorded checks, coverage and reasons | ✕ Report `PASS` when nothing was assessed, a check did not run, or an item was skipped |
| ✓ Every reason a result is not a pass (`not_assessed_reasons`, `items_skipped`) | ✕ Guess an ambiguous number, or let NaN or infinity pass a comparison |
| ✓ In the report: `run_id`, `generated_at`, thresholds, counts, coverage | ✕ Trust a report's own `verdict` without checking it against the report's data |
| ✓ A non-zero exit code for everything that is not `PASS` (1 for `FAIL`, 2 for `NOT_ASSESSED`) | ✕ Turn a missing, malformed, stale or foreign report into success |
| ✓ The exception, when the guarded code crashes | ✕ Swallow an exception, or relax a `FAIL` with `--allow-not-assessed` |
| ✓ Only synthetic or anonymised data in the repository | ✕ Make a network call, run a command from input, or hard-code a credential |

## 5. Coverage gaps

- **Not tamper-proof.** The gate catches empty, inconsistent, stale and foreign reports. A complete, consistent, fresh report forged with the right run id passes; there is no signature.
- **Stale-report protection is opt-in.** Without `--max-age` or a run id, an old but internally consistent report can pass. CI has to set one of them (the README shows how).
- **It cannot tell that an upstream check is wrong,** only that it did not run, did not cover the input, or ran on untrustworthy data.
- **Amounts only.** Parsing covers amounts; dates, currencies and units are not handled.
- **Locale has to be stated** where a number such as `1,000` is ambiguous; otherwise the item is not assessed.
- **The adapters are illustrations,** not patches: a real tool has to wire its checks through the guard.
- **Not packaged as a GitHub Action yet;** use the CLI in a CI step.
- **No concurrency support:** one guard is not meant to be shared between threads.

## 6. Status / validation

All of these ran on 2026-11-10: `python -m pytest`, 116 passed (Python 3.12; the code uses only syntax valid on 3.9).

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-1 no input, no check, skipped item, non-boolean check | ☑ | `tests/test_guard.py`: nothing assessed, pass needs a check and coverage, skipped item, non-bool outcome |
| CO-1 failed check dominates; exception recorded; labels | ☑ | `tests/test_guard.py`: violation dominates, exception recorded and not swallowed, claim requires checks that ran |
| CO-2 number parsing | ☑ | `tests/test_numbers.py` (ambiguous, locale, non-finite, garbage) |
| CO-2 decoy columns, `None` columns, tolerance | ☑ | `tests/test_guard.py`, `tests/test_regressions.py` |
| CO-3 report checked against its own data | ☑ | `tests/test_gate.py` (bare PASS, PASS without checks, PASS with a failed check, missing and malformed fields) |
| CO-3 stale or foreign report | ☑ | `tests/test_gate.py` (max age, timestamps, run id, crashed-run case) |
| CO-3 `--allow-not-assessed` limits; unreadable report; atomic write | ☑ | `tests/test_gate.py`, `tests/test_cli.py` |
| CO-4 stdlib only, no network, no execution of input | ☑ | `tests/test_boundaries.py`: imports must be on an allow list, no network or process modules, no `eval`/`exec`, no runtime dependencies |
| All criteria stress-tested by an independent team | ☐ | Open: A1 stress-test |

Next step: offer the criteria to an A1 team for a stress test.
