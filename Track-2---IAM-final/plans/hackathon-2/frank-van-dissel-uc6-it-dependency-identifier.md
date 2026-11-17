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

Modern business processes are inextricably linked to IT systems. An automated control is only as reliable as the systems it runs on — yet many internal audit teams assess automated controls without explicitly mapping their IT dependencies. A "system-generated aging report" control, for example, is only reliable if the underlying ERP database, report writer, and access controls are themselves reliable. The IT Dependency & Infrastructure Identifier Agent solves this: for every automated or semi-automated control identified in UC1–UC5, it maps the specific IT systems involved, links them to their required IT General Controls (ITGCs), assesses reliability, and recommends which IT systems must be added to the audit scope.

This is **Use Case 6 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It consumes outputs from [UC1](frank-van-dissel-uc1-policy-process-intake.md) through UC5 and feeds its IT Dependency Matrix into the [RCM Builder (UC7)](frank-van-dissel-uc7-rcm-builder.md).

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — IT Dependency Mapping (GIAS 13.2, 13.3)

**Applicable standards:**

- GIAS 13.2 — "Identify and gather... governance, risk management, and control processes... review information to understand how processes are intended to operate."
- GIAS 13.3 — "The scope must establish the engagement's focus and boundaries by specifying the... systems, components... and be sufficient to achieve objectives."

**In scope:**

- System mapping: identifying the software application and database for every automated/semi-automated control
- Dependency linkage: mapping Application Controls to their underlying ITGCs (Access, Change, Operations)
- Reliability assessment: Fully Automated vs. Semi-Automated (IPE — Information Produced by Entity)
- Cascading failure modeling: "If ITGC [X] fails, then Automated Control [Y] is deemed unreliable"
- Scope extension: recommending IT systems to add to the audit scope (GIAS 13.3)
- Identifying silent dependencies — controls that appear manual but rely on system-generated data (IPE)

**Out of scope:**

- Detailed IT General Controls testing (that is the role of UC8)
- Network penetration testing or active IT security assessment
- Cloud infrastructure configuration assessment

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | IT dependency extraction prompt; IPE silent dependency detector; cascading failure logic prompt |
| **Tools** | System architecture diagram parser; component relationship mapping; conditional If-Then logic for ITGC-control dependencies |
| **Regulatory** | GIAS 13.2, 13.3; COBIT 2019 ITGC taxonomy reusable from `regulatory/control-mappings/` |
| **Outputs** | IT Dependency Matrix: Control ID, Host System, Dependency Level (ITGCs required), Reliability Status, Technical Scope Recommendations |

---

## 5. Prompts

### System prompt (draft — IT Dependency Mapper)

```
You are an IT audit specialist in control dependency mapping.
Given a list of business process controls and the available IT system documentation
(architecture diagrams, asset register, system descriptions):

For each automated or semi-automated control:
1. Identify the specific software application and database that hosts the control
2. Identify the required IT General Controls (Access Management, Change Management,
   IT Operations) that must be reliable for this control to function
3. Assess reliability: Fully Automated (no human intervention) or Semi-Automated
   (IPE — system-produced information used by a human)
4. Define cascading failure logic: "If ITGC [X] is ineffective, then Control [Y] is unreliable"
5. Recommend whether the host system must be added to the audit scope

Flag any controls that appear manual but actually rely on system-generated data (silent IPE dependency).
```

### Example user prompts

**Prompt 1 — Dependency mapping:**
```
Business process controls from UC1-UC5:
- Control C-001: "Review of system-generated duplicate payment report" (Semi-Automated)
- Control C-002: "ERP auto-blocks invoices without valid PO reference" (Fully Automated)

IT Asset Register: [ERP system = SAP S/4HANA, Report Writer = SAP Analytics Cloud]

Map IT dependencies, required ITGCs, and reliability status for each control.
```

**Prompt 2 — Scope extension:**
```
Audit scope currently includes: Accounts Payable process.
Identified control: "Expense management approval via Concur SaaS."

Should the Concur SaaS platform be added to the audit scope?
If so, what should be assessed (SOC1/SOC2 report review, access controls, etc.)?
```

**Intended file location:** `prompts/audit-use-cases/uc6-it-dependency-identifier.md`

---

## 6. Tools and Techniques

### Approach

Two-agent pipeline with consistency validation:

1. **IT Dependency Mapper:** Parses system documentation and asset registers; maps each control to its host system, required ITGCs, and reliability status; produces cascading failure logic
2. **Integrity Validator:** Detects "silent IPE dependencies" — controls that participants might consider manual but actually rely on system-generated data
3. **Infrastructure Consistency Check:** Ensures that if an application is in scope, the agent has also identified the relevant database and operating system dependencies

### Quality Safeguards

**Safeguard 1 — Integrity Validator (Silent IPE Detector):** Checks all controls categorized as "Manual" for hidden system data dependencies. A control where the auditor relies on a system-generated report is Semi-Automated (IPE) regardless of how it is described.

**Safeguard 2 — Infrastructure Consistency Check:** If application X is in scope, the agent verifies that the underlying database and OS layers have also been considered — preventing assessment of only the application layer.

### Example script or pseudocode

```python
def run_it_dependency_agent(controls: list[dict], it_docs: dict) -> dict:
    dependency_map = map_dependencies(controls, it_docs)   # For each control: system + ITGCs
    
    # Quality gates
    dependency_map = detect_silent_ipe(dependency_map)        # Integrity Validator
    dependency_map = check_infrastructure_consistency(dependency_map)  # Consistency Check
    
    scope_recommendations = identify_scope_extensions(dependency_map)
    
    return build_it_dependency_matrix(dependency_map, scope_recommendations)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), JSON schema mapping

**Intended file location:** `tools/scripts/uc6-it-dependency-identifier/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2 | Understanding governance and control processes of the activity under review |
| GIAS 13.3 | Scope must specify systems and components sufficient to achieve objectives |
| COBIT 2019 | ITGC taxonomy: Access Management, Change Management, IT Operations |

### Claude / AI tool usage notes

IT architecture diagrams and asset registers may be confidential. Use synthetic or anonymized system documentation for testing. The agent processes system architecture — not personal data — but system documentation should be reviewed for confidentiality before processing.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (IT Dependency Matrix)

**Schema reference:** Scope recommendations and reliability failures map to `outputs/schemas/finding-schema.json`

### Test Scenario 1 — The "Broken Foundation" Logic

- **Input:** Semi-automated control: "Review of System-Generated Duplicate Payment Report"
- **Expected:** Agent identifies ERP Database and Report Writer Module as dependencies; flags "Database Access Controls" and "Change Management" as mandatory ITGCs
- **Validation:** IT audit specialist confirms dependency map is technically accurate

### Test Scenario 2 — Scope Expansion

- **Input:** Process using a third-party SaaS for expense management (Concur)
- **Expected:** Agent identifies dependency on SaaS provider; recommends including SOC1/SOC2 Report Review in audit scope and criteria (UC5)
- **Validation:** IT audit lead confirms recommendation is appropriate

### Synthetic example output

```json
{
  "dependency_matrix": [
    {
      "control_id": "C-001",
      "control_description": "Review of system-generated duplicate payment report",
      "reliability_type": "Semi-Automated (IPE)",
      "host_system": "SAP S/4HANA",
      "host_database": "SAP HANA Database",
      "required_itgcs": ["Access Management — SAP", "Change Management — SAP", "IT Operations — SAP HANA"],
      "cascading_failure": "If Change Management ITGC is ineffective, unauthorized changes to report logic cannot be detected — control C-001 is unreliable",
      "reliability_status": "Medium — dependent on ITGC effectiveness",
      "scope_recommendation": "Add SAP S/4HANA Access Management and Change Management to audit scope"
    }
  ],
  "silent_ipe_flags": [],
  "scope_extensions": ["SAP S/4HANA — Access Management", "SAP S/4HANA — Change Management"]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.9+
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Automated parsing of BPMN or architecture diagram formats (Visio, Lucidchart exports)
- [ ] Integration with CMDB (Configuration Management Database) for live asset data

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- IT Dependency Mapper prompt with ITGC taxonomy
- Silent IPE Detector logic
- IT Dependency Matrix JSON schema

**What help I'm looking for:**

- IT audit specialists to validate the ITGC dependency logic
- Organizations willing to share anonymized IT architecture documentation for testing

**Video Transcription Insights (Hackathon #3 analysis):**

**Technical debt analyzer pattern:**

Video analysis identified a complementary use case from a technical architecture session: the **technical debt analyzer**. When mapping IT dependencies, the agent can simultaneously flag technical debt risks that create audit exposure:

- Deprecated libraries with known CVEs in the dependency graph (cross-reference with public NVD/OSV databases)
- End-of-life software versions identified in the architecture map (e.g., Python 2, OpenSSL < 3.0)
- Circular dependencies that indicate poor architectural separation (audit relevance: change management risk, blast radius of incidents)
- Undocumented dependencies (systems in the dependency map that have no corresponding documentation in Confluence)

Implementation: extend the IT Dependency Matrix output with a `technical_debt_flags` field. For each flagged system, output: system name, debt type (EOL/CVE/undocumented/circular), risk rating, and suggested remediation.

This directly links IT dependency mapping (audit scope) to patch management and technical debt (DORA ICT risk, ISO 27001 A.12.6). The `cli-audit-system-wrapper.md` plan can query package managers (pip, npm, maven) for dependency version data as evidence input.

**Related SAAF plans:**

- [UC1 — Policy-to-Process Intake](frank-van-dissel-uc1-policy-process-intake.md) — provides native control register as input
- [UC5 — Regulatory Criteria](frank-van-dissel-uc5-regulatory-criteria.md) — SaaS scope extensions feed back into criteria (SOC1/SOC2)
- [UC7 — RCM Builder](frank-van-dissel-uc7-rcm-builder.md) — consumes IT Dependency Matrix as input
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates scope completeness
- [`plans/hackathon-3/cli-audit-system-wrapper.md`](../hackathon-3/cli-audit-system-wrapper.md) — CLI wrapper to query package managers for dependency version evidence

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie IT audit dependency mapping |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What is the minimum viable IT documentation input — can the agent work from a plain-text system description if no architecture diagram is available?
2. How should the agent handle cloud-native environments where the distinction between application and infrastructure is blurred (e.g., serverless functions)?
3. Should the ITGCs be assessed in UC6 or deferred entirely to UC8 (Work Program) — or should UC6 only flag the dependency and UC8 define the test?
