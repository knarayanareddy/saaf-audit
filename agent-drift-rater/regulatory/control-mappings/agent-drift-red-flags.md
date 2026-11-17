# Agent Drift — Red Flags and Controls Mapping

**Standard:** OWASP Top 10 for LLM Applications 2025; EU AI Act (benchmark); SAAF guardrails.
**Audit domain:** AI Agent Governance — drift (an agent acting outside its approved mandate without anyone changing it).
**Source:** "Drift Watch", J. Angula, Agents Gone Rogue, Amsterdam, 6 October 2026.
**SAAF prompt reference:** `prompts/audit-use-cases/agent-drift-rater.md`

---

## Scope note

The EU AI Act articles are used as a **good-practice benchmark**, not a compliance assertion:
most SAAF hackathon agents are unlikely to be high-risk systems under Annex III. Ratings from
the agent drift rater are **design evidence from static review, not certification**.

## Red flags (the six "what to look for" signs)

| Red flag | Auditable control | Frameworks | Risk if absent | SAAF Prompt Reference |
|---|---|---|---|---|
| RF1 — It can edit itself | The agent cannot modify its own prompt, memory, or tool configuration at runtime without reviewed change control. | OWASP LLM04; EU AI Act Art. 15(4) | High | `prompts/audit-use-cases/agent-drift-rater.md` |
| RF2 — A target in its context | No performance score/KPI that rewards bending a rule sits in the agent's decision context. | Drift Watch; EU AI Act Art. 9 | Medium | `prompts/audit-use-cases/agent-drift-rater.md` |
| RF3 — Rules only in the prompt | Each mandate hard rule is enforced in code before the action, not only stated in the prompt. | OWASP LLM07; EU AI Act Art. 15 | High | `prompts/audit-use-cases/agent-drift-rater.md` |
| RF4 — Escalations falling | Escalation rate is monitored; a fall without a change in case mix is investigated. (Not statically observable — proxy only.) | Drift Watch; EU AI Act Art. 9 | Medium | `prompts/audit-use-cases/agent-drift-rater.md` |
| RF5 — Softening language | Agent-written notes/memory are reviewed; rule wording is not quietly weakened ("required" → "plausible"). | Drift Watch; EU AI Act Art. 12 | Medium | `prompts/audit-use-cases/agent-drift-rater.md` |
| RF6 — No replayable log | Each decision links to its instruction/model version, inputs, tool calls, and outcome. | OWASP LLM02 (log hygiene); EU AI Act Art. 12 | High | `prompts/audit-use-cases/agent-drift-rater.md` |

## Controls to expect (the five "evidence to ask for")

| Control | Auditable control | Frameworks | Risk Rating | SAAF Prompt Reference |
|---|---|---|---|---|
| C1 — Hard rules in code + guard test | Hard limits enforced in code, with a test proving the guard blocks a violating action regardless of model output. | OWASP LLM07, LLM06; EU AI Act Art. 15, 9(6-8) | High | `prompts/audit-use-cases/agent-drift-rater.md` |
| C2 — Versioned instructions | Instructions, memory, and model are versioned and diffed against an approved baseline. | OWASP LLM04, LLM03; EU AI Act Art. 11, 12 | Medium | `prompts/audit-use-cases/agent-drift-rater.md` |
| C3 — Independent drift review | An independent review (tests, evals, a validator, or drift metrics) checks the agent's behaviour. | OWASP LLM09; EU AI Act Art. 9, 72 | Medium | `prompts/audit-use-cases/agent-drift-rater.md` |
| C4 — Oversight, rollback & quarantine | A human approves mandated actions; a rollback/quarantine path exists and has been exercised. | OWASP LLM06; EU AI Act Art. 14(4) | High | `prompts/audit-use-cases/agent-drift-rater.md` |
| C5 — Replayable decision log | Every decision can be re-performed from the logged input, instruction and model version, tool calls, and outcome. | OWASP LLM02; EU AI Act Art. 12, 26(6); IIA 2340 | High | `prompts/audit-use-cases/agent-drift-rater.md` |

## SAAF guardrails cross-check

Permission creep (driver D5) is also checked against `regulatory/guardrails/allowed-commands.md`:
shell or `eval`/`exec` on model output, prohibited command tokens (`rm`, `sudo`, `curl`, `wget`,
`ssh`, `pip install`) in the agent's own code, and permission-bypass modes
(`bypassPermissions`, `--dangerously-skip-permissions`) each raise the agency risk.

---

## Audit Objectives

1. Confirm the agent has a documented, approved mandate against which drift can be detected.
2. Verify that each stated hard rule is enforced in code, not only in the prompt.
3. Confirm the agent cannot rewrite its own instructions, memory, or tools unreviewed.
4. Confirm untrusted input cannot drive privileged actions without a code-enforced guard.
5. Confirm every decision is replayable from a log that records the instruction and model version.

---

## Evidence Typically Required

- The approved mandate (AUDIT-CRITERIA.md, policy, or plan) and its version history.
- Code showing each hard rule enforced before the action, plus a test proving the block.
- The instruction/prompt versioning and baseline-diff mechanism.
- The decision log schema and a sample entry with instruction and model version.
- The rollback/quarantine procedure and evidence it has been exercised.
- The tool/command allowlist and the agent's permission configuration.
