---
title: "A4 — Local / EU-Sovereign Deploy & Cost"
subtitle: "SAAF Hackathon #5 · Session 6 · 16 June 2026"
---

# A4 — Local / EU-Sovereign Deploy & Cost

**For:** Developers (the scarce skill — use it well) · **Team size:** 2–4 · **Time:** 3 hours

## Goal
Find out whether one agent can run **locally or on an EU-sovereign model** instead of a hosted API, and what that costs. Produce a clear setup + cost picture and a go/no-go recommendation.

## Why it matters
Data residency and token spend are the two things that decide whether an agent can be adopted for real audit work. Knowing the local/sovereign path — and its cost — turns a demo into something a firm can actually deploy.

## Pick your agent
Choose a working agent (ideally one from the shortlist that runs today). Note its name and URL.

## What to do
1. **Get it running on hosted first (40 min).** Establish a baseline: clone, install, run once on dummy data. Record the model used and a rough cost/latency for one representative run.
2. **Try a local / EU-sovereign model (70 min).** Swap to a local model (e.g. via Ollama) or an EU-hosted/sovereign endpoint. Record what changed in config and whether output quality held up. Capture every blocker.
3. **Measure (30 min).** Fill the cost/latency table for hosted vs local/sovereign: cost per run, latency, output quality (1–5), data-residency status.
4. **Check guardrails (10 min).** Confirm the agent's scripts respect the command allowlist (below). Flag any violation.
5. **Recommend (10 min).** Go / no-go for local/sovereign deployment, with the one or two things that must be fixed first.

## Inline reference
**Cost/latency table columns:** Setup (hosted / local / sovereign) | Model | Cost per run | Latency | Output quality (1–5) | Data residency (EU? on-prem?) | Notes.

**Guardrails — these must NOT appear in agent scripts:** `rm`, `sudo`, `curl`, `wget`, `ssh`, `scp`, `chmod`, `chown`, `cron`, and **no `pip install` at runtime**. API keys must come from environment variables, never hard-coded. Scripts should run only from the `tools/scripts/` folder.

## Definition of Done
- [ ] Agent named; hosted baseline run captured
- [ ] A local OR EU-sovereign model attempted (with blockers documented even if it failed)
- [ ] Cost/latency table filled for at least 2 setups
- [ ] Guardrail check done
- [ ] Go/no-go recommendation with prerequisites

## SMART
**S** one agent's deployment path · **M** ≥2 setups measured · **A** scoped to one agent · **R** residency + cost decide adoption · **T** 3 hours.

## Suggested time-box
40 hosted baseline · 70 local/sovereign · 30 measure · 10 guardrails · 10 recommend · 20 write-up & hand in.

---

## Hand-in template (copy into your Word/PDF)
**Assignment:** A4 Local/Sovereign Deploy & Cost · **Team:** ___ · **Members:** ___ · **Agent + URL:** ___

1. **Hosted baseline:** model, run result, rough cost/latency
2. **Local / sovereign attempt:** what you changed, did it work, blockers
3. **Cost/latency table** (columns above)
4. **Guardrail check:** pass/fail + any violations
5. **Recommendation (go/no-go) + prerequisites:** ___
6. **What's left (PDCA homework):** ___

**Hand in to:** `https://drive.google.com/drive/folders/1NuRZS1jQ5o5sAfnGTf7ULO2K3Z6dGJxG` before **16:30**.
