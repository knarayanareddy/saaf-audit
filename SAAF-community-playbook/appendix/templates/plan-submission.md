# Plan Submission — Template

> The plan template used at chapter sessions. Adapted from the
> main SAAF Project's plan template; defer to the upstream
> version if the chapter is contributing back directly.

---

```markdown
---
title: [One-line use-case description]
type: [Agent | Skill | Workflow]
submitter: [Name or pseudonym]
organisation: [Optional — leave blank if pseudonymous]
chapter: [Chapter name]
session: [Hackathon number or date]
audit_domain: [Audit domain — see docs/reference/domains-and-frameworks.md upstream]
status: Plan
claimed_by: [Name(s) — leave blank if unclaimed]
date_submitted: [YYYY-MM-DD]
---

## 1. Use Case Summary

[One paragraph. What audit problem does this solve? Who benefits?
What is the concrete improvement over the manual baseline?]

## 2. Type And Scope

[Why this is an agent / skill / workflow rather than the others.
What it includes; what it deliberately doesn't.]

## 3. Inputs And Outputs

**Inputs:**
- [Input 1: what kind of data, in what format, from where]
- [Input 2]

**Outputs:**
- [Output 1: format, schema reference, where it goes]
- [Output 2]

## 4. Prompts (Pillar 1)

[The system instructions and the user-prompt template. Use the
SAAF prompt convention — metadata header, system context block,
user prompt template with [placeholder] syntax. If you don't have
prompts yet, list the prompt-shaped questions the agent needs to
ask.]

## 5. Tools (Pillar 2)

[The tools / APIs / MCPs the agent uses. Pseudocode is fine; full
implementation is great. List dependencies; mark which are
already available in the SAAF repo and which need to be built.]

## 6. Regulatory (Pillar 3)

[The control mappings, frameworks, or regulatory criteria this
plan addresses. Cite specific clauses where possible (DORA Article
13, ISO 27001 A.8.16, EU AI Act Article 6, etc.). Note any AI
guardrails — what the agent must not do.]

## 7. Outputs Schema (Pillar 4)

[The structured output the agent produces. Reference
`outputs/schemas/finding-schema.json` if applicable; otherwise
specify the schema for this plan.]

## 8. Demo Plan

[How will this be demoed at the session? What synthetic data is
needed? What does success look like in a 5-minute demo?]

## 9. Open Questions

[List of things you don't know yet. Open questions are welcomed,
not penalised. The community will help.]

## 10. PDCA Status

- **Plan:** [Date submitted]
- **Do:** [Status: not started | in progress | complete; date]
- **Check:** [Status: not started | in progress | complete; org
  where validated; date]
- **Act:** [Status: not started | complete; lesson learned URL;
  date]

## 11. Lessons Learned (Filled After Act)

[1–3 sentences per lesson. See feeding-back-to-saaf/lessons-learned.md
for the format.]

## 12. Cross-references

- Related plans: [Links to other plans in the repo]
- Related artefacts: [Links to existing prompts, tools, schemas]
- Standards: [Links to applicable standards documents]
```

---

## Notes On Use

- Plans are **public** (or chapter-public). Don't include client
  names, real data references, or anything that would not survive
  being read by a competing organisation.

- If a section doesn't apply, write *"Not applicable"* with a
  reason. Don't leave sections blank without comment — the
  main SAAF Project's plan-quality scoring rewards completeness
  and treats blanks as missing.

- The `claimed_by` field signals to others whether someone is
  actively building this. If you soft-claim a plan in advance,
  add your name. If you finish a session having built only a
  partial implementation, update the field with "[Name] (carry
  forward to [next session])."

- **Pseudonyms permitted** in `submitter` and `claimed_by`. Use
  whichever identity you'd want to see on the artefact in five
  years.

- **Type matters.** If the plan describes an agent that orchestrates
  multiple skills with human checkpoints, that's a workflow. If it
  describes a single prompt + parsing function, that's a skill.
  Mis-typing a plan makes it harder to claim and harder to compose.

- Lessons learned are filled after the plan reaches Act. Until
  then, the section is empty.
