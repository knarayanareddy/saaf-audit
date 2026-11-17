# SAAF agent scanner + security-review skill

The scanner and skill find the security weaknesses that were most common across SAAF audit-agent repositories during the SAAF Security Challenge (10 Nov 2026). There are two parts:

1. **`saaf_scan.py`** is a static scanner with 17 checks. It is read-only and uses only the Python standard library, so there's nothing to install. Output is a CSV in the SAAF findings format plus a prevalence summary.
2. **`skill/saaf-security-review/`** is a Claude Code skill. It runs the scanner, then guides manual triage, a checklist review for what static checks can't see, and a two-lens adversarial verification. It ends with SAAF-format findings.

Scanner hits are **candidates**. The skill turns them into findings you can act on. Don't submit raw scanner output.

## Quick start
```bash
python3 -I saaf_scan.py path/to/repo [more repos ...] --history --team "<team>" --out saaf-scan-out
python3 -I saaf_scan.py --list              # show all checks
python3 -I tests/test_checks.py             # self-test: every check vs. its synthetic fixtures
```
| Output | Contents |
|---|---|
| `findings.csv` | Columns `title,repo,risk_rating,observation,recommendation,verified,team`, one row per check per repo. Same root cause in one repo = one row; every location is listed. |
| `findings.json` | All hits with `path:line`, evidence (secrets redacted) and the reason for the match |
| `summary.md` | Per-check prevalence ("matched N of M repos") and a per-repo overview |

| Option | Effect |
|---|---|
| `--history` | Also scans the full git history, all refs, for secrets (including deleted `.env` files) |
| `--fail-on High` | Exit code 1 when any finding is at or above that severity (for CI) |
| `--include-tests` | Also scans `tests/`, `fixtures/` and `examples/` (skipped by default) |
| `--only SAAF-004,SAAF-009` | Runs only the listed checks |

### Claude Code skill
Copy `skill/saaf-security-review/` to `~/.claude/skills/` (or a repo's `.claude/skills/`) and ask:
*"Run the SAAF security review on ./my-agent"*. The skill reads `SKILL.md`, `checklist.md` and `prompts.md`.

### CI
`ci/saaf-scan.yml` runs the scanner on every pull request:
- uses `pull_request`, not `pull_request_target`
- `contents: read` only, no secrets
- actions pinned by SHA

Before using it, set `vars.SCANNER_REF` to a reviewed commit SHA of this repo. The action SHAs in the example were written from memory, so check them against the official releases.

## Checks and measured quality
How the numbers were measured: every check was evaluated against **50 SAAF-Project repositories**, using **224 manually triaged, 2-vote verified findings** as ground truth. Each check was built by one agent and re-measured by an independent reviewer that opened the real code for each sampled hit.

- **Precision** = sampled hits judged true positives.
- **Recall** = ground-truth repositories the check catches, counting only findings of that class that a static pattern can reasonably detect.

Small samples; treat the numbers as indicative.

| ID | Sev. | Detects | Precision | Recall | Repos matched |
|---|---|---|---|---|---|
| SAAF-001 | High | Files from a cloned repo or archive read without a symlink/containment check (`notes.md -> /proc/self/environ` leaks API keys) | 2/2 | 2/3 | 2 |
| SAAF-002 | Medium | `nan` accepted as a number, so every `abs(a-b) > tolerance` check is False and the result is a silent MATCH | 9/9 | 1/1 | 1 |
| SAAF-003 | Low | Fail-open verdicts: a missing value skips the check, or the verdict defaults to a passing value | 3/6 → tuned to 3/3 | 3/5 | 3 |
| SAAF-004 | Medium | Untrusted document/evidence text in the LLM prompt with no trust separation (indirect prompt injection) | 9/11 | 7/7 detectable (7/19 overall) | 10 |
| SAAF-005 | Medium | Model output parsed and its verdict/score/owner fields used without schema or source cross-check | 6/6 | 4/7 | 5 |
| SAAF-006 | Medium | Web app bound to `0.0.0.0` with state-changing or LLM routes and no authentication | 4/5 | 4/13 | 5 |
| SAAF-007 | Medium | Server-side fetch/clone of a user-supplied URL with no allowlist (SSRF, local disclosure, `git` option injection) | 7/7 | 4/5 | 4 |
| SAAF-008 | Medium | Wildcard CORS on the application API | 3/3 | 3/3 | 3 |
| SAAF-009 | Medium | Model output or documents rendered as raw HTML/Markdown (XSS, remote-image exfiltration) | 9/10 | 6/11 | 10 |
| SAAF-010 | High | Real-format API keys and credentials in the tree or git history (with `--history`) | 4/4 | 2/2 | 2 |
| SAAF-011 | Medium | GitHub Actions: `pull_request_target`, `${{ github.event.* }}` in `run:`, write tokens, unpinned third-party actions | 8/8 | 6/7 | 6 |
| SAAF-012 | High | Agent with unrestricted tools or no approval (`bypassPermissions`, Bash/Write on untrusted input, shell/REPL tools) | 2/2 | 2/4 | 2 |
| SAAF-013 | Low | LLM loops, calls or regexes without limits (no iteration cap, timeout, size cap; catastrophic backtracking) | 7/7 | 5 | 6 |
| SAAF-014 | Low | Unpinned dependencies with no lockfile, CDN scripts without SRI, mutable branch references | 13/14 | 13/15 | 34 |
| SAAF-015 | Medium | Human-review checkpoint optional, off by default, or decided by the model's own output | 3/3 | 2/7 | 3 |
| SAAF-016 | Low | Full prompts, responses, uploaded documents or secrets written to logs, stdout or unprotected temp files | 5/7 | 1/1 | 4 |
| SAAF-017 | High | Shell command or SQL built by string interpolation (command/SQL injection) | 2/2 | 1/2 | 2 |

A full 50-repo scan with `--history` takes about 30 seconds and produces about 100 candidates.

### What the scanner cannot find (use the skill's `checklist.md`)
- Whether a manipulated document actually changes the conclusion. This was the most common SAAF weakness (60% of repos); static checks only catch the fail-open coding patterns behind it.
- Prompt injection across files or in Markdown/skills, injection through structured data with generic variable names, and incomplete "data, not instructions" rules.
- Authorisation and data-isolation logic, IDOR, business rules, and design-level gaps such as caps that silently drop scope.
- Anything that only shows up when the agent runs (non-deterministic model behaviour). Test that in an isolated sandbox with synthetic data and mocked integrations.

## Adding a check
1. Copy `checks/001_symlink_follow_read.py` and fill in the `CHECK` dict: `id, slug, category, severity, title, intended, actual, impact, recommendation, refs`.
2. Implement `run(repo)` and return a list of `Hit(path, line, evidence, detail)`. Use `repo.files()`, `repo.read()`, `repo.lines()`, `repo.grep()` and `repo.git_log_patch()`, plus the helpers `functions()`, `snippet()` and `redact()` from `_lib`.
3. Add `tests/fixtures/<ID>/vulnerable/` (must give at least 1 hit) and `tests/fixtures/<ID>/safe/` (must give 0), then run `python3 -I tests/test_checks.py`.
4. Measure against real repos: open the hits, count true positives, and add the numbers to the table above.

## Permissions, safety and limitations
- **Read-only:** checks only read files and run read-only `git log`/`rev-parse`. Nothing from the scanned repository is imported, installed or executed. No network access.
- **Secrets:** shown redacted to the first 4 characters. The test files contain only synthetic values marked `NOT real`.
- **Heuristic:** checks are regex and indentation based and target Python, JS/TS, YAML, Markdown and HTML. Expect false negatives (see recall), and confirm every candidate in the code.
- **Ratings:** default severities are starting points. Reality-check each finding in context (attacker, preconditions, impact) before reporting.

Built by team ragtag for the SAAF Security Challenge. Findings that motivated these checks were reported privately to SAAF.
