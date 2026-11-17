---
title: "A3 — Observability & Risk"
subtitle: "SAAF Hackathon #5 · Session 6 · 16 June 2026"
---

# A3 — Observability & Risk

**For:** Auditors / Vaktechniek · **Team size:** 3–4 · **Time:** 3 hours

## Goal
Make one agent **observable and risk-assessed**. Answer the ten observability questions and build a risk register, so we can see how the agent behaves, where it can fail, and what controls keep it safe.

## Why it matters
An agent you cannot observe is an agent you cannot trust or audit. This is exactly the auditor's lens: what could go wrong, how would we know, and what control catches it?

## Pick your agent
Choose an agent you **built** or would **adopt**. Note its name and URL.

## What to do
1. **Answer the 10 observability questions (80 min).** Work through each question below for your agent. Be concrete; if the answer is "nothing today", say so — that is itself a finding.
2. **Build a risk register (50 min).** List **≥5 risks** of using this agent. For each: likelihood, impact, the control that mitigates it (existing or proposed), and the residual risk after that control.
3. **Pick the top 3 (10 min).** Highlight the three risks that would most worry you in a real audit, and what you'd require before go-live.

## Inline reference — the 10 observability questions
1. **Purpose** — what is this agent for?
2. **Users / stakeholders** — who relies on its output?
3. **Workflow** — what is the step-by-step process it runs?
4. **Critical decisions** — what judgements does it make that matter?
5. **Failure modes** — how can it go wrong (wrong output, hallucination, silent failure)?
6. **Observable fields** — what should be logged/visible on every run (inputs, model, confidence, output, errors)?
7. **Controls** — what keeps it within bounds (human review, guardrails, validation)?
8. **Audit evidence** — what trail does it leave that an auditor could inspect later?
9. **Alerts / triggers** — what conditions should raise a flag or stop the run?
10. **Success metrics** — how do we measure that it is working well?

**Risk register columns:** Risk | Likelihood (H/M/L) | Impact (H/M/L) | Control (existing/proposed) | Residual risk (H/M/L).

## Definition of Done
- [ ] Agent named
- [ ] **All 10 observability questions answered** (no blanks)
- [ ] **≥5 risks** with likelihood, impact, control, residual
- [ ] Top-3 risks + go-live requirements

## SMART
**S** one agent · **M** 10/10 answered + ≥5 risks · **A** no coding · **R** an agent you'd use · **T** 3 hours.

## Suggested time-box
80 observability · 50 risk register · 10 top-3 · 20 write-up & hand in.

---

## Hand-in template (copy into your Word/PDF)
**Assignment:** A3 Observability & Risk · **Team:** ___ · **Members:** ___ · **Agent + URL:** ___

1. **Observability** — answer all 10 questions (numbered)
2. **Risk register** — table: Risk | Likelihood | Impact | Control | Residual
3. **Top-3 risks + go-live requirements:** ___
4. **What's left (PDCA homework):** ___

**Hand in to:** `https://drive.google.com/drive/folders/1NuRZS1jQ5o5sAfnGTf7ULO2K3Z6dGJxG` before **16:30**.
