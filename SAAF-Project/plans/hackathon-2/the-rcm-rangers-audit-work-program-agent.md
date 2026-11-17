# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | The RCM Rangers |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Workflow |
| **Status** | Draft |

---

## 2. Problem Statement

Internal auditors spend significant time manually translating a completed
Risk & Control Matrix (RCM) into an executable Audit Work Program. This process
is repetitive and error-prone: test steps are often too generic, methodology
selection is inconsistent across team members, opportunities for data analytics
(CAATs) are missed, and hour estimates are unreliable.

Today, an auditor opens the RCM in Excel, writes test procedures in Word by hand,
selects methodologies based on personal experience, and estimates hours without
a structured method. For a compliance/regulatory audit with 15–30 controls, this
easily takes a full day of preparation — before any actual testing begins.

This plan describes a Claude-powered workflow that automates that translation:
from RCM input to a structured, GIAS 13.6-compliant Audit Work Program, including
test procedures (ToD + ToE), methodology selection, CAATs identification, auditor
assignment, and hour estimates.

---

## 3. Use-Case Type and Scope

**Audit domain:** Compliance & Regulatory (e.g. GDPR, DORA, AVG)

**Applicable standards:**

- GIAS Standard 13.5 — Resource identification and sufficiency
- GIAS Standard 13.6 — Engagement work program requirements
- GDPR (AVG) — Used as primary example regulatory framework
- DORA — Digital Operational Resilience Act, used for IT-related controls

**In scope:**

- Generating Test of Design (ToD) and Test of Operating Effectiveness (ToE) procedures per control
- Selecting audit methodology per test step (Inquiry, Observation, Inspection, Re-performance, Analytical)
- Identifying CAATs opportunities and suggesting tools (Excel / Power Query)
- Assigning auditors to tasks based on seniority and skill
- Estimating hours per task

**Out of scope:**

- Executing the audit tests (this plan covers preparation only)
- Generating audit findings or reports
- Integration with audit management software (e.g. TeamMate, AuditBoard)
- Phase 2 automation via Python/API (planned for Hackathon 3)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | 4 new prompts in `prompts/audit-use-cases/rcm-rangers-work-program.md` |
| **Tools** | Prompt chaining workflow (manual, no code); pseudocode for Phase 2 in `tools/scripts/` |
| **Regulatory** | Reuse or extend `regulatory/control-mappings/` with GDPR and DORA references |
| **Outputs** | Structured Work Program table (Word/Excel); synthetic example conforming to `outputs/schemas/finding-schema.json` |

---

## 5. Prompts

### System prompt (draft)

```
You are a senior internal auditor with deep expertise in compliance and
regulatory audits (GDPR, DORA, ISO 27001, AVG).

Your role is to transform a Risk & Control Matrix (RCM) into a detailed,
executable Audit Work Program that complies with GIAS Standard 13.6.

Always:
- Write test procedures in clear, step-by-step language suitable for a junior auditor
- Be specific: name the exact document, system, or dataset to be reviewed
- Reference the applicable regulation or standard for each procedure (e.g. GDPR Art. 32)
- Structure output as a table with columns: WP-ID | RCM Ref | Objective | Procedure |
  Methodology | Evidence Required | Pass/Fail Criteria | Assigned Auditor | Est. Hours

Never:
- Use generic steps like "review the policy" without specifying which policy and what to check
- Assign "Inquiry" as the only methodology for a High significance risk
- Include real personal data, client names, or system credentials in any output
```

### Example user prompts

**Prompt 1 — Generate test procedures:**
```
I will give you a Risk & Control Matrix (RCM) for a GDPR compliance audit.

For each control, generate:
1. A Test of Design (ToD) procedure — does the control exist as intended?
2. A Test of Operating Effectiveness (ToE) procedure — is it working in practice?

Use step-by-step language a junior auditor can follow independently.
Reference the relevant GDPR article for each control.

Here is the RCM:
[PASTE RCM TABLE HERE]
```

**Prompt 2 — Assign methodology and flag gaps:**
```
Below are the test procedures from our GDPR audit work program.

For each procedure:
1. Assign the most appropriate methodology:
   Inquiry / Observation / Inspection / Re-performance / Analytical procedures
2. Flag any High significance risk where Inquiry is the only method —
   these need at least one additional methodology.
3. Identify which procedures could be replaced or supplemented by a
   data analytics test using Excel or Power Query.

[PASTE TEST PROCEDURES HERE]
```

**Intended file location:** `prompts/audit-use-cases/rcm-rangers-work-program.md`

---

## 6. Tools and Techniques

### Approach

The workflow uses **prompt chaining** — a sequence of four Claude prompts where
the output of each step becomes the input of the next. No coding or API access
is required in Phase 1. The auditor works entirely in the Claude chat interface
(claude.ai) and formats the output in Microsoft Word or Excel.

```
Step 1: RCM (Excel) → Prompt 1 → Test Procedures (ToD + ToE)
Step 2: Test Procedures → Prompt 2 → Methodology per step + CAATs flags
Step 3: Full procedures + methodology → Prompt 3 → Hour estimates + auditor assignments
Step 4: Complete program → Prompt 4 → Quality check (flag missing coverage, over-allocation)
Step 5: Auditor reviews output → Final Word document → CAE review
```

### Example script or pseudocode

```python
# Phase 2 pseudocode (planned for Hackathon 3 — not required for this plan)
# Requires: Python 3.11+, anthropic SDK, python-docx

import anthropic

client = anthropic.Anthropic()  # API key from environment variable

def generate_work_program(rcm_text: str) -> str:
    """Takes RCM as plain text, returns structured work program."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,  # loaded from prompts/audit-use-cases/
        messages=[
            {"role": "user", "content": f"Generate work program for:\n{rcm_text}"}
        ]
    )
    return response.content[0].text

# Output written to Word document via python-docx
# Test data loaded from Strapi synthetic data API (SAAF-sponsored)
```

**Tech stack used:** Claude (claude.ai, browser-based), Microsoft Word, Microsoft Excel,
Power Query (CAATs). Phase 2: Python 3.11, Claude API (claude-sonnet-4-6), Strapi (synthetic data)

**Intended file location:** `tools/scripts/rcm-rangers-work-program.py` _(Phase 2 only)_

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.5 | Identify types and quantity of resources; assess whether available resources are appropriate and sufficient |
| GIAS 13.6 | Document criteria, tasks, methodologies, tools, auditor assignments, and resource requirements |
| GDPR Art. 32 | Security of processing — used as primary example for test procedure generation |
| GDPR Art. 5(1)(e) | Storage limitation — example for data retention control testing |
| DORA Art. 11 | ICT business continuity — example for IT resilience control testing |

### Claude / AI tool usage notes

- No real PII, client data, or audit evidence will be sent to the Claude API.
  All testing uses anonymized or synthetic data only.
- RCM inputs must be anonymized before use: replace organization names, system
  names, and employee names with placeholders (e.g. [ORG], [SYSTEM-A], [AUDITOR-1]).
- All Claude-generated output must be reviewed and approved by a qualified
  auditor before inclusion in the formal work program.
- The Claude model version used (claude-sonnet-4-6) must be documented in the
  work program header for auditability and reproducibility.
- Prompts used during the engagement must be saved alongside the work program
  so the AI-assisted process is traceable and reviewable by the CAE.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown table (in Claude output) → copied to Word/Excel by auditor

**Schema reference:** `outputs/schemas/finding-schema.json` _(for findings generated in later phases)_

### Synthetic example output

```json
{
  "wp_id": "WP-003",
  "rcm_reference": "CTR-007",
  "objective": "Verify that access to personal data is restricted to authorized staff only, per GDPR Art. 32.",
  "procedure": [
    "1. Request the current user access list from the system owner for [SYSTEM-A].",
    "2. Compare the list against the approved roles matrix (HR records, latest version).",
    "3. Identify any users with active access who are no longer in an authorized role.",
    "4. For a sample of 5 users, confirm that access was formally approved in writing."
  ],
  "methodology": ["Inspection", "Analytical procedures"],
  "evidence_required": [
    "User access log exported from [SYSTEM-A]",
    "Approved roles matrix (HR Excel)",
    "Access approval emails or tickets"
  ],
  "pass_fail_criteria": "Pass: 0 unauthorized users identified. Fail: any active user outside the approved roles matrix.",
  "assigned_auditor": "Auditor A (Senior)",
  "estimated_hours": 3,
  "status": "Not started"
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Desktop
- [ ] Python 3.9+
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional)
- [x] Other: Microsoft Word, Microsoft Excel, Power Query

**Stretch goals:**

- [ ] Python script to auto-generate Word document from RCM JSON (Phase 2)
- [ ] Strapi synthetic RCM dataset shared with all SAAF members for standardized testing

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The 4 system prompts and example user prompts (ready to copy-paste)
- A synthetic GDPR compliance RCM (10–15 controls) for community testing
- The output format standard (Word/Excel template)

**What help I'm looking for:**

- Input from auditors in other domains (IT audit, financial audit) to validate
  whether the prompts generalize beyond compliance/regulatory
- Someone with Python experience to help build Phase 2 automation (Hackathon 3)
- Feedback on whether the hour estimates Claude produces are realistic

**Cross-org interest:**

Yes — the RCM-to-Work-Program translation is a universal audit task regardless
of industry or domain. Any organization doing structured internal audits could
benefit from this workflow. Collaboration is very welcome.

**Related SAAF plans:**

- [Floris Stokkers — Audit Work Program Agent](floris-stokkers-work-program-agent.md) — individual plan from an RCM Rangers team member; coordinates on the same use case with a more agent-based approach
- [Frank van Dissel — UC8 Work Program Agent](frank-van-dissel-uc8-audit-work-program.md) — parallel submission on the same use case; align on output schema
- [Inge Garretsen — Audit Work Program Agent](inge-garretsen-audit-work-program-agent.md) — related cross-domain approach; potential alignment on methodology selection

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Template filled in; prompts drafted; workflow defined |
| **Do** | In progress | Manual prompt chaining tested during Hackathon 2 |
| **Check** | Not started | Planned: validate output quality against real RCM post-hackathon |
| **Act** | Not started | Target: share refined prompts and lessons learned at Hackathon 3 |

---

## 12. Open Questions

1. Should the work program output format align with a specific existing schema
   in the SAAF repo, or should we propose a new `work-program-schema.json`?
2. How do other SAAF members handle auditor assignment when the team is unknown
   at planning time — should we use role labels (Senior/Junior) instead of names?
3. Are there existing GDPR or DORA control mappings in the repo we can reuse
   for the regulatory references in the test procedures?
