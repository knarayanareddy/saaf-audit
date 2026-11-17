# Plan: Audit Work Program & Methodology Agent

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Floris Stokkers |
| **Organisation** | RCM-Rangers |
| **Session** | Session 3 (Hackathon #2) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Audit work programs are written manually today: the auditor reads the Risk & Control Matrix (RCM), translates each control into test procedures, chooses a methodology, estimates hours, and informally assigns tasks. This is slow, inconsistent, and rarely challenged. In practice: procedures stay generic ("review approvals"), methodology rationale is absent, hour estimates are guesses, and auditor assignments are based on availability rather than skill. The result is a work program that gives the audit team weak guidance and is difficult to defend against a GIAS Standard 13.6 quality review.

In practice, drafting a work program for a 30-control RCM takes an experienced auditor 1–2 days and produces procedures that are rarely challenged in quality review.

This agent automates the translation from RCM to Work Program. It generates granular, specific test procedures (Test of Design and Test of Operating Effectiveness) per control, selects the appropriate methodology, identifies Computer-Assisted Audit Technique (CAAT) opportunities for automated controls, assigns auditors from a skills directory, estimates hours, and flags resource gaps and methodology weaknesses before the audit begins.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Engagement Work Program (GIAS Pillar V: Managing Internal Audit)

**Applicable standards:**

- GIAS 2024 Standard 13.5 — Engagement Resources: identify types, quantity, and sufficiency of resources
- GIAS 2024 Standard 13.6 — Work Program: criteria, tasks, methodologies, tools, assigned auditors per task
- IIA Global Technology Audit Guide (GTAG): Data Analysis Technologies

**In scope:**

- Generating ToD and ToE test procedures for every control in the input RCM
- Selecting methodology: inquiry, observation, inspection, re-performance, or analytical
- Identifying CAAT opportunities for automated and IT-dependent controls
- Assigning auditors from a skill-tagged resource directory (GIAS 13.6)
- Estimating hours per task based on methodology and risk significance (GIAS 13.5)
- Running two quality checks: methodology sufficiency and resource allocation alerts
- Exporting the work program as Excel (primary), Word, and JSON

**Out of scope:**

- Risk assessment and RCM creation (Use Case 6)
- CAE approval workflow and compliance scoring (Use Case 9)
- Finding documentation and audit reporting (downstream phases)
- Real-time integrations with audit management systems

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompt for work program generation in `prompts/audit-use-cases/work-program-agent.md` |
| **Tools** | Deterministic Python matching script in `tools/scripts/work-program-matching.py` |
| **Regulatory** | New GIAS 13.5 and 13.6 control mapping in `regulatory/control-mappings/gias-13-work-program.md` |
| **Outputs** | Structured Work Program JSON with new task schema in `outputs/schemas/work-program-task.json` |

---

## 5. Prompts

### System prompt (draft)

```
You are a senior internal audit manager generating a detailed engagement work program.
For each control, generate Test of Design (ToD), Test of Operating Effectiveness (ToE),
and optionally a CAAT task (methodology = analytical).

RULES (non-negotiable):
1. ToD sequence_order = 1, ToE sequence_order = 2, CAAT sequence_order = 3, per control.
2. For high-significance risks: use at least 2 different methodologies across ToD and ToE.
3. Inquiry alone is NEVER sufficient for a high-significance risk.
4. For automated or it_dependent controls: always evaluate caat_opportunity (usually true).
5. For risks containing: duplicate, completeness, reconciliation, large volume - set
   caat_opportunity=true and suggest 100% population testing via SQL or Python.
6. Procedures must name the exact system, document type, date range, and responsible person.
7. Pass/fail criteria must be binary and testable (not subjective).
8. Tools must be specific: write SQL/Snowflake not SQL, Python/Pandas not Python.
9. Evidence must include the source system or document, format, and period.
Never invent auditor names not present in the provided resource directory.
Output ONLY a valid JSON array. No explanation, no markdown.
```

### Example user prompts

**Prompt 1 - CAAT opportunity for duplicate payments:**

```
Control C-03: Risk = Duplicate vendor payments processed due to lack of automated detection.
Risk significance: High. Control type: automated. Control owner: AP Manager.
Linked objective: Ensure completeness and accuracy of vendor payments.
Data schema: SAP BSEG table - fields: vendor_id, amount, payment_date, document_nr.
Auditor directory: Maria de Vries (specialist, skills: data analytics/SQL/Python, 80h available).
Generate ToD, ToE, and CAAT tasks for this control.
```

**Prompt 2 - Resource constraint scenario:**

```
RCM with 50 controls (12 high, 28 medium, 10 low significance).
Auditor directory:
- Jan Bakker (junior, skills: inspection/inquiry, 40h available)
- Lisa Smit (senior, skills: re-performance/inspection, 40h available)
No data schema. No audit manual.
Generate the full work program and flag any resource constraints per GIAS 13.5.
```

**Intended file location:** `prompts/audit-use-cases/work-program-agent.md`

---

## 6. Tools and Techniques

### Approach

The agent parses the RCM (XLSX or DOCX) and Auditor Resource Directory (XLSX), then calls Claude in batches of 5 controls to generate granular ToD, ToE, and CAAT tasks with explicit methodology, tools, evidence, and pass/fail criteria. Auditor assignment and resource gap calculation are handled deterministically in Python with no AI involvement. Two quality checks run automatically: a methodology sufficiency check (flags Inquiry-only for high-risk controls) and a resource allocation check (flags over-allocated auditors and junior-without-oversight assignments). Output is an Excel workbook with 4 sheets: Summary, Work Program, Resource Summary, and Quality Alerts.

### Example script 1 — Claude API call (batched per 5 controls)

```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

def generate_tasks_for_batch(batch: list[dict], auditors: list[dict]) -> list[dict]:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(batch, auditors)}],
    )
    return json.loads(response.content[0].text)
```

### Example script 2 — deterministic auditor matching

```python
import json

LEVEL_RANK = {"junior": 1, "senior": 2, "manager": 3, "specialist": 3}

TASK_COMPLEXITY_MAP = {
    ("analytical",     "high"):   {"min_level": "senior", "required_skills": ["data analytics", "SQL", "Python"]},
    ("analytical",     "medium"): {"min_level": "senior", "required_skills": ["data analytics", "SQL"]},
    ("re-performance", "high"):   {"min_level": "senior", "required_skills": ["IT audit", "CISA"]},
    ("re-performance", "medium"): {"min_level": "senior", "required_skills": []},
    ("inspection",     "high"):   {"min_level": "senior", "required_skills": []},
    ("inspection",     "medium"): {"min_level": "junior", "required_skills": []},
    ("inquiry",        "high"):   {"min_level": "senior", "required_skills": []},
    ("inquiry",        "medium"): {"min_level": "junior", "required_skills": []},
    ("observation",    "high"):   {"min_level": "senior", "required_skills": []},
    ("observation",    "medium"): {"min_level": "junior", "required_skills": []},
}

def assign_auditor(methodology, risk_significance, auditors, allocated):
    key = (methodology, risk_significance)
    rules = TASK_COMPLEXITY_MAP.get(key, {"min_level": "junior", "required_skills": []})
    min_rank = LEVEL_RANK[rules["min_level"]]
    req_skills = rules["required_skills"]
    eligible = []
    for a in auditors:
        if LEVEL_RANK.get(a["level"], 1) < min_rank:
            continue
        skills = json.loads(a["skill_tags"])
        if req_skills and not any(s in skills for s in req_skills):
            continue
        eligible.append(a)
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda a: a["available_hours"] - allocated.get(a["auditor_name"], 0)
    )["auditor_name"]
```

**Tech stack used:** Python 3.11, Claude API (`claude-sonnet-4-6`), openpyxl, python-docx, pdfplumber

**Intended file location:** `tools/scripts/work-program-matching.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 2024 Standard 13.5 | Identify types and quantity of resources; assess whether available human and technological resources are appropriate and sufficient for the nature, complexity, and time frame |
| GIAS 2024 Standard 13.6 | Document a work program identifying: criteria to evaluate, tasks to achieve objectives, methodologies and analytical tools, internal auditors assigned to each task |
| IIA GTAG: Data Analysis Technologies | Guidance on CAAT design, population testing, SQL/Python-based analytical procedures |

### Claude / AI tool usage notes

- No real audit evidence, PII, or credentials are sent to the Claude API. All testing uses synthetic data only.
- Claude is used for task generation (text reasoning) only. Resource matching and quality checks are deterministic Python with no AI involvement in those decisions.
- The agent is advisory: a human auditor reviews and can edit every generated task. Human edits are preserved and never overwritten.
- API key loaded from environment variable ANTHROPIC_API_KEY. Never hardcoded.
- Model: `claude-sonnet-4-6`. Substitutable with any claude-* model without code changes.

### Guardrails checklist

- [x] No rm, sudo, curl, wget, or ssh in scripts
- [x] No runtime pip install
- [x] Python scripts run only from tools/scripts/
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Excel (.xlsx) primary; JSON and Word (.docx) secondary

**Schema reference:** `outputs/schemas/work-program-task.json` (new schema produced with this plan)

### Synthetic example output - single CAAT task (JSON)

```json
{
  "control_id": "C-03",
  "task_type": "caat",
  "sequence_order": 3,
  "objective": "Detect duplicate vendor payments across the full FY2025 population using SQL on SAP BSEG.",
  "procedure": "1. Extract AP payment dataset from SAP BSEG for Jan-Dec 2025. 2. Write SQL grouping by vendor_id, amount, payment_date +/- 3 days. 3. Flag clusters with more than one matching record. 4. Export to Excel for review. 5. Confirm each duplicate with the AP Manager.",
  "methodology": "analytical",
  "tools": ["SQL/SAP HANA", "Python/Pandas", "Excel"],
  "caat_opportunity": true,
  "caat_rationale": "1.2 million transactions in FY2025. 100% population testing eliminates sampling risk.",
  "evidence_required": "SAP BSEG export FY2025 (CSV), AP ledger reconciliation Q1-Q4 2025",
  "pass_fail_criteria": "Zero unresolved duplicate payments after management review = PASS. Any unresolved duplicate = FAIL.",
  "sampling_design": "100pct_population",
  "sampling_rationale": "Automated control with CAAT capability. Full population testing eliminates sampling risk.",
  "assigned_auditor": "Maria de Vries",
  "estimated_hours": 12.0,
  "human_edited": false
}
```

### Excel output sheet structure

| Sheet | Purpose |
|---|---|
| Summary | Totals: controls, tasks, hours required vs available, CAAT count |
| Work Program | Full task table, colour-coded: ToD = blue, ToE = green, CAAT = purple |
| Resource Summary | Per-auditor: available vs allocated hours, OK / Over-allocated / Underutilised |
| Quality Alerts | Methodology insufficiency and resource alerts with recommendations |

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (`claude-sonnet-4-6`)
- [x] Python 3.11
- [x] openpyxl (Excel export)
- [x] python-docx + pdfplumber (RCM input parsing)
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data — optional)

**Stretch goals:**

- [ ] FastAPI + SQLite backend for persistent session storage
- [ ] React 18 + TypeScript + Vite browser frontend
- [ ] Auto-load RCM output from Use Case 6 as direct input
- [ ] Auto-pass Work Program to Use Case 9 for CAE approval check
- [ ] Dutch/English multilingual support for RCM and audit manual inputs

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- System prompt for work program generation (prompts/audit-use-cases/work-program-agent.md)
- Deterministic auditor matching algorithm (tools/scripts/work-program-matching.py)
- Full methodology sufficiency rules and hour estimation table (Python dicts, ready to import)
- Dutch/English column alias maps for RCM and auditor directory XLSX inputs
- Synthetic test dataset: 10-control RCM + auditor directory XLSX for shared testing

**What help I am looking for:**

- Input on a standard skill taxonomy for auditor profiles across SAAF member organisations
- Review of the GIAS 13.5 and 13.6 control mapping by someone with IIA standards expertise
- A SQL or data engineering specialist to validate the CAAT procedure templates

**Cross-org interest:**

The problem of translating an RCM into a Work Program is universal across all internal audit functions regardless of industry. Any SAAF member running assurance engagements could reuse the prompt and matching algorithm directly. Collaboration is actively welcomed, especially for building industry-specific methodology templates for financial services, healthcare, and IT general controls.

Inge Garretsen (Anonymous) submitted a plan for the same UC8 topic at Hackathon #2. Rather than compete, we propose combining both approaches: Inge's simpler Python-first prototype as the accessible entry point, and this plan's deterministic matching algorithm and richer output schema as the production-ready evolution. We specifically invite alignment on a **shared skill taxonomy standard** (open question #1) and a **shared synthetic RCM test dataset** so the full UC6 → UC8 → UC9 pipeline can be validated end-to-end across organisations.

**Video Transcription Insights (Hackathon #3 analysis):**

**Ralph mode / context engineering for multi-iteration work programs:**

The most significant enhancement identified from video analysis is the "Ralph loop" pattern applied to iterative work program generation. Work programs often require 3-5 refinement cycles: initial generation → auditor review → scope adjustment → regeneration. The current plan handles one cycle.

The Ralph mode enhancement:
- Store the current work program state in a JSON task file between iterations (see `overnight-audit-batch-processing-agent.md` for the pattern)
- The agent loads the previous state, applies auditor feedback (provided as natural language), and regenerates only the affected sections — not the entire work program
- Track which work program steps have been marked "complete" vs. "in progress" vs. "not started" across the audit execution
- This converts the work program from a static document into a living agent state that evolves throughout the audit

This is the key distinction between a work program agent (Level 2 — one-shot generation) and an audit execution agent (Level 3 — adaptive, multi-iteration). See [`plans/hackathon-3/audit-workflow-automation-levels.md`](../hackathon-3/audit-workflow-automation-levels.md) for the framework.

**Related SAAF plans:**

- [The RCM Rangers — Audit Work Program Agent (Workflow)](the-rcm-rangers-audit-work-program-agent.md) — team-level submission from the same RCM-Rangers group; workflow-first approach (no code in Phase 1); coordinate on prompt design and output format
- [Frank van Dissel — UC8 Work Program Agent](frank-van-dissel-uc8-audit-work-program.md) — parallel submission from Mollie; align on output schema
- [Inge Garretsen — Audit Work Program Agent](inge-garretsen-audit-work-program-agent.md) — cross-domain approach; potential alignment on methodology selection and skill taxonomy
- [`plans/hackathon-3/overnight-audit-batch-processing-agent.md`](../hackathon-3/overnight-audit-batch-processing-agent.md) — Ralph loop pattern for multi-iteration work program runs

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | All sections filled in |
| **Do** | Complete | Prototype built at Hackathon #2 (March 24, 2026, Schuberg Philis) |
| **Check** | Not started | Planned: validate against synthetic SAAF test dataset |
| **Act** | Not started | Target: Hackathon #3 |

---

## 12. Open Questions

1. Should SAAF define a controlled vocabulary of auditor skill tags (e.g. `["data analytics", "IT audit", "CISA"]`) as a shared standard so resource directories are interoperable across UC8, UC9, and future agents?
2. What format should the shared synthetic RCM test dataset use? Proposing a 10-control XLSX spanning 3 audit domains — should it be contributed to `tools/scripts/test_data/` or served via Strapi so all UC6–UC9 plans can share the same input?
3. The deterministic matching algorithm assumes a flat skill-tag list. Is there interest in a hierarchy (e.g. "senior auditor" implies all junior skills), or is flat simpler to maintain across organisations?
