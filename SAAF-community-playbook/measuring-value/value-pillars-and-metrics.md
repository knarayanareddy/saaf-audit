# Value Pillars And Metrics

The chapter measures four pillars. No more. The pillars are anchored
in the executive's existing decision frameworks, not in a separate
"community measurement" framework.

This page describes the pillars, the metrics under each, and the
distinction between *activity metrics* (which look like measurement
but aren't) and *outcome metrics* (which actually inform decisions).

---

## The Four Value Pillars

```
Pillar 1: Audit hours returned
Pillar 2: Coverage and confidence
Pillar 3: Risk surfaced earlier
Pillar 4: Capability and resilience
```

Each pillar answers a question the executive sponsor or endorsing
body already asks about audit work — not a new question invented by
the chapter.

| Pillar | Executive question it answers | Why it matters |
|---|---|---|
| Audit hours returned | "How much auditor time has the chapter saved?" | Easiest to measure, easiest to misuse. |
| Coverage and confidence | "Where has the chapter expanded what we can audit, or how reliably?" | The most defensible of the four pillars. |
| Risk surfaced earlier | "What risks did the chapter find before they would otherwise have surfaced?" | The highest-impact pillar. Slow but worth it. |
| Capability and resilience | "What can our people do now that they couldn't before?" | The most durable. Underweighted by short-term sponsors. |

---

## Activity vs. Outcome Metrics

This is the single most important distinction in the playbook.

### Activity metrics

Activity metrics describe what the chapter *did*:

- Number of attendees per session.
- Number of organisations represented.
- Number of plans submitted.
- Number of plans built.
- Hours of build time.
- Demo count at sessions.
- Channel messages per week.

These metrics are easy to gather and easy to report. They are also
easy to dismiss. An executive seeing "we had 80 attendees from 45
organisations" cannot decide anything based on it.

Activity metrics belong in the recap, not in the executive readout.
They are the chapter's internal pulse — useful for the captain,
mostly invisible to the sponsor.

### Outcome metrics

Outcome metrics describe what the chapter *changed*:

- Audit hours returned per task, on what population.
- New audit coverage enabled (how many controls / records / domains).
- Risks surfaced earlier than baseline, with evidence.
- Plans completed (reached Act), with the artefact in production.
- People who can now build/review AI-assisted output, vs. baseline.

Outcome metrics are harder to gather and harder to report honestly.
They are what an executive can act on. They are the right basis for
the quarterly readout.

### A useful test

Before reporting any metric, ask: *"What would the executive sponsor
do differently if this number doubled, halved, or stayed the same?"*

If the answer is "nothing different," it is an activity metric. Either
move it to the chapter's internal pulse (still useful) or drop it.

---

## Pillar 1 — Audit Hours Returned

**Question:** Has the chapter freed measurable auditor time?

**Sub-metrics:**

| Metric | How to measure | Caveats |
|---|---|---|
| Hours per audit task on synthetic data | Time the agent vs. the manual process on a comparable test set. | Synthetic-data results don't always match live; state the assumption. |
| Hours per audit task on live data | Repeat the comparison post-pilot, on real data, behind the firewall. | Available only at Check stage. |
| Annualised hours estimate | Per-task hours × annual task volume. | Highly sensitive to task-volume assumptions; show the assumption. |
| Adoption rate of an artefact | Number of audit teams using a community-contributed artefact. | Indirect measure; better than nothing for new chapters. |

**Reporting language:**

Good: *"Evidence-extraction agent reduced PBC review time from 90
min/document to 25 min/document on a 30-document synthetic test set.
At our current PBC volume of ~400/year, that is roughly 430 hours of
senior auditor time, *if* live performance matches synthetic. Live
validation in Q3."*

Bad: *"Saved 430 hours."*

The bad version is misleading and unauditable. State the population,
the assumption, and the validation status.

---

## Pillar 2 — Coverage And Confidence

**Question:** Has the chapter extended what audit can cover, or how
reliably it can do so?

This is often the most defensible pillar because it doesn't require
hour-counting. The artefact either works on a population the manual
process couldn't reach, or it doesn't.

**Sub-metrics:**

| Metric | How to measure |
|---|---|
| Population coverage | "Manual process: 25-record sample. Agent: 100% of 200-record population." |
| Cross-framework mapping breadth | "Manual process: ISO 27001 only. Agent: ISO 27001 + DORA + GDPR." |
| Audit domain coverage | New domains the chapter's agents now cover that the audit team did not previously address. |
| Reproducibility | Same prompt, same input, same output, across at least two stacks. |

**Reporting language:**

Good: *"Synthetic access-review agent reviewed all 200 records in
the test population vs. our prior 25-item sample. Three exceptions
that would have been missed by sampling were detected. Methodology
team is updating the sampling guidance."*

Bad: *"Improved coverage."*

The bad version doesn't say what was covered or by how much. The good
version names the population, the prior baseline, and the
consequence (methodology change).

---

## Pillar 3 — Risk Surfaced Earlier

**Question:** What risks did the chapter find that the standard audit
cycle would have found later, or not at all?

This is the highest-value pillar in executive eyes. It is also the
slowest to accumulate and the hardest to attribute. Most chapters do
not have a clean Pillar 3 result in their first year. That is fine.

**Sub-metrics:**

| Metric | How to measure |
|---|---|
| Findings produced earlier than baseline | "Standard quarterly review would have surfaced this in Q3; community agent surfaced it in Q1." |
| Control gaps discovered through community work | New gaps in existing control universes. |
| Regulatory mismatches identified | Discrepancies between policy, control, and current regulation, found by community-built monitors. |
| Cross-organisation patterns visible only at chapter scale | "Three organisations independently saw [pattern]; the chapter is the place that saw it." (Regional chapters only.) |

**Reporting language:**

Good: *"Regulatory change tracker flagged a draft DNB circular six
weeks before our standard quarterly review would have surfaced it.
Three control owners had time to update before the publication date."*

Bad: *"Helped identify regulatory risk."*

The good version is specific: which finding, what timing
differential, what consequence. The bad version is unfalsifiable.

---

## Pillar 4 — Capability And Resilience

**Question:** What can our people do now that they couldn't before?

This pillar matures slowly — capability grows over months, and the
metrics are softer than the other three. But the long-term value of
the chapter is in this pillar more than in any of the others.

**Sub-metrics:**

| Metric | How to measure |
|---|---|
| People who completed an "AI-assisted audit walkthrough" | Count of auditors who have run, reviewed, or signed off on an AI-assisted output. |
| Roles filled internally that previously required external help | E.g. "Three audits in Q4 used in-house AI-assisted analytics that we previously outsourced." |
| Internal contributions to plans | Plans submitted, claimed, or built by internal members. |
| Cross-team contribution | Number of distinct teams (or organisations, for regional) actively contributing. |

**Reporting language:**

Good: *"Twelve auditors completed the 'review an AI-generated
finding' walkthrough this quarter, up from three last quarter. Audit
plan for next year includes two engagements that we previously would
have outsourced for lack of internal capacity."*

Bad: *"Strong capability building this quarter."*

The good version connects capability to a *decision* — what's now in
the audit plan that wasn't before. The bad version is opinion.

---

## What To Avoid Measuring

Some metrics are easy to gather and actively counterproductive:

| Metric | Why to avoid |
|---|---|
| Net Promoter Score for sessions | Audit professionals over-rate everything social and under-rate everything technical. NPS is noise. |
| "Engagement score" combining multiple signals | A single composite hides the underlying signals. Show the components. |
| Vanity metrics (LinkedIn impressions, recap downloads) | Optimising for these creates content production work that isn't the chapter's job. |
| Per-organisation contribution rankings | Pits member organisations against each other; breaks neutrality. |
| Sentiment surveys ("how do you feel about the chapter?") | Don't generate decisions; do generate captain anxiety. |

Resist the request to measure these even if a stakeholder asks. Offer
alternatives that map to the four pillars instead.

---

## A Minimum Measurement Footprint

The smallest useful measurement set, for a chapter in its first year:

- **Plans by PDCA stage**, updated after every session.
- **One Pillar 1 result** per quarter (ideally with assumption stated).
- **One Pillar 2 result** per quarter.
- **Roll-call list** updated annually for Pillar 4.

That's it. Pillar 3 results take longer to mature; report them when
they exist, not on a forced cadence.

A chapter that consistently produces this minimum footprint, well,
will be evaluated more positively by executives than a chapter
producing a forty-metric dashboard.

---

## When Measurement Matures

In years two and three, the chapter can consider:

- **Cross-pillar attribution.** A single artefact contributing to
  multiple pillars — e.g. a regulatory tracker that returns hours
  (Pillar 1), expands coverage (Pillar 2), and surfaces risks
  earlier (Pillar 3).
- **Longitudinal capability tracking.** People who completed the
  first walkthrough a year ago — what are they doing now?
- **Sponsor-defined metrics.** Once trust is established, the
  sponsor sometimes asks for a specific metric. Provide it carefully
  and within the four-pillar frame.

**Measurement should mature as credibility grows.** Don't reach for
sophisticated measurement before the chapter has earned the
credibility to be measured against it.
