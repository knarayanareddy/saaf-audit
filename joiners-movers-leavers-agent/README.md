# Joiners-Movers-Leavers Access Audit Agent

A SAAF audit agent that tests whether access rights follow the joiner, mover and leaver (JML) lifecycle, checked against the Jira tickets in which access was requested and approved.

| Reads | Checks | Returns |
|---|---|---|
| HR master data, directory accounts, entitlement exports per system (AD groups, ERP roles), a Jira export of access requests, and the access policy | 12 deterministic JML controls plus 5 baseline account checks, on every record in the audit period | Exceptions with their source rows, draft findings in the SAAF finding schema, and a report that is final only after an auditor signs off |

It runs in two ways:

- **As a tool with a web UI** on your own laptop: a guided five-step audit with few clicks (works with a presentation clicker).
- **As an agent from Claude Code**: point it at your own exports and let Claude Code run the review and draft the findings.

> **Spin-off of [`SAAF-Project/Track-2---IAM-final`](https://github.com/SAAF-Project/Track-2---IAM-final).** The baseline account engine (`engine/access_review.py`) is Bart van den Broek's access review comparator from Track 2 (`tools/scripts/bart/`), reused with permission and kept close to the original. This repo adds the JML tests, the Jira reconciliation, the Claude Code step and the UI.

All data in this repository is synthetic. The organisation, people and tickets are fictional.

---

## Quick start

**On a Mac, no terminal needed:** double-click **`Start Demo.command`**.
The first start prepares a local Python environment (one to two minutes, needs internet once). After that it starts offline and opens the browser at `http://127.0.0.1:8765`.

If macOS blocks the file the first time, right-click it, choose **Open**, then **Open** again.

**From a terminal (macOS, Linux, Windows):**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip
.venv/bin/python run.py                          # add --lang nl for Dutch
```

Requirements: Python 3.9 or newer. For live findings: [Claude Code](https://claude.com/claude-code) installed and logged in (`claude` once in a terminal). Without Claude Code the agent still runs and uses the prepared result (see below).

## The five steps

| Step | What happens | Click |
|---|---|---|
| 1 Scope | The six source files load; row counts and SHA-256 hashes are shown | *Load the sources* |
| 2 Controls | The 17 checks run; results appear per lifecycle | *Run the controls* |
| 3 Exceptions | Tiles for joiners, movers, leavers and baseline; select an exception to see the person's timeline and the source rows | *See the exceptions* |
| 4 Findings | Claude Code assesses each exception and drafts grouped findings; every finding is validated against the input | *Draft the findings* |
| 5 Sign-off | The auditor confirms the review and signs off; the report opens (print or save as PDF) | *Sign off and open the report* |

Keyboard: **→** or **Page Down** runs the next action, **←** or **Page Up** goes back, so a presentation clicker drives the whole flow. **EN / NL** in the header switches the language at any time.

## The controls

| ID | Lifecycle | Control | Main reference |
|---|---|---|---|
| J1 | Joiner | Access granted without an approved ticket | ISO 27001 A.5.18, SOC 2 CC6.2 |
| J2 | Joiner | More access granted than requested | ISO 27001 A.5.18, A.8.2 |
| J3 | Joiner | Access provisioned before approval | SOC 2 CC6.2 |
| J4 | Joiner | Request approved by the requester | ISO 27001 A.5.3 |
| J5 | Joiner | Request does not specify the access | ISO 27001 A.5.18 |
| M1 | Mover | Previous role access not removed within the mover SLA | SOC 2 CC6.3 |
| M2 | Mover | Segregation of duties conflict (rules in the policy file) | ISO 27001 A.5.3 |
| M3 | Mover | Directory profile not updated after transfer (Track 2 engine) | SOC 2 CC6.3 |
| L1 | Leaver | Directory account still enabled after termination (Track 2 engine) | ISO 27001 A.5.18 |
| L2 | Leaver | Access removed later than the leaver SLA | SOC 2 CC6.2 |
| L3 | Leaver | Login after termination date | ISO 27001 A.5.18 |
| L4 | Leaver | Application access still assigned after termination | ISO 27001 A.8.2 |
| B1-B5 | Baseline | Orphaned, departed-before-period, profile mismatch, stale and duplicate accounts (Track 2 engine) | ISO 27001 A.5.18 |

J tests apply to every access grant in the period (joiners and movers' new access), excluding birthright groups named in the policy. The sample data contains 15 planted exceptions and several clean cases; `tools/generate_sample_data.py` documents each one.

## How the Claude step works

1. The deterministic engine (`engine/jml_checks.py`) produces the exceptions. No model is involved.
2. `engine/pseudonymise.py` replaces every name and username with a USER-NNN reference, also inside ticket text.
3. `ai/claude_runner.py` calls Claude Code headless with your own login:
   `claude -p --output-format json --json-schema … --tools "" --strict-mcp-config --no-session-persistence`.
   All tools are off, so the model can only read its input. The prompt is in `prompts/draft-findings.md`.
4. `engine/findings.py` validates the result: schema, ids, and every cited identifier must exist in the input. Failing findings are rejected and shown as such.
5. Names are restored locally for the auditor's view. The report stays a draft until sign-off.

**Fallback.** If Claude Code is missing, logged out, offline or too slow (180 s, `JML_CLAUDE_TIMEOUT`), the agent uses:

1. a **prepared result** (`demo/prepared_findings.<lang>.json`): a real earlier live run on the same data, used only when the data set fingerprint matches; or
2. a **deterministic draft** built from templates, for any other data.

The UI and the report always say which path was used. To force a path, start with `JML_DRAFT_MODE=prepared` or `JML_DRAFT_MODE=deterministic`. To refresh the prepared results after changing the sample data:

```bash
.venv/bin/python -m ai.claude_runner --prepare --lang en
.venv/bin/python -m ai.claude_runner --prepare --lang nl
```

## Agent mode: your own sources

1. Copy `sources.sample.yaml` to `sources.yaml` (gitignored) and point it at your exports. Required columns are listed in `engine/sources.py` (`REQUIRED_COLUMNS`); the policy format is `sample_data/access_policy.json`.
2. Run the review, with or without a draft:

   ```bash
   .venv/bin/python -m engine.cli --sources sources.yaml            # tests only
   .venv/bin/python -m engine.cli --sources sources.yaml --draft    # plus Claude Code findings
   .venv/bin/python run.py --sources sources.yaml                   # same data in the web UI
   ```

3. Or open this folder in Claude Code and run the skill **`/jml-audit`** (`.claude/skills/jml-audit/SKILL.md`). Claude Code runs the engine, reads only the pseudonymised `model_input.json`, drafts findings and validates them with the same checks.

Each run writes a folder under `runs/` (gitignored): `review_local.json` (with names, stays local), `model_input.json` (pseudonymised), `summary.txt`, and with a draft also `draft.json`.

## Data protection

- Use synthetic or anonymised data in this repository. Never commit real exports (`sources.yaml` and `runs/` are gitignored).
- Only pseudonymised data reaches the model, under your own Claude Code account. Check that this is acceptable for your organisation before using real data, and review free text for identifiers the pseudonymiser cannot know (e-mail addresses, nicknames).
- The web UI listens on 127.0.0.1 only.

## Security notes

Report a weakness as the [SAAF security policy](https://github.com/SAAF-Project/.github/blob/main/SECURITY.md) describes, never in a public issue. Do not include real audit data in a report.

- The web UI binds to 127.0.0.1 and has no authentication: it is meant for one auditor on their own machine. Do not expose it on a network.
- The model step runs Claude Code headless with all tools disabled (`--tools ""`, `--strict-mcp-config`). The model can read only the pseudonymised input it is given.
- No credentials are stored in this repository. Claude Code uses the auditor's own login.
- Source exports are read, never modified. Run output goes to `runs/` (gitignored) and stays local.
- All sample data is synthetic.
- Known limitations: see `AUDIT-CRITERIA.md`, section 5 (Coverage gaps). Pseudonymisation is name-based, the sign-off is not authenticated, and the event log is not tamper-evident.

## Observability

Every UI session writes `runs/<stamp>-ui/events.jsonl` (append-only) with sources and hashes, test counts, the draft path, model, duration, any fallback reason, validation results and the sign-off, next to the exact model input and raw output. See `AUDIT-CRITERIA.md` section 7 for what is not logged yet.

## Repository layout

```
engine/          deterministic tests, source loading, pseudonymisation, findings validation, CLI
  access_review.py   Track 2 baseline engine (Bart van den Broek), small documented changes
ai/              headless Claude Code call with prepared and deterministic fallback
prompts/         the model prompt (SAAF prompt template)
schemas/         finding-schema.json (copy of SAAF-Project/outputs/schemas)
web/             FastAPI app, templates, i18n (en, nl), static files and SAAF brand assets
sample_data/     synthetic exports and access policy
demo/            prepared live results for the sample data
tools/           sample data generator
tests/           pytest suite, mapped to AUDIT-CRITERIA.md
docs/            presenter walkthrough
```

## Tests

```bash
.venv/bin/python -m pytest -q
```

The tests are mapped to the acceptance criteria in [`AUDIT-CRITERIA.md`](AUDIT-CRITERIA.md).

## SAAF standards

- [`AUDIT-CRITERIA.md`](AUDIT-CRITERIA.md): control objectives, acceptance criteria and coverage gaps (A2 standard).
- [`agent.yaml`](agent.yaml): manifest for the [SAAF Living Map](https://github.com/SAAF-Project/saaf-living-map), including the agent's mandate.
- Findings follow `finding-schema.json`; the model prompt follows the SAAF prompt template; tool use follows `regulatory/guardrails/allowed-commands.md` (the model has no tools).
- Language: all content is English. The only exception is `web/i18n/nl.json`, the Dutch interface text for the NL switch.
- Branding: SAAF Light style and the SAAF logo from the TAG x SAAF design system; Geist fonts are bundled under the SIL Open Font License (`web/static/brand/fonts/OFL.txt`).

## Contributing

Branch naming `your-name/feature-description`, at least one review per pull request, reference an issue in each commit. Never commit real audit evidence, personal data or credentials.

## Licence

MIT, see [`LICENSE`](LICENSE).
