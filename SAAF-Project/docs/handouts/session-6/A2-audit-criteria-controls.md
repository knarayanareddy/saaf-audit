---
title: "A2 — Audit Criteria & Controls"
subtitle: "SAAF Hackathon #5 · Session 6 · 16 June 2026"
---

# A2 — Audit Criteria & Controls

**For:** Vaktechniek / Auditors · **Team size:** 3–4 · **Time:** 3 hours

## Goal
Define **what "good" looks like** for one agent. Which audit controls does it actually test? Against which criteria and standards should it be judged? Produce a criteria sheet that any later team can use to assess the agent objectively.

## Why it matters
Right now we judge agents on gut feel. Clear, framework-anchored criteria turn "it seems fine" into "it meets/fails these specific requirements" — the foundation for trusting an agent in real audit work.

## Pick your agent
Choose an agent you **built** or would **adopt**. Note its name and URL.

## What to do
1. **Describe what it does (20 min).** In plain language: purpose, input, output, and the audit task it supports.
2. **Map to controls & standards (50 min).** Identify **≥3 control objectives** the agent supports or tests, and tie each to a recognised framework (menu below). State the specific clause/area where you can.
3. **Write acceptance criteria (50 min).** For each control objective, write **testable acceptance criteria** — concrete statements the agent must satisfy. Good criteria are pass/fail and measurable (see examples).
4. **Define "good output" (30 min).** What must a *correct* output contain? What must it never do (e.g. never invent a citation, always flag low confidence, always keep a human-review step)?
5. **Note coverage gaps (10 min).** What relevant controls does the agent *not* cover that an auditor would expect?

## Inline reference
**Framework menu** (pick what fits): ISO 27001 · GDPR · DORA · NIS2 · EU AI Act · COSO · COBIT · SOx (ICFR) · IIA Standards · OWASP (LLM/AI).

**A control objective** states the outcome a control should achieve, e.g. *"Access to production systems is restricted to authorised personnel and reviewed periodically."*

**Acceptance criteria are testable.** Examples:
- *"Given a policy with no review date, the agent flags it as a finding."*
- *"Every finding cites a real control reference that exists in the source framework."*
- *"The agent never outputs a risk rating without an observation supporting it."*

## Definition of Done
- [ ] Agent named + plain-language description
- [ ] **≥3 control objectives**, each tied to a named framework
- [ ] **Testable acceptance criteria** per objective (pass/fail)
- [ ] A short "good output / never do" list
- [ ] At least 2 coverage gaps noted

## SMART
**S** one agent's criteria · **M** ≥3 objectives + acceptance criteria each · **A** no coding · **R** an agent you'd use · **T** 3 hours.

## Suggested time-box
20 describe · 50 map controls · 50 acceptance criteria · 30 good-output rules · 10 gaps · 20 write-up & hand in.

> **This is now a SAAF standard.** Your result becomes an `AUDIT-CRITERIA.md` that lives next to the agent's `README.md`. Structure follows the template `docs/conventions/audit-criteria-template.md`. Hand in your filled doc to the Drive folder; if you have a developer, also drop `AUDIT-CRITERIA.md` into the agent's repo via PR.

---

## Hand-in template (copy into your Word/PDF)
**Assignment:** A2 Audit Criteria & Controls · **Team:** ___ · **Members:** ___ · **Agent + URL:** ___

1. **What the agent does:** ___
2. **Control objectives & framework mapping** — table: Objective | Framework + clause | Why relevant
3. **Acceptance criteria** — per objective, the pass/fail tests
4. **Good output / never do:** ___
5. **Coverage gaps:** ___
6. **What's left (PDCA homework):** ___

**Hand in to:** `https://drive.google.com/drive/folders/1NuRZS1jQ5o5sAfnGTf7ULO2K3Z6dGJxG` before **16:30**.
