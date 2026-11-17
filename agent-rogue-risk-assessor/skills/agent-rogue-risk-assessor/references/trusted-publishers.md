# Trusted skill publishers (skills.sh)

skills.sh (operated by Vercel) indexes skills by install count and activity; it
does not publish a pre-listing security review. Third-party scans have reported
that a large share of skills in the wild carry security flaws. Publisher trust
is therefore the control.

## Allowlist (install without prompting, after reading SKILL.md and scripts/)

Match on the exact GitHub owner. Look-alikes (`trail0fbits`, `anthropic-skills`,
forks such as `<someone>/skills` that copy a trusted README) are NOT trusted.

| Owner | Organisation | Why trusted |
|---|---|---|
| `anthropics` | Anthropic | Publisher of the Agent Skills format and reference skills |
| `trailofbits` | Trail of Bits | Established security research / audit firm |
| `vercel-labs` | Vercel | Operator of skills.sh |
| `openai` | OpenAI | Major model provider |
| `microsoft` | Microsoft | Major vendor |
| `github` | GitHub | Major vendor |

Maintain this list through the SAAF review process; record who approved each
addition and when.

## Candidate skills for this assessment

Verify each still exists and check the current commit before installing.

| Skill | Publisher | Use in this agent | Install |
|---|---|---|---|
| audit-context-building | trailofbits | Build architectural context of the target agent before judging RF1/RF3 reachability | `npx skills add trailofbits/skills --skill audit-context-building` |
| agentic-actions-auditor | trailofbits | Audit GitHub Actions workflows that run AI agents (CI paths that can rewrite prompts/config = RF1) | `npx skills add trailofbits/skills --skill agentic-actions-auditor` |
| semgrep / codeql (static-analysis) | trailofbits | Confirm write paths to prompt/memory files and guard coverage with data-flow, beyond keyword matching | `npx skills add trailofbits/skills --skill semgrep` |
| differential-review | trailofbits | Review git history of prompt/memory files (RF5, C2) | `npx skills add trailofbits/skills --skill differential-review` |
| fix-review | trailofbits | Verify remediation commits (Step 7a) address findings without new bugs | `npx skills add trailofbits/skills --skill fix-review` |
| skill-creator | anthropics | Maintain and evaluate this skill itself (not used during an assessment) | `npx skills add anthropics/skills --skill skill-creator` |

## Prompt-if-unsure rule

Ask the user before installing when ANY of these hold:
- owner not in the allowlist;
- owner in the allowlist but the repo is not the organisation's main skills repo;
- the skill ships scripts that use network, credentials, or write outside the
  project directory;
- install count is very low or "first seen" is within the last 30 days for a
  skill claiming a trusted brand.
