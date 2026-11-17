---
title: "Build Block — Repo Hardening & Audit Criteria"
subtitle: "SAAF Hackathon · Session 7 · 15 September 2026"
---

# Build Block — Repo Hardening & Audit Criteria

## Your repos are going public. Make them earn it.

Every agent repo in the SAAF org is about to be released to the public. Assume an unknown auditor, developer, and journalist will all read it. Today's build block has **one mandatory task, for every team** — no A1–A7 menu this time.

## The task

**Add or finish `AUDIT-CRITERIA.md` next to your repo's `README.md`, and submit it as a pull request.**

1. **Check what already exists first.**
   - Look for an open issue titled **"Add AUDIT-CRITERIA.md (SAAF A2 standard)"** on your repo — that's your task ticket. Close it with your PR.
   - Check whether your team already did the **A2 — Audit Criteria & Controls** assignment in Session 6. If so, don't start from scratch — turn that hand-in into the file, don't rewrite it.
   - Good example to model the depth on: RCM-Builder's Session 6 A2 hand-in (Team 007s) — 5 control objectives, named frameworks, testable acceptance criteria per objective.

2. **Fill the template properly.** `docs/conventions/audit-criteria-template.md` in `SAAF-Project`. Required:
   - ≥3 control objectives, each tied to a named framework (ISO 27001, GDPR, DORA, NIS2, EU AI Act, COSO, COBIT, SOx/ICFR, IIA Standards, OWASP LLM/AI)
   - Testable, pass/fail acceptance criteria per objective
   - A "good output / never do" list
   - Honest coverage gaps — a repo that admits what it doesn't cover is in better shape than one that hides it

3. **Use your own tribal knowledge, not just the exercise.** You know audit. Be critical of the agent you built or adopted. If it doesn't hold up, say so in the coverage gaps.

4. **Opportunistic fixes — while you're in there, not a separate assignment:**
   - Obvious security issues (hardcoded secrets, missing input validation, overly broad permissions) — patch them.
   - No observability described anywhere? Add a short section (README or `AUDIT-CRITERIA.md`) stating what's logged/traced today and what's missing.
   - Don't go hunting for hours — fix what you find while doing #2.

## Hand-in: a real pull request, not a Drive upload

Open a **PR against the agent's own repository** (or `SAAF-Project` for shared/prompt work) adding or updating `AUDIT-CRITERIA.md`, plus any patches from step 4. Reference the "Add AUDIT-CRITERIA.md" issue if one exists (`Closes #<n>`). Tag a maintainer for review.

## Definition of Done

- [ ] `AUDIT-CRITERIA.md` exists next to `README.md`, following the template
- [ ] ≥3 control objectives, each tied to a named framework, with testable acceptance criteria
- [ ] "Good output / never do" list + named coverage gaps
- [ ] PR opened against the agent's repo (linked issue closed if one existed)
- [ ] Anything patched, or left unfinished, is noted in the PR description

## Time-box (adjust to today's actual sprint window)

20 min pick your repo, read what already exists (issue, Session 6 hand-in) · 40 min describe + map controls · 40 min acceptance criteria + good-output/never-do · 20 min coverage gaps + opportunistic fixes · 20 min open the PR.
