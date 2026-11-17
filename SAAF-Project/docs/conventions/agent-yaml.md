# agent.yaml — the Living Map manifest

*Convention file for SAAF agent repos. Lives at `docs/conventions/agent-yaml.md`, next to `audit-criteria-template.md`. Summary and context in [getting-started.md](../getting-started.md#building-an-agent).*

Every SAAF agent repo should carry one small file, `agent.yaml`, in the root of its default branch, from the start; it is required from Ready onward. Until the file exists, the map shows a seed entry. The [SAAF Living Map](https://saaf-project.github.io/saaf-living-map/) ([source](https://github.com/SAAF-Project/saaf-living-map)) rebuilds from these files on a schedule and renders every agent on one map: which island it belongs to, how mature it is, what it depends on, and whether it has open slots for contributors. Nobody maintains the map by hand; when you change your `agent.yaml`, the map changes.

`agent.yaml` is not the dependency manifest the Agent Library asks for; that is still `requirements.txt` (or `pyproject.toml` / `package.json`). It is also not a replacement for `AUDIT-CRITERIA.md`: the README says what the agent does, AUDIT-CRITERIA.md says what it is judged against, `agent.yaml` says where it sits in SAAF and what it is allowed to do.

If your repo has no `agent.yaml` yet, the map uses a seed manifest drafted from the portal. Adding the real file replaces the seed and makes you the owner of what the map says about your agent.

## 1. Where the file goes

```
your-agent-repo/
  README.md            ← required
  AUDIT-CRITERIA.md    ← required
  agent.yaml           ← from the start; required from Ready onward — this file
  requirements.txt
  your_agent.py
  samples/
  tests/
```

The file must be in the repo root on the `main` or `master` branch. Any other location or branch is not picked up. If your repo is not flat yet (code under `tools/scripts/`, say), that is fine; `agent.yaml` still goes in the root.

## 2. Minimal example

This is the smallest file that passes without warnings: a simplified example based on [RCM-Builder's manifest](https://github.com/SAAF-Project/RCM-Builder/blob/main/agent.yaml). Copy it, change the values, open a PR.

```yaml
name: RCM Builder (UC7)
repo: SAAF-Project/RCM-Builder
island: planning
maturity: ready
description: Three-stage Python pipeline that builds a Risk Control Matrix from UC1-UC5 risk inputs. Outputs JSON and Markdown for UC8.

mandate:
  purpose: Turn structured UC1-UC5 risk inputs into a GIAS-aligned risk-control matrix that UC8 can consume without manual rework.
  allowed_tools: [read_risk_inputs, read_it_matrix, write_rcm_json, write_rcm_markdown]
  forbidden_actions:
    - action: change_own_config
      rationale: Changes to this mandate go through a pull request.
    - action: modify_source_data
      rationale: Risk inputs are audit evidence and must stay unchanged.
    - action: call_llm
      rationale: The pipeline is deterministic by design; every control traces to a stated risk through code, not generation.
  trusted_inputs: [risk_inputs_uc1_uc5, it_dependency_matrix]
  max_runtime_minutes: 15
  human_approval_required_for: [publishing the RCM to UC8]
  evidence_policy: cite_only_given_context
```

`max_runtime_minutes` is needed from `maturity: ready` onward; a `building` agent can leave it out. Note that a mandate can forbid LLM calls: if your agent is plain code, say so, it is a strength. A fuller example with every optional field is in [`agent.example.yaml`](https://github.com/SAAF-Project/saaf-living-map/blob/main/agent.example.yaml).

### The real one: RCM-Builder

This is the current [`agent.yaml` on RCM-Builder `main`](https://github.com/SAAF-Project/RCM-Builder/blob/main/agent.yaml), copied as it is apart from its two header comment lines:

```yaml
name: RCM Builder (UC7)
repo: SAAF-Project/RCM-Builder
island: planning
# The owner can adjust this as the agent moves through the maturity stages.
maturity: ready   # building | ready | tested | improving
category: "Risk & Controls"
language: Python
depends_on: []            # consumes UC1-UC6 outputs as files, not as repos on the map
tags: [RCM, GIAS, UC7, COSO, COBIT, ITGC]
open_slots: 0
description: "Builds a Risk and Control Matrix from UC1-UC5 risk inputs: normalise risks, design controls, validate IT dependencies."

# The approved mandate. Changing this requires a pull request.
mandate:
  purpose: >-
    Turn the use-case risk inputs and the IT dependency matrix into a traceable,
    schema-valid Risk and Control Matrix that a human auditor approves before it
    goes to the Audit Work Program agent (UC8).
  allowed_tools: [read_use_case_inputs, read_it_matrix, validate_schema, write_rcm]
  forbidden_actions:
    - action: change_own_config
      rationale: Changes to this mandate, the scoring factors or the schema go through a pull request.
    - action: modify_source_data
      rationale: The UC inputs and IT matrix are evidence; the RCM must trace back to them unchanged.
    - action: create_untraced_risk
      rationale: Every risk needs a source reference (or a documented UC6 IT-dependency trigger); no orphan risks.
    - action: mark_rcm_approved
      rationale: Only the auditor approves the RCM; UC8 must work from an approved matrix.
    - action: send_email
      rationale: Communication with process owners goes through the auditor, not the agent.
  trusted_inputs: [use_case_inputs_uc1_uc5, it_dependency_matrix, rcm_schema, rcm_frameworks_reference]  # anything else is untrusted
  max_runtime_minutes: 15
  human_approval_required_for: [approving the RCM before hand-off to UC8, overriding risk appetite or scoring factors]
  evidence_policy: cite_only_given_context   # every risk and control cites a trusted input
  sharing: standard_is_shared_mandate_is_private
```

## 3. Field reference

### Required

| Field | What it is | Allowed values |
|---|---|---|
| `name` | Short display name for the agent | Free text, keep it under ~30 characters |
| `repo` | The repo this file lives in | `owner/name`, e.g. `SAAF-Project/RCM-Builder` |
| `island` | Which part of the SAAF project the agent serves; one of the portal's part ids | `planning` (GIAS Audit Planning Pipeline) · `collection` (Evidence Collection & Extraction) · `reporting` (Reporting & Visualization) · `monitoring` (Compliance & Regulatory Assessment) · `governance` (AI Governance & Quality Assurance) · `foundation` (Shared Infrastructure) · `quarry` (not yet assigned to a track). Note that `monitoring` means compliance and regulatory assessment, not audit follow-up. |
| `maturity` | Where the agent is in its life cycle; one of the portal's stage keys | `building` · `ready` · `tested` · `improving` |
| `description` | One sentence: what the agent does and for whom | Free text |
| `mandate` | What the agent may and may not do (see below) | Block |

Island and maturity values must match the list exactly; the keys are lowercase, as the portal writes them. Anything else is flagged as unknown. A manifest never says `draft-plan` or `final-plan`: a plan at those stages has no repo and therefore no manifest yet.

### Optional

| Field | What it is | Example |
|---|---|---|
| `category` | Audit domain | `Compliance`, `IT General Controls`, `Financial` |
| `language` | Main implementation language | `Python`, `TypeScript` |
| `depends_on` | Other SAAF repos this agent consumes output from | `[SAAF-Project/RCM-Builder]` |
| `tags` | Free keywords for search and filtering | `[audit, work-program, anthropic]` |
| `open_slots` | How many contributors you could still use | `2` |

`depends_on` draws the arrows on the map. If you list a repo that is not yet on the map, it appears as a ghost node so the gap is visible.

### The `mandate` block

The mandate is the agent's approved operating envelope. It is what the mandate guard checks at runtime and what the map uses to show whether an agent is safe to reuse. The build checks the block but never publishes it: `map.json` carries only `has_mandate`, true when the block is present and passes every check. Changing a mandate should always go through a pull request, not a direct commit.

| Field | Required | Notes |
|---|---|---|
| `purpose` | yes | One sentence. What the agent exists to do. |
| `allowed_tools` | yes | List of tool or action names the agent may use. |
| `forbidden_actions` | yes | List of `{action, rationale}` pairs. **Every entry needs a rationale.** Must include `change_own_config`. |
| `trusted_inputs` | yes | Named inputs the agent may treat as evidence. Everything else is untrusted. |
| `human_approval_required_for` | yes | At least one step a human signs off on. |
| `evidence_policy` | yes | How findings are grounded, e.g. `cite_only_given_context`. |
| `max_runtime_minutes` | from `maturity: ready` onward | Hard stop for a run. |
| `sharing` | no | e.g. `standard_is_shared_mandate_is_private`. |

A tool cannot appear in both `allowed_tools` and `forbidden_actions`; the build flags the clash.

## 4. Check your file before you open the PR

You do not need to install anything beyond Python and PyYAML. The build reads from GitHub, so to check a file that is still on your disk, drop it in as a seed and run offline:

```bash
git clone https://github.com/SAAF-Project/saaf-living-map
cd saaf-living-map
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pyyaml
cp /path/to/your/agent.yaml manifests/SAAF-Project__your-repo.yaml
echo "SAAF-Project/your-repo" > my.txt
python scripts/build_map.py --offline --repos my.txt --out /tmp/map.json
```

The output lists your repo with the number of warnings. Zero warnings means the map will show your agent cleanly. The warnings are plain English (`missing field: island`, `forbidden actions without rationale: send_email`) and point at exactly what to fix. Delete the copied seed afterwards; the real file lives in your repo.

## 5. Getting onto the map

Being listed as developer on the portal does not give you push rights on the repo, so this is the same fork → branch → PR flow as any other SAAF contribution:

```bash
git clone https://github.com/SAAF-Project/your-repo
cd your-repo
git checkout -b your-name/agent-yaml
cp /path/to/agent.yaml .
git add agent.yaml
git commit -m "Add agent.yaml for the SAAF Living Map"
gh repo fork --remote          # makes your fork the 'origin' remote, SAAF the 'upstream'
git push -u origin your-name/agent-yaml
gh pr create --repo SAAF-Project/your-repo --base main --title "Add agent.yaml (Living Map manifest)"
```

Then:

1. If your repo is not yet listed in [`repos.txt`](https://github.com/SAAF-Project/saaf-living-map/blob/main/repos.txt), open a one-line pull request there adding `SAAF-Project/your-repo`. Repos already in the list need nothing further.
2. Once your PR is merged, wait for the next scheduled build (or ask a maintainer to run it). Your agent appears on the map sourced from your repo rather than from a seed.

Private repos are read with a token on the map maintainer's account; the map reads the manifest only and never shows code. RCM-Builder is private and is read this way today.

## 6. Keeping it current

Update `agent.yaml` as part of normal work:

- Moving from `building` to `ready`, or from `ready` to `tested`? Change `maturity`.
- Started consuming another agent's output? Add it to `depends_on`.
- Need help? Set `open_slots` so people browsing the map can find you.
- Changed what the agent is allowed to do? Update the `mandate` in a pull request so a reviewer sees it.

The map is only as good as the manifests behind it. A stale `agent.yaml` is worse than none, because it looks authoritative.

## Pull request checklist

- [ ] `agent.yaml` is in the repo root, PR targets `main` (or `master`)
- [ ] `island` and `maturity` use one of the listed values
- [ ] Every `forbidden_actions` entry has a `rationale`, and `change_own_config` is among them
- [ ] `trusted_inputs`, `human_approval_required_for` and `evidence_policy` are filled in
- [ ] Ran `build_map.py --offline` locally with zero warnings
- [ ] Repo is listed in `repos.txt` (or a PR to add it is open)
