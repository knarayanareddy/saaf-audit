---
title: "Build Block — Open-Source Readiness"
subtitle: "SAAF Hackathon · Session 9 · Just Eat Takeaway · 6 October 2026"
---

# Build Block — Open-Source Readiness

## Every agent gets a team. Every team gets a skill.

At ASML we set the standard: every agent repo carries an `AUDIT-CRITERIA.md` next to its `README.md`. Since then we turned that manual task into a Claude Code skill — **`/harden-agent-repo`** — that cleans up a repo, interviews you into the audit criteria and opens the PR.

Today, **every agent in the SAAF org gets walked through** and enriched until it is ready to go public. One block, one goal: as many agents above the open-source bar as possible — and a sharper skill at the end of the day than at the start.

**Where we start (3 October):** 36 repos in the org · 12 reviewed · 3 with `AUDIT-CRITERIA.md` · **3 open-source ready**.

## What "open-source ready" means

A repo counts as **ready** when both are true:

1. **Reviewed** — real working code, a runnable interface (CLI, web app, API) and a dependency manifest. Tests and sample inputs/outputs strongly preferred.
2. **`AUDIT-CRITERIA.md` merged** next to the README — ≥3 control objectives tied to named frameworks, testable pass/fail acceptance criteria, a "good output / never do" list, and honest coverage gaps.

The portal tracks both live. After your PR merges, maintainers review the repo and it turns green.

## Step 1 — Form a team: at least 1 developer + 1 auditor

| Role | Owns |
|---|---|
| **Developer** | Running the skill, code cleanup, README, secrets/security fixes, the PR |
| **Auditor** | Control objectives, framework mapping, acceptance criteria, coverage gaps — and a critical eye on whether the agent actually holds up |

No partner yet? Use **Participants** in the portal, or claim as one role and wait for someone to join you — the card shows "Needs an auditor" / "Needs a developer" until the team is complete.

## Step 2 — Claim a repo in the portal

Go to **saaf-portal.vercel.app → Open-Source Readiness** (also linked from the top of your dashboard).

- Pick an **unclaimed** repo and click **Claim as developer** or **Claim as auditor**.
- Repo already claimed? **Join that team** — one team per repo, so we collaborate instead of duplicating work.
- You can be on at most 2 teams. Your own agent is a great pick; so is one nobody owns anymore.
- Use the filters (*Unclaimed*, *Needs auditor*, *Needs developer*) to find where you're needed.

## Step 3 — Run the skill

Install once (needs Claude Code + `gh` CLI logged in):

```bash
mkdir -p ~/.claude/skills/harden-agent-repo && \
gh api repos/SAAF-Project/SAAF-Project/contents/.claude/skills/harden-agent-repo/SKILL.md \
  --jq .content | base64 -d > ~/.claude/skills/harden-agent-repo/SKILL.md
```

Then, per repo:

```bash
gh repo clone SAAF-Project/<repo> && cd <repo>
claude
> /harden-agent-repo
```

What the skill walks you through:

1. **Orient** — is the README real? Open tracking issue? Branch divergence? Does the agent actually call an LLM?
2. **Reuse** — your Session 6 A2 hand-in, plan doc or `CLAUDE.md` becomes the source, not a blank page.
3. **Light cleanup** — hardcoded secrets, `.env` in git, a short Observability section.
4. **Interview** — developer and auditor answer together: control objectives about the *agent's own* trustworthy behaviour, testable criteria, good output / never do, coverage gaps.
5. **Write & PR** — branch, commit, `gh pr create` (with `Closes #<n>` if an issue exists).

## Hand-in: the PR link on your card

Paste the PR link on your repo card in the portal (**Save PR link**). Don't merge it yourself — a maintainer reviews it.

## Optional — sharpen the skill

The skill is only as good as the lessons in it. If it asked the wrong question, missed a check an auditor would expect, or you found a new real-world pattern: open a PR on `.claude/skills/harden-agent-repo/SKILL.md` in `SAAF-Project`. Auditors sharpen the criteria steps; developers make the cleanup and PR steps more robust.

**Why it matters:** the goal is an *army of agents* — all skill agents together, continuously and autonomously sweeping every SAAF agent repo, with **Agent-Auditor** grading each `AUDIT-CRITERIA.md` at org scale. Every improvement today makes that quality bar more trustworthy.

## Definition of Done

- [ ] Team of ≥1 developer + ≥1 auditor registered on the repo in the portal
- [ ] README explains what the agent does, input/output and how to run it
- [ ] `AUDIT-CRITERIA.md` next to the README: ≥3 framework-mapped control objectives, testable acceptance criteria, good output / never do, coverage gaps
- [ ] Obvious secrets/security issues fixed or noted; Observability section present
- [ ] PR opened on the agent repo and the link saved on the portal card
- [ ] Anything left unfinished is noted in the PR description (and, if you hit a skill gap, an issue or PR on the skill)

## Time-box (adjust to today's actual sprint window)

15 min form a team + claim a repo · 15 min install the skill, clone, orient · 60 min interview: objectives, criteria, good/never, gaps · 20 min cleanup + PR + link on the card · 10 min skill feedback.
