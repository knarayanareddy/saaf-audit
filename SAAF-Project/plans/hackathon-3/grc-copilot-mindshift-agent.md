# GRC Copilot Mindshift Agent

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Schuberg Philis) |
| **Organisation** | Schuberg Philis |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Schuberg Philis's GRC (Governance, Risk and Compliance) team identified a fundamental adoption gap in their 2026 AI strategy: **"Technology is in 2026, our behavior is in 2010."** M365 Copilot is available across the organisation, but GRC/audit workflows still rely on manual email triage, copy-pasting from Teams meeting notes, and searching SharePoint for evidence documents.

Specific pain points:

- **Meeting intelligence gap**: Teams calls between auditors and auditees produce hours of recordings; extracting action items, commitments, and open points is manual
- **Evidence collection friction**: Auditors search SharePoint/Teams channels for policy documents and evidence files; 30–60 minutes per audit area
- **Email overload**: Audit-related emails (requests, responses, reminders) are not triaged intelligently against open audit items
- **Copilot underutilisation**: M365 Copilot license exists but GRC team lacks structured prompts and workflows to integrate it into audit practice

This plan designs an agent that bridges GRC audit workflows with M365 Copilot, making the adoption practical rather than theoretical.

---

## 3. Use-Case Type and Scope

**Audit domain:** GRC — M365 Copilot Adoption for Internal Audit

**Applicable standards:**

- IIA Standard 1210 (Proficiency — using appropriate tools)
- IIA Standard 2310 (Identifying Information — gathering sufficient evidence)
- Microsoft 365 Copilot usage policies

**In scope:**

- Structured M365 Copilot prompts for audit-specific use cases (meeting summaries, evidence search, email triage)
- Agent workflow: auditor describes audit area → agent generates Copilot prompt library for that area
- Prompt templates for 6 common GRC/audit Copilot scenarios
- Output: practitioner-ready "Copilot Cheat Sheet" per audit domain

**Out of scope:**

- Building a custom M365 Copilot plugin (requires Microsoft certification)
- Processing real audit evidence through the API
- Automated Copilot execution (prompts are designed for human-in-the-loop use)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Prompt library: 6 Copilot prompt templates per audit scenario; Claude prompt that generates a customised Copilot cheat sheet given an audit domain |
| **Tools** | Python script that renders a Markdown cheat sheet from a template + Claude-generated customisations |
| **Regulatory** | IIA Standards on evidence gathering and proficiency; Microsoft AI usage policy notes |
| **Outputs** | Practitioner-ready Copilot Cheat Sheet (Markdown/PDF) per audit domain; not a machine-readable finding |

---

## 5. Prompts

### System prompt (draft)

```
You are a GRC/internal audit Copilot coach for Schuberg Philis.
Your role is to help auditors get maximum value from Microsoft 365 Copilot in their daily
audit work.

You generate specific, copy-paste-ready Copilot prompts for six audit scenarios:
1. Summarise a Teams meeting recording for audit action items
2. Search SharePoint for policy documents relevant to a control area
3. Draft an evidence request email to the auditee
4. Summarise an inbox thread related to an open audit item
5. Extract commitments and deadlines from a Teams chat transcript
6. Generate a structured agenda for an audit kick-off meeting

For each scenario, you generate:
- A specific, copy-paste-ready Copilot prompt
- The expected output format
- Tips for refining the prompt if the result is too generic

Always ground prompts in the specific audit domain provided. Use plain Dutch or English
depending on the user's language. Be concise — auditors are busy.
```

### Example user prompts

**Prompt 1 — Domain-specific cheat sheet:**
```
Generate a M365 Copilot cheat sheet for an audit of Identity & Access Management controls
(ISO 27001 A.5.15–A.5.18). The auditor needs prompts for:
- Summarising the Teams call where IT explained the joiner/mover/leaver process
- Finding the IAM policy in SharePoint
- Drafting an evidence request for the Active Directory extract

Language: Dutch
Audience: Internal auditor with basic Copilot experience
```

**Prompt 2 — Meeting summary extraction:**
```
I have a 90-minute Teams meeting transcript (pasted below) from a kickoff meeting with the
IT Operations team. Extract:
1. All action items (who, what, by when)
2. Open audit questions that need follow-up
3. Any risks or exceptions mentioned by the auditee

Format as a structured Markdown note I can paste into my audit workpaper.

[Transcript pasted here]
```

**Intended file location:** `prompts/audit-use-cases/grc-copilot-mindshift.md`

---

## 6. Tools and Techniques

### Approach

**Phase 1 — Copilot prompt library (manual, human-curated):**

Six prompt templates for the most common GRC audit scenarios, written and validated by the Schuberg Philis GRC team. These are the "starter kit" — prompts that work without any customisation.

**Phase 2 — Claude-powered customisation agent:**

An agent (Claude) that takes an audit domain as input and generates domain-specific Copilot prompts by adapting the template library. This removes the "blank page" problem for auditors who want to use Copilot for a new audit area.

**Phase 3 — Cheat sheet renderer:**

A lightweight Python script that combines the template library with Claude-generated customisations to produce a printable/shareable Markdown cheat sheet.

### Example script or pseudocode

```python
import anthropic
from pathlib import Path

TEMPLATE_LIBRARY = Path("prompts/audit-use-cases/grc-copilot-templates.md").read_text()
client = anthropic.Anthropic()

def generate_cheat_sheet(audit_domain: str, language: str = "nl") -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Generate a Copilot cheat sheet for: {audit_domain}\nLanguage: {language}"
        }]
    )
    return response.content[0].text

def render_pdf(cheat_sheet_md: str, output_path: str) -> None:
    # pandoc conversion for distribution
    import subprocess
    subprocess.run(["pandoc", "-o", output_path, "--from=markdown"], input=cheat_sheet_md.encode())
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), Microsoft 365 Copilot (human-in-the-loop), `pandoc` (optional PDF rendering)

**Intended file location:** `tools/scripts/grc_copilot_generator.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA Standard 1210 | Proficiency — using appropriate AI tools |
| IIA Standard 2310 | Identifying Information — evidence sufficiency |
| Microsoft AI Use Policy | M365 Copilot data residency and privacy guidelines |

### Claude / AI tool usage notes

- No real audit data sent to the API — prompts are generated based on domain descriptions, not real evidence.
- Meeting transcripts in examples are synthetic.
- M365 Copilot processes real organisational data within Microsoft's data boundary (separate concern from this script).

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown (cheat sheet) + optional PDF via pandoc

**Schema reference:** N/A (practitioner guide, not audit findings)

### Synthetic example — cheat sheet excerpt

```markdown
## M365 Copilot Cheat Sheet — Identity & Access Management Audit

### Scenario 1: Teams meeting summary

**When to use:** After kick-off or walkthroughs with IT/IAM team
**Copilot prompt:**

> "Summarise this meeting. Focus on: (1) how the joiner/mover/leaver process works,
> (2) any exceptions or known issues mentioned, (3) action items with owners and deadlines.
> Format as bullet points."

**Expected output:** Structured summary with action items
**Tip:** If the summary misses context, add: "The meeting was about our ISO 27001 A.5.18 control review."

---

### Scenario 2: SharePoint evidence search

**When to use:** When you need the IAM policy document
**Copilot prompt:**

> "Find the Identity & Access Management policy in SharePoint. Show me the version date
> and the section on privileged access management."

**Expected output:** Link to document + relevant excerpt
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6 — cheat sheet generation)
- [x] Python 3.9+
- [x] Markdown templates (manually curated)
- [x] M365 Copilot (human-in-the-loop, not API)

**Stretch goals:**

- [ ] PDF rendering via pandoc for distribution as printable cards
- [ ] Dutch and English versions of all templates
- [ ] Integration with Skills Registry: match Copilot cheat sheets to participant skill level
- [ ] M365 Copilot Plugin (requires Microsoft certification — longer-term)

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- 6 Copilot prompt templates (Markdown, language-agnostic)
- Claude customisation script
- Cheat sheet renderer

**What help I'm looking for:**

- GRC auditors at other organisations to validate and extend the template library
- Microsoft 365 specialists to advise on Copilot plugin pathway
- Dutch-language audit practitioners for NL prompt validation

**Cross-org interest:**

M365 Copilot is available at many SAAF member organisations (Mollie, Schuberg Philis, Wolters Kluwer). Any organisation with Copilot licenses and an internal audit function benefits from this cheat sheet approach. Prompts are organisation-agnostic by design.

**Community Contributors and EU AI Act Context (April 2026):**

**Patrick Chu (NOREA):** Patrick is an active member of NOREA (the Dutch IT Auditor body) and contributed significantly to the discussion around this plan in the SAAF WhatsApp community (April 2026). Patrick's perspective: M365 Copilot adoption in Dutch audit teams is accelerating post-EU AI Act Article 4 (AI Literacy obligation) — organizations need to demonstrate that their audit staff can effectively use AI tools. The Copilot cheat sheet directly serves as evidence of structured AI literacy training. Patrick is a candidate contributor for Dutch-language prompt validation and NOREA channel distribution.

**EU AI Act GPAI Use Case:** The EU AI Act General Purpose AI (GPAI) provisions (Chapter V, Articles 51–56) become enforceable August 2, 2026. M365 Copilot is a GPAI model as defined by the Act. Internal audit functions that use Copilot for audit work must therefore:
1. Assess whether Copilot's use in their organization falls under high-risk AI system provisions (Annex III)
2. Maintain documentation of how Copilot is used in audit workflows (this cheat sheet serves as that documentation)
3. Ensure auditors using Copilot have "adequate AI literacy" as required by Art. 4

This positions the Copilot cheat sheet not just as a productivity tool but as **compliance evidence** under the EU AI Act — a significantly stronger business case for CAEs and IT managers.

**Related SAAF plans:**

- [`plans/hackathon-2/rohan-sobha-compliance-report-generator.md`](../hackathon-2/rohan-sobha-compliance-report-generator.md) — report generation shares the Copilot + Claude hybrid approach
- [`plans/hackathon-2/robeminem94-vendor-guard.md`](../hackathon-2/robeminem94-vendor-guard.md) — vendor risk use case where Copilot email summarisation is immediately applicable
- [`docs/reference/skills-and-agents.md`](../../docs/reference/skills-and-agents.md) — Audit Chaser Bot (email/Teams) is a related adjacent skill
- [`plans/hackathon-3/eu-ai-act-compliance-monitor.md`](eu-ai-act-compliance-monitor.md) — EU AI Act GPAI deadline monitoring (Aug 2, 2026); Copilot use in audit is in scope
- [`plans/hackathon-3/audit-skills-transformation-curriculum.md`](audit-skills-transformation-curriculum.md) — AI literacy curriculum; Copilot cheat sheets map to Stage 2 skill development

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | 6 scenarios defined; template structure designed |
| **Do** | In progress | Prompt library + generator script at Hackathon #3 |
| **Check** | Not started | Validate: do prompts produce useful output in real Copilot environment? |
| **Act** | Not started | Target: GRC team adopts cheat sheets in next audit cycle (Q2 2026) |

---

## 12. Open Questions

1. Should the cheat sheets be language-specific (NL/EN) from the start, or start English-only?
2. Are there Microsoft content policies that restrict how Teams transcript content can be processed through external AI (Claude) — even if only synthetic examples are used?
3. How should we handle the gap between M365 Copilot (which has SharePoint/Teams access) and Claude Code (which does not)? Should this be a pure Copilot plan, or a hybrid Copilot + Claude plan?
4. Could a Microsoft Graph API connector make this plan more powerful (fetching real SharePoint/Teams data with permission)?
