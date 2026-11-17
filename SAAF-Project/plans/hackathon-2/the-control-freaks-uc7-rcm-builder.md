# Plan — The Control Freaks: RCM Builder Agent (Use Case 7)

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Ilona Hofland, Imane Akhyar, Peter Jongen, Guus Focken, Bart Loow, Joey Wild, Mourad Fakirou |
| **Organisation** | The Control Freaks (cross-org) |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Creating and maintaining a Risk & Control Matrix (RCM) is one of the most time-consuming and error-prone activities in audit planning. In practice, auditors manually copy risks from prior-year Excel RCMs, paste findings from multiple audit reports, incident logs, fraud assessments, and regulatory outputs into a single working spreadsheet, and then reconcile terminology, eliminate duplicates, and assign process linkages by hand. This process typically takes several days per engagement and is heavily dependent on individual auditor knowledge and experience. This often results in:

- Risk duplication and inconsistent wording ("risk bloat")
- Missing linkage between risks, processes, and objectives
- Orphaned risks or controls
- Lack of structured control classification
- Limited audit defensibility and traceability

The RCM Builder Agent automates and structures this synthesis, ensuring the RCM is complete, risk-focused, and aligned with GIAS requirements. Critically, the agent operates across a **three-stage lifecycle** — including a validation loop with UC6 (IT Dependency Identifier) — to produce a Validated RCM ready for audit execution design (UC8).

---

## 3. Use-Case Type and Scope

**Audit domain:** Audit Planning — Risk & Control structuring (GIAS 13.2, 13.6)

The agent operates across three high-level stages:

- **Stage 1 – Ingest & Align (UC1–UC5):** Consolidation and normalization of process context and risk inputs into a structured and deduplicated risk universe
- **Stage 2 – Draft RCM (UC7):** Structuring of risks, objectives, and controls into an initial Risk & Control Matrix reflecting control design
- **Stage 3 – Validation Loop (UC6 → UC7):** Enrichment of the Draft RCM with IT dependency and control reliability insights from UC6, resulting in a Validated RCM

Outputs are progressively refined across these stages, ensuring full traceability from risk identification to validated control design.

**Applicable standards:**

- GIAS 13.2 — Risk identification, assessment, and prioritization linked to business objectives
- GIAS 13.6 — Work program development: criteria, tasks, and methodologies
- COSO ERM — Risk categorization, inherent and residual risk scoring, control response types
- COBIT 2019 — IT governance controls, application controls, and ITGC dependencies
- DORA (EU 2022/2554) — ICT risk management, incident classification, third-party risk
- NIS2 Directive — Network and information security controls, incident response
- NIST CSF / SP 800-53 — Security and privacy control families for IT-dependent control mapping
- ISO/IEC 27001:2022 — Information security controls (Annex A)
- EU AI Act — Risk classification, transparency, human oversight for AI-assisted outputs

**In scope:**

- Ingestion of process context and objectives (UC1)
- Consolidation of risk intelligence (UC2–UC5)
- Risk normalization and deduplication
- Mapping of risks to processes and business objectives
- Control design and structuring using 5W+H logic
- Control classification (execution type, nature, significance)
- Inherent risk scoring and residual risk estimation
- Identification of design gaps
- Integration of IT dependency and reliability insights via UC6 validation loop

**Out of scope:**

- Validation of control existence in practice (fieldwork)
- Detailed testing of control operating effectiveness (fieldwork)
- Independent testing of ITGC effectiveness (fieldwork)
- Real-time monitoring or continuous auditing
- Final audit conclusions or assurance opinions
- Formal validation with process owners or management

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompt at `prompts/audit-use-cases/rcm-builder-agent.md`, covering all three stages (ingest, draft, validate) |
| **Tools** | `tools/scripts/rcm_builder.py` — risk normalization, deduplication, control classification, scoring; `tools/scripts/rcm_it_validator.py` — UC6 integration module (separate, independently testable) |
| **Regulatory** | New GIAS/COSO/COBIT mapping at `regulatory/control-mappings/rcm-frameworks.md`; domain-specific mappings (DORA, NIS2, ISO 27001, EU AI Act) as separate files or appended to existing mappings |
| **Outputs** | Validated RCM in JSON and Markdown; new schema registered as `outputs/schemas/rcm-schema.json`; conforms to `outputs/schemas/finding-schema.json` conventions for findings-level records |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI audit assistant specialized in Risk & Control Matrix (RCM) design.
Your role is to:
- Consolidate risks from multiple audit intelligence sources
- Map risks to processes, sub-processes, and business objectives
- Design and classify controls
- Assess inherent and residual risk

Always:
- Use structured risk format: As a result of [Cause], there is a risk that [Event], leading to [Impact]
- Ensure every risk is linked to an objective
- Ensure every risk has at least one control
- Classify controls:
  • Execution type (Manual / IT-dependent / Automated)
  • Preventive / Detective
  • Key / Non-key
- Distinguish between control design and control reliability

Never:
- Create duplicate risks
- Create orphaned risks or controls
- Assume control effectiveness without validation
```

### Example user prompts

**1. End-to-end RCM generation (primary use case):**
```
Using the provided inputs from UC1–UC5 (process map, objectives, and risk sources),
generate a Draft RCM. Ensure all risks are normalized, deduplicated, mapped to
sub-processes and objectives, and linked to at least one control with full classification.
```

**2. Risk consolidation (Stage 1 focus):**
```
Consolidate and deduplicate the provided risks from multiple sources (audit findings,
incidents, fraud scenarios, and regulatory inputs). Normalize each risk using the
Cause–Event–Impact structure and map it to the relevant process and sub-process.
```

**3. Control design (Stage 2 focus):**
```
For each identified risk, design one or more mitigating controls using structured
logic (5W+H). Ensure controls are clearly defined, testable, and include appropriate
evidence types.
```

**4. Control classification:**
```
Classify each control in the RCM according to execution type (Manual, IT-dependent,
Automated), control nature (Preventive or Detective), and significance (Key or Non-key).
Include control strength assessment.
```

**5. Risk scoring:**
```
Assess inherent risk for each identified risk using impact and likelihood. Then estimate
preliminary residual risk based on control design and control strength.
```

**6. Design gap analysis:**
```
Analyze the RCM and identify control design gaps, including missing controls, insufficient
controls, unmapped controls, and redundant controls. Provide a brief explanation for each.
```

**7. UC6 validation integration (Stage 3):**
```
Using the provided UC6 output (IT dependencies and control reliability assessment),
update the Draft RCM to reflect control reliability, introduce any additional risks
(e.g. IPE risks), and recalculate residual risk.
```

**8. Reliability-focused review:**
```
Evaluate all IT-dependent controls in the RCM for reliability. Assess ITGC dependencies,
IPE validation, and determine whether each control is reliable, partially reliable,
or unreliable.
```

**9. RCM quality review (audit perspective):**
```
Review the RCM for completeness and audit readiness. Ensure there are no orphan risks
or controls, all risks are linked to objectives, and control classifications are consistent.
```

**10. Generate final validated RCM:**
```
Produce a Validated RCM incorporating control design, classification, reliability
assessment, and updated residual risk. Ensure the output is structured and ready
for audit execution planning (UC8).
```

**11. Output formatting (table / export):**
```
Convert the Validated RCM into a structured table format suitable for export to Excel,
ensuring all required columns are included and clearly labeled.
```

**12. Cross-risk consistency check:**
```
Identify inconsistencies across similar risks and controls in the RCM and propose
standardization improvements.
```

**13. Control optimization:**
```
Identify redundant or overlapping controls and propose opportunities to streamline the
control framework while maintaining adequate risk coverage.
```

**Intended file location:** `prompts/audit-use-cases/rcm-builder-agent.md`

---

## 6. Tools and Techniques

### Approach

The agent follows a three-stage modular lifecycle:

**Stage 1 – Ingest & Align (UC1–UC5)**

Ingests structured and semi-structured inputs (JSON/Markdown/text) from upstream use cases:
- UC1: Process map, sub-processes, and business objectives
- UC2: Historical risks and audit findings
- UC3: Incident and issue data
- UC4: Fraud scenarios
- UC5: Regulatory and compliance risks

Processing steps:
1. Import process map and objectives (UC1)
2. Ingest & consolidate risk intelligence (UC2–UC5)
3. Normalize risk descriptions to Cause→Event→Impact format
4. Semantic deduplication — merge overlapping risks; preserve source references
5. Risk taxonomy alignment — map to standard categories (operational, compliance, IT, fraud)

Output: clean, deduplicated, standardized **Risk Universe**

**Stage 2 – Draft RCM Creation**

Each consolidated risk is enriched and structured:
1. Map each risk to a sub-process and business objective (from UC1)
2. Design controls using 5W+H: Who / What / When / Where / How / Why / Evidence generated
3. Classify each control: Execution type (Manual / IT-dependent / Automated), Nature (Preventive / Detective), Significance (Key / Non-key), Frequency, Owner, Evidence type, Design quality (Strong / Moderate / Weak)
4. Score inherent risk: Impact × Likelihood → High / Medium / Low
5. Identify design gaps: missing controls, weak controls, unmapped controls, redundant controls
6. Estimate preliminary residual risk (design-based, not yet validated)

Output: structured **Draft RCM**

**Stage 3 – Validation & Refinement (UC6 → UC7 loop)**

The Draft RCM is enriched with UC6 insights:
1. IT dependency mapping — identify systems and data sources for each control
2. Control reliability assessment based on ITGC strength, system-generated data dependency, and validation procedures → Reliable / Partially Reliable / Unreliable
3. IPE assessment — for IT-dependent controls, validate completeness, accuracy, and integrity of data
4. Introduction of new risks surfaced by UC6 (e.g. IPE risks, ITGC gaps, unauthorized system changes)
5. Residual risk recalibration — combines control design (UC7) and control reliability (UC6)
6. RCM refinement — reflect reliability, include ITGC controls, incorporate new risks

Output: **Validated RCM** (final output for UC8)

### Example script or pseudocode

```python
# rcm_builder.py — core pipeline
for risk in incoming_risks:
    # Stage 1
    risk = normalize_risk(risk)                      # Cause–Event–Impact
    risk = deduplicate(risk, risk_library)
    process = map_to_process(risk, process_map)
    objective = link_to_objective(process)

    # Stage 2
    controls = propose_controls(risk)                # 5W+H logic
    for control in controls:
        classify_control(control)                    # type / nature / significance
        assign_control_attributes(control)           # frequency / owner / evidence
    inherent_risk = score_inherent(risk)
    residual_risk = estimate_residual(inherent_risk, controls)
    store_draft_rcm(risk, controls)

# Stage 3 — UC6 integration (rcm_it_validator.py called by rcm_builder.py)
for control in rcm_controls:
    assess_it_dependency(control)        # rcm_it_validator.py
    map_itgc_dependency(control)         # rcm_it_validator.py
    assess_ipe_reliability(control)      # rcm_it_validator.py
    classify_control_reliability(control) # rcm_it_validator.py
    adjust_residual_risk(control)        # rcm_builder.py

introduce_uc6_risks(rcm, uc6_output)    # rcm_builder.py
output_validated_rcm()                  # rcm_builder.py
```

The UC6 integration module (`rcm_it_validator.py`) operates as a standalone callable — keeping core RCM builder logic free of IT-specific dependencies, making both modules independently testable.

**Architecture:** Input layer (UC1–UC5 JSON/Markdown) → Processing layer (normalization, deduplication, control design, scoring) → Validation layer (UC6 integration) → Output layer (JSON + table)

**Tech stack used:** Python 3.11, Claude API (claude-sonnet-4-6), JSON / Markdown / CSV, Strapi (optional synthetic data)

**Intended file locations:** `tools/scripts/rcm_builder.py`, `tools/scripts/rcm_it_validator.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA GIAS 13.2 | Risk identification, assessment, and prioritization linked to business objectives |
| IIA GIAS 13.6 | Work program development: criteria, tasks, and methodologies |
| COSO ERM | Risk categorization, inherent and residual risk scoring, control response types |
| COBIT 2019 | IT governance controls, application controls, and ITGC dependencies |
| DORA (EU 2022/2554) | ICT risk management framework, incident classification, third-party risk controls |
| NIS2 Directive | Network and information security controls, incident response obligations |
| NIST CSF / SP 800-53 | Security and privacy control families for IT-dependent control mapping |
| ISO/IEC 27001:2022 | Information security controls (Annex A) applicable to IT-dependent risks |
| EU AI Act | Risk classification, transparency, human oversight, and data governance for AI-assisted outputs |

### Claude / AI tool usage notes

- No real audit evidence, confidential data, or PII is used during development or testing
- Synthetic or anonymized data is used where realistic scenarios are required (e.g. via Strapi)
- All outputs are traceable (linked to input sources) and explainable (clear reasoning for risk/control generation)
- The agent supports audit planning but does not replace professional judgment
- Outputs must be reviewed and validated by auditors before use

### Guardrails checklist

**Data & privacy:**
- [x] No sensitive or confidential audit data stored or exposed
- [x] No credentials or API keys hardcoded
- [x] All secrets managed via environment variables

**Execution:**
- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`

**Audit integrity:**
- [x] No assumptions of control effectiveness without validation
- [x] No generation of orphaned risks or controls
- [x] All outputs maintain: risk-to-objective linkage, control traceability, classification consistency

**AI reliability:**
- [x] LLM outputs treated as decision support, not final conclusions
- [x] Hallucinations mitigated via structured prompts, validation logic, and deterministic post-processing

---

## 8. Output Format and Examples

**Format:** JSON (primary, for system integration) + Markdown / table (human-readable) + optional CSV/Excel export

**Schema reference:** New schema `outputs/schemas/rcm-schema.json`; findings-level records conform to `outputs/schemas/finding-schema.json`

### Output specification by stage

**Stage 1 — Risk Universe record:**

| Field | Description |
|---|---|
| `process_id`, `process_name` | From UC1 process map |
| `sub_process_id`, `sub_process_name` | From UC1 |
| `objective_id`, `objective_description` | Linked business objective |
| `risk_id`, `risk_description` | Cause–Event–Impact format |
| `risk_category` | Operational / IT / Compliance / Fraud / Financial |
| `risk_source` | UC2 / UC3 / UC4 / UC5 |
| `source_reference` | Report / incident ID / regulation |

**Stage 2 — Additional columns (Draft RCM):**

| Field | Description |
|---|---|
| `impact`, `likelihood`, `inherent_risk_rating` | H/M/L |
| `control_id`, `control_description` | 5W+H structured |
| `execution_type` | Manual / IT-dependent / Automated |
| `control_nature` | Preventive / Detective |
| `control_significance` | Key / Non-key |
| `control_frequency`, `control_owner` | Operational attributes |
| `evidence_type` | System generated / workflow approval / documentation-based / data analysis / observation / inquiry |
| `control_design_effectiveness` | Strong / Moderate / Weak |
| `preliminary_residual_risk` | Design-based estimate |
| `design_gap_indicator`, `design_gap_description` | Missing / Weak / Unmapped / Redundant |

**Stage 3 — Additional columns (Validated RCM):**

| Field | Description |
|---|---|
| `it_dependency_flag` | Yes / No |
| `system_application_name` | Host system |
| `data_source_report_name` | IPE source |
| `itgc_dependency_type` | Access Management / Change Management / IT Operations |
| `control_reliability` | Reliable / Partially Reliable / Unreliable |
| `ipe_validation_level` | Strong / Weak / None |
| `updated_residual_risk`, `residual_risk_delta` | Post-validation |
| `new_risk_flag_uc6`, `new_risk_description` | UC6-introduced risks |
| `additional_itgc_control_required`, `itgc_control_description` | Additional controls |

### Synthetic example output

**Stage 1 — Risk Universe record:**
```json
{
  "process_id": "P-03",
  "process_name": "User Access Management",
  "sub_process_id": "SP-03.1",
  "sub_process_name": "Access Provisioning",
  "objective_id": "OBJ-03",
  "objective_description": "Ensure only authorized users are granted access to systems and data",
  "risk_id": "R-007",
  "risk_description": "As a result of insufficient approval controls during access provisioning, there is a risk that unauthorized users are granted system access, leading to data breaches and compliance violations",
  "risk_category": "IT",
  "risk_source": "UC3",
  "source_reference": "Incident INC-2024-0412 – unauthorized admin account created"
}
```

**Stage 2/3 — Validated RCM record:**
```json
{
  "risk_id": "R-007",
  "control_id": "C-007",
  "control_description": "Manager approval required for all access requests via IAM workflow",
  "execution_type": "IT-dependent",
  "control_nature": "Preventive",
  "control_significance": "Key",
  "inherent_risk": "High",
  "preliminary_residual_risk": "Medium",
  "it_dependency_flag": true,
  "system_application_name": "IAM Platform",
  "itgc_dependency_type": "Access Management",
  "control_reliability": "Partially Reliable",
  "ipe_validation_level": "Weak",
  "updated_residual_risk": "High",
  "residual_risk_delta": "+1 (Medium → High)",
  "new_risk_flag_uc6": true,
  "new_risk_description": "IAM audit log completeness not validated — IPE risk"
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.11
- [x] GitHub (fork + PR)
- [x] JSON — primary data structure for RCM representation
- [x] Markdown / CSV — human-readable output formats
- [ ] Strapi — optional synthetic data API for realistic test scenarios

**Architecture principles:** Modular — input / processing / validation / output layers kept separate. `rcm_it_validator.py` independently callable so UC6 integration can be tested and reused without the full pipeline.

**Stretch goals:**

- [ ] Export to Excel (XLSX) for direct audit team use
- [ ] RCM visualization: heatmaps and risk concentration dashboards
- [ ] Integration with GRC platforms (AuditBoard, ServiceNow GRC)
- [ ] API-based inter-use-case communication (UC6, UC8, UC9)
- [ ] Version-controlled RCM delta reporting across audit cycles

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- System prompt(s) for RCM generation and validation (all stages)
- Risk normalization and deduplication logic (Cause–Event–Impact format)
- Control classification framework (5W+H, execution type, nature, significance)
- Example RCM outputs (JSON and table format)
- `rcm_builder.py` and `rcm_it_validator.py` pseudocode / scripts

**What help I'm looking for:**

- Technical team members for Hackathon 3 — the team currently lacks sufficient technical capacity to implement the full pipeline
- Domain experts to validate risk taxonomy and control classifications across industries
- Alignment on evidence types and control definitions with other SAAF teams
- Technical helpdesk support during build time to avoid getting stuck

**Related SAAF plans:**

- [Frank van Dissel & Lauren Browne — UC7 RCM Builder (Mollie)](frank-van-dissel-uc7-rcm-builder.md) — parallel submission addressing the same use case from a different angle; coordinate on RCM output schema and UC6 validation loop design
- [Frank van Dissel — UC1](frank-van-dissel-uc1-policy-process-intake.md), [UC2](frank-van-dissel-uc2-previous-audit-intelligence.md), [UC3](frank-van-dissel-uc3-incident-issue-intelligence.md), [UC4](frank-van-dissel-uc4-fraud-risk-assessment.md), [UC5](frank-van-dissel-uc5-regulatory-criteria.md) — provide risk input data to Stage 1
- [Frank van Dissel — UC6 IT Dependency Identifier](frank-van-dissel-uc6-it-dependency-identifier.md) — validation loop partner: UC6 output feeds Stage 3 of this agent
- [Frank van Dissel — UC8 Work Program](frank-van-dissel-uc8-audit-work-program.md) — consumes the Validated RCM
- [Frank van Dissel — UC9 Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates completeness and quality of RCM output
- [Floris Stokkers — Work Program Agent](floris-stokkers-work-program-agent.md) — downstream consumer; coordinate on output schema
- [Inge Garretsen — Audit Work Program Agent](inge-garretsen-audit-work-program-agent.md) — related downstream use case

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Fully elaborated by The Control Freaks; submitted ahead of Hackathon 2 |
| **Do** | In progress | Prototype agent to be built at Hackathon 2 |
| **Check** | Not started | Planned pilot validation |
| **Act** | Not started | Post-hackathon iteration |

---

## 12. Open Questions

**Risk & control modeling:**
1. What is the optimal level of risk granularity — process-level vs. sub-process vs. activity-level?
2. Should controls reflect the current state, target state, or both?
3. How should risk acceptance (no control) be explicitly captured in the RCM?

**Scoring and classification:**
4. How should inherent and residual risk scoring be calibrated across organizations?
5. What criteria determine whether a control is classified as "key"?
6. How should control strength (design quality) and control reliability (UC6) be combined in residual risk assessment?

**Data and integration:**
7. What level of standardization is required for inputs from UC1–UC5 to enable automated ingestion?
8. How should inconsistencies in upstream data be handled?
9. How should outputs be structured to ensure seamless integration with UC6, UC8, and UC9?

**Audit usability:**
10. How can the RCM best support audit execution design (UC8)?
11. What level of detail is required for practical audit use vs. automation?
12. How should outputs be validated with auditors and process owners?

**Scalability and reuse:**
13. How can the solution be adapted across different industries and regulatory environments?
14. What level of customization should be allowed vs. standardization enforced?
15. How can prompts and logic be maintained and version-controlled across SAAF organizations?
