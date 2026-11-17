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

## Security Reminders

- Never commit real audit evidence, personal data, or credentials.
- Use environment variables for API keys and passwords.
- When in doubt, anonymize or use synthetic data.
- Review `regulatory/guardrails/allowed-commands.md` before running agent scripts.

## Questions?

Reach out to Eduward van de Kamp or Mathijs Schouten, or open a GitHub Discussion in this repository.
