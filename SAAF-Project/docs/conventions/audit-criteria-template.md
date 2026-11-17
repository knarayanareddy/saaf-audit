# `AUDIT-CRITERIA.md` — template

> **Copy this file into your agent repo as `AUDIT-CRITERIA.md` and fill it in.**
> It sits **next to** your `README.md`, not inside it. The README says *what the agent does and how to run it*; this document says *what the agent must be judged against as an auditee* — its control objectives, testable acceptance criteria, and known limits.
>
> This is a SAAF standard (produced by the **A2 — Audit Criteria & Controls** track). Stress-test teams (**A1**) test against the acceptance criteria you write here. Keep it in English. Reference, don't reinvent: link findings to `outputs/schemas/finding-schema.json` and frameworks to `docs/reference/domains-and-frameworks.md` in the main SAAF-Project repo.

---

## Metadata

| Field | Value |
|---|---|
| **Agent** | [name] |
| **Repository** | [url] |
| **Maintainer(s)** | [who owns this] |
| **Last reviewed** | [YYYY-MM-DD] |
| **Status** | Draft / Reviewed / Validated |

## 1. What the agent does

Plain language: purpose, input, output, and the audit task it supports. (2–4 sentences.)

## 2. Control objectives & framework mapping (≥3)

State the outcomes the agent supports or tests, each tied to a recognised framework. A control objective describes an outcome (e.g. *"Access to production is restricted to authorised personnel and reviewed periodically"*).

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| CO-1 — … | e.g. IIA Global Internal Audit Standards, Domain V | … |
| CO-2 — … | e.g. COSO 2013 / ISO 27001 Annex A | … |
| CO-3 — … | e.g. EU AI Act Art. 13 & 14 | … |

*Framework menu: ISO 27001 · GDPR · DORA · NIS2 · EU AI Act · COSO · COBIT · SOx (ICFR) · IIA Global Internal Audit Standards · OWASP (LLM/AI). Full catalogue: `docs/reference/domains-and-frameworks.md`. Name a clause only when you are sure of it: the framework and the area are enough.*

## 3. Acceptance criteria (testable, pass/fail)

Per control objective, concrete pass/fail statements a tester can run against synthetic data. Pattern: *"Given X, the agent does Y."* Every criterion has a fixed number (`CO-1.2` is the second criterion of objective 1) and one tag.

*Tags: `[code]` when a program can decide it exactly, `[llm]` when someone, or a model acting as judge, has to read the run; it does not matter whether the agent itself calls a model. The tag and the number come first on the line. One failure mode per line. A number stays with its criterion: a new criterion gets the next number, a removed number is not used again.*

**CO-1**
- [code] CO-1.1 Given …, the agent … .
- [llm] CO-1.2 Given …, the agent does not … .

**CO-2**
- [code] CO-2.1 Given …, the agent … .

**CO-3**
- [llm] CO-3.1 Given …, the agent … .

## 4. Good output / never do

Numbered and tagged like the acceptance criteria: `M-1` for must, `N-1` for never.

| # | A correct output MUST contain | # | The agent must NEVER |
|---|---|---|---|
| M-1 | ✓ [code] … | N-1 | ✕ [llm] Invent facts / citations not in the input |
| M-2 | ✓ [code] … (findings conform to `finding-schema.json` where applicable) | N-2 | ✕ [llm] Present output as audit-ready with no human-review gate |
| M-3 | ✓ [llm] … | N-3 | ✕ [code] Run commands outside the allowlist (`regulatory/guardrails/allowed-commands.md`) |
| M-4 | ✓ [llm] … | N-4 | ✕ [code] Hard-code credentials or secrets |

## 5. Coverage gaps

Controls or capabilities an auditor would reasonably expect that the agent does **not** (yet) cover. Be honest — this is where the next plan/iteration starts.

- …
- …

## 6. Status / validation

Which criteria are already verified (live run / tests) and what is still open. One row per number. Link evidence (test run, traced run, A1 stress-test report) where you can.

| Criterion | Verified? | Evidence |
|---|---|---|
| CO-1.1 | ☐ / ☑ | … |
| CO-1.2 | ☐ / ☑ | … |
| M-1 | ☐ / ☑ | … |
| N-1 | ☐ / ☑ | … |
