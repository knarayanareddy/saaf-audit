# Roles And Tracks

The four SAAF roles — auditor, Professional Practices, analyst, engineer — are
described in [foundations/what-saaf-is.md](../foundations/what-saaf-is.md).
This page covers how those roles operate **on the day**: how teams are
formed, how tracks are organised, and how to keep the role mix
healthy.

---

## How A Team Forms

A team is two to five people, ideally covering at least two of the
four roles. The most productive shape is:

> 1 auditor (drives the use case)
> 1 engineer (builds the harness)
> 1 analyst or Professional Practices (validates the output)
> 1 floater (often a first-timer learning by doing)

Three is a good minimum. Six is the practical maximum — beyond that,
coordination overhead eats the day.

Teams form during the **claim moment** at the end of the plan
walkthrough (~11:30), then converge over lunch. The
[SAAF Portal](../measuring-value/saaf-portal.md) shows the plans
already claimed in advance; the captain reads those out first so
existing teams find each other quickly. Each table is a track;
the table sign shows the track name and which plans belong to it.

People move toward the table that holds the plan they want to work
on. The captain or track lead spots imbalances ("this table has four
engineers, no auditor") and walks people across.

If a team can't form for a given plan, the plan goes back into the
pool. That is fine. Plans never expire — they stay claimable in the
portal until someone picks them up at a future session.

---

## The Tracks

Tracks are the organising vocabulary of the day. They map roughly to
audit phases or audit domains and exist so people can find their
team.

### Default tracks

Most sessions use three to five of these, picked by the captain based
on the plans submitted:

| Track | What's on it | Typical role mix |
|---|---|---|
| **Audit planning** | Risk assessment, work programme generation, scoping agents | Auditor-heavy + engineer |
| **Fieldwork & evidence** | PBC assistants, evidence extraction, control testing | Auditor + engineer + analyst |
| **Reporting & findings** | Finding generators, management-letter drafting, consistency checkers | Auditor + Professional Practices + engineer |
| **Compliance & regulatory** | Regulatory monitors, control-mapping agents, policy-to-control extractors | Professional Practices + engineer |
| **Vendor / third-party** | Vendor risk pre-screen, contract review, SLA monitoring | Auditor + analyst + engineer |
| **Continuous monitoring** | Anomaly detection, intelligence monitors, always-on agents | Analyst + engineer |
| **Infrastructure** | RAG knowledge bases, MCP servers, synthetic data sandboxes | Engineer-heavy |
| **Audit quality / methodology** | Explainability frameworks, hallucination detection, output validation | Professional Practices + engineer |

The track names are not sacred. Use what fits the plans you have.
Avoid creating a track for fewer than three plans — small tracks
fragment the room.

### Track leads

Each track has a named lead for the day. The track lead:

- Walks the room of their track at each break.
- Knows every plan and every team in their track.
- Resolves "we're stuck" moments before they become quitting moments.
- Is the recap writer's source of truth for that track.

A track lead is not a dictator. They are an enabler. The
[facilitation.md](facilitation.md) page covers how to do the role
well.

---

## Role Health Checks

Before the day starts, the captain looks at the registration list
through the lens of role mix. Healthy ratios for a 50-person session:

| Role | Healthy share | Unhealthy share |
|---|---|---|
| Auditor | 35–50% | <25% (toy day) |
| Engineer | 25–40% | >50% (no domain pull) |
| Professional Practices | 10–20% | <5% (no quality oversight) |
| Analyst | 10–20% | <5% (no validation) |

If the registration is heavily skewed, *do something about it before
the day*:

- Too few auditors? Reach back to founding partners and ask them to
  send seniors specifically. Offer to designate them as track leads.
- Too few engineers? Reach into the engineering networks of member
  organisations or sponsors. Sometimes a partner's product team will
  send people if asked directly.
- Too few Professional Practices? Reach to the audit-quality function in member
  firms. The IIA and NOREA equivalents often have networks of
  Professional Practices who will attend if invited as a peer group.
- Too few analysts? Recruit from internal data analytics teams in
  member firms. Some of the best analysts are not in audit teams at
  all but in finance, risk, or data engineering.

The role mix is the lead indicator of session quality. Most session
post-mortems blame the agenda, the venue, or the facilitator. Most
session post-mortems are wrong; the real problem was the role mix.

---

## First-Timers And The Floater Role

Newcomers are easier to integrate when they are explicitly invited to
be **floaters** — joining a team without yet committing to a specific
role. The floater shadows the team for the first sprint, then settles
into whichever role they connect with.

The floater convention also gives senior auditors a face-saving way
to attend without committing to be the auditor on a team. They can
float for the first half-day, see what the chapter is, and decide
whether to deepen at the next session.

Always hold one or two floater slots open in registration, even if
the session is full. A senior who walks in on the day deserves a seat.

---

## When A Team Is Stuck

By 14:30 (after sprint 1 in the afternoon hackathon), some teams will
be stuck. The track lead diagnoses:

| Symptom | Likely cause | Move |
|---|---|---|
| Team is debating scope endlessly | No auditor decisively driving the use case | Pair them with a senior auditor from another team for 30 min |
| Team can't decide on the stack | Too many engineers, no clear pick | Track lead picks for them. The stack is a means, not an end. |
| Team has built nothing | Plan was too ambitious | Help them carve a 90-minute MVP from the larger plan |
| Team is bored | Plan was too small | Suggest a stretch goal — adding regulatory checks, an output schema, a second use case |
| One team member is dominating | Group dynamic | Track lead pulls the dominant member aside privately during the break |

The 14:30 coffee break is **the** intervention window. With only one
build sprint left after it, teams that stay stuck through the break
will not ship at 16:00. The track lead's job at 14:30 is to re-scope
relentlessly.

In rare cases, dissolve a team and re-form it at the coffee break.
Frame it as "let's try a different combination" not as failure.

---

## Cross-track collaboration

Some plans need help across tracks. A regulatory-tracker agent might
need an MCP server from the infrastructure track. An evidence-
extraction agent might need a finding schema from the reporting
track.

Foster this by:

- Posting plan dependencies on a visible wall ("Team X needs a Jira
  MCP — anyone in infra track want to help?").
- Using the 14:30 coffee break to surface cross-track needs across
  the room.
- Letting team members swap tracks for an hour if the dependency is
  big enough.

Cross-track collaboration is a sign of a healthy session. Sessions
where every team works in isolation are sessions that are not yet
operating as a community.

---

## Cross-reference

For who facilitates the day, see
[facilitation.md](facilitation.md).
For how the plans flow through PDCA, see
[plans-and-pdca.md](plans-and-pdca.md).
