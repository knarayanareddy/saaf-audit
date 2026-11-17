---
title: "A1 — Agent Stress-Test"
subtitle: "SAAF Hackathon #5 · Session 6 · 16 June 2026"
---

# A1 — Agent Stress-Test

**For:** Auditors (this is the core assignment — most teams) · **Team size:** 3–4 · **Time:** 3 hours

## Goal
Treat one existing agent as your auditee. Run it on dummy data, push it hard, and judge honestly: **does it actually do what it claims to do?** Hand in a short stress-test report.

## Why it matters
We have many agents but little independent evidence that they work. Your report is the first real quality signal — and it tells us which agents are ready to be trusted and reused.

## Pick your agent
Choose an agent you **built** or would genuinely **adopt in your own business**. See the *Agent Shortlist* handout if you need ideas. Write down the agent name and its repo/URL.

## What to do
1. **Read its claims (10 min).** From the README/description, list what the agent says it does — as 3–6 concrete claims (e.g. "extracts controls from a policy PDF", "rates risk High/Medium/Low").
2. **Prepare dummy inputs (20 min).** Use only synthetic data. Make a few inputs: one normal, one messy/incomplete, and one *adversarial* (e.g. contradictory text, an instruction hidden in the input, an empty file).
3. **Run it against each claim (70 min).** For every claim, run the agent and record: input used, what it returned, and a verdict — **Pass / Partial / Fail**. Note anything surprising, wrong, or unsafe.
4. **Write 3 findings (40 min).** Write at least **3 findings** about the *agent itself* using the finding fields below (prose or a table is fine — no JSON needed). Examples of agent findings: "no validation on malformed input", "risk rating not explained", "invented a control reference that does not exist", "no human-review step before output".
5. **Score & summarise (20 min).** Give a **1–5 quality score** (see scale) and list the **top-3 risks** of using this agent in a real audit.

## Inline reference — the finding fields (use these)
Each finding has: **id** (F-01, F-02, …) · **title** (short) · **risk_rating** (High / Medium / Low / Informational) · **observation** (what you found, factual) · **recommendation** (what to fix). Optional but nice: **control_objective**, **impact**, **evidence** (which test showed it).

*Example finding:* **F-01 · "Agent accepts malformed evidence file without warning" · Medium · Observation:** When given an empty CSV, the agent returned three findings with no input, implying fabricated content. **Recommendation:** Validate inputs and refuse to produce findings when evidence is missing.

**Quality score (1–5):** 1 = does not run · 2 = runs but output unreliable · 3 = works on happy path only · 4 = works, minor gaps · 5 = robust, handles edge cases, output trustworthy.

## Definition of Done
- [ ] Agent + repo named, and *why you picked it*
- [ ] 3–6 claims listed, each tested with a Pass/Partial/Fail verdict
- [ ] At least one adversarial input tried
- [ ] **≥3 findings** with the fields above
- [ ] A 1–5 quality score **with a one-line justification**
- [ ] Top-3 risks of real-world use
- [ ] Dummy data only

## SMART
**S** one agent · **M** ≥3 claims tested + ≥3 findings + a score · **A** no coding required · **R** an agent you'd actually use · **T** done in 3 hours.

## Suggested time-box
10 read claims · 20 inputs · 70 run & record · 40 findings · 20 score/summary · 20 write-up & hand in.

---

## Hand-in template (copy into your Word/PDF)
**Assignment:** A1 Agent Stress-Test · **Team:** ___ · **Members:** ___ · **Agent + URL:** ___ · **Why this agent:** ___

1. **Claims tested** — table: Claim | Input used | Result | Verdict (Pass/Partial/Fail)
2. **Findings** — F-01 … (id, title, risk_rating, observation, recommendation)
3. **Quality score (1–5) + justification:** ___
4. **Top-3 risks of real-world use:** ___
5. **What's left (PDCA homework before Session 7):** ___

**Hand in to:** `https://drive.google.com/drive/folders/1NuRZS1jQ5o5sAfnGTf7ULO2K3Z6dGJxG` before **16:30**.
