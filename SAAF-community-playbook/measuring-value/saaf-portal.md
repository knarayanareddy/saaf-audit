# The SAAF Portal

The **SAAF Portal** is the participant-facing app maintained by the
main SAAF Project. It is the single place where members of the
federation sign in, see what's running, claim work, and have their
contribution recognised.

- **Repository:** [github.com/SAAF-Project/saaf-portal](https://github.com/SAAF-Project/saaf-portal)
- **Live:** [saaf-portal.vercel.app](https://saaf-portal.vercel.app/)

This page is about **what the portal does for a chapter**, how to
weave it into a chapter's operating rhythm, and where it intersects
with the rest of this playbook.

---

## What The Portal Does

The portal is a Next.js app, signed-in with GitHub (org-member check),
that gives chapter members one place to:

| Feature | What it is | Where it lands in the playbook |
|---|---|---|
| **Profile** | Members add their organisation, role, track, skills, company logo. | [advocacy-funnel.md](../engagement-and-growth/advocacy-funnel.md) — visibility of contributors. |
| **Track and plan browser** | All current tracks and the plans in each — claim a plan in advance, not just on session day. | [plans-and-pdca.md](../running-hackathons/plans-and-pdca.md) and [roles-and-tracks.md](../running-hackathons/roles-and-tracks.md) — the claim mechanism. |
| **Leaderboard** | Ranked view of contribution activity across the federation. | [recognition-and-rituals.md](../engagement-and-growth/recognition-and-rituals.md) — recognition. |
| **Recent activity feed** | Visibility of what people across the federation are doing. | [communication-channels.md](../engagement-and-growth/communication-channels.md) — federation visibility. |
| **Observability checks** | A 10-question framework filled in per plan — captures whether an agent's outputs are auditable, explainable, traceable. | [value-pillars-and-metrics.md](value-pillars-and-metrics.md) — Pillar 2 (Coverage and confidence). |
| **Badges** | Observability Observer, Contributor, Plan Author, Plan Improver, Implementer. | [advocacy-funnel.md](../engagement-and-growth/advocacy-funnel.md) — visible stage progression. |
| **Participant directory** | Filter by skill / role / track / organisation. | [identifying-champions.md](../internal-chapter/identifying-champions.md) — finding people. |
| **Personal repo view** | A member's own repos in the SAAF-Project GitHub organisation. | [feeding-back-to-saaf/contribution-flow.md](../feeding-back-to-saaf/contribution-flow.md). |
| **Mission / timeline / how-to-contribute** | The canonical version of these documents, kept current by the main project. | [foundations/what-saaf-is.md](../foundations/what-saaf-is.md). |
| **Agent library** | Curated subset of org repos. | [feeding-back-to-saaf/contribution-flow.md](../feeding-back-to-saaf/contribution-flow.md). |
| **External e-learning** | Recommended resources from Anthropic, ccforeveryone, ForHumanity. | Member self-development. |
| **Feedback button** | Members send feedback to admins; admin triage. | Captain / Foundation channels. |
| **Access request flow** | Non-members can request access. | Onboarding new contributors. |

---

## Why The Portal Exists

A federation of chapters works only if its members can see each other.
Without a shared surface:

- Members in one chapter don't know what members in another are
  building.
- Track claiming happens on the day, by physical presence — which
  works for one session at a time, but does not let plans persist
  visibly across sessions.
- Contribution stays invisible to anyone not in the room.
- Recognition is captain-issued and ephemeral; it doesn't compound.

The portal addresses each of these. It is **the federation's
operating surface** between sessions, much as the hackathon is its
operating surface during sessions.

---

## How A Chapter Uses The Portal

### For members

Every chapter member is encouraged to:

1. **Sign in** with their GitHub account at the start of the
   chapter's first session for them.
2. **Complete their profile** — organisation, role, track interest,
   skills, optional company logo.
3. **Browse tracks and plans** — claim plans they want to work on,
   not just on session day but in the weeks before.
4. **Submit observability checks** when they've built or reviewed an
   agent. This is where the 10-question framework gets filled in.
5. **Earn badges** as their contribution shape grows.

### For captains

The captain's portal-facing duties:

- **Direct new members to the portal** as part of onboarding. (See
  [communication-channels.md](../engagement-and-growth/communication-channels.md#onboarding-documents-that-nobody-reads)
  for the "what new members actually need" minimum.)
- **Use the participant directory** when recruiting champions or
  forming teams — see [identifying-champions.md](../internal-chapter/identifying-champions.md).
- **Quote the leaderboard sparingly** in recaps and quarterly
  readouts. The leaderboard is a member-facing recognition mechanism,
  not an executive metric — see the caution in
  [recognition-and-rituals.md](../engagement-and-growth/recognition-and-rituals.md#the-leaderboard-question).
- **Treat portal activity as a leading signal** of chapter health.
  Drops in portal activity often precede drops in session attendance
  — see [rebuilding-participation.md](../engagement-and-growth/rebuilding-participation.md).

### For organisers (Foundation / main project)

Admins (currently `MSACC`, the main project organisers) get an
`/admin` page with signup requests and feedback to triage. Chapter
captains are not admins by default; if a captain needs admin access
for a specific chapter-level workflow, raise it with the main
project organisers.

---

## The Observability Check Framework

This is the portal feature most directly aligned with this section
of the playbook. A 10-question framework per plan, filled in by a
member who has built or reviewed the agent, captures whether the
agent's outputs are:

- Auditable (can someone trace the agent's reasoning?)
- Explainable (does the output answer "how did you arrive at this?")
- Traceable (are inputs, prompts, and outputs preserved?)
- Synthetic-data-only (no real client data ever?)
- Aligned with manifesto principles (vendor-agnostic, attribution
  preserved, etc.)

The 10 specific questions are maintained in the portal and updated
by the main project organisers as the community learns. **Refer to
the portal for the current version**; this playbook does not
duplicate them, because they change as the framework matures.

The observability check is the closest the federation has to a
shared **quality bar**. It is not a gate; it is a record. A plan
without observability checks is not invalid — it is just less
visible to the rest of the federation as a proven artefact.

For chapters, the observability check feeds Pillar 2 of value
measurement (Coverage and confidence) — see
[value-pillars-and-metrics.md](value-pillars-and-metrics.md).

---

## Badges And The Advocacy Funnel

The portal's badge set maps onto the advocacy funnel stages from
[advocacy-funnel.md](../engagement-and-growth/advocacy-funnel.md):

| Badge | Roughly maps to | What it signals |
|---|---|---|
| **Observability Observer** | Participant becoming Contributor | The member has filled in an observability check on someone else's plan. |
| **Contributor** | Contributor | The member has submitted a plan, prompt, or review. |
| **Plan Author** | Contributor | The member's name is on a plan in the four-pillar repository. |
| **Plan Improver** | Contributor / Ambassador | The member has extended someone else's plan. |
| **Implementer** | Ambassador / Champion | The member has carried a plan through to Check or Act stage inside an organisation. |

Badges are visible on the leaderboard and on member profiles. They
are awarded by the portal automatically based on activity (plan PRs,
observability checks, etc.) — not granted manually by captains. This
keeps recognition consistent across chapters and removes any
captain-favouritism concern.

A member can advance through badges at their own pace. The badge set
is not a ladder — it is a shape of contribution, made visible.

---

## Portal Activity As A Chapter Health Signal

Once a chapter has been running long enough to have a portal-active
member base, portal activity becomes one of the cheapest leading
indicators of chapter health.

| Signal | What it might mean |
|---|---|
| New profiles per quarter trending up | Chapter is recruiting; advocacy funnel is working. |
| Plan claims per quarter trending up | Build pipeline is healthy. |
| Observability checks per quarter trending up | Quality / methodology work is happening between sessions, not just during them. |
| Badge progression — members advancing through the badge set | Advocacy funnel is moving people along the stages. |
| Leaderboard movement — different people in top positions over time | Recognition is reaching new contributors, not just founders. |

The captain should look at these once a quarter as part of the
[operating rhythm](operating-rhythm.md#the-plan-portfolio-review).
Drops in portal activity that precede the next session's
attendance drop are the earliest warning of decay — see
[rebuilding-participation.md](../engagement-and-growth/rebuilding-participation.md).

---

## What The Portal Is Not

- **It is not the chapter's source of truth for value reporting to
  executives.** Use the four value pillars and the cadenced reports
  described in [reporting-to-stakeholders.md](reporting-to-stakeholders.md).
  The portal is member-facing recognition; the executive readout is
  outcome-facing decision support. Don't substitute.
- **It is not a replacement for the GitHub repository.** Plans,
  prompts, tools, regulatory mappings, and outputs still live in
  the SAAF-Project GitHub organisation. The portal *surfaces* them;
  it does not *store* them.
- **It is not where the chapter has its conversations.** The
  messaging platform (see
  [communication-channels.md](../engagement-and-growth/communication-channels.md))
  is where conversations happen. The portal is the static surface.
- **It is not a substitute for the recap.** The portal shows
  activity; the [recap](../running-hackathons/post-event-recap.md)
  tells the story.

---

## Operational Notes For Chapter Captains

- The portal lives in the **SAAF-Project GitHub organisation**.
  Federation alignment (see
  [communication-channels.md#align-with-the-main-saaf-project-by-default](../engagement-and-growth/communication-channels.md#align-with-the-main-saaf-project-by-default))
  means chapters use this portal rather than building their own.
- The portal requires members to be **SAAF-Project GitHub
  organisation members**. Onboarding flow includes the access
  request feature.
- The portal's plan, track, and badge data is **the source of
  truth across the federation**. Do not maintain a parallel
  spreadsheet that drifts from it.
- Bugs, feature requests, and feedback go through the portal's
  feedback button (admin-triaged). Chapter captains who notice
  something missing — a specific workflow their chapter would
  benefit from — should raise it that way rather than building a
  workaround inside the chapter.

---

## Cross-reference

For value reporting to executives:
[reporting-to-stakeholders.md](reporting-to-stakeholders.md) and
[value-pillars-and-metrics.md](value-pillars-and-metrics.md).

For the recognition philosophy that frames the leaderboard:
[../engagement-and-growth/recognition-and-rituals.md](../engagement-and-growth/recognition-and-rituals.md).

For where the portal sits in the federation stack:
[../engagement-and-growth/communication-channels.md](../engagement-and-growth/communication-channels.md).
