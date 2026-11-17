---
title: "Security Challenge"
subtitle: "SAAF Hackathon · Session 10 · Mollie Amsterdam · 10 November 2026"
---

# Security Challenge

The printable version is `00-security-challenge.pdf`, as handed out on the day. Afterwards the quiz and pizza pages were removed from the portal; the challenge page lives under Learn, "Earlier sessions" (`saaf-portal.vercel.app/sessions`).

## Build one guard that stops a bad actor

Find weaknesses in the SAAF agents, then turn what you learn into a skill, a workflow or a CI check that any SAAF repository can reuse. Give it a name. Prizes for the best three.

| Kind | Example |
|---|---|
| Skill | An injection guard that marks auditee documents as data, not instructions. |
| Workflow | A secret scan over the full git history on every push. |
| CI check | A dependency audit that fails the build on a critical advisory. |

## Hand in your findings

Mail a CSV to info@saafproject.com with the subject "SAAF findings: your team name". Every mail adds to your team's count; repeats are removed. One plain `.csv` attachment per mail (no zip, Excel, PDF or links), at most 500 rows and 1 MB, UTF-8, comma or semicolon. Last CSV before 16:30.

Columns, in this order:

```
title,repo,risk_rating,observation,recommendation,verified,team
```

`repo` is the SAAF-Project repository name or the site. `risk_rating` is Critical, High, Medium, Low or Informational. `verified` is yes or no.

## What counts as one finding

| Rule | Meaning |
|---|---|
| Counts | One weakness in one place (a repo plus file, endpoint or site), behaviour that is not what was intended or safe, with a plausible security, privacy or audit impact. |
| In scope | SAAF-Project repos and their pull requests that were live before 13:30 that day, plus the live SAAF sites. Repos or pull requests created that day do not count. |
| Once | The same root cause in one repo counts once. |
| Per repo | The same issue in three repos counts three times. |
| Not new | Anything among the 127 found before the day, false positives, third-party services, repos outside SAAF-Project. |
| Never | No live keys or secret values, no personal data, no attacks on live systems. Local copies only; live sites passive only. |

## The afternoon

| Time | What |
|---|---|
| 14:05 | What the hackers found, five minutes each. |
| 14:45 | Assignment and quiz, then form teams with at least one hacker or developer each. |
| by 16:15 | Sign up for a demo in the portal. |
| 16:30 | Demos, offline on your own laptop. Random order, five minutes at most. |
| 17:00 | The jury deliberates. |
| 17:10 | Prizes, and the quiz winner. |

Judged on: does it stop a real finding from that day, can another SAAF repo reuse it, and is it named and documented (README, how to run, limitations).

## What came of it

Ten teams handed in 402 new weaknesses, for 529 distinct findings including the 127 found before the day, and built twelve guards in five families (secrets, prompt injection, supply chain, repo scanners, sign-off). Session 11, the hardening day of 17 November 2026, closes what they found.
