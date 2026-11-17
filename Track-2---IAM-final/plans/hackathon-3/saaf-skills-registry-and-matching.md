# SAAF Skills Registry & Hackathon Matching

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Workflow |
| **Status** | Draft |

---

## 2. Problem Statement

SAAF has 45+ participating organisations and 80+ individual participants across four roles (Auditor, Vaktechniek/Audit Specialist, Analyst, Engineer). Each hackathon involves assigning participants to plans/tasks, but currently:

- There is no structured record of what skills each participant has
- Matching is done ad hoc on the day (self-selection or organiser assignment)
- Plans have different technical requirements (Python, Jira API, Claude prompting, SOx knowledge) that are rarely made explicit
- Result: some participants feel under-challenged, others are blocked on skills they don't have

This workflow creates a skills registry and a lightweight matching algorithm that maps participants to plans based on their background, across all four SAAF pillars (Prompts, Tools, Regulatory, Outputs).

---

## 3. Use-Case Type and Scope

**Audit domain:** SAAF Governance / Hackathon Organisation

**Applicable standards:**

- IIA Standard 1200 (Proficiency and Due Professional Care)
- COBIT BAI08 (Manage Knowledge)

**In scope:**

- Skills questionnaire (15 questions, ~5 minutes)
- Participant registry stored in Strapi (or Google Forms → JSON export)
- Matching algorithm: score participant skills vs. plan requirements across 4 pillars
- "Eerst kiest eerste maalt" (first-come-first-served) assignment with suitability score
- Output: assignment matrix in Markdown for each hackathon session

**Out of scope:**

- Continuous skills development tracking (v1 = hackathon-day snapshot)
- Real-time UI/app (Markdown output is sufficient for v1)
- Automated email/Slack notifications (manual distribution)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Claude prompt that takes a participant's skills JSON and a plan's requirements, and outputs a suitability score + rationale in JSON |
| **Tools** | Python matching script (`tools/scripts/skills_matching.py`); optional Strapi content type for participant registry |
| **Regulatory** | IIA Standard 1200 (proficiency) as the normative basis for the questionnaire design |
| **Outputs** | Assignment matrix Markdown: who does what at each hackathon, with suitability scores |

---

## 5. Prompts

### System prompt (draft)

```
You are a hackathon organiser for SAAF (Shared Audit Agents Framework), a community of
internal auditors building AI agents.

You receive a participant's skills profile and a hackathon plan's requirements.
Your job is to calculate a suitability score (0–100) and provide a brief rationale.

The four SAAF pillars are:
- Prompts: ability to write and iterate on AI system prompts
- Tools: ability to write Python scripts, use APIs, work with CLI tools
- Regulatory: knowledge of audit standards (IIA, ISO 27001, GDPR, DORA, SOx, etc.)
- Outputs: ability to document findings, write reports, define schemas

Score each pillar 0–25 and return the total (0–100).
Always respond with valid JSON only.
```

### Example user prompts

**Prompt 1 — Match participant to plan:**
```
Participant profile:
{
  "name": "Jan de Vries",
  "role": "Engineer",
  "prompts_level": 2,
  "tools_level": 4,
  "regulatory_level": 1,
  "outputs_level": 2,
  "languages": ["Python", "TypeScript"],
  "domain_knowledge": ["IT Operations", "Cloud"],
  "availability_hours": 4
}

Plan requirements:
{
  "slug": "saaf-jira-confluence-mcp",
  "type": "Skill",
  "prompts_required": 1,
  "tools_required": 5,
  "regulatory_required": 1,
  "outputs_required": 2,
  "languages_preferred": ["TypeScript"],
  "domain": "IT Infrastructure"
}

Return: { "suitability_score": <0-100>, "pillar_scores": {...}, "rationale": "..." }
```

**Prompt 2 — Generate assignment matrix:**
```
Given the following participant-plan suitability scores (JSON array), produce an assignment
matrix following "first-come-first-served" logic: the best-matching participant gets first
choice, then the next, etc. Each plan has a max capacity of 2 participants.
Minimize total unsuitability (maximize aggregate score).

[scores array injected here]
```

**Intended file location:** `prompts/audit-use-cases/skills-matching.md`

---

## 6. Tools and Techniques

### Approach

**Phase 1 — Skills questionnaire (15 questions):**

1. Role (Auditor / Vaktechniek / Analyst / Engineer)
2. Years of audit experience
3. Prompts pillar: "Can you write a system prompt from scratch?" (1–5)
4. Prompts pillar: "Have you used Claude / GPT for audit tasks?" (Y/N + description)
5. Tools pillar: "Python proficiency" (None / Basic / Intermediate / Advanced)
6. Tools pillar: "Have you used APIs (REST/MCP)?" (Y/N)
7. Tools pillar: "GitHub comfort level" (Can read / Can commit / Can review PRs / Can administer)
8. Regulatory pillar: "Which standards do you know well?" (multi-select: ISO 27001, GDPR, DORA, SOx, COBIT, ITIL, NEN 7510, Other)
9. Regulatory pillar: "Primary audit domain" (free text)
10. Outputs pillar: "Comfortable writing structured findings?" (Y/N)
11. Outputs pillar: "Experience with JSON/YAML schemas?" (Y/N)
12. Preferred hackathon role: Builder / Reviewer / Documenter / Tester
13. Available hours on hackathon day
14. Interested in cross-org collaboration? (Y/N)
15. Free text: "What do you most want to learn at this hackathon?"

**Phase 2 — Matching algorithm:**

```python
def suitability(participant, plan):
    score = 0
    for pillar in ["prompts", "tools", "regulatory", "outputs"]:
        p_level = participant[f"{pillar}_level"]   # 1–5
        req_level = plan[f"{pillar}_required"]     # 1–5
        # Reward overskill slightly less than exact match
        if p_level >= req_level:
            score += 25 * (req_level / p_level) ** 0.5
        else:
            score += 25 * (p_level / req_level) ** 2  # Penalise underskill harder
    return round(score)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6 for rationale generation), Strapi 4 (participant data store, optional), GitHub Actions (runs matching before each hackathon)

**Intended file location:** `tools/scripts/skills_matching.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA Standard 1200 | Proficiency — auditors must have the knowledge to perform their work |
| IIA Standard 1230 | Continuing Professional Development |
| COBIT BAI08 | Manage Knowledge — skills inventory best practice |

### Claude / AI tool usage notes

- Questionnaire responses contain only professional profile data — no PII beyond first name and organisation.
- No real audit evidence processed.
- Matching rationale generated by Claude is advisory only; final assignment decisions made by human organisers.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown (assignment matrix) + JSON (participant registry)

**Schema reference:** N/A (not audit findings)

### Synthetic example — skills profile

```json
{
  "id": "participant-042",
  "name": "Anon Auditor",
  "role": "Auditor",
  "prompts_level": 3,
  "tools_level": 1,
  "regulatory_level": 5,
  "outputs_level": 4,
  "domain_knowledge": ["Compliance", "GDPR", "DORA"],
  "availability_hours": 6,
  "preferred_role": "Reviewer"
}
```

### Synthetic example — assignment matrix

```markdown
## Hackathon #3 Assignment Matrix

| Participant | Plan | Suitability | Pillar match | Notes |
|---|---|---|---|---|
| Anon Auditor | `johannesiv-policy-to-controls-extractor` | 88/100 | R:25 P:18 O:22 T:5 | Strong regulatory fit |
| Jan de Vries | `saaf-jira-confluence-mcp` | 91/100 | T:25 P:20 R:5 O:15 | Strong engineering fit |
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6 for rationale)
- [x] Python 3.9+
- [x] Google Forms or Strapi (questionnaire input)
- [x] Markdown output (assignment matrix)

**Stretch goals:**

- [ ] Strapi content type for persistent participant registry
- [ ] GitHub Actions: auto-run matching 48h before each hackathon
- [ ] GitHub Pages: participant profile cards with skill bars
- [ ] Real-time matching during hackathon (live dashboard)

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Questionnaire template (Google Forms export + Strapi schema)
- Python matching algorithm
- Claude rationale prompt

**What help I'm looking for:**

- Auditors and vaktechniek to validate the questionnaire covers relevant competencies
- Engineers to help with Strapi integration (if not Google Forms)
- Analysts to suggest better scoring rubrics

**Cross-org interest:**

Multiple organisations have mentioned difficulty matching participants to tasks. This is core shared infrastructure. Intended for reuse at every future SAAF hackathon.

**Video Transcription Insights (Hackathon #3 analysis):**

**Step-by-step skill creation workflow for non-technical builders:**

Video analysis identified a key barrier: non-technical auditors want to build skills but don't know where to start. A structured step-by-step workflow (not just a questionnaire) bridges this gap:

1. **Define the skill output first** — what exactly should the skill produce? (JSON finding, Markdown report, email draft, filled template). Non-technical builders often start with the process; starting with the output is more effective.
2. **Write a test case before the prompt** — describe one specific input and the expected output in plain language. This becomes the evaluation criterion.
3. **Use the plan template as the build specification** — the SAAF 12-section plan template is not just documentation; sections 5 (Prompts), 6 (Tools), and 8 (Output Format) constitute the minimum viable specification for a skill.
4. **Validate with synthetic data** — use Strapi data to test the skill before presenting to the group.
5. **Submit before it's perfect** — a 70% complete plan with a working prototype is more valuable than a perfect plan with no code.

Integrate this workflow into the skills matching UI: when a participant is assigned to a plan, they receive the 5-step workflow as a "getting started" guide specific to their plan. This converts the skills registry from a matching tool into an onboarding system.

**Related SAAF plans:**

- [`plans/hackathon-2/floris-stokkers-work-program-agent.md`](../hackathon-2/floris-stokkers-work-program-agent.md) — auditor assignment is a sub-problem of this workflow
- [`plans/hackathon-3/saaf-strapi-synthetic-data.md`](saaf-strapi-synthetic-data.md) — Strapi sandbox that can host the participant registry
- [`docs/reference/skills-and-agents.md`](../../docs/reference/skills-and-agents.md) — 12 agent archetypes used to define plan requirements
- [`plans/hackathon-3/audit-skills-transformation-curriculum.md`](audit-skills-transformation-curriculum.md) — reskilling framework that maps to the skills taxonomy in this plan

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Questionnaire designed; algorithm defined |
| **Do** | In progress | Prototype matching script at Hackathon #3 |
| **Check** | Not started | Post-hackathon: did matched assignments lead to better outcomes? |
| **Act** | Not started | Target: standardise questionnaire for Hackathon #4 |

---

## 12. Open Questions

1. Should the questionnaire be mandatory (pre-registration) or optional (day-of)?
2. Is Strapi the right backend, or is a simple Google Sheet + Python script sufficient for v1?
3. How do we handle participants who want to work alone vs. those who want to pair?
4. Should plans declare their required skills explicitly (in frontmatter), or should the organiser annotate them manually?
