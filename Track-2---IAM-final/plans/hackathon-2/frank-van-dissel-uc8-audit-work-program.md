# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Frank van Dissel & Lauren Browne) |
| **Organisation** | Mollie |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

The audit work program is the tactical blueprint that tells auditors exactly what to do, how to do it, who does it, and how long it will take. Today, drafting a work program for a 30-control RCM takes an experienced auditor one to two days — and the result is often generic ("review approvals"), lacks methodology rationale, contains hour estimates that are guesses, and assigns tasks based on availability rather than skill. The Audit Work Program & Methodology Agent translates the "What" (Risks and Controls in the RCM from UC7) into a detailed "How": it drafts granular test procedures (Test of Design and Test of Operating Effectiveness), selects methodology per task (inquiry, observation, inspection, re-performance, analytical procedures), identifies opportunities for data analytics (CAATs), assigns tasks to auditors based on skill and availability, specifies evidence requirements, and estimates hours — all in compliance with GIAS 13.5 and 13.6.

This is **Use Case 8 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It consumes the RCM from [UC7](frank-van-dissel-uc7-rcm-builder.md) and its output is validated by [UC9 (Quality & Resource Guard)](frank-van-dissel-uc9-quality-resource-guard.md).

**Related SAAF plans pursuing the same goal:** [Floris Stokkers — Work Program Agent](floris-stokkers-work-program-agent.md) and [Inge Garretsen — Audit Work Program Agent](inge-garretsen-audit-work-program-agent.md). These three teams should coordinate on RCM input schema and output format.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Work Program Development (GIAS 13.5, 13.6)

**Applicable standards:**

- GIAS 13.6 — "Identify: Criteria to be used... Tasks to achieve objectives... Methodologies, including the analytical procedures to be used, and tools... Internal auditors assigned to perform each task."
- GIAS 13.5 — "Identify the types and quantity of resources necessary... Consider the nature and complexity... time frame... and whether available human and technological resources are appropriate."

**In scope:**

- Drafting Test of Design (ToD) and Test of Operating Effectiveness (ToE) procedures for every control in the RCM
- Selecting methodology per task (inquiry, observation, inspection, re-performance, analytical procedures)
- Identifying Computer-Assisted Audit Techniques (CAATs) for population-wide testing
- Specifying tools for analytical procedures (Python, SQL, Claude Code)
- Assigning tasks to auditors based on skill tags and availability
- Specifying evidence requirements (what to request, from whom, for what period)
- Estimating hours per task
- Designing sampling rationale (statistical vs. judgement; 100% population where analytics apply)

**Out of scope:**

- Executing the work program (field work)
- Assessing quality of completed work (UC9)
- CAE approval (UC9)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Task generation prompt (ToD/ToE); methodology selection prompt; CAAT identification prompt; auditor assignment prompt; Sufficiency & Methodology Reviewer prompt |
| **Tools** | Python pipeline: RCM reader → procedure generator → methodology selector → CAAT identifier → auditor matcher → hour estimator |
| **Regulatory** | GIAS 13.5, 13.6; IIA audit testing standards; reuse `regulatory/control-mappings/`; `outputs/schemas/finding-schema.json` for evidence specification |
| **Outputs** | Engagement Work Program: Test Objectives, Audit Procedures, Methodologies & Tools, Resource Assignments (GIAS 13.6), Resource Requirements in hours (GIAS 13.5), Sampling Design |

---

## 5. Prompts

### System prompt (draft — Work Program Generator)

```
You are an internal audit work program specialist.
Given a completed Risk and Control Matrix (RCM) and an auditor resource directory:

For each control in the RCM:
1. Draft a Test of Design (ToD) procedure: how do we verify the control is designed adequately?
2. Draft a Test of Operating Effectiveness (ToE) procedure: how do we verify it operates effectively?
3. Select the methodology for each step (inquiry / observation / inspection / re-performance / analytical procedure)
4. Identify if this control is a candidate for a Computer-Assisted Audit Technique (CAAT):
   - If yes: specify the analytical procedure, tool (Python/SQL/Claude Code), and data requirements
5. Specify the evidence required (document name, responsible party, time period)
6. Define Pass/Fail criteria for each test objective
7. Assign to the most appropriate auditor based on skill tags and availability
8. Estimate hours required

Sequence: ToD before ToE. Flag resource conflicts where a single auditor is over-allocated.
```

### Example user prompts

**Prompt 1 — Standard control:**
```
RCM control C-P01-001:
Risk: Duplicate payments
Control: System-generated duplicate payment check (Automated, every transaction)
Control type: Fully Automated

Draft ToD, ToE, methodology, evidence requirements, Pass/Fail criteria, and hour estimate.
Auditor resource pool: [Data Specialist — Python/SQL, Senior Auditor — process knowledge]
```

**Prompt 2 — CAAT opportunity:**
```
RCM control C-P01-002:
Risk: Invoices approved by the same person who initiated the purchase order
Control: Segregation of duties policy — initiator cannot approve
Population: 1 million transactions in ERP, FY 2025

Identify CAAT opportunity. Specify the Python/SQL query to test 100% of the population.
Assign to Data Specialist. Estimate hours including data extraction.
```

**Intended file location:** `prompts/audit-use-cases/uc8-audit-work-program.md`

---

## 6. Tools and Techniques

### Approach

Sequential pipeline (ToD before ToE is enforced by design):

1. **Procedure Generator:** For each RCM control, drafts ToD and ToE steps with specific evidence requests
2. **Methodology Selector:** Assigns inquiry/observation/inspection/re-performance/analytical procedure to each step
3. **CAAT Identifier:** Flags controls suitable for analytical procedures; specifies tool (Python, SQL, Claude Code) and data schema
4. **Auditor Matcher:** Matches tasks to auditors based on skill tags (IT Specialist, Data Specialist, Process Expert) and availability
5. **Hour Estimator:** Estimates hours per task based on control complexity, population size, and methodology
6. **Resource Conflict Detector:** Flags over-allocated auditors and generates a "Resource Alert" if total hours exceed available capacity

### Quality Safeguards

**Safeguard 1 — Sufficiency & Methodology Reviewer:** Evaluates whether the proposed methodology is sufficient to test the risk. Flags: High-significance risk tested only by Inquiry (insufficient); automated control with no IT environment testing (incomplete).

**Safeguard 2 — Assignment Logic Check:** Ensures no auditor is over-allocated; complex tasks are not assigned to junior staff without documented oversight.

### Example script or pseudocode

```python
def run_work_program_agent(rcm: dict, auditor_directory: dict, audit_manual: dict) -> dict:
    work_program = []
    for control in rcm["rcm"]:
        procedures = generate_procedures(control)          # ToD + ToE
        procedures = select_methodology(procedures, control)
        procedures = identify_caats(procedures, control)   # CAAT flagging
        
        assigned = assign_auditor(procedures, auditor_directory)
        hours = estimate_hours(procedures, control)
        
        work_program.append({**procedures, **assigned, **hours})
    
    # Quality gates
    work_program = sufficiency_reviewer(work_program)
    resource_report = check_resource_allocation(work_program, auditor_directory)
    
    return {"work_program": work_program, "resource_report": resource_report}
```

**Tech stack used:** Python 3.9+, Claude API (claude-opus-4-6 for procedure generation, claude-sonnet-4-6 for methodology review)

**Intended file location:** `tools/scripts/uc8-audit-work-program/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.6 | Criteria, tasks, methodologies, tools, and auditor assignments |
| GIAS 13.5 | Types and quantity of resources; appropriateness and sufficiency |
| IIA Testing Standards | ToD before ToE sequencing; methodology sufficiency |

### Claude / AI tool usage notes

The RCM input is a planning document — no real audit evidence or personal data is involved at this stage. The auditor resource directory should contain only role-based skill tags and availability data, not personal information.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON + XLSX (Engagement Work Program)

**Schema reference:** Test objectives link to RCM risk IDs; evidence specifications link to `outputs/schemas/finding-schema.json`

### Test Scenario 1 — Complex Analytical Procedure

- **Input:** Control for "Detecting Duplicate Payments" — 1 million transactions
- **Expected:** Agent suggests CAAT using SQL/Python; identifies Snowflake/Claude Code as tool; assigns to Data Specialist; estimates hours
- **Validation:** Data Audit Manager confirms technical feasibility

### Test Scenario 2 — Resource Allocation

- **Input:** RCM with 50 controls; resource pool of 2 auditors
- **Expected:** Populated work program with assignments + "Resource Alert" that available capacity is insufficient for the timeframe (feeding into UC9)
- **Validation:** Audit manager confirms alert is accurate

### Synthetic example output

```json
{
  "work_program": [
    {
      "task_id": "T-001",
      "control_id": "C-P01-001",
      "test_type": "ToE",
      "objective": "Verify that the duplicate payment check prevented all duplicate invoices in FY 2025",
      "procedure": "Extract all approved invoices for FY 2025 from ERP. Using Python, identify duplicates (same supplier + amount + invoice date ± 5 days). Compare to blocked transactions log.",
      "methodology": "Analytical Procedure (CAAT)",
      "tool": "Python (pandas) + ERP data export",
      "evidence_required": "ERP invoice export (FY 2025), blocked transactions log",
      "pass_fail": "Pass: 0 duplicate payments processed. Fail: >0 duplicates found in approved payment run.",
      "assigned_to": "Data Specialist",
      "estimated_hours": 8,
      "sampling": "100% population (automated CAAT)"
    }
  ],
  "resource_report": {"total_hours_required": 320, "available_hours": 160, "resource_alert": "Insufficient capacity — consider scope reduction or additional resource."}
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6)
- [x] Python 3.9+
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] XLSX work program export compatible with TeamMate+ import
- [ ] Interactive auditor assignment UI with drag-and-drop reallocation

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Procedure generation prompt (ToD/ToE, methodology, CAAT)
- Sufficiency & Methodology Reviewer prompt
- Work Program JSON schema

**What help I'm looking for:**

- Auditors to validate that ToD/ToE procedures are audit-appropriate across different control types
- Data specialists to review CAAT identification logic and SQL/Python template quality

**Related SAAF plans:**

- [UC7 — RCM Builder](frank-van-dissel-uc7-rcm-builder.md) — provides RCM input
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates and approves this output
- [Floris Stokkers — Work Program Agent](floris-stokkers-work-program-agent.md) — parallel effort; coordinate on RCM input schema and output format
- [Inge Garretsen — Audit Work Program Agent](inge-garretsen-audit-work-program-agent.md) — related approach; consider alignment

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie work program templates |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. How do we align the work program output schema with the input format required by [Floris Stokkers' agent](floris-stokkers-work-program-agent.md) — they address the same problem from different angles?
2. Should CAAT scripts be generated by this agent (draft Python/SQL), or only identified and left for the Data Specialist to implement?
3. How should the agent handle controls where the testing methodology is genuinely ambiguous — flag for auditor judgment, or propose a default?
