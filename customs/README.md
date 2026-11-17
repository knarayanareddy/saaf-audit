# Customs

**Customs inspects every contribution to shared SAAF prompts, skills and agent settings before it reaches the organisations that reuse them.**

SAAF works because more than 65 organisations share prompts, skills and scripts through common repositories, then run them inside their own audit environments. That is also the exposure. One malicious contribution, such as a hidden instruction in a skill file, could end up running in many audit functions at once.

Customs treats shared content as untrusted until it has been inspected, in the same way an auditor treats a report received from a third party. It runs on every pull request, looks for content that could steer an agent against the person using it, and blocks the merge with a plain English explanation of what it found and where.

Customs uses no AI model and makes no network calls. It gives the same answer whichever AI tool an organisation uses (Copilot, Gemini, Claude or a local model), and it runs offline.

## What it checks

| Rule | Severity | What it catches |
|---|---|---|
| CUS-H1 | High | Invisible characters that hide text from a reviewer. Text hidden in Unicode tag characters is decoded and shown in the report, then checked again. |
| CUS-H2 | Medium | HTML comments, which GitHub hides from view but an agent reads in full. |
| CUS-H3 | High or Low | Long encoded strings. High when they decode to readable text, which is then checked again. |
| CUS-H4 | Medium | Styling that hides text from a reader. |
| CUS-O1 | High | Wording that tells the agent to set aside its instructions, avoid human approval or keep things from the user. English and Dutch. |
| CUS-N1 | High | Instructions to send or copy data to an outside address. |
| CUS-N2 | Medium | Web addresses outside the approved domain list. |
| CUS-N3 | Low | Email addresses outside the approved domain list. |
| CUS-N4 | Medium | Network commands. |
| CUS-N5 | High | Commands that download code and run it straight away. |
| CUS-S1 | High | References to credential files, keys and other locations outside the project. |
| CUS-P1 | High | Agent settings that grant blanket permissions or remove approval prompts. |
| CUS-P2 | Medium | Agent settings that add tool servers or download packages at start-up, especially unpinned versions. |
| CUS-G1 | Medium | Changes to Customs itself, its settings, its exception list or the CI workflows. |
| CUS-X1 | Low | Files that cannot be read as text. |

By default, findings rated High or above block the merge. Lower findings are listed for the reviewer.

Customs recognises guardrail wording. A sentence that forbids something, such as an instruction never to finalise a report before the reviewer has approved it, is not reported as an override.

By default Customs inspects Markdown, prompt and text files, and agent configuration files (tool server settings, editor agent settings, files with "agent" in the name). Change this with `extra_include` in `customs.toml`.

## Run it locally

Requires Python 3.11 or later. Nothing to install.

```
python3 customs/customs.py                         # whole repository
python3 customs/customs.py --changed-since main    # only what your branch changes
python3 customs/customs.py skills/my-skill         # one file or folder
```

| Option | Purpose |
|---|---|
| `--fail-on Medium` | Change the lowest severity that blocks. |
| `--json report.json` | Also write the results as JSON. |
| `--markdown report.md` | Also write a Markdown summary. |
| `--config other.toml` | Use a different settings file. |
| `--allow-empty` | Clear a scan that matches no files. Without it, such a scan is reported as not assessed. |

Exit codes: `0` cleared, `1` blocked, `2` could not run or nothing was inspected.

**No silent pass.** Customs never clears what it did not inspect. If a full scan, or a folder you name, matches no files (for example because the prompts use a file type that is not included, or everything is excluded), Customs reports NOT ASSESSED and exits with `2`, so the check fails instead of showing green. A pull request that changes no inspected files (`--changed-since`) is still cleared, because there is nothing to inspect.

In GitHub Actions, Customs also writes a summary table to the run page and marks each finding on the changed line of the pull request.

## Try the demo

```
./demo.sh
```

The demo builds a throwaway repository with a clean vendor review skill, then adds a contribution that hides instructions in the skill and adds a tool configuration. Customs clears the first and blocks the second. It runs offline and leaves nothing behind.

## Add Customs to a SAAF repository

### Option A: reusable workflow (recommended)

Create `.github/workflows/customs.yml` in your repository:

```yaml
name: Customs
on: pull_request
permissions:
  contents: read
jobs:
  customs:
    uses: SAAF-Project/customs/.github/workflows/customs-reusable.yml@v1
```

The checker is fetched from a tagged Customs release, not from the pull request, so a contribution cannot weaken the check that inspects it. Replace `SAAF-Project/customs` with the location where this repository is published.

### Option B: copy it in

Copy the `customs/` folder and `.github/workflows/customs.yml` into your repository. This is simpler and works without access to another repository, but a contribution could edit the checker that inspects it. If you choose this option, the code owner setting below is essential.

## Protecting the guard

A control is only as strong as the controls around it. Customs has two protections built in and relies on three settings in GitHub.

Built in:

- When Customs checks a pull request, it reads its settings (`customs.toml`) and its exception list (`.customs-allowlist.toml`) from the base branch, not from the contribution. A pull request cannot loosen the rules for itself or approve its own exception.
- Any change to Customs, its settings, its exception list or the CI workflows is reported as CUS-G1, so the reviewer sees it.

In GitHub:

1. Make the Customs check a required status check in branch protection. If a contribution deletes or renames the workflow, the check never reports and the merge stays blocked.
2. Add code owners for the control files in `.github/CODEOWNERS`, so changes to them need approval from a maintainer:

   ```
   /customs/                 @SAAF-Project/maintainers
   /customs.toml             @SAAF-Project/maintainers
   /.customs-allowlist.toml  @SAAF-Project/maintainers
   /.github/workflows/       @SAAF-Project/maintainers
   ```

3. Before production use, pin the GitHub actions in the workflows to a full commit SHA rather than a tag. Keep the `pull_request` trigger. Do not switch to `pull_request_target`, which runs with write access and repository secrets.

## Settings

All settings in `customs.toml` are optional:

```toml
fail_on = "High"                         # lowest severity that blocks
extra_allowed_domains = ["bis.org"]      # destinations that are not reported
extra_include = ["prompts/**/*.yaml"]    # more files to inspect
extra_exclude = ["docs/archive/**"]      # files to skip
```

Approved domains cover their subdomains, so `github.com` also covers `docs.github.com`.

## Exceptions

When a finding is legitimate, record it in `.customs-allowlist.toml` rather than lowering the threshold:

```toml
[[exception]]
rule = "CUS-N2"
path = "docs/regulation/*.md"
contains = "bis.org"            # optional: only lines containing this text
justification = "Links to the Basel Committee principles the agent maps controls to."
approved_by = "SAAF maintainers"
expires = 2027-06-30
```

Every field except `contains` is required. Customs ignores and reports any exception without a justification, an approver or a valid expiry date, and stops applying an exception once it expires, so exceptions are reviewed periodically. Accepted findings stay in the report with their justification, which keeps the audit trail visible.

## Findings from the security challenge it addresses

Checked against the findings handed in on 10 November 2026:

| Finding | Repo | How Customs responds |
|---|---|---|
| AGENTS.md, auto-loaded through CLAUDE.md, tells coding agents to clone code and contact outside services | python-mcp-framework | Reports each network command (CUS-N4, which now includes `git clone`) and each unapproved address (CUS-N2) for the reviewer. Reproduced in `tests/fixtures/autorun`. |
| Several checks across SAAF report OK when they assessed nothing | three-way-match-audit, Stress-test, saaf-living-map and others | Customs applies the same lesson to itself: a scan that inspects nothing is NOT ASSESSED, not CLEARED. |

The wider aim is the one in the opening section: a hidden instruction in a shared skill should be stopped before it reaches the organisations that reuse it.

## Security notes

Report a weakness as the [SAAF security policy](https://github.com/SAAF-Project/.github/blob/main/SECURITY.md) describes, never in a public issue. A hidden instruction that Customs fails to catch, or a way to make it clear a contribution it should block, counts as a security bug. Describe how to reproduce it.

## Limitations

- **Pattern matching, not understanding.** An attacker can rephrase an instruction so that no pattern matches, or write in a language other than English or Dutch. Customs catches the common techniques and raises the effort an attack needs. It supports a human reviewer; it does not replace one.
- **It reads text; it does not run code.** A script that looks harmless but behaves badly when run will pass. Script review needs separate tooling.
- **It inspects the repository, not what an agent reads later.** Auditee documents, emails and web pages that an agent opens at run time need a separate guard, for example one that marks auditee documents as data rather than instructions.
- **File coverage depends on configuration.** Repositories that keep prompts in other file types need to extend `include`.
- **Some false positives are expected,** for example installation guides that contain download commands. Handle these with a dated exception rather than by lowering the threshold.
- **Early version.** Customs has been tested on example content written for the SAAF security challenge. It has not yet been tuned against every SAAF repository.

## Project layout

```
customs/customs.py        the scanner
customs/rules.py          the rules, with plain English reasons
customs.toml              settings
.customs-allowlist.toml   exception list (template)
.github/workflows/        CI workflow, reusable workflow and tests
tests/                    tests and the clean and poisoned example skills
demo.sh                   offline demo
```

Run the tests with `python3 -m unittest discover -s tests -v`.

To add a rule or phrase, edit `customs/rules.py` and add a test case to `tests/test_customs.py`.

## Authors

Built by team Dungeon Dwellers at the SAAF security challenge (Mollie, Amsterdam, 10 November 2026): Anja Nell and Tony Barratt.
