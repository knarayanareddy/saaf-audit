---
name: saaf-repo-scan
description: Run a full security scan and report over SAAF agent repositories (scan, review, merge, report in Dutch or English). Use when asked to scan/test SAAF repos for security, run the security challenge again, make a findings report, or "repos scannen / beveiligingsscan / bevindingenrapport / security test van de agents".
---

# SAAF repo scan & report

Turns a folder of SAAF repo clones into a grouped findings report (HTML, NL/EN switch) and a challenge-format CSV.
The deterministic core is `python -m saaf_guard.scan` (no network, no LLM). The content review is done by the
`saaf-security-reviewer` agent. Keep it simple: one output folder, three files.

Setup once: `pip install -e <path>/saaf-guard` (no dependencies), or prefix commands with `PYTHONPATH=<path>/saaf-guard`.
Copy `agents/saaf-security-reviewer.md` to `.claude/agents/` and this skill to `.claude/skills/`.

## 0. Agree scope first (ask if unclear)
- Authorisation: only repos the user is allowed to test (own org / challenge). Local copies only; live sites passive only.
- Workspace folder, which repos (all or a subset), language (`nl`/`en`), team name (only needed for a challenge CSV),
  and whether to scan git history for keys (`--history`, slower).
- Output folder, default `scan-out/` next to the workspace (never inside a repo).

## 1. Get the repos (optional)
If the user gives a GitHub org and clones are missing or stale:
```bash
gh repo list <org> --limit 500 --json name -q '.[].name'   # then gh repo clone / git pull --ff-only per repo
```
Note: Windows PowerShell 5.1 has no `&&` — give the user one command per line.

## 2. Automatic scan (leads)
```bash
python -m saaf_guard.scan <workspace> --out <out>/auto --history --lang <nl|en>
```
Use `<out>/auto/findings.json` as leads for the reviewers. Do not report these as-is: they are heuristics.

## 3. Review in parallel
Split the repos into at most 6 groups of related repos (e.g. web apps, orchestrators, compliance, data/GRC,
assurance tools, platform). Launch one `saaf-security-reviewer` agent per group **in one message** (background), each with:
`workspace`, `repos`, `out: <out>/reviews/<group>.json`, `lang`, `leads: <out>/auto/findings.json`.
Skip empty repos. If agents are interrupted, resume them rather than starting over.

## 4. Verify before reporting
- For every Critical and High finding: read the cited code yourself and confirm. Fix wrong line numbers.
- If a reviewer could not check GitHub issues, run `gh issue list` for its repos and drop or narrow known issues.
- Check no output contains key values or personal data (the scan refuses to write if it detects key formats).

## 5. Merge and report
```bash
python -m saaf_guard.scan <workspace> --reviews <out>/reviews --out <out> --lang <nl|en> [--team <name>] [--history]
```
Produces `<out>/findings.json`, `<out>/findings.csv` (title,repo,risk_rating,observation,recommendation,verified,team)
and `<out>/report.html` (grouped by nine root causes, NL/EN toggle, linked to SAAF Guard skill rules).
Review findings win over automatic ones for the same cause in the same file.

## 6. Present
- Summarise per root cause (count, severity, what goes wrong) and list Critical/High first. Mention what was not verified.
- Give the full Windows path of `report.html`, or open it (`Start-Process "<path>"`).
- **Never send, publish, push or file issues with the results without explicit user approval** — findings describe
  unfixed weaknesses. Recommend keeping reports private until fixed.

## 7. Report to the online repos (GitHub issues)
```bash
python -m saaf_guard.issues --findings <out>/findings.json --org <org> --preview <out>/issues-preview          # dry run
python -m saaf_guard.issues --findings <out>/findings.json --org <org> --preview <out>/issues-preview --apply  # only after approval
```
- One issue per repo with a checklist; a hidden marker makes the next run **update** that issue instead of opening a new one.
- **Public repos never get a public issue** (that would disclose an open weakness): GitHub Private Vulnerability Reporting
  is used when enabled, otherwise the repo is skipped — tell the user which ones and suggest contacting the maintainers.
- Only review findings by default (`--include-auto` adds heuristic ones). The text is checked for key values.
- Show the dry-run plan and get explicit approval before `--apply`: it notifies every repo's maintainers.

## Prevent instead of find
Point teams to the `saaf-guard` skill (nine build rules) and the CI check, so the same root causes do not return.
