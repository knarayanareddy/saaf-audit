# Plans And PDCA

A SAAF plan is a one-page-ish document describing an agent, skill, or
workflow that someone wants to build. Plans are the unit of currency
in the chapter. They persist across sessions, accumulate claims, and
move through Plan → Do → Check → Act over their lifecycle.

This page is about how plans work in practice — how they're submitted,
claimed, built, and tracked.

---

## What A Plan Is (And Isn't)

A plan **is**:

- A one-page document describing the use case, the four-pillar
  components, the inputs/outputs, and the open questions.
- Owned by one named person — pseudonyms permitted.
- Filed in the chapter's repo (or contributed to the main SAAF
  Project's repo) before the session it is intended for.
- Available for any other contributor to claim, fork, or extend.

A plan **is not**:

- A guarantee that someone will build it.
- A finished design — open questions are welcome and expected.
- A vendor pitch — products belong in another forum.
- A research paper — five hundred words of prose without a use case
  is not a plan.

The main SAAF Project maintains a plan template; chapters can use
it directly or adapt it. The template lives at
[appendix/templates/plan-submission.md](../appendix/templates/plan-submission.md).

---

## The Plan Lifecycle Across Sessions

```
Submission        Claim             Build (Do)        Validate (Check)     Share back (Act)
────────────      ─────────         ──────────         ───────────────      ───────────────
Member writes     A team            Working agent      Tested inside        Lessons learned
plan, files PR    claims it on      built at the       a member org's       contributed to
weeks before      session day       hackathon          firewall, on real    chapter recap
session.          or in advance.    using synthetic    or anonymised data.  and to national
                                    data.                                   SAAF Project.
```

Plans persist between sessions. A plan submitted before session 3 and
not built that day is still live for sessions 4, 5, 6, and beyond.
The chapter does not retire plans; it just doesn't always work on
all of them.

A plan is *complete* when it has reached **Act** — i.e. someone has
shipped a working version, validated it inside an organisation, and
documented what was learned. At that point it stops being a plan and
becomes a contributed artefact in the four-pillar repository.

---

## Claiming A Plan

Plans are claimed in three places. The federation's primary surface
for claiming is the **[SAAF Portal](../measuring-value/saaf-portal.md)**
— members browse tracks and plans there, and claim them in advance.
The fallback is a direct PR to the plan file. Either mechanism feeds
the same `Claimed By` field.

### Before the session — the soft claim

Members claim a plan in the [SAAF Portal](../measuring-value/saaf-portal.md)
(preferred) or by submitting a PR adding their name to the plan's
`Claimed By` field. This signals to the room — and to the rest of
the federation — that the plan has a likely builder.

A soft claim is not exclusive. If two people soft-claim the same
plan, the captain pairs them up before the session. The portal makes
this visible early, so pairing can happen weeks in advance instead
of on the day.

### On the day — the hard claim

The claim moment after the plan walkthrough. Whoever physically sits
at the table for a plan claims it for the day. Soft claims are
honoured, but the on-the-day team is the one that builds.

### Post-session — the carry claim

If a team made progress but didn't ship, they can carry the plan
forward by updating its `Claimed By` field (in the portal or via PR)
with their name and a target session. The captain confirms the carry
in the recap.

A plan that has been carried forward three sessions without
completing is a plan that needs to be re-scoped. The captain or track
lead works with the carry-claimer to either narrow the scope, recruit
help, or formally hand off to a new owner.

---

## Plan Quality

Not all plans are equal. The main SAAF Project scores plans 1–5
on completeness:

- **1** — Idea only. One paragraph.
- **2** — Use case described. No prompt, no tool, no schema.
- **3** — Use case + at least one of: prompt template, tool design,
  output schema. Some open questions called out.
- **4** — All four pillars covered, even thinly. Open questions clear.
  Could be claimed and built.
- **5** — Production-ready template. Working prompts, named tools,
  regulatory mapping, output schema. Could be implemented from the
  document alone.

You do not need to score plans formally in your chapter. But the
captain should know roughly where each plan sits, because:

- Score-2 plans are great for senior auditors (who can shape them) but
  bad for first-timers (who need more structure).
- Score-4 plans are great for first-timers (who can follow them) and
  bad for senior contributors (who get bored).
- Score-5 plans should usually go straight to a Check pilot inside a
  member organisation, not be re-built at a hackathon.

Use the score informally to match plans to people.

---

## How Many Plans Should A Session Have?

Rough ratios:

| Session size | Plans on the day | Plans submitted in advance |
|---|---|---|
| 30 people | 6–10 plans | 8–12 plans (some carry over) |
| 50 people | 10–15 plans | 14–20 |
| 80 people | 15–25 plans | 20–30 |

If you have many more plans than the session can claim, that is
healthy — it means the chapter is producing supply faster than the
day can consume it. Carry forward the unclaimed.

If you have fewer plans than the session needs, do not run the
session yet. Push the date and recruit plans first.

---

## The Three Plan Types

Following the SAAF NL convention:

| Type | Definition | Example |
|---|---|---|
| **Agent** | Autonomous, multi-step execution. Has its own system prompt and calls one or more tools to complete an audit task without continuous human steering. | A vendor risk pre-screen agent. |
| **Skill** | Single-purpose reusable capability. Typically a prompt paired with a parsing function — easily composed into larger agents or workflows. | A regulatory-text retrieval skill, an OWASP-LLM-Top-10 prompt skill. |
| **Workflow** | Orchestrated sequence of agents and/or skills with defined human checkpoints. | An end-to-end audit reporting workflow. |

A plan that says "agent" but describes a workflow is a plan that needs
re-scoping. Likewise for skill / agent confusion. The type is not
ornamental; it determines how the plan gets built.

---

## How PDCA Status Is Tracked

Each plan has a PDCA status field. The captain updates it:

- After every session (mass update during recap).
- Whenever a member organisation reports progress in the Check or
  Act stage between sessions.

A simple text field is fine:

```
PDCA Status: Plan
PDCA Status: Do (in progress, claimed by [name], target session [date])
PDCA Status: Do (complete, demoed at [session])
PDCA Status: Check (in progress, validating at [organisation])
PDCA Status: Act (complete, lesson learned filed at [URL])
```

The chapter's plan portfolio at any moment shows where every plan is.
This is the single most useful artefact for the executive sponsor or
endorsing body — it is the visible evidence of compounding work.

---

## Cross-organisation Plans (Regional Chapters Only)

A regional chapter sometimes has plans that no single organisation
can build alone — for example, a control-mapping agent that requires
control libraries from three different firms.

Handling:

- The plan calls out the cross-organisation requirement explicitly.
- Each organisation contributes a sanitised / synthetic version of
  their input.
- The build happens in a shared sandbox using only those synthetic
  inputs.
- The Check stage happens *separately* inside each organisation,
  with each organisation's real data.
- The Act stage shares back the methodology, not the data.

This is the SAAF model at its most powerful — a plan that no single
organisation could afford to build, made possible by sharing the
shape of the problem.

---

## Plan Hygiene Rules

A few simple rules keep the plan portfolio readable:

- **One plan per file.** Don't bundle.
- **Names, not pseudonyms-only, in the contributor section** —
  pseudonyms are fine in the `Claimed By` field, but the
  contribution log should make it possible to credit the person.
- **No client names. No real data references.** Plans are public
  (or chapter-public). Anything that could not survive being seen by
  a competing organisation should not be in the plan.
- **No vendor naming in the use-case description.** Vendor naming is
  fine in the *implementation notes* of a plan ("we used [vendor's]
  API for the prototype"), but the use case must be vendor-neutral.

---

## Cross-reference

For the plan submission template, see
[appendix/templates/plan-submission.md](../appendix/templates/plan-submission.md).
For how plans flow back to the main SAAF Project, see
[../feeding-back-to-saaf/contribution-flow.md](../feeding-back-to-saaf/contribution-flow.md).
