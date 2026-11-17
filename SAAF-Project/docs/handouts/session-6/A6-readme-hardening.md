---
title: "A6 — README / Docs Hardening"
subtitle: "SAAF Hackathon #5 · Session 6 · 16 June 2026"
---

# A6 — README / Docs Hardening

**For:** Anyone (an auditor can absolutely do this) · **Team size:** 3–4 · **Time:** 3 hours

## Goal
Answer one question for one agent: **could a stranger deploy this from the README and dummy data alone?** Try it for real, list every gap, then rewrite the README so the answer becomes "yes". Hand in the rewritten README.

## Why it matters
An agent nobody else can run is an agent nobody else can use. Good docs are what turn one team's prototype into a shared, reusable asset — the whole point of SAAF.

## Pick your agent
Choose an agent you would like to see widely used. Note its name and URL.

## What to do
1. **Cold-start test (60 min).** Pretend you have never seen this agent. Follow *only* the README. Try to get it running on dummy data. Write down every point where you got stuck, had to guess, or needed outside help.
2. **Gap list (30 min).** Turn each stuck-point into a gap (missing step, unclear command, no sample data, undocumented key, etc.).
3. **Rewrite the README (60 min).** Produce a new README that passes the checklist below. Where you can't verify something, mark it `TODO:` rather than guessing.
4. **Re-test (20 min).** Hand your new README to a teammate who hasn't touched it. Can they get further? Note the result.

## Inline reference — minimal "deployable" README checklist
A good README has:
- [ ] **What it does** — one paragraph + the audit task it supports
- [ ] **Inputs / outputs** — what you feed it, what it returns (if it emits findings, note the finding fields)
- [ ] **Prerequisites** — language/runtime version; any accounts/keys (keys via **environment variables only**, never committed)
- [ ] **Install** — exact commands; dependencies pinned; no `pip install` at runtime
- [ ] **Run** — one copy-paste command that runs a demo on **included dummy data**
- [ ] **Sample data** — a small synthetic input shipped with the agent so the demo works offline
- [ ] **Guardrails note** — confirms no `rm/sudo/curl/wget/ssh/chmod/chown/cron`; scripts run from `tools/scripts/`
- [ ] **Model / data-residency note** — which model; hosted vs local/EU-sovereign option
- [ ] **Limitations & human-review gate** — what it must NOT be trusted to do unattended
- [ ] **License / contact / link** to the agent's plan

## Definition of Done
- [ ] Cold-start test done; every stuck-point recorded
- [ ] Gap list produced
- [ ] **Rewritten README** that meets the checklist (TODOs allowed where unverifiable)
- [ ] Re-test result from a fresh teammate

## SMART
**S** one agent's README · **M** checklist met + gaps listed · **A** no coding needed to write docs · **R** docs enable reuse · **T** 3 hours.

## Suggested time-box
60 cold-start · 30 gaps · 60 rewrite · 20 re-test · 10 write-up & hand in.

---

## Hand-in template (copy into your Word/PDF)
**Assignment:** A6 README Hardening · **Team:** ___ · **Members:** ___ · **Agent + URL:** ___

1. **Cold-start test:** what worked, where you got stuck
2. **Gap list:** ___
3. **Rewritten README:** (paste the full new README)
4. **Re-test result (fresh teammate):** ___
5. **What's left (PDCA homework):** ___

*Optional:* if a developer is on the team, open a pull request with the new README — but the **document hand-in is what counts**.

**Hand in to:** `https://drive.google.com/drive/folders/1NuRZS1jQ5o5sAfnGTf7ULO2K3Z6dGJxG` before **16:30**.
