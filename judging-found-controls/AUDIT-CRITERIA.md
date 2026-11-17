# `AUDIT-CRITERIA.md` — template

> **Copy this file into your agent repo as `AUDIT-CRITERIA.md` and fill it in.**
> It sits **next to** your `README.md`, not inside it. The README says *what the agent does and how to run it*; this document says *what the agent must be judged against as an auditee* — its control objectives, testable acceptance criteria, and known limits.
>
> This is a SAAF standard (produced by the **A2 — Audit Criteria & Controls** track). Stress-test teams (**A1**) test against the acceptance criteria you write here. Keep it in English. Reference, don't reinvent: link findings to `outputs/schemas/finding-schema.json` and frameworks to `docs/reference/domains-and-frameworks.md` in the main SAAF-Project repo.

---

## Metadata

| Field | Value |
|---|---|
| **Agent** | Judging Found Controls |
| **Repository** | https://github.com/SAAF-Project/judging-found-controls |
| **Maintainer(s)** | unknown |
| **Last reviewed** | 2026-09-15 |
| **Status** | Draft |

## 1. What the agent does

Validates that each control extracted from a policy document is actually grounded in the source text, returning a machine-readable verdict per control.

## 2. Control objectives & framework mapping (≥3)

This agent does not test control objectives. It tests if found control objectives are grounded in a source truth. This cannot be mapped to a known framework.

## 3. Acceptance criteria (testable, pass/fail)

There are no control objectives that can be mapped to a known framework.

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ All controls in the input | ✕ Hallucinate that a control is present in the source when it is not |
| ✓ Give a partial verdict instead of yes or no | ✕ Hallucinate and come up with controls not in the input |
| ✓ The related paragraph per control | ✕ Never invent or paraphrase policy text. |
| ✓ Correct classifications for all controls | ✕ Never return found: "yes" only because the control seems reasonable or standard practice |
| ✓ Return output as a json object | ✕ - Never return prose outside the JSON object.|

## 5. Coverage gaps

Controls or capabilities an auditor would reasonably expect that the agent does **not** (yet) cover. Be honest — this is where the next plan/iteration starts.

- Not currently known.

## 6. Status / validation

Which criteria are already verified (live run / tests) and what is still open. Link evidence (test run, A1 stress-test report) where you can.

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-1 #1 | ☐ / ☑ | … |