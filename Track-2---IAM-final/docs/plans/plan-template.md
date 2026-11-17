# Plan Template — SAAF Hackathon Submission

<!-- Copy this file to plans/hackathon-4/firstname-lastname-your-slug.md and fill it in.
     Delete instruction comments (lines starting with <!--) before opening your PR.
     Mark any section you haven't completed yet as "TBD" — that's fine. -->

---

## 1. Metadata

<!-- Fill in each field. For Type, pick one: Agent / Skill / Workflow.
     For Status, start with "Draft"; update to "Presented" after the session and "Finalised" when your PR is merged. -->

| Field | Value |
|---|---|
| **Submitter** | Firstname Lastname (pseudonym permitted) |
| **Organisation** | Your org (or "Anonymous") |
| **Session** | Hackathon 4 (Session 5) |
| **Type** | Agent / Skill / Workflow |
| **Status** | Draft / Presented / Finalised |
| **Claimed By** | _Your name if you are actively building this — leave blank if proposing only_ |

---

## 2. Problem Statement

<!-- Describe the audit task that is currently slow, error-prone, or not done at all.
     Be specific: what does the auditor do today? What goes wrong or takes too long? -->

_What audit task is this solving? Why does it matter?_

---

## 3. Use-Case Type and Scope

<!-- Name the audit domain (e.g. Access Management, Vendor Risk, Change Management).
     List 1–3 applicable standards or frameworks (e.g. ISO 27001, SOC 2, ISAE 3402).
     Be clear about what is IN scope for this plan and what is explicitly OUT of scope. -->

**Audit domain:** _e.g. Access Management_

**Applicable standards:**

- _Standard 1_
- _Standard 2_

**In scope:**

- _Item 1_

**Out of scope:**

- _Item 1_

---

## 4. SAAF 4-Pillar Mapping

<!-- For each pillar, describe what you will produce (Output) or what you will reuse from the shared repo (Input/Reuse).
     Leave a pillar blank if it genuinely does not apply to your plan. -->

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | _e.g. New system prompt in `prompts/audit-use-cases/`_ |
| **Tools** | _e.g. New Python script in `tools/scripts/`_ |
| **Regulatory** | _e.g. Reuse `regulatory/control-mappings/iso27001.md`_ |
| **Outputs** | _e.g. JSON finding conforming to `outputs/schemas/finding-schema.json`_ |

---

## 5. Prompts

<!-- Provide a first draft of the system prompt and two example user prompts.
     Even rough drafts are valuable — the community will iterate on them.
     Note the intended file path once you add it to the repo. -->

### System prompt (draft)

```
You are an AI audit assistant specialised in [domain].
Your role is to [describe the goal].
Always [key behaviour constraint].
Never [key guardrail].
```

### Example user prompts

**Prompt 1:**
```
[Paste an example user message the agent will receive]
```

**Prompt 2:**
```
[Paste a second example]
```

**Intended file location:** `prompts/audit-use-cases/your-slug.md`

---

## 6. Tools and Techniques

<!-- Describe the technical approach at a level that lets a team-mate reproduce it.
     Include a short code snippet or pseudocode if helpful.
     Any tech stack is valid. Strapi is available as an optional synthetic data API if you want
     realistic-looking test data without using real audit evidence. -->

### Approach

_Describe the technical method in plain language._

### Example script or pseudocode

```python
# Pseudocode or real snippet — either is fine at plan stage
```

**Tech stack used:** _e.g. Python 3.11, Claude API (claude-sonnet-4-6), Strapi (synthetic data)_

**Intended file location:** `tools/scripts/your-slug.py` _(if applicable)_

---

## 7. Regulatory and Policies

<!-- List the standards or control objectives your agent addresses.
     Note any specific Claude / AI tool usage considerations (e.g. data residency, model choice).
     Work through the guardrails checklist — tick what applies. -->

### Applicable standards

| Standard | Relevant controls |
|---|---|
| _e.g. ISO 27001_ | _e.g. A.9.2 — User access management_ |

### Claude / AI tool usage notes

_e.g. No real PII will be sent to the API. Synthetic data only during testing._

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

<!-- Describe what the agent/skill produces.
     If it produces findings, reference finding-schema.json.
     Include a short synthetic example so reviewers can see what "done" looks like. -->

**Format:** JSON / Markdown / CSV / Other

**Schema reference:** `outputs/schemas/finding-schema.json` _(if producing findings)_

### Synthetic example output

```json
{
  "id": "F-001",
  "title": "Example finding title",
  "risk_rating": "High",
  "observation": "Synthetic observation text.",
  "recommendation": "Synthetic recommendation text."
}
```

---

## 9. Tech Stack

<!-- Tick what you plan to use. Add items that aren't listed.
     Separate MVP (what you need to demo) from stretch goals (what would be nice). -->

**MVP scope:**

- [ ] Claude API / Claude Desktop
- [ ] Python 3.9+
- [ ] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional)
- [ ] _Other: ___

**Stretch goals:**

- [ ] _Stretch goal 1_
- [ ] _Stretch goal 2_

---

## 10. Collaboration and Knowledge Sharing

<!-- The S in SAAF is Shared. This section captures the community value of your plan.
     Be as specific as you can about what you'll open-source and what help you're looking for. -->

**What I plan to open-source:**

- _e.g. The system prompt and a synthetic test dataset_

**What help I'm looking for:**

- _e.g. Someone with SOC 2 expertise to review the control mappings_

**Cross-org interest:**

_Are other organizations working on the same problem? Would you welcome collaboration?_

---

## 11. PDCA Positioning

<!-- Mark where this plan sits in the Plan–Do–Check–Act cycle.
     Be honest — "Plan only" is a valid and valuable contribution. -->

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete / In progress / Not started | _e.g. Template filled in_ |
| **Do** | Complete / In progress / Not started | _e.g. Prototype built at hackathon_ |
| **Check** | Complete / In progress / Not started | _e.g. Planned for Q2 adoption_ |
| **Act** | Complete / In progress / Not started | _e.g. Target: Hackathon 3_ |

---

## 12. Open Questions

<!-- List anything unresolved that you want input on during the session.
     No question is too basic — this is a collaborative space. -->

1. _Question 1_
2. _Question 2_
3. _Question 3_
