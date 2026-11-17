# Red Pencil (the scanner in this repo)

**A CI check that marks unsafe output and prompt-handling patterns in SAAF agent repos, and fails the build on them.**

Auditors mark workpapers with a red pencil. Red Pencil does the same for agent code:
it reads a repo, marks the lines where a document could act as an instruction, a
secret could reach a page, or model output could run as HTML, and stops the merge.

Built at the SAAF Security Challenge, Mollie Amsterdam, 10 November 2026.

## What it stops

Every rule comes from a real weakness found in a SAAF repo on 10 November 2026.

| Rule | Severity | What it catches | Seen in |
|------|----------|-----------------|---------|
| RP001 `jinja-autoescape-off` | High | Jinja `Template` or `Environment` without autoescaping, so model output renders as live HTML | Finding-analysis `report/report_generator.py:16` |
| RP002 `secret-sent-to-page` | High | A secret from the environment passed to `render_template`, `jsonify` or a response | Finding-analysis `app.py:34` |
| RP003 `secret-in-template` | High | A template printing a secret-looking variable, even into a password field | Finding-analysis `templates/index.html:157` |
| RP004 `fixed-delimiter-wrapper` | High | Untrusted text wrapped in a fixed tag that the text itself can close | Executive-Summary-Writer `scripts/material.py:211` (and its frontend copy) |
| RP005 `unbounded-join-into-prompt` | Medium | Documents glued with newlines into a prompt with no boundary at all | Compliance-Audit-Agent `scripts/build_prompt.py:389, 597` |
| RP006 `debug-server` | Medium | `app.run(debug=True)` or `app.debug = True` | Finding-analysis `app.py:218`, OWASP-top-10-LLM-assessment (2 apps) |
| RP007 `dev-reload` | Low | `uvicorn.run(reload=True)` in a run script | three-way-match-audit `webapp/run.py:9` |
| RP008 `path-check-without-resolve` | Medium | A path containment check on `.parent` without `resolve()` | three-way-match-audit `webapp/app/main.py:151` |

These map to three of the four attack types queued for the challenge:
prompt injection hidden in evidence documents (RP004, RP005), leaking secrets
through outputs (RP001, RP002, RP003), and unsafe defaults an attacker can use
(RP006, RP007, RP008).

**Result on 9 public SAAF repos:** 12 findings in 5 repos (5 high, 6 medium, 1 low),
in under a second, with no false alarms in the ones checked by hand.

## How to run it

Requirements: Python 3.10 or newer. Nothing to install: standard library only.

```bash
cd red-pencil
python -m red_pencil path/to/some-saaf-agent
```

Useful options:

```bash
python -m red_pencil --list-rules                        # show the rules
python -m red_pencil REPO --fail-on medium               # stricter gate
python -m red_pencil REPO --format json                  # machine-readable
python -m red_pencil REPO --format saaf-csv --team "My team" --output findings.csv
python -m red_pencil REPO --exclude "tests/*"            # skip some files
```

Exit code: `0` when nothing at or above `--fail-on` was found (default `high`),
`1` when something was, `2` for a usage error. A one-line summary goes to stderr.

### SAAF findings CSV

`--format saaf-csv` writes the exact hand-in format of the SAAF Security Challenge:
`title,repo,risk_rating,observation,recommendation,verified,team`.
`verified` is always `no`: a tool finding is a lead, and a person confirms it.
Use `--output` rather than shell redirection on Windows PowerShell 5.1, which
would write UTF-16 instead of UTF-8.

## Use it in CI (any SAAF repo)

Copy [examples/red-pencil.yml](examples/red-pencil.yml) to `.github/workflows/` in the
agent repo. It calls this repo as a GitHub Action on every push and pull request:

```yaml
- uses: SAAF-Project/four-eyes@main   # pin to a commit SHA once published
  with:
    path: .
    fail-on: high
```

## Suppressing a finding

Add a comment on the flagged line with the rule ID and a reason:

```python
app.run(debug=True)  # red-pencil: ignore[RP006] local demo laptop only, never deployed
```

Every suppression is visible in the code and in review, so an auditor can
challenge it. Suppressions should go through a pull request, like a mandate change.

## How it works

- Python files are parsed with Python's own `ast` module (the syntax tree).
  HTML and Jinja templates are read line by line.
- **It never imports, runs or sends the code it scans.** A test proves this: it
  scans a file that would write a marker file if run, and checks no marker appears.
- In CI it runs Python in isolated mode (`-I`), so a module planted in the scanned
  repo cannot hijack the scanner.
- No network access, no dependencies, no data leaves the machine or the CI runner.
- Its own mandate is declared in [agent.yaml](agent.yaml) in the SAAF living-map schema.

## Tests

```bash
cd red-pencil
python -m unittest discover -s tests -v
```

27 tests: a "bad" snippet per rule modelled on the real SAAF finding, the fixed
version that must pass, false alarms found while tuning, suppression, exit codes,
the SAAF CSV columns, and the never-executes check.

## Limitations

- **Patterns, not proof.** It finds known risky patterns. It does not prove a repo is safe,
  and a clean run is not a clean bill of health.
- **Python and HTML/Jinja templates only.** TypeScript and JavaScript are not scanned yet.
- **RP004 and RP005 read f-strings only.** Wrappers built with `+`, `%` or `.format()`
  are not seen. RP005 only fires when the joined items have document-like names
  (policies, documents, evidence, summary...), tuned on the SAAF repos.
- **Secrets are recognised by name** (`api_key`, `secret`, `token`, `password`...).
  A secret in a variable called `x` is missed. It does not replace a git-history
  secret scan such as gitleaks.
- **Escaping is recognised by name** (a call containing `escape`, `fence`, `sanitize`...).
  A badly written function with a good name will pass.
- It does not check the agent's runtime behaviour, such as whether a human approval
  step can be skipped. That needs a test inside the agent itself.

## Data residency and observability

Runs locally or on the CI runner. Reads files only. Output is a text, JSON or CSV
report plus an exit code; nothing is logged elsewhere.

## Status, owners, licence

- Status: building (v0.1.0), hackathon prototype.
- Owners: to be confirmed (team at the SAAF Security Challenge).
- Licence: to be decided with Stichting SAAF; most SAAF repos use MIT.
