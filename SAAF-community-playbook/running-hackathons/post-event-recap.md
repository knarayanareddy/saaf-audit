# Post-Event Recap

The recap is the chapter's most-read artefact. People who couldn't
attend read it. Sponsors read it. Endorsing bodies read it. Future
participants read it before deciding whether to come. New chapter
captains read it when starting their own chapters.

The recap is also the easiest part of the chapter to neglect. Sessions
where the recap doesn't get written within seven days quietly become
sessions that didn't really happen.

---

## What A Recap Is

A recap document of a single session. Markdown. Two to ten pages.
Lives in the chapter's repo. Public to chapter members; selectively
public to the wider community.

A recap **is**:

- A factual record of what happened, who was there (in aggregate),
  and what was built.
- A summary of each plan that progressed, including PDCA status
  changes.
- The lessons learned — what worked, what didn't.
- A pointer to the next session.

A recap **is not**:

- A marketing document.
- A vendor pitch.
- A long-form essay on AI in audit.
- A photo album. (Photos are fine; the recap is not built around
  them.)

---

## The Default Recap Structure

```markdown
# [Chapter Name] — Session N Recap
## [Date] · [Venue]

## Overview
- A short paragraph: how many people, how many organisations,
  what was the theme, what was built.
- Headline numbers in a small table.

## Agents Built / Plans Progressed
- One subsection per plan that moved at this session.
- For each: what it does, who built it, current PDCA status, link
  to the plan and (if applicable) the repository.

## Cross-track Highlights
- Where teams collaborated across tracks.
- Plans that produced shared infrastructure (MCPs, schemas,
  templates) used by other plans.

## Lessons Learned
- 3–7 lessons, each one to three sentences.
- Each lesson should be specific enough that another chapter
  could apply it. "Have backup wifi" is a lesson; "Be prepared"
  is not.

## Plan Portfolio Status
- Total plans, by PDCA stage.
- Plans that completed (reached Act).
- Plans that need help, and what kind of help.

## Acknowledgements
- Host organisation.
- Speakers (with their consent).
- Volunteers.
- Sponsors (acknowledged, not advertised).

## Next Session
- Date, venue, theme (if any), call for plans deadline.
```

Use this as a starting template. A 30-person session's recap might
be three pages; an 80-person session's might be eight. Length should
match the session's content, not be padded for the appearance of
substance.

---

## Who Writes It

The recap writer. A named person, ideally not the captain (the
captain is too tired and was too busy to remember everything).

The recap writer's role on the day:

- Sit at the back during keynotes and demos, taking notes.
- Walk the room during build sprints, asking each team for a one-
  paragraph summary of what they're building.
- Photograph (with consent) demo screens and notable moments.
- Take a final photo of any whiteboards, sticky-note walls, or
  shared documents before they get wiped.

The recap writer's role after the day:

- Draft the recap within seven days.
- Circulate to the captain, co-captain, and any named team leads for
  factual corrections.
- Publish.

---

## Tone

Plain, factual, generous. Specific names credited (with consent).
Numbers where possible. Lessons stated directly.

What to avoid:

- Hyperbole. "Incredible day," "amazing energy," "transformative
  experience." These are filler.
- Vagueness. "Great discussions" — about what?
- Editorial. The recap is not the place to argue for a position;
  put that in a separate post.
- Vendor-flavoured language. If the recap reads like a vendor's
  case study, the chapter is drifting.

The voice of a SAAF recap should sound like a careful auditor wrote
it, not like a marketing team did.

---

## Photos

Use them sparingly and with consent.

Acceptable:

- Wide-shot photos of the room with people working (consent
  collected at registration).
- Demo screen captures (with the demoing team's consent).
- Sticky-note walls or whiteboards with no participant names visible.

Avoid:

- Photos of individual participants without their explicit consent.
- Photos that include code, credentials, or anything client-
  identifying on screens.
- Captioned photos that name participants who haven't consented to
  being named.

Default: blur faces of anyone who hasn't opted in. Most photo-editing
tools do this in two clicks. Mistakes here are unforgiving.

---

## What To Share Publicly

The chapter has multiple audiences for the recap:

| Audience | What they see |
|---|---|
| Chapter members | Full recap, with all details. |
| Sponsor / endorsing body | Full recap, often with an additional executive summary on top. |
| Main SAAF Project | Selected lessons learned, plan status updates, contributed artefacts. |
| Wider public (LinkedIn, blog) | A summary post, optional, captain's discretion. |

Default to **full recap to chapter members**. Default to **selected
lessons to the main SAAF Project**. The wider-public summary is
not required and is sometimes counterproductive — there is value in
the chapter feeling like a thing you have to be part of to see.

---

## Marketing On Social Media

Social media is the chapter's most-used public surface and the most
likely to go wrong. This section is about how to amplify a recap on
social media well — and how not to.

The default channel is **LinkedIn**. Audit professionals live there;
they do not live on Twitter / X, Mastodon, Instagram, or TikTok.
Posting elsewhere is optional and usually a captain time-sink without
return.

### The principle

> **Social media amplifies the recap; it does not replace it.**

A LinkedIn post is the trailer. The recap is the film. If the post
does not link to the recap, the post is doing the wrong job.

The aim of social media is **threefold**:

1. Make contributors visible inside their own organisations — their
   managers see what they shipped, named.
2. Bring new participants to the next session — people who didn't
   know the chapter exists discover it through someone they trust.
3. Show host organisations and sponsors that hosting / sponsoring
   was worth it — proof of reach beyond the room.

It is **not** for chapter brand-building, vendor co-marketing, or
audience-metric chasing. Resist those.

### Who posts

In rough order of preference:

1. **Individual contributors** posting about their own work. This is
   the most powerful by a wide margin. Their network is more relevant
   than a chapter account's would be. Their voice is more credible
   than a captain's would be.
2. **The captain**, posting one summary thread after the recap is
   published. Once per session, not more.
3. **The host organisation**, with a post they draft and the captain
   reviews before it goes live.
4. **Sponsors**, with the same review constraint.
5. **A chapter-owned LinkedIn page** — only if a chapter has run for
   12+ months and has a clear reason. Most chapters should not have
   one (see
   [../engagement-and-growth/communication-channels.md](../engagement-and-growth/communication-channels.md#public-social-media-for-the-chapter-itself)).

The captain's social-media job is **not** to be the chapter's
spokesperson. It is to make it easy for the other four groups to post
well.

### Consent — non-negotiable

Audit is a profession where confidentiality is part of the
professional standard. Social-media consent must be explicit, in
writing, and per-person.

The defaults:

- **Photos that name or clearly show individuals require their
  consent.** A photo of the back of a room is usually fine.
- **Quoting a participant by name requires their consent**, even if
  the quote is positive.
- **Tagging participants requires their consent.** Don't tag without
  asking.
- **Naming a participant's employer requires the participant's
  consent**, and in some firms requires the employer's communications
  team's approval. The captain should know which member organisations
  require approval before any social-media mention.

Collect photo and tag consent at registration with a clear opt-in
checkbox. Maintain a list. The recap writer cross-references the
list before publishing.

### What's safe to post

- The fact that the session happened, with the date, venue, and
  attendee count.
- The number of plans claimed, the number of plans demoed.
- Named contributors *with consent*.
- Wide-shot photos of the room *where individuals consented or are
  not identifiable*.
- A high-level description of what was built — "vendor risk
  pre-screen agent," not "[client]'s vendor process."
- The manifesto, in part or in full.
- The next session's date and how to register.

### What is never safe to post

- Real client names, even obliquely.
- Screen captures showing real data, even if synthetic-looking.
- Anything from a team's working notes that hasn't been cleared for
  publication.
- Specific findings, even anonymised, unless the artefact owner has
  signed off.
- Photos that include laptop screens with credentials, code with
  embedded keys, or any login UI.
- The names of organisations that did not consent to be mentioned.

The recap writer should treat every photo and every quote as if a
member organisation's General Counsel will read it tomorrow. Often
one will.

### Suggested post shapes

Three formats that work, ordered from lowest effort to highest:

**1. The contributor's named post (5 minutes to write).**
A short post from a participant about what *they* built, with one
line on what the chapter is and a link to the recap.

> *"Spent yesterday at the [Chapter] hackathon working with two
> audit colleagues from other firms on a vendor risk pre-screen
> agent. We got it to a working demo in three hours of build time.
> Synthetic data only; the methodology is open-source. Recap and
> next session: [link]. #InternalAudit #AIaudit"*

**2. The captain's summary post (15 minutes to write).**
One post from the captain, published the same day as the recap.

> *"[Chapter] session 4 wrapped yesterday. [N] auditors from [N]
> organisations built [N] AI audit agents over an afternoon.
> Highlights: [one-sentence demo summaries × 2–3]. Full recap and
> next session: [link]. Thanks to [host] for the venue, and to
> [speaker names with consent] for the morning talks."*

**3. The contributor thread / carousel (30 minutes to write).**
A longer post or carousel by a named contributor showing the build
in more depth, with screenshots of synthetic-data demos. Strongest
content if available, hardest to produce. Reserve for the
genuinely impressive demos.

### Timing

The window is short. The optimal posting time is:

- **Within 24 hours of the session** for the captain's summary
  post — while contributors' colleagues are asking "how was the
  event?"
- **Within 7 days of the recap publication** for contributor posts —
  the recap link gives the post substance.
- **One follow-up post 4–6 weeks later**, when registration opens
  for the next session.

Beyond two weeks post-recap, the post has missed its window. Don't
force late content; save the energy for the next session.

### Hashtags and mentions

Keep both minimal.

- **2–3 hashtags maximum.** Suggested: `#InternalAudit`, `#AIaudit`,
  and one chapter-specific tag if you have one.
- **Mention named partners and sponsors only with their explicit
  agreement** to be mentioned. Many firms' comms teams require an
  approval flow.
- **Mention the main SAAF Project** (with consent or by tagging the
  SAAF Project's official channel if one exists) when the post is
  about contributing back.

### What about vendor / sponsor co-marketing?

A vendor who sponsored catering or hosted the venue will sometimes
ask to post about the event with chapter branding. The default
answer is **yes to acknowledgement, no to ownership of the
narrative**:

- The vendor can post that they sponsored / hosted.
- The vendor can use a photo with the chapter's consent.
- The vendor cannot frame the post as "we ran the [Chapter] hackathon."
- The vendor cannot include a product pitch.
- The captain reviews the draft before it is posted.

If a vendor pushes back on review, that is a signal that the next
sponsorship invitation should be sized down. The chapter's
neutrality is more valuable than any one sponsor's amplification.

### When social media goes wrong

The most common failure modes:

- A photo gets posted with a participant who didn't consent. Take
  it down within the hour and apologise privately. Make consent
  more explicit at the next registration.
- A vendor posts a co-marketing piece without review. Ask them to
  edit or remove. Decline future sponsorship if the pattern
  repeats.
- A contributor's post quotes someone else without consent. The
  captain pulls the contributor aside, explains the norm, and the
  contributor edits the post.
- A post quotes a real finding or client. This is a serious
  incident — take down immediately, notify the contributor's
  employer's comms / legal contact, and document the lesson.

Captains who treat social media as a casual amplification channel
get caught by the last failure mode eventually. The norm is to
treat every social-media post about the chapter as if it were a
firm press release: small, careful, and reviewed.

---

## Lessons Learned — How To Write Them

This is the section future captains will mine most heavily. Make it
specific, honest, and brief.

Format each lesson as:

- *What we did:* (one short sentence)
- *What happened:* (one short sentence)
- *What we'll do next time:* (one short sentence)

Examples:

> *What we did:* Booked the venue without checking power outlets.
> *What happened:* Three teams ran out of laptop battery during
> build sprint 2.
> *What we'll do next time:* Bring multi-socket extension strips for
> every table; verify outlets in pre-event walkthrough.

> *What we did:* Allowed the morning keynote to run forty-five
> minutes instead of thirty.
> *What happened:* The plan walkthrough was compressed and three
> teams arrived at the afternoon hackathon without a clear plan.
> *What we'll do next time:* Hard cap, visible timer, captain cuts
> the speaker at thirty minutes regardless.

Three to seven lessons per session is the right range. Fewer and you
weren't paying attention. More and you're padding.

---

## Plan Portfolio Status

This is the part the executive sponsor reads most carefully. The
table form:

| PDCA stage | Count this session | Trend (vs last session) |
|---|---|---|
| Plan | 14 | +3 |
| Do (in progress) | 8 | -1 |
| Do (complete) | 6 | +2 |
| Check | 3 | +1 |
| Act | 2 | +1 |

The trend column is the important one. Plans growing on the left
(Plan, Do) without movement on the right (Check, Act) is the early
warning of the
[productionise-it-later graveyard](../internal-chapter/pitfalls.md#3-the-well-productionise-it-later-graveyard).

---

## Linking Back To The Main SAAF Project

A regional chapter's recap should include a section pointing to:

- Any artefacts being contributed back to the main SAAF Project
  repository this session.
- Cross-references to plans the main SAAF Project has that this
  chapter is also working on.
- Lessons that the main SAAF Project should consider for its
  own playbook.

See [feeding-back-to-saaf/](../feeding-back-to-saaf/) for the
contribution flow.

---

## Recaps That Compound

A recap is most valuable when it gets read. Captains can do a small
amount of work to make sure recaps actually circulate:

- **Email the recap to all attendees within seven days.** Cc
  participant managers if they consented at registration. Never cc
  managers without explicit consent — that's a privacy issue.
- **Post the recap link in the chapter's communication channel.**
  Not the full recap; the link.
- **Send the recap to the executive sponsor / endorsing body** with
  one short cover paragraph that highlights the part you most want
  them to read.
- **Index the recap.** A simple chronological page on the chapter's
  site listing every recap with date, venue, and one-line summary.

After three sessions, the chapter should have a record of recaps that
a new attendee can browse to understand what the chapter is. After
ten sessions, that archive becomes the chapter's most valuable
asset.

---

## A Recap Quality Test

Once you have a recap draft, run this test:

> *"If I were a senior auditor in another organisation who has never
> heard of SAAF, would this recap make me want to attend the next
> session?"*

If the answer is yes, publish it. If the answer is "maybe," figure
out which paragraph is doing the most work and which is doing the
least, and tighten. If the answer is no, the recap is not yet ready
— the problem is usually that the lessons-learned section is too
abstract.

---

## When You Miss The Seven-Day Window

Recaps that take longer than two weeks usually never get written.

If you slip past seven days:

- Send the *next session announcement* with a one-paragraph "session
  recap" embedded. Much better than nothing.
- Schedule a one-hour block to write the full recap by day fourteen.
- If you can't make day fourteen either, give up gracefully — accept
  this session won't have a full recap, write a half-page note in
  the chapter's repo explaining why, and re-commit to the next one.

The half-page note matters. It tells future captains that recap
hygiene slipped here, and why. That is itself a useful lesson.
