# Lessons Learned

A lesson learned is a single concrete thing the chapter discovered,
written so that another chapter (or another organisation) can use
it. It is the highest-value artefact a chapter produces, and the
most often half-done.

This page is the format the main SAAF Project consumes. Use it
in your own chapter's recaps and contribute selected lessons back.

---

## What A Lesson Learned Is

A lesson learned **is**:

- A single concrete observation, not a theme.
- Specific enough that another chapter could apply it.
- Honest about what didn't work.
- Time-bounded — when it was learned, by whom, in what context.

A lesson learned **is not**:

- A best practice (these are too generic).
- A position paper (too long).
- A retrospective summary (covers too much).
- Marketing.

A useful test: *"Could another captain, reading this, do something
differently next week as a result?"* If yes, it's a lesson. If no,
it's a reflection — keep it for your own running log.

---

## The Format

Each lesson learned is a short markdown file with a fixed structure:

```markdown
---
title: [Specific lesson, in active voice]
chapter: [Chapter name]
session: [Session number or date]
contributors: [Names or pseudonyms]
pillar: [The relevant SAAF pillar, or "operations" for chapter-running lessons]
date: [YYYY-MM-DD when filed]
---

## What we did

[1–3 sentences. Specific. What was the action that produced this lesson.]

## What happened

[1–3 sentences. The result, including the unexpected. Numbers where
relevant.]

## What we'll do next time

[1–3 sentences. The forward-looking action. Specific enough to
implement.]

## Why this matters to other chapters

[1–3 sentences. Who benefits from knowing this, and under what
conditions. If the lesson is highly chapter-specific, say so.]
```

That's the whole format. A lesson learned should fit on one screen.

### Example: A practical lesson

```markdown
---
title: Multi-socket extension strips on every table prevent mid-sprint power outages
chapter: SAAF Belgium
session: Hackathon 2 — March 2026
contributors: Jan Bakker, Mira de Vries
pillar: operations
date: 2026-04-12
---

## What we did

Booked the venue without confirming outlet density. The room had
twelve outlets for forty laptop users.

## What happened

Three teams ran out of laptop battery during build sprint 2. One
team's demo was lost when their laptop died and they hadn't pushed
their work. Twenty minutes of the demo session was eaten by recovery
attempts.

## What we'll do next time

Bring multi-socket extension strips for every table — at minimum two
per table for ~6 laptops. Verify outlet count at the pre-event
walkthrough, not from the venue's PDF.

## Why this matters to other chapters

Outlets are the most underestimated venue requirement. Most venues
do not have one outlet per laptop. The fix is cheap (extension
strips cost ~€10 each), but only if you remember to bring them.
```

### Example: A use-case lesson

```markdown
---
title: Synthetic data for vendor risk scoring needs at least three risk profiles to surface scoring drift
chapter: SAAF Project (national)
session: Hackathon 1 — March 2026
contributors: robeminem94
pillar: tools
date: 2026-04-02
---

## What we did

Ran the vendor risk pre-screen agent on a synthetic vendor dataset
with a single risk profile (a low-risk supplier with clean data).

## What happened

The agent scored every test case "low risk." We could not
distinguish between an agent that was working and one that was
trivially returning the most common label.

## What we'll do next time

Generate synthetic vendor data across at least three risk profiles
(low, medium, high) before testing. Validate by running known-high-
risk and known-low-risk inputs and checking the scores diverge.

## Why this matters to other chapters

Any agent that produces a categorical or numeric score needs
synthetic test data spanning the score range. Single-profile data
gives false confidence and masks scoring degeneracy. This applies
to vendor risk, fraud risk, compliance risk, and any classification
agent.
```

---

## What To Capture As A Lesson

After every session, the chapter typically produces three to seven
lessons. Distinguish two categories:

### Operational lessons

About running the chapter. Venue, logistics, agenda timing,
recruitment, sponsor communication, demo formats. Most go in your
own chapter's running log; a few should be contributed back because
they help other chapters.

Operational lessons benefit other chapters most when they are about:

- A failure mode that's easy to repeat (the wifi pattern, the outlet
  pattern, the keynote-runs-long pattern).
- An unusual format that worked (a particular demo structure, a
  particular onboarding ritual).
- A diagnostic question that surfaced something invisible.

### Use-case / artefact lessons

About what the chapter built. Specific to a plan, a prompt, a tool,
a control mapping. These are the lessons that compound across
chapters because they prevent rebuilding the same wrong thing.

Use-case lessons benefit other chapters most when they are about:

- Why a particular approach didn't work (negative results are
  scarce and valuable).
- A specific data shape, prompt structure, or output schema that
  consistently produced better results.
- A regulatory mapping that turned out to be more / less complex
  than expected.

---

## What Not To Bother Filing

Some "lessons" are not worth filing — neither in your own log nor
upstream:

- *"We need to communicate better."* Too generic. What specifically?
- *"AI is changing fast."* True; not actionable.
- *"More auditors should attend."* Aspirational, not a lesson.
- *"The session went well."* That's a recap, not a lesson.

If the lesson can't survive the "could another captain act on this"
test, don't file it. The lessons-learned folder degrades fast when
it accumulates filler.

---

## How Lessons Get Used

Lessons learned at the main SAAF Project are read by:

- New chapter captains, before launching their first session.
- Returning chapter captains, before each session as a checklist.
- Sponsors and endorsing bodies, when assessing the chapter's
  rigour.
- Other communities (security champions programmes, vendor
  partners) that look to SAAF as a reference.

The format is therefore optimised for re-use, not for narrative
flow. Specific titles, specific actions, specific outcomes.

---

## When To Contribute Back

After every session, the chapter should:

- File three to seven lessons in the chapter's own log (visible to
  chapter members).
- Identify one to three lessons worth contributing upstream.
- Open a PR contributing those lessons to the main SAAF Project's
  `docs/lessons-learned/` folder.

Don't hold lessons for an annual roundup. Lessons land best when
they are fresh and specific. The national project's lessons-learned
folder is the chapter's most durable contribution; treat it as such.

---

## Cross-reference

The main SAAF Project maintains a session-recap template and a
lesson template; defer to those if they conflict with what's
written here. The format above is recommended for new chapters
that don't yet have an established style.

For the broader recap, see
[../running-hackathons/post-event-recap.md](../running-hackathons/post-event-recap.md).
For the PR mechanics, see [contribution-flow.md](contribution-flow.md).
