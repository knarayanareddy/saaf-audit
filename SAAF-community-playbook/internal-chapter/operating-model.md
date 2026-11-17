# Operating Model

The first 90 days, and the recurring rhythm that follows.

This page is the *operations manual* for an internal chapter. If you
read it and immediately want to add more meetings, you are misreading
it. The point is to do as little ceremony as possible while still
keeping the work coherent.

---

## The First 90 Days

### Days 0–30: Setup, not launch

The first month is invisible work. No public announcement, no kickoff
event. You are putting the conditions in place so that your launch
event has something real to anchor on.

Tasks for the founding captain (and co-captain):

1. **Write the chapter charter.**
   ([template](../appendix/templates/chapter-charter.md)) — one page.
   Vision, scope, sponsor, governance, manifesto adoption, success
   criteria for year one.
2. **Get sponsor sign-off in writing.**
   Email is fine. Verbal is not. The charter goes in an email; the
   sponsor replies "approved" in the email.
3. **Recruit the founding three to five champions.**
   See [identifying-champions.md](identifying-champions.md). Have a
   one-on-one with each. Send a manager brief to each champion's
   manager.
4. **Decide cadence and venue.**
   Quarterly is the safest default. Monthly only if you have a
   dedicated facilitator and a steady stream of plans. Pick the venue
   for sessions one and two before announcing session one.
5. **Stand up the minimum viable infrastructure.**
   - A shared repo or folder (for plans, recaps, prompts).
   - A communication channel (Slack / Teams) — *one*, not three.
   - A calendar that lists the next four sessions.
6. **Write the launch announcement.**
   Do not send it yet.

### Days 31–60: Pre-launch dry run

Before going public, run a small, invitation-only proof event. Six to
ten people, two hours, one shared problem. Treat it as a session-zero
hackathon. Use it to:

- Validate the format works in your organisation's context.
- Stress-test the venue, the wifi, the AV, the room layout.
- Find the first two plans that will be the headline of the launch
  session.
- Write the recap from session zero, even though it is internal.

If session zero feels forced, do another. Do not launch publicly with
a format you have not actually run.

### Days 61–90: Public launch

Send the announcement. The launch session is the third session, not
the first — sessions zero and minus-one already happened privately.
This is why the launch can include a real demo and real plan
submissions. There is no "blank page" energy.

The launch is also where the executive sponsor speaks for five to ten
minutes, in person, to the room. Not virtually. Not by recorded video.
In person. The sponsor's body language in that room is read more than
their words.

After the launch session, write the recap within seven days. Send it to
the sponsor, the sponsor's peers, and the participants' managers. Cc
matters. Champions should be visible to their managers via the recap,
not via their own self-promotion.

---

## The Recurring Rhythm

Once the chapter is past 90 days, settle into a rhythm. Resist the
temptation to add more.

### Weekly

| Cadence | What | Owner |
|---|---|---|
| 30-min organiser huddle | Captain + co-captain. What's in flight, what's blocked, what next session looks like. | Captain |
| Async channel triage | Read the channel, surface threads worth a wider audience, reply to questions. | Champions on rotation |

### Monthly

| Cadence | What | Owner |
|---|---|---|
| 5-line update to sponsor | Email. What shipped, what's blocked, what decision needed. | Captain |
| 1-hour champion meet | Optional. Discuss plans coming up, recruitment, any drift. | Captain |
| One demo / show-and-tell | 45 minutes. Someone shows what they built. Recorded for those who can't attend. | Rotating |

### Quarterly

| Cadence | What | Owner |
|---|---|---|
| The hackathon session | Full day. See [running-hackathons/](../running-hackathons/). | Captain + facilitators |
| Quarterly readout | One-page report against the four value pillars. To sponsor and skip-level. | Captain |
| Plan portfolio review | Look at all open plans. Which moved? Which are stuck? Which to retire? | Captain + track leads |

### Annually

| Cadence | What | Owner |
|---|---|---|
| Captain rotation review | Has the captain been in role 12+ months? Plan handover. | Sponsor + captain |
| Charter review | Does the charter still describe what we are doing? Update if not. | Captain + champions |
| Three-page annual case | For the next year's budget. | Captain |
| External recap to community | Contribute lessons learned back to the main SAAF Project. | Captain |

---

## Roles Inside The Chapter

The four SAAF roles (auditor / Professional Practices / analyst / engineer) describe
*what people do at sessions*. Inside the chapter's operating model, you
also need *organisational roles* — these may be played by the same people
or different people.

| Role | Responsibility | Time per quarter |
|---|---|---|
| Captain | Owns the chapter. One named person. | 1 day / week |
| Co-captain | Shadows captain, runs sessions when captain is out. | 1 day / month |
| Facilitator | Runs tracks at sessions. Trained on facilitation. | 2 days / quarter |
| Track lead | Owns a specific topic across sessions (e.g. controls mapping). | 1 day / month |
| Recap writer | Produces the recap within 7 days of each session. | 2 days / quarter |
| Sponsor liaison | Keeps the executive sponsor informed. Often the captain. | 0.5 day / month |

For a chapter with 20–40 active members, you need at minimum: one
captain, one co-captain, three facilitators, three track leads, one
recap writer. Some of these can be the same person; none should be the
captain alone.

---

## Plan Lifecycle Inside An Internal Chapter

The PDCA cycle from [foundations/what-saaf-is.md](../foundations/what-saaf-is.md)
applies. Inside an internal chapter, you have one privileged
capability the regional chapter does not: you can do **Check** on
*real* internal data, with the right controls.

The internal-specific plan lifecycle:

```
Plan submitted
  ↓
Hackathon build  →  rough working artefact, demo'd to room
  ↓
Professional Practices review → does the output meet methodology?
  ↓
Synthetic-data validation → quantitative test, results captured
  ↓
Pilot scope agreed → which audit team, which engagement, what controls
  ↓
Live pilot → behind firewall, real data, audit-quality oversight
  ↓
Pilot retro → what worked, what didn't, what to share back
  ↓
Production adoption  ←─────  decision to scale
  OR
  Retire and document  ────►  contribute lesson back to community
```

The pilot stage is where most internal chapters fall over. The thing
that gets it past the wall is not technical; it is the Professional Practices
sign-off and the named audit team that owns the engagement.

---

## What To Stop Doing

Internal chapters tend to accumulate ceremonies that look reasonable
in isolation but starve the build time.

Stop or never start:

- A separate "AI ethics" working group inside the chapter. Either it
  is part of every plan's review, or it isn't real.
- A monthly all-hands. The quarterly readout plus the demo cadence is
  enough.
- A vendor evaluation committee. The chapter is vendor-agnostic; if
  the organisation is choosing a vendor, that is a procurement
  exercise, not chapter work.
- A "communications working group." The captain owns communications,
  with help from one designated champion. Committees do not write
  good comms.
- A glossary maintained by everyone. Maintained by no one is the
  same outcome with more meetings.

If a ceremony has not produced something visible to the room in three
months, kill it.

---

## Cross-reference

For the build day itself, see [running-hackathons/](../running-hackathons/).
For metrics and reporting, see [measuring-value/](../measuring-value/).
For what to do when participation drops, see
[engagement-and-growth/rebuilding-participation.md](../engagement-and-growth/rebuilding-participation.md).
