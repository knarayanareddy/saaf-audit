# Communication Channels

One channel. One mailing list. One calendar. **Aligned with the main
SAAF Project wherever possible.**

The most common chapter mistake on communications is *too much
infrastructure too early*. A new chapter does not need a Slack
workspace, a Discord server, a LinkedIn group, a podcast, a
newsletter, a forum, and a Mastodon account. It needs one place where
people talk between sessions, and one way to reach them when a
session is coming up.

The second most common mistake is **building that infrastructure in
isolation from the main SAAF Project**. A chapter that runs its own
Slack, its own repo, and its own calendar disconnected from the main
project is a chapter that has voluntarily cut itself off from the
federation's network effects.

---

## Align With The Main SAAF Project By Default

Before standing up any chapter infrastructure, ask the main SAAF
Project organisers (see
[../internal-chapter/README.md#get-in-touch-with-the-main-saaf-project-first](../internal-chapter/README.md#get-in-touch-with-the-main-saaf-project-first)
or
[../regional-chapter/README.md](../regional-chapter/README.md))
which platforms they use. The default — for messaging, repository,
and calendar — is to **join the main project's stack** and operate
within a chapter-specific area inside it.

Why alignment matters:

- **Network effects.** Members of one chapter can drop into another
  chapter's space, ask questions, share artefacts. A SAAF Belgium
  contributor can see what SAAF NL just shipped without waiting for
  a quarterly sync.
- **Backflow happens by default.** Conversations, plans, and lessons
  surface upstream because they are *already* in the main project's
  space. The "feed it back to the main project" step is the same as
  the "post it in the channel" step.
- **Lower captain burden.** The chapter does not maintain its own
  infrastructure, its own admin, its own access controls. The main
  project's organisers maintain the platform; the captain maintains
  the conversation inside it.
- **Stronger federation.** One community across many chapters
  rather than many silos that occasionally talk to each other.

When alignment is **not possible** — usually because a member
organisation's IT or security policy blocks the main project's
platform, or because the chapter operates under a regulatory regime
with data-locality requirements — the chapter sets up a parallel
channel **with a named human bridge**: one person whose job is to
make sure conversations and artefacts flow both ways. Without the
bridge, the chapter is operating outside the federation in practice
even if not in name.

---

## The Minimum Stack

| Channel | Purpose | Default |
|---|---|---|
| **One messaging channel** | Conversation between members between sessions | A chapter-specific space inside the main SAAF Project's messaging platform (or whatever the main project currently uses). Avoid spinning up a separate workspace. |
| **One mailing list** | Session announcements, recap distribution, calls for plans | Per-chapter (members differ per chapter), but consider subscribing the chapter to any main-project announcement list, and the main project to the chapter's recap list. |
| **One calendar** | Future sessions, deadlines | Per-chapter calendar published to the main project's shared calendar so cross-chapter events are visible. |
| **One repository / shared folder** | Plans, prompts, recaps, templates | The main SAAF Project's GitHub organisation — either contributing directly to the main repo or in a chapter-specific subfolder / repo within the same organisation. |
| **The SAAF Portal** | Profiles, track and plan browsing, leaderboard, observability checks, badges, participant directory | The main project's [SAAF Portal](../measuring-value/saaf-portal.md). Members sign in with their GitHub account; chapters do not run their own. |

That's it. A first-year chapter can run entirely on these five. Most
chapters in their second or third year still should.

---

## The Messaging Channel

The default is to **join the main SAAF Project's messaging platform**
and operate as a chapter-specific space inside it. Ask the main
project organisers what they use before standing anything up.

Selection criteria, in order:

1. **What the main SAAF Project uses.** The federation works because
   chapters share the same conversational surface. Deviating from
   this should be a deliberate, named decision with a stated
   mitigation (the bridge described above).
2. **Compatible with the security policies of member
   organisations.** If a key member organisation cannot access the
   main project's platform, raise it with the main project
   organisers — sometimes a workspace setting or a federation
   feature resolves it. Don't fork the platform on the first
   obstacle.
3. **Workspace-shareable across organisations.** Regional chapters
   need cross-firewall access; internal chapters may use the
   organisation's existing instance with a federation-bridge to the
   main project.
4. **Searchable.** Both Slack and Teams meet this bar; Discord
   doesn't, in the audit context.

### Channel structure

The chapter operates as one or more **channels inside the main
SAAF Project workspace**, with naming that makes the chapter
identifiable.

Suggested naming convention (adapt to the main project's actual
conventions, which take precedence):

- `#chapter-[name]-general` — main conversation for the chapter.
- `#chapter-[name]-sessions` — session-specific announcements.
- `#chapter-[name]-help` — questions during builds or between
  sessions.

For a larger chapter (50+ members), add:

- `#chapter-[name]-plans` — discussion of plan submissions.
- `#chapter-[name]-track-[name]` — one channel per track, only if
  active.

Chapter members are encouraged to also join the **cross-chapter
channels** maintained by the main SAAF Project (`#general`,
`#announcements`, topic channels, etc.). The chapter's channels are
a place to do chapter-specific work; the cross-chapter channels are
where federation conversations happen.

Avoid:

- A separate workspace from the main SAAF Project (this is the big
  one — once a chapter has its own workspace, backflow stops by
  default).
- Per-organisation channels (fragments the cross-organisation
  conversation).
- Per-vendor channels (defeats vendor neutrality).
- A `#random` or `#water-cooler` channel — well-meaning, but tends
  to make the main channel feel less welcoming because the small
  talk has been "sent elsewhere."

### Channel etiquette

The captain (or a designated channel manager) gently maintains
norms:

- Threading long discussions, so the main channel stays scannable.
- Pinning key resources (manifesto, charter, next session details).
- Welcoming new joiners by name, in their first 24 hours.
- Closing-out questions when answered, so the channel doesn't feel
  abandoned.
- Removing or archiving very stale messages (rarely needed).

The channel should feel like a low-pressure, friendly space. If it
becomes a place where lurkers feel watched or contributors feel
defensive, the chapter has a culture problem more than a comms
problem.

---

## The Mailing List

The mailing list reaches everyone who registered. It is the canonical
way to announce a session, share a recap, or call for plans.

### Default cadence

- **Six weeks before a session:** save-the-date + the calendar
  invitation itself. Accept / decline on the invitation is the RSVP.
- **Four weeks before:** call for plans. (Capacity status mentioned
  if the waiting list has been activated.)
- **One week before:** tentative respondents get a personal
  follow-up from the operator. Confirmed attendees get the logistics
  email — address, time, what to bring, who to contact.
- **Day before:** practical reminder to confirmed attendees only.
- **Within seven days after:** recap.

That's roughly four chapter-wide emails per session, plus
individually-addressed tentative follow-ups. Quarterly cadence × 4 =
16 chapter-wide emails a year. That's the right level — visible
enough to maintain mindshare, sparse enough not to feel like a
newsletter that needs unsubscribing from.

**No "are you still coming?" reconfirmation email.** The calendar
invitation is the RSVP. Asking auditors to confirm twice trains them
to ignore the second ask, and adds friction for no information gain.
Tentatives are the only category that gets a follow-up, and it's
personal, not a mass send.

### What to include in a session announcement

Keep it short. The reader needs to know:

- Date, time, venue, address.
- Headline theme of the session.
- 2–3 plans that look promising for this session.
- How to RSVP: accept the calendar invitation that arrives alongside
  (or shortly after) this email. Sign-up link for anyone not yet on
  the chapter distribution list.
- Capacity note if relevant ("session is filling — waitlist after
  [date]").
- Deadline for plan submissions.
- One-line "what to expect" for first-timers.
- Sign-off from the captain, by name.

Resist the marketing-newsletter tone. A captain's email reads as
written by one person to a community — not as written by a
communications team to a list.

### Unsubscribe etiquette

A clear unsubscribe link in every mass email. No re-subscription
attempts; no "we're sorry to see you go" follow-ups. People come
back when they are ready.

---

## The Calendar

A single shared calendar with all chapter events. Subscribable. The
URL is in every session email and pinned in the channel.

**Publish chapter events to the main SAAF Project's federation
calendar as well**, so members of other chapters can see what's
happening and drop in where it makes sense. The chapter calendar is
the primary; the main project calendar is the aggregate view. Most
calendar tools support cross-publishing or shared subscriptions
natively.

What goes on it:

- All sessions (alignment, hackathons).
- Plan submission deadlines.
- Quarterly readout / sponsor briefings.
- Community demos or show-and-tells — invite cross-chapter attendees
  where appropriate.

What does not:

- Member-organisation internal events.
- Vendor product launches.
- Recurring meetings of subgroups (those go in the subgroups' own
  invites).

A clean calendar is a sign of a well-run chapter. A calendar
cluttered with adjacent events confuses members about what is and
isn't part of the chapter.

---

## The Repository / Shared Folder

The technical home of plans, prompts, recaps, and templates. The
main SAAF Project uses GitHub. The default is to **work directly
inside the main project's GitHub organisation**:

- **Preferred:** the main SAAF Project repository, contributing
  alongside other chapters. Backflow is automatic. (See
  [feeding-back-to-saaf/](../feeding-back-to-saaf/).)
- **Acceptable:** a separate repo within the main project's GitHub
  organisation, for chapter-specific work that warrants its own
  space. Still inside the federation; still visible to the main
  project.
- **Last resort:** a self-hosted Git or shared folder, only if
  neither GitHub nor GitLab is workable for the chapter's
  organisations. In that case, the chapter must designate a named
  human bridge who regularly syncs artefacts to the main project's
  repository.

Whatever you pick, mirror the four-pillar structure. Don't reinvent
the layout.

A chapter that maintains its own repo *outside* the main project's
GitHub organisation will quietly drift apart from the federation,
even with good intentions. The decision to host elsewhere should be
re-evaluated by the captain at each annual charter review.

---

## What To Avoid

### A separate workspace from the main SAAF Project

The biggest comms anti-pattern: a chapter sets up its own Slack /
Teams workspace independent of the main SAAF Project's. Within six
months, the chapter and the main project are operating as separate
communities. Cross-pollination stops. Backflow drops to whatever the
captain remembers to manually copy across.

If a chapter is already in this state, the fix is to **join the main
project's workspace** as chapter-specific channels and gradually
migrate conversations. The old workspace can be archived once the
new structure is settled.

### Multiple channels for the same conversation

A common pattern: the chapter is on the main project's Slack, but a
few members prefer WhatsApp, so a WhatsApp group emerges. Now half
the chapter's conversation is invisible to the other half — and
invisible to the main project.

Pick one. Politely ask the WhatsApp group to migrate to the channel
or to be a personal chat between specific people. The chapter cannot
function with shadow conversations.

### Newsletters

A newsletter is a different shape from a chapter mailing list. It
suggests recurring content production, an audience, and broadcast
metrics — all of which are anti-patterns for a SAAF chapter (see
[foundations/principles.md](../foundations/principles.md#5-build-community-not-audience)).

If you find yourself writing a "chapter newsletter," stop and write a
session recap instead.

### Public social media for the chapter itself

A LinkedIn page or a Twitter / Mastodon account for the chapter
sounds reasonable. In practice it is a maintenance overhead with low
return.

The chapter's public face is the chapter site (one page) and the
manifesto. Its members use their own LinkedIn to talk about the
chapter — that's how the work spreads. The chapter does not need its
own brand voice on social media.

If you must have social media, point it at the recap and the next
session. Don't post original content; the captain has more useful
things to do.

### Onboarding documents that nobody reads

Long welcome PDFs, multi-page member handbooks, recorded training
sessions. The community-engagement literature is consistent on this:
detailed onboarding materials are a *founder-comfort* artefact, not a
*member-onboarding* artefact.

What new members actually need:

- A welcome message (one paragraph).
- A link to the manifesto.
- A link to the next session.
- The name of the channel and how to join.
- The name of someone they can ask anything.

That's it. Anything more is the founder's anxiety, not the new
member's need.

---

## Communications Calendar

A simple sheet — visible to the captain and co-captain — listing
every planned communication for the next quarter. Five session
emails per session, plus the channel and any quarterly readout.
Everything else is event-driven.

Review it at the monthly organiser huddle. Remove anything that
doesn't have a clear reason to exist.

---

## Cross-reference

For what to put in the recap, see
[../running-hackathons/post-event-recap.md](../running-hackathons/post-event-recap.md).
For what to share back to the main SAAF Project (and via what
channels), see
[../feeding-back-to-saaf/contribution-flow.md](../feeding-back-to-saaf/contribution-flow.md).
