# Slides outline: Open-Source Readiness (Session 9 · Just Eat Takeaway · 6 Oct 2026)

These are presenter slides for the build-block kick-off. They take about 8 minutes. The other tracks are presented separately and are not covered here.

---

## Slide 1: Our agents are going public

- Every SAAF agent repo is about to be released as open source.
- Assume an unknown auditor, developer and journalist will all read it.
- Today's goal is to walk every agent through and enrich it until it is ready.

*Speaker note: Link back to ASML. There we set the `AUDIT-CRITERIA.md` standard. Today we scale it.*

---

## Slide 2: Where we are today (baseline 3 Oct)

| | Count |
|---|---|
| Agent repos in the org | 33 |
| Reviewed (working code, interface, manifest) | 12 |
| With `AUDIT-CRITERIA.md` | 3 |
| **Open-source ready** | **3** |

- That leaves 30 agents to harden.
- Visual: the SAAF growth chart (repos 10 → 36, members 21 → 151) next to a readiness bar showing 3 of 33.

*Speaker note: Growth is great. Quality now has to catch up with quantity.*

---

## Slide 3: What "ready" means

1. **Reviewed:** real working code, a runnable interface and a dependency manifest. Tests and samples are preferred.
2. **`AUDIT-CRITERIA.md` merged:** at least 3 control objectives mapped to named frameworks, testable pass/fail criteria, a good output / never do list, and honest coverage gaps.

- Both are tracked live in the portal.

---

## Slide 4: One repo, one team (at least 1 dev and 1 auditor)

- The **developer** runs the skill and owns code cleanup, the README, security fixes and the PR.
- The **auditor** owns the control objectives, criteria and gaps, and asks whether the agent actually holds up.
- There is one team per repo. If a repo is already claimed, join that team instead of starting your own.

---

## Slide 5: Claim it in the portal

- *Screenshot: the dashboard banner "Claim a repo →" and the Open-Source Readiness tab.*
- Go to saaf-portal.vercel.app and open the **Open-Source Readiness** tab.
- Use the filters to find your repo: *Unclaimed*, *Needs auditor*, *Needs developer*.
- Click **Claim as developer** or **Claim as auditor**. The card shows a warning until the team is complete.
- When your PR is open, paste the link on your card.

---

## Slide 6: The skill, `/harden-agent-repo`

Flow: **Orient → Reuse → Cleanup → Interview → PR**

- **Orient:** is the README real? Is there branch drift? Does the agent actually make LLM calls?
- **Reuse:** start from your Session 6 hand-in, plan doc or `CLAUDE.md`.
- **Cleanup:** remove secrets and add an Observability section.
- **Interview:** dev and auditor answer together. The skill then writes `AUDIT-CRITERIA.md`.
- **PR:** `gh pr create`. The skill does not merge it; a maintainer reviews it.

*Speaker note: Show the one-line install command from the handout or the portal (it has a copy button).*

---

## Slide 7: Sharpen the skill

- Every run is feedback. Wrong question, missing check, or a new pattern? Change `SKILL.md`.
- Auditors sharpen the criteria steps.
- Developers make the cleanup and PR steps more robust.
- Send improvements as a PR to `.claude/skills/harden-agent-repo/SKILL.md` in SAAF-Project.

---

## Slide 8: Towards an army of agents

- **Today:** humans and the skill harden one repo at a time.
- **Next:** all skill agents together (hardening, review, stress-testing) sweep every agent repo autonomously and continuously.
- **Agent-Auditor** grades every `AUDIT-CRITERIA.md` at org scale.
- **Outcome:** a quality standard every public SAAF agent sits above, with a reasonable degree of assurance.

*Speaker note: What you fix and sharpen today is the training data for that army.*

---

## Slide 9: Go

1. Find your partner (dev and auditor).
2. Claim a repo in the portal.
3. Run `/harden-agent-repo`.
4. Paste your PR link on the card.

- **End-of-day goal:** move the readiness bar from 3 of 33 to as many as possible.
- *Show the portal progress bar on screen during the build block.*
