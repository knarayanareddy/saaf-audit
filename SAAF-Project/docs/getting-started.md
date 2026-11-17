# Getting Started — SAAF Project Repository

Welcome to the SAAF Project shared repository. This guide will get you set up and contributing within a few minutes.

## What This Repository Is For

This is the shared workspace where participating organizations store and collaborate on AI audit agent components. The four pillars mirror the SAAF framework:

- **Prompts:** audit prompts and system instructions
- **Tools:** scripts, APIs, and integrations
- **Regulatory:** control mappings, guardrails, and policies
- **Outputs:** report templates, schemas, and examples

## Prerequisites

- Git installed ([git-scm.com](https://git-scm.com))
- Python 3.10+ (for running scripts in `tools/`)
- A GitHub account with access to this repository
- (Optional) Claude Desktop or VS Code with GitHub Copilot for AI-assisted work

## Step 1: Clone the Repository

```bash
git clone https://github.com/SAAF-Project/SAAF-Project.git
cd SAAF-Project
```

## Step 2: Explore the Structure

```
prompts/        Audit prompts and system instructions
tools/          Scripts and integrations
regulatory/     Control mappings and policies
outputs/        Report templates and examples
docs/           This guide and lessons learned
```

Start with the README in the pillar most relevant to your current work.

## Step 3: Set Up Your Python Environment (optional)

If you plan to run or contribute scripts:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r tools/scripts/requirements.txt   # if present
```

## Step 4: Try an Example

1. Open `prompts/audit-use-cases/access-review.md` and read the prompt template.
2. Run a test with synthetic data using `tools/scripts/example_data_extract.py`.
3. Review the example output in `outputs/examples/example-access-review-output.md`.

## Contributing

Because the repository uses read-only access for org members, contributions go through a fork-based workflow. All changes to `main` require a pull request — direct pushes are not possible.

### Step-by-step

1. **Fork** this repository to your own GitHub account (button in the top-right on GitHub).
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/SAAF-Project.git
   cd SAAF-Project
   ```
3. **Create a branch** in your fork:
   ```bash
   git checkout -b your-name/feature-description
   ```
4. Add or edit files in the relevant pillar folder, following the conventions in each folder's README.
5. **Push** to your fork:
   ```bash
   git push origin your-name/feature-description
   ```
6. Open a **pull request** from your fork's branch to `SAAF-Project/SAAF-Project:main`.

### What to Contribute

- A prompt you used in a hackathon session
- A script that extracted or analyzed audit data
- A control mapping for a framework your organization uses
- A report template or example output (anonymized)
- Lessons learned from a session (see `docs/lessons-learned/`)
- A Hackathon 2 plan in `plans/hackathon-2/` using `docs/plans/plan-template.md`
- An `agent.yaml` in your agent repo, so it appears on the [Living Map](https://saaf-project.github.io/saaf-living-map/) (see [Building an agent](#building-an-agent))

## Submitting a Plan

### Why share?

SAAF stands for **Shared** Audit Agents Framework. Every plan you submit is one more agent, skill, or workflow the entire community of 45+ organizations can build on, adapt, and improve. One hour of your thinking compounds into value for dozens of teams working on the same audit challenges.

### Use-case types

| Type | Definition |
|---|---|
| **Agent** | Autonomous, multi-step execution. Has its own system prompt and calls one or more tools to complete an audit task without continuous human steering. |
| **Skill** | Single-purpose reusable capability. Typically a prompt paired with a parsing function — easily composed into larger agents or workflows. |
| **Workflow** | Orchestrated sequence of agents and/or skills with defined human checkpoints. Useful for audit processes that require sign-off at key stages. |

### PDCA framing

SAAF sessions follow a Plan–Do–Check–Act cycle across hackathons:

- **Plan** — design your agent/skill/workflow (this hackathon)
- **Do** — build a working prototype (this hackathon)
- **Check** — validate in private adoption at your organization (between sessions)
- **Act** — share learnings and improvements at the next hackathon

A plan submitted now is the starting point for all three subsequent phases.

### How to submit

Every plan must be based on the submission template. The template and the index of submitted plans are the two files to know:

- **Template:** [`docs/plans/plan-template.md`](plans/plan-template.md)
- **All plans overview:** [`plans/overview.md`](../plans/overview.md) — quality scores, domain coverage, merge candidates
- **Current session index:** [`plans/hackathon-4/README.md`](../plans/hackathon-4/README.md)

The steps below use **Claude Code** and the **`gh` CLI** throughout. Claude Code can read any file in the repo, follow links between sections, and guide you through filling in the template.

> **Browse plans visually:** run `cd website && python3 -m http.server 8080` and open `http://localhost:8080` to explore all plans, tracks, and PDCA status in the Hackathon Harness.

#### 1. Fork and clone with `gh`

```bash
gh repo fork SAAF-Project/SAAF-Project --clone
cd SAAF-Project
```

#### 2. Read the repo and template with Claude Code

Start Claude Code in the repo root and ask it to read the relevant files:

```
Read docs/plans/plan-template.md and plans/hackathon-4/README.md.
Help me fill in the template for my use case.
```

Claude Code will read the template section by section, link to related files in the repo (prompts, schemas, regulatory mappings), and help you draft each required section.

#### 3. Copy the template and fill it in

```bash
cp docs/plans/plan-template.md plans/hackathon-4/firstname-lastname-your-slug.md
```

File naming: lowercase, hyphens, pseudonym permitted. Example: `jan-bakker-vendor-risk-agent.md`

Link to existing repo files where relevant — for example reference `outputs/schemas/finding-schema.json` in section 8 or `regulatory/guardrails/allowed-commands.md` in section 7. Claude Code can find and read these for you.

**Claim your plan:** If you are actively building this (not just proposing), add your name to the `Claimed By` field in Section 1. This signals to others that the work is in progress and prevents duplication.

**Reference related plans:** Use relative markdown links to cross-reference plans that your work builds on or extends. Browse [`plans/gap-analysis.md`](../plans/gap-analysis.md) to find uncovered domains worth addressing.

#### 4. Commit and push

```bash
git checkout -b firstname/plan-your-slug
git add plans/hackathon-4/firstname-lastname-your-slug.md
git commit -m "plan: firstname-lastname-your-slug"
git push origin firstname/plan-your-slug
```

#### 5. Open a pull request with `gh`

```bash
gh pr create \
  --title "Plan: your slug" \
  --body "Hackathon 4 plan — see plans/hackathon-4/firstname-lastname-your-slug.md" \
  --base main
```

Once the PR is merged, the organizers will add a row to [`plans/hackathon-4/README.md`](../plans/hackathon-4/README.md).

### Timeline

| When | What |
|---|---|
| Before the session | Submit a draft PR — organizers may reach out to coordinate |
| During the session | Present and discuss; update based on feedback |
| Within 1 week after | Finalise and open (or update) your PR; update PDCA status |
| Between sessions | Test at your org (Check), share learnings at the next hackathon (Act) |

### All knowledge levels welcome

A prompt-only skill plan is as valid as a fully coded agent. Fill in what you know; mark the rest as open questions. The community will help.

## Building an agent

When you move from a plan to working code, the recommended home is a **dedicated repo per agent**
in the [SAAF-Project organisation](https://github.com/orgs/SAAF-Project/repositories) — most agents
are standalone and deployed on their own, so one repo per agent keeps things easy to run, review,
and deploy.

| In your own agent repo | Stays in this repo |
|---|---|
| Source code, tests, sample inputs/outputs, README, **`AUDIT-CRITERIA.md`**, **`agent.yaml`**, deploy config | Prompts, regulatory mappings, output schemas, shared utility scripts (e.g. transcription), the `AUDIT-CRITERIA.md` **template**, your plan, and a reference row to your repo |

**Every agent repo must include an `AUDIT-CRITERIA.md` next to its `README.md`.** The README explains what the agent does and how to run it; `AUDIT-CRITERIA.md` says what it must be judged against as an auditee — control objectives mapped to frameworks, testable pass/fail acceptance criteria, a "good output / never do" list, and known coverage gaps. Copy and fill in the template at [`docs/conventions/audit-criteria-template.md`](conventions/audit-criteria-template.md). This is the deliverable of the **A2 — Audit Criteria & Controls** track, and the **A1** stress-test track verifies an agent against these criteria.

**Every agent repo should carry an `agent.yaml` in its root from the start; it is required from Ready onward.** The README says *what the agent does*, `AUDIT-CRITERIA.md` says *what it is judged against*, and `agent.yaml` says *where it sits in SAAF*: which island (`planning`, `collection`, `reporting`, `monitoring`, `governance`, `foundation` or `quarry`, the portal's part ids), how mature it is (`building` → `ready` → `tested` → `improving`, the portal's stage keys), which other agents it depends on, and its mandate — allowed tools, forbidden actions, trusted inputs, human approval steps. The [SAAF Living Map](https://saaf-project.github.io/saaf-living-map/) rebuilds from these files on a schedule and renders every agent on one map; nobody maintains it by hand. Until your repo has one, the map shows a seed manifest drafted from the portal. Field reference, a real example ([RCM-Builder](https://github.com/SAAF-Project/RCM-Builder/blob/main/agent.yaml)) and a one-command local check: [`docs/conventions/agent-yaml.md`](conventions/agent-yaml.md). Add it by pull request like any other change.

**Every agent repo goes through the nine quality standards.** Since Session 11 (17 November 2026) an agent is finished when nine things are on its default branch (for example `main` or `master`): `README.md`, `agent.yaml`, `AUDIT-CRITERIA.md`, `SECURITY.md` (the vulnerability disclosure policy), `LICENSE` (MIT), at least one test, pinned dependencies, a CI workflow on pull requests and `CODEOWNERS`. What each one must contain and how it is checked is in [`docs/conventions/quality-standards.md`](conventions/quality-standards.md).

- **Existing agent:** run the `harden-agent-repo` skill inside your repo. It is the standard route: it checks the nine, asks what is missing and opens the pull request. Install it once:
  ```bash
  mkdir -p ~/.claude/skills/harden-agent-repo && \
  gh api repos/SAAF-Project/SAAF-Project/contents/.claude/skills/harden-agent-repo/SKILL.md \
    --jq .content | base64 -d > ~/.claude/skills/harden-agent-repo/SKILL.md
  ```
  Then open Claude Code in your repo and type `/harden-agent-repo`.
- **New agent:** create the repo from the template [`SAAF-Project/agent-template`](https://github.com/SAAF-Project/agent-template). All nine are already in place, with placeholders, and its pull request workflow fails until you replace them.
- **See where you stand:** the standards board in the portal, [`/standards`](https://saaf-portal.vercel.app/standards), shows one tile per standard for every repo. It reads the default branch only, so a tile turns on after a merge.

A dedicated repo also earns the **Agent Builder bonus** on the
[portal leaderboard](https://saaf-portal.vercel.app/leaderboard), and can be promoted to
**reviewed** in the [agent library](https://saaf-portal.vercel.app/agent-library) once it has a real
README and, ideally, tests + sample data.

> _Future direction:_ the agent repos may be wired together as a monorepo (e.g. Turborepo) so they
> can be spun up from this repo while each agent keeps its own home. For now, one dedicated repo per agent.

### Migrating an existing agent out of this repo

Built your agent inside this repo (e.g. under `tools/scripts/`)? Please move it to its own repo:

1. **Create a new repo** in the SAAF-Project org and push your code there (keep git history if you can) with a clear README.
2. **Open a removal PR** on `SAAF-Project/SAAF-Project` that deletes your agent's folder (uses the same fork/PR workflow as above).
3. **Link the removal PR to your new repo** in the PR description, and list the files you moved — so a maintainer can confirm nothing more is removed than what now lives in your agent repo.
4. **Leave a reference**: add or keep a row in the README Agent Overview table linking to your new repo.

**This is good for your score**, not a penalty: you keep the points from your original contribution,
the removal PR counts as a merged PR, and your new repo earns the Agent Builder bonus (a reviewed
agent is worth more). Early movers who follow the rules come out ahead.

### Make your work easy to follow

So the community (and maintainers) can see what you built and where it lives:

- **Connect the dots:** state which plan your agent implements; link plan ↔ repo ↔ PR both ways.
- **Be explicit about where the code lives** — your own repo, or (for now) a folder in this repo.
- **Write a README that explains itself:** what the agent does, how to run it (install, env vars, one command), what each main file/module does, and example inputs/outputs.
- **Add an `AUDIT-CRITERIA.md`** next to the README, using [`docs/conventions/audit-criteria-template.md`](conventions/audit-criteria-template.md) — control objectives, framework mapping, and testable acceptance criteria so others can assess the agent objectively.
- **Add the rest of the nine:** `SECURITY.md` from [`docs/conventions/security-md-template.md`](conventions/security-md-template.md), a `LICENSE` (MIT), a test, pinned dependencies, a CI workflow and `CODEOWNERS`. The `harden-agent-repo` skill adds them with you.
- **Add an `agent.yaml`** in the repo root, using [`docs/conventions/agent-yaml.md`](conventions/agent-yaml.md) — island, maturity, dependencies and mandate, so the Living Map (and anyone browsing it) knows what you built and what it depends on.

## Security Reminders

- Never commit real audit evidence, personal data, or credentials.
- Use environment variables for API keys and passwords.
- When in doubt, anonymize or use synthetic data.
- Review `regulatory/guardrails/allowed-commands.md` before running agent scripts.
- Found a weakness in a SAAF repo? Follow that repo's `SECURITY.md`. Report it privately, never in a public issue.

## Questions?

Reach out to Eduward van de Kamp or Mathijs Schouten, or open a GitHub Discussion in this repository.
