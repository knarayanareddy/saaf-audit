# What SAAF Is

SAAF is short for **Shared Audit Agents Framework**.

It is not a tool. It is not a product. It is not a working group, a
research project, or an industry consortium. It is a recurring,
practitioner-led, hands-on community of auditors who build AI audit
agents together — and share the result.

The simplest correct definition:

> **SAAF is the format that turns "auditors talking about AI" into
> "auditors shipping AI."**

Everything in this playbook exists to defend that sentence.

---

## What SAAF Is Not

Most of these look reasonable on day one. SAAF is:

- **Not a working group.** Working groups produce documents; SAAF
  produces working agents.
- **Not a vendor user group.** Vendor-agnostic by default; vendors
  participate, they do not steer.
- **Not a training programme.** People learn here, but the purpose
  of the gathering is to ship.
- **Not a thought leadership platform.** Demos, not decks.
- **Not consultancy in disguise.** No one bills anyone for SAAF work.

When a chapter starts to drift toward any of these, the dedicated
treatments are in [when-to-start.md](when-to-start.md) (pre-launch
anti-patterns) and
[../internal-chapter/pitfalls.md](../internal-chapter/pitfalls.md)
(failure modes once running).

---

## The Four Pillars

Every SAAF artefact lives in one of four pillars. They are the
vocabulary of the community — referenced in plan templates, recap
documents, and the contribution flow back to the main SAAF Project.

| Pillar | What it holds | Examples |
|---|---|---|
| **Prompts** | Domain-specific audit prompts and system instructions | An access-review prompt, a control-extraction system prompt, an evidence-PBC drafting prompt |
| **Tools** | Scripts, APIs, integrations, MCP servers | A Jira/Confluence MCP, a Strapi synthetic-data sandbox, a finding-extraction script |
| **Regulatory** | Control mappings, guardrails, AI usage policies | ISO 27001 mappings, an AI-agent allowed-commands list, an EU AI Act gate |
| **Outputs** | Standardised report formats, finding schemas, templates | A `finding-schema.json`, a management-letter template, a recap template |

When a contribution is hard to place in a pillar, that is usually a
signal that it is two contributions, not one.

The pillars are not folders someone owns. They are coordinates — they
let two builders in different organisations realise they are working on
adjacent problems.

---

## The PDCA Cycle Across Sessions

SAAF runs on Plan–Do–Check–Act, but stretched across multiple hackathon
sessions instead of completed in one workshop.

```
Hackathon N        Hackathon N+1       Between sessions     Hackathon N+2
─────────────      ─────────────       ─────────────────    ─────────────
   PLAN     ──▶       DO        ──▶        CHECK         ──▶     ACT
                                      (private adoption    (share back
                                       inside an org)        what happened)
```

- **Plan.** Submit a plan describing the agent / skill / workflow you
  want to build. The plan is the artefact, even if you never code it.
- **Do.** Build a rough, working version at the next hackathon. Demo it.
- **Check.** Test it quietly inside your own organisation against real
  internal data, on the inside of your firewall.
- **Act.** Bring the lessons back to the next session. What worked, what
  didn't, what the community should do differently.

Plans never expire. They wait for a builder. A plan written in session 3
is still live in session 7 if it has not been claimed and shipped.

This shape — *plan persists, builders rotate, lessons compound* — is the
most underappreciated thing about SAAF. It is the reason a one-day
hackathon does not end in a demo graveyard.

---

## The Four Roles

SAAF deliberately splits the room into four roles, so domain expertise
and engineering capacity can pair up without anyone being asked to be
both at once.

| Role | Who it is | What they do at a hackathon |
|---|---|---|
| **Auditor** | Senior or experienced auditor, no coding required | Brings the use case, the controls, the standards, the judgement. Drives what gets built and why. |
| **Professional Practices** | Audit + technical (often the firm's audit-quality function) | Validates that the agent's logic is defensible against IIA / ISA / firm methodology. Final reviewer of any output that touches a real audit. |
| **Analyst** | Data + Python literate | Wrangles synthetic data, runs scripts, builds quick visualisations, validates output. |
| **Engineer** | Software / cloud / DevOps | Builds the harness, deploys the MCP, wires the API, makes the demo run. |

The role mix at a session is the lead indicator of what gets built. Too
many engineers, no auditors → the day produces toys. Too many auditors,
no engineers → the day produces slide decks. Two of each per team is
the rough target.

A given participant may carry more than one role over time, but in a
given session they pick one. This keeps teams legible and accountable.

---

## What "Vendor-Agnostic" Means In Practice

Vendor-agnostic does not mean "we ignore vendors." It means:

1. **Artefacts must run on at least two stacks.** A prompt that depends
   on one specific model's quirks is a worse SAAF artefact than the same
   prompt rephrased to work across Claude, GPT, and an open-weights
   model.
2. **Demos may use one stack; documentation describes the contract.**
   A demo at a hackathon will use whatever the team has access to. The
   *plan* must describe the inputs, outputs, and dependencies in
   stack-neutral terms.
3. **No exclusive sponsorship.** A single vendor cannot be the sponsor
   of an entire chapter or session. Sponsorship is shared, rotated, or
   declined.
4. **Member organisations choose their own stack.** When a SAAF artefact
   lands inside an organisation, that organisation picks the model,
   the cloud, and the runtime that fits its risk profile.

The point is not vendor neutrality as virtue. The point is that audit
work outlives any specific vendor's roadmap, and SAAF artefacts must
outlive that too.

---

## Languages, Borders, and Branding

The main SAAF Project operates in English in its repository and in
its shared artefacts, even when the host country's working language is
not English. This is deliberate: it lets a regional chapter pick up an
artefact and use it without translation.

Local sessions can run in whatever language the room speaks. The
*deliverables* go in the shared repo in English, and any non-English
source material is translated before contribution.

A regional chapter's branding must distinguish it from the main SAAF
Project. "SAAF Belgium," "SAAF Public Sector," "SAAF DACH" are fine.
"SAAF" alone, without qualifier, is reserved for the main project
that started in NL.

The **SAAF name**, the name **"SAAF Project"**, and the **SAAF
logo** are all owned by the **SAAF Foundation**. Only affiliated
SAAF chapters may use them. A community of auditors building AI
audit agents together is welcome to exist without SAAF Foundation
affiliation — but it has to choose a different name. The details of
affiliation and brand use live in
[../feeding-back-to-saaf/governance-and-ip.md](../feeding-back-to-saaf/governance-and-ip.md).

---

## What Success Looks Like

A SAAF chapter is succeeding when, after twelve months:

- Member organisations are running agents in their own audit work that
  trace back to community-shared artefacts.
- New plans show up between sessions, not just during them.
- People volunteer to host, facilitate, or organise without being
  asked twice.
- Recaps from each session are read by people who weren't there.
- The plan-to-Act ratio is improving. Plans are not just accumulating;
  they are completing.

If those signals are absent after twelve months, the chapter has drifted
into one of the failure modes above. Read
[when-to-start.md](when-to-start.md) for how to recognise that earlier.
