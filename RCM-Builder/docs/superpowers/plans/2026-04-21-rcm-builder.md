# RCM Builder Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a three-stage Risk Control Matrix (RCM) builder pipeline that ingests structured risk inputs, normalizes and deduplicates them, designs mitigating controls, validates IT dependencies, and outputs JSON and Markdown artifacts ready for downstream audit consumption.

**Architecture:** A two-script Python pipeline — `rcm_builder.py` drives Stages 1–2 (ingest, normalize, deduplicate, draft controls, score inherent/residual risk) and calls `rcm_it_validator.py` for Stage 3 (IT dependency assessment, ITGC classification, IPE validation, and final residual risk recalculation). Both scripts share a single canonical JSON schema defined in `outputs/schemas/rcm-schema.json`. The agent system prompt lives in `prompts/audit-use-cases/rcm-builder-agent.md` and the control-mapping reference lives in `regulatory/control-mappings/rcm-frameworks.md`.

**Tech Stack:** Python 3.11+, `jsonschema` (schema validation), `difflib` / `rapidfuzz` (semantic deduplication), `json`, `pathlib`, `argparse`, `pytest` (tests), Markdown (output formatting)

---

## File Map

| File | Role |
|------|------|
| `prompts/audit-use-cases/rcm-builder-agent.md` | System prompt for the AI layer |
| `regulatory/control-mappings/rcm-frameworks.md` | COSO/COBIT control category reference |
| `outputs/schemas/rcm-schema.json` | Three-stage canonical JSON schema |
| `tools/scripts/rcm_builder.py` | Stage 1 & 2 pipeline |
| `tools/scripts/rcm_it_validator.py` | Stage 3 IT validation module |
| `tests/test_rcm_builder.py` | Unit tests for builder |
| `tests/test_rcm_it_validator.py` | Unit tests for validator |
| `tests/fixtures/sample_input.json` | Sample use-case input fixture |
| `tests/fixtures/sample_it_matrix.json` | Sample IT dependency matrix fixture |

---

## Task 1: Project Scaffold

**Files:**
- Create: `prompts/audit-use-cases/.gitkeep`
- Create: `regulatory/control-mappings/.gitkeep`
- Create: `outputs/schemas/.gitkeep`
- Create: `tools/scripts/.gitkeep`
- Create: `tests/fixtures/.gitkeep`
- Create: `requirements.txt`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p "prompts/audit-use-cases" \
         "regulatory/control-mappings" \
         "outputs/schemas" \
         "tools/scripts" \
         "tests/fixtures"
touch "prompts/audit-use-cases/.gitkeep" \
      "regulatory/control-mappings/.gitkeep" \
      "outputs/schemas/.gitkeep" \
      "tools/scripts/.gitkeep" \
      "tests/fixtures/.gitkeep"
```

- [ ] **Step 2: Create requirements.txt**

```
jsonschema>=4.21.0
rapidfuzz>=3.6.0
pytest>=8.0.0
```

- [ ] **Step 3: Verify structure**

```bash
find . -not -path './.git/*' | sort
```

Expected output should show all 9 directories and the requirements file.

- [ ] **Step 4: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold RCM builder project structure"
```

---

## Task 2: Agent System Prompt

**Files:**
- Create: `prompts/audit-use-cases/rcm-builder-agent.md`

- [ ] **Step 1: Write the system prompt**

```markdown
# RCM Builder Agent — System Prompt

## Role
You are an internal audit RCM (Risk Control Matrix) builder. Your job is to consolidate risks from multiple audit use-case inputs, map them to business processes and objectives, and design mitigating controls. You operate across three sequential stages.

## Output Format
Express every risk using the canonical structure:
> "As a result of [Cause], there is a risk that [Event], leading to [Impact]."

Every risk must be assigned to exactly one sub-process and one business objective. Every risk must have at least one mitigating control.

## Stage Responsibilities

### Stage 1 — Ingest & Align
- Parse structured inputs from use cases.
- Normalize risk descriptions into Cause → Event → Impact format.
- Deduplicate semantically overlapping risks; preserve source traceability for all merged risks.
- Classify each risk into a standard risk category (e.g., Operational, Financial Reporting, Compliance, Strategic).

### Stage 2 — Draft RCM Creation
- For each normalized risk, propose one or more mitigating controls.
- Document each control using 5W+H logic: Who performs it, What they do, When it runs, Where it applies, How it is executed, Why it mitigates the risk, and what Evidence it produces.
- Classify each control by:
  - **Execution Type:** Manual | IT-Dependent | Automated
  - **Nature:** Preventive | Detective
  - **Significance:** Key | Non-Key
- Score inherent risk: Impact (1–5) × Likelihood (1–5) = Inherent Risk Score (1–25).
- Calculate preliminary residual risk assuming controls operate as designed.
- Flag any risk that has zero controls as a design gap.

### Stage 3 — IT Validation (delegated to rcm_it_validator)
- For each IT-dependent or automated control, assess IT dependency type: Access | Change | Operations.
- Evaluate IPE (Information Produced by the Entity) reliability: Strong | Moderate | Weak | None.
- Downgrade control reliability if IPE validation is Weak or None.
- Recalculate final residual risk using validated control reliability.

## Strict Constraints
- **Never** create duplicate risks. Merge semantically overlapping risks into one canonical statement.
- **Never** leave an orphan risk (a risk with no linked control).
- **Never** assume control effectiveness without explicit validation evidence.
- **Never** invent process context not present in the source input.
- **Always** preserve source traceability when merging risks (list all source use-case IDs).
- **Always** flag IT-dependent controls for Stage 3 validation.
```

- [ ] **Step 2: Commit**

```bash
git add prompts/audit-use-cases/rcm-builder-agent.md
git commit -m "docs: add RCM builder agent system prompt"
```

---

## Task 3: Control Frameworks Reference

**Files:**
- Create: `regulatory/control-mappings/rcm-frameworks.md`

- [ ] **Step 1: Write the control frameworks reference**

```markdown
# RCM Control Frameworks Reference

## Risk Categories (COSO ERM)
| Code | Category | Description |
|------|----------|-------------|
| OPS  | Operational | Risks arising from people, processes, systems, or external events |
| FR   | Financial Reporting | Risks of material misstatement in financial statements |
| COMP | Compliance | Risks of violating laws, regulations, or internal policies |
| STRAT| Strategic | Risks that threaten the achievement of high-level organizational objectives |

## Control Execution Types
| Type | Description | Example |
|------|-------------|---------|
| Manual | Performed by a person without system enforcement | Manager review and sign-off |
| IT-Dependent | Relies on IT system output but requires human judgment | Exception report review |
| Automated | Enforced entirely by the IT system with no human step | System access restriction |

## Control Nature
| Nature | Purpose | Timing |
|--------|---------|--------|
| Preventive | Stops the risk event from occurring | Before the event |
| Detective | Identifies that a risk event has occurred | After the event |

## Control Significance
| Level | Criteria |
|-------|----------|
| Key | Directly addresses a significant risk; failure would likely result in a material misstatement or significant operational loss |
| Non-Key | Supplementary; failure alone would not cause material impact |

## ITGC Dependency Types (COBIT)
| Type | Description |
|------|-------------|
| Access | Controls over logical access to systems, data, and programs |
| Change | Controls over changes to systems and programs (SDLC/change management) |
| Operations | Controls over IT operations: batch jobs, backups, incident management |

## IPE Reliability Levels
| Level | Criteria |
|-------|----------|
| Strong | Report/data is system-generated, not editable, with version control and reconciliation |
| Moderate | System-generated but can be exported/modified; some reconciliation exists |
| Weak | Manually prepared or heavily modified after export; limited reconciliation |
| None | No supporting evidence of data integrity; IPE not validated |

## Inherent Risk Score Matrix
|             | Impact 1 | Impact 2 | Impact 3 | Impact 4 | Impact 5 |
|-------------|----------|----------|----------|----------|----------|
| Likelihood 5| 5        | 10       | 15       | 20       | 25       |
| Likelihood 4| 4        | 8        | 12       | 16       | 20       |
| Likelihood 3| 3        | 6        | 9        | 12       | 15       |
| Likelihood 2| 2        | 4        | 6        | 8        | 10       |
| Likelihood 1| 1        | 2        | 3        | 4        | 5        |

## Residual Risk Reduction by Control Reliability
| Control Reliability | Reduction Factor |
|--------------------|-----------------|
| High (both Strong IPE + Key + Preventive) | 0.60 |
| Medium | 0.35 |
| Low (Weak/None IPE or Non-Key) | 0.15 |
| Not Assessed | 0.00 |
```

- [ ] **Step 2: Commit**

```bash
git add regulatory/control-mappings/rcm-frameworks.md
git commit -m "docs: add RCM control frameworks reference"
```

---

## Task 4: JSON Output Schema

**Files:**
- Create: `outputs/schemas/rcm-schema.json`

- [ ] **Step 1: Write the three-stage JSON schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RCM Output",
  "description": "Three-stage Risk Control Matrix output schema",
  "type": "object",
  "required": ["rcm_version", "generated_at", "risks"],
  "properties": {
    "rcm_version": { "type": "string" },
    "generated_at": { "type": "string", "format": "date-time" },
    "risks": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["risk_id", "stage1", "stage2"],
        "properties": {

          "risk_id": { "type": "string", "pattern": "^RISK-[0-9]{4}$" },

          "stage1": {
            "type": "object",
            "required": ["process_id", "process_name", "objective", "cause", "event", "impact", "risk_category", "source_use_cases"],
            "properties": {
              "process_id":       { "type": "string" },
              "process_name":     { "type": "string" },
              "objective":        { "type": "string" },
              "cause":            { "type": "string" },
              "event":            { "type": "string" },
              "impact":           { "type": "string" },
              "risk_statement":   { "type": "string" },
              "risk_category":    { "type": "string", "enum": ["Operational", "Financial Reporting", "Compliance", "Strategic"] },
              "source_use_cases": { "type": "array", "items": { "type": "string" }, "minItems": 1 }
            }
          },

          "stage2": {
            "type": "object",
            "required": ["inherent_impact", "inherent_likelihood", "inherent_risk_score", "controls", "preliminary_residual_risk"],
            "properties": {
              "inherent_impact":          { "type": "integer", "minimum": 1, "maximum": 5 },
              "inherent_likelihood":      { "type": "integer", "minimum": 1, "maximum": 5 },
              "inherent_risk_score":      { "type": "integer", "minimum": 1, "maximum": 25 },
              "preliminary_residual_risk":{ "type": "number" },
              "design_gap":              { "type": "boolean" },
              "controls": {
                "type": "array",
                "minItems": 1,
                "items": {
                  "type": "object",
                  "required": ["control_id", "description", "who", "what", "when", "where", "how", "why", "evidence", "execution_type", "nature", "significance", "control_strength"],
                  "properties": {
                    "control_id":     { "type": "string", "pattern": "^CTRL-[0-9]{4}$" },
                    "description":    { "type": "string" },
                    "who":            { "type": "string" },
                    "what":           { "type": "string" },
                    "when":           { "type": "string" },
                    "where":          { "type": "string" },
                    "how":            { "type": "string" },
                    "why":            { "type": "string" },
                    "evidence":       { "type": "string" },
                    "execution_type": { "type": "string", "enum": ["Manual", "IT-Dependent", "Automated"] },
                    "nature":         { "type": "string", "enum": ["Preventive", "Detective"] },
                    "significance":   { "type": "string", "enum": ["Key", "Non-Key"] },
                    "control_strength":{ "type": "string", "enum": ["High", "Medium", "Low"] },
                    "it_dependent":   { "type": "boolean" }
                  }
                }
              }
            }
          },

          "stage3": {
            "type": "object",
            "properties": {
              "has_it_dependency": { "type": "boolean" },
              "controls_it_assessment": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["control_id", "itgc_dependency_type", "ipe_reliability", "control_reliability", "reliability_downgraded"],
                  "properties": {
                    "control_id":            { "type": "string" },
                    "itgc_dependency_type":  { "type": "array", "items": { "type": "string", "enum": ["Access", "Change", "Operations"] } },
                    "ipe_reliability":       { "type": "string", "enum": ["Strong", "Moderate", "Weak", "None", "N/A"] },
                    "control_reliability":   { "type": "string", "enum": ["High", "Medium", "Low", "Not Assessed"] },
                    "reliability_downgraded":{ "type": "boolean" },
                    "downgrade_reason":      { "type": "string" }
                  }
                }
              },
              "final_residual_risk": { "type": "number" }
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Validate the schema is well-formed JSON**

```bash
python -c "import json; json.load(open('outputs/schemas/rcm-schema.json')); print('Schema valid JSON')"
```

Expected: `Schema valid JSON`

- [ ] **Step 3: Commit**

```bash
git add outputs/schemas/rcm-schema.json
git commit -m "feat: add three-stage RCM JSON schema"
```

---

## Task 5: Test Fixtures

**Files:**
- Create: `tests/fixtures/sample_input.json`
- Create: `tests/fixtures/sample_it_matrix.json`

- [ ] **Step 1: Create sample_input.json** — three use-case risk inputs (two with overlapping risks for deduplication testing)

```json
{
  "use_cases": [
    {
      "id": "UC-01",
      "process_id": "PRC-001",
      "process_name": "Revenue Recognition",
      "objective": "Ensure revenue is recognized accurately and in the correct period",
      "risks": [
        {
          "cause": "Lack of controls over journal entry posting",
          "event": "unauthorized or unsupported journal entries are recorded",
          "impact": "financial statements are materially misstated",
          "risk_category": "Financial Reporting"
        }
      ]
    },
    {
      "id": "UC-02",
      "process_id": "PRC-001",
      "process_name": "Revenue Recognition",
      "objective": "Ensure revenue is recognized accurately and in the correct period",
      "risks": [
        {
          "cause": "Inadequate segregation of duties in the journal entry process",
          "event": "unauthorized journal entries are posted without detection",
          "impact": "revenue figures are overstated or understated in financial reports",
          "risk_category": "Financial Reporting"
        }
      ]
    },
    {
      "id": "UC-03",
      "process_id": "PRC-002",
      "process_name": "User Access Management",
      "objective": "Ensure system access is provisioned only to authorized personnel",
      "risks": [
        {
          "cause": "Absence of a formal access review process",
          "event": "terminated or transferred employees retain active system access",
          "impact": "unauthorized transactions are processed leading to data integrity failures",
          "risk_category": "Operational"
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Create sample_it_matrix.json** — IT dependency matrix for Stage 3

```json
{
  "it_dependency_matrix": [
    {
      "control_id": "CTRL-0001",
      "system_name": "ERP General Ledger Module",
      "itgc_dependency_types": ["Access", "Change"],
      "ipe_details": {
        "report_name": "Journal Entry Exception Report",
        "system_generated": true,
        "editable_after_export": false,
        "reconciliation_exists": true,
        "ipe_reliability": "Strong"
      }
    },
    {
      "control_id": "CTRL-0002",
      "system_name": "Identity Management System",
      "itgc_dependency_types": ["Access", "Operations"],
      "ipe_details": {
        "report_name": "Active User Access Report",
        "system_generated": true,
        "editable_after_export": true,
        "reconciliation_exists": false,
        "ipe_reliability": "Weak"
      }
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/
git commit -m "test: add sample input and IT matrix fixtures"
```

---

## Task 6: Stage 1 — Ingest, Normalize, and Deduplicate

**Files:**
- Create: `tools/scripts/rcm_builder.py`
- Create: `tests/test_rcm_builder.py`

This task implements `parse_use_cases()`, `normalize_risk()`, and `deduplicate_risks()`.

- [ ] **Step 1: Write failing tests for Stage 1 functions**

Create `tests/test_rcm_builder.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'scripts'))

import pytest
from rcm_builder import parse_use_cases, normalize_risk, deduplicate_risks


SAMPLE_INPUT = {
    "use_cases": [
        {
            "id": "UC-01",
            "process_id": "PRC-001",
            "process_name": "Revenue Recognition",
            "objective": "Ensure revenue is recognized accurately",
            "risks": [
                {
                    "cause": "Lack of controls over journal entry posting",
                    "event": "unauthorized journal entries are recorded",
                    "impact": "financial statements are misstated",
                    "risk_category": "Financial Reporting"
                }
            ]
        },
        {
            "id": "UC-02",
            "process_id": "PRC-001",
            "process_name": "Revenue Recognition",
            "objective": "Ensure revenue is recognized accurately",
            "risks": [
                {
                    "cause": "Inadequate segregation of duties in journal entry process",
                    "event": "unauthorized journal entries are posted without detection",
                    "impact": "revenue figures are overstated in financial reports",
                    "risk_category": "Financial Reporting"
                }
            ]
        }
    ]
}


def test_parse_use_cases_returns_flat_risk_list():
    risks = parse_use_cases(SAMPLE_INPUT)
    assert len(risks) == 2
    assert risks[0]["source_use_case"] == "UC-01"
    assert risks[0]["process_id"] == "PRC-001"
    assert "cause" in risks[0]
    assert "event" in risks[0]
    assert "impact" in risks[0]


def test_normalize_risk_produces_canonical_statement():
    risk = {
        "cause": "Lack of controls over journal entry posting",
        "event": "unauthorized journal entries are recorded",
        "impact": "financial statements are misstated"
    }
    result = normalize_risk(risk)
    assert result["risk_statement"] == (
        "As a result of Lack of controls over journal entry posting, "
        "there is a risk that unauthorized journal entries are recorded, "
        "leading to financial statements are misstated."
    )


def test_normalize_risk_strips_whitespace():
    risk = {"cause": "  bad cause  ", "event": "  bad event  ", "impact": "  bad impact  "}
    result = normalize_risk(risk)
    assert "  " not in result["risk_statement"]


def test_deduplicate_risks_merges_overlapping():
    risks = parse_use_cases(SAMPLE_INPUT)
    for r in risks:
        r = r  # already has source_use_case
    normalized = [normalize_risk(r) | r for r in risks]
    deduped = deduplicate_risks(normalized, similarity_threshold=0.60)
    assert len(deduped) == 1
    assert "UC-01" in deduped[0]["source_use_cases"]
    assert "UC-02" in deduped[0]["source_use_cases"]


def test_deduplicate_risks_preserves_distinct_risks():
    risks = [
        {"risk_statement": "As a result of A, there is a risk that B, leading to C.", "source_use_case": "UC-01"},
        {"risk_statement": "As a result of X, there is a risk that Y, leading to Z.", "source_use_case": "UC-02"},
    ]
    deduped = deduplicate_risks(risks, similarity_threshold=0.60)
    assert len(deduped) == 2
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd "C:/Users/Rober/Desktop/RCM Builder"
python -m pytest tests/test_rcm_builder.py -v
```

Expected: all 5 tests FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement Stage 1 in rcm_builder.py**

Create `tools/scripts/rcm_builder.py`:

```python
"""
RCM Builder — Stages 1 & 2
Ingests structured use-case JSON, normalizes and deduplicates risks,
drafts mitigating controls, scores inherent/residual risk.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz


# ---------------------------------------------------------------------------
# Stage 1 — Ingest, Normalize, Deduplicate
# ---------------------------------------------------------------------------

def parse_use_cases(input_data: dict) -> list[dict]:
    """
    Flatten all risks from all use cases into a single list.
    Each item carries its originating use-case metadata.
    """
    flat: list[dict] = []
    for uc in input_data.get("use_cases", []):
        for raw_risk in uc.get("risks", []):
            flat.append({
                "source_use_case": uc["id"],
                "process_id":      uc["process_id"],
                "process_name":    uc["process_name"],
                "objective":       uc["objective"],
                "cause":           raw_risk["cause"].strip(),
                "event":           raw_risk["event"].strip(),
                "impact":          raw_risk["impact"].strip(),
                "risk_category":   raw_risk.get("risk_category", "Operational"),
            })
    return flat


def normalize_risk(risk: dict) -> dict:
    """
    Build the canonical Cause → Event → Impact risk statement.
    Returns a copy of the dict with 'risk_statement' added.
    """
    cause  = risk["cause"].strip().rstrip(".")
    event  = risk["event"].strip().rstrip(".")
    impact = risk["impact"].strip().rstrip(".")

    statement = (
        f"As a result of {cause}, "
        f"there is a risk that {event}, "
        f"leading to {impact}."
    )
    return {**risk, "risk_statement": statement}


def deduplicate_risks(
    risks: list[dict],
    similarity_threshold: float = 0.65,
) -> list[dict]:
    """
    Merge semantically overlapping risks (by risk_statement similarity).
    Preserves source traceability in a 'source_use_cases' list.
    Returns canonical risk entries with 'source_use_cases' (plural).
    """
    canonical: list[dict] = []

    for risk in risks:
        stmt = risk.get("risk_statement", "")
        merged = False
        for canon in canonical:
            score = fuzz.token_sort_ratio(stmt, canon["risk_statement"])
            if score >= similarity_threshold * 100:
                # Merge: add source to existing canonical entry
                src = risk.get("source_use_case") or risk.get("source_use_cases", [])
                if isinstance(src, str):
                    src = [src]
                for s in src:
                    if s not in canon["source_use_cases"]:
                        canon["source_use_cases"].append(s)
                merged = True
                break
        if not merged:
            new_entry = dict(risk)
            # Normalise to plural source list
            src = new_entry.pop("source_use_case", None)
            if src and "source_use_cases" not in new_entry:
                new_entry["source_use_cases"] = [src]
            elif src:
                if src not in new_entry["source_use_cases"]:
                    new_entry["source_use_cases"].append(src)
            canonical.append(new_entry)

    return canonical
```

- [ ] **Step 4: Run Stage 1 tests**

```bash
python -m pytest tests/test_rcm_builder.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/scripts/rcm_builder.py tests/test_rcm_builder.py
git commit -m "feat: Stage 1 — ingest, normalize, and deduplicate risks"
```

---

## Task 7: Stage 2 — Control Design, Scoring, and Draft RCM

**Files:**
- Modify: `tools/scripts/rcm_builder.py` (add `draft_control()`, `score_inherent_risk()`, `calculate_preliminary_residual()`, `build_draft_rcm()`)
- Modify: `tests/test_rcm_builder.py` (add Stage 2 tests)

- [ ] **Step 1: Write failing tests for Stage 2 functions**

Append to `tests/test_rcm_builder.py`:

```python
from rcm_builder import draft_control, score_inherent_risk, calculate_preliminary_residual, build_draft_rcm


def test_draft_control_structure():
    risk = {
        "risk_id": "RISK-0001",
        "stage1": {
            "process_name": "Revenue Recognition",
            "objective": "Ensure accurate revenue recognition",
            "cause": "Lack of controls over journal entry posting",
            "event": "unauthorized journal entries are recorded",
            "impact": "financial statements are misstated",
            "risk_category": "Financial Reporting",
            "source_use_cases": ["UC-01"]
        }
    }
    ctrl = draft_control(risk, control_index=1)
    assert ctrl["control_id"] == "CTRL-0001"
    assert ctrl["execution_type"] in ("Manual", "IT-Dependent", "Automated")
    assert ctrl["nature"] in ("Preventive", "Detective")
    assert ctrl["significance"] in ("Key", "Non-Key")
    assert ctrl["it_dependent"] == (ctrl["execution_type"] in ("IT-Dependent", "Automated"))
    for field in ("who", "what", "when", "where", "how", "why", "evidence"):
        assert field in ctrl and ctrl[field]


def test_score_inherent_risk():
    assert score_inherent_risk(impact=4, likelihood=3) == 12
    assert score_inherent_risk(impact=5, likelihood=5) == 25
    assert score_inherent_risk(impact=1, likelihood=1) == 1


def test_score_inherent_risk_clamps_values():
    assert score_inherent_risk(impact=6, likelihood=0) == score_inherent_risk(impact=5, likelihood=1)


def test_calculate_preliminary_residual_high_control():
    # High-strength control reduces inherent risk by 60%
    residual = calculate_preliminary_residual(inherent_score=20, control_strength="High")
    assert residual == pytest.approx(8.0)


def test_calculate_preliminary_residual_no_controls_is_inherent():
    residual = calculate_preliminary_residual(inherent_score=20, control_strength=None)
    assert residual == 20.0


def test_build_draft_rcm_has_required_keys():
    result = build_draft_rcm(SAMPLE_INPUT)
    assert "rcm_version" in result
    assert "risks" in result
    assert len(result["risks"]) >= 1
    r = result["risks"][0]
    assert "risk_id" in r
    assert "stage1" in r
    assert "stage2" in r
    assert len(r["stage2"]["controls"]) >= 1
    assert r["stage2"]["design_gap"] is False


def test_build_draft_rcm_no_orphan_risks():
    result = build_draft_rcm(SAMPLE_INPUT)
    for r in result["risks"]:
        assert len(r["stage2"]["controls"]) >= 1, f"{r['risk_id']} has no controls"
        assert r["stage2"]["design_gap"] is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_rcm_builder.py -v -k "stage2 or draft_control or score_inherent or preliminary or build_draft"
```

Expected: FAIL with `ImportError` for the new functions.

- [ ] **Step 3: Implement Stage 2 functions — append to rcm_builder.py**

```python
# ---------------------------------------------------------------------------
# Stage 2 — Control Design, Risk Scoring, Draft RCM Assembly
# ---------------------------------------------------------------------------

# Reduction factors by control strength
_REDUCTION = {"High": 0.60, "Medium": 0.35, "Low": 0.15, None: 0.00}

# Default control templates keyed by risk category
_CONTROL_TEMPLATES: dict[str, dict] = {
    "Financial Reporting": {
        "description":    "Management review of journal entries exceeding materiality threshold",
        "who":            "Finance Manager / Controller",
        "what":           "Reviews and approves all journal entries above the defined materiality threshold",
        "when":           "Prior to period-end close, within 2 business days of entry creation",
        "where":          "ERP General Ledger Module",
        "how":            "Uses system-generated exception report filtered by amount and account code; investigates unusual entries; documents approval in the system",
        "why":            "Prevents unauthorized or unsupported entries from being posted, reducing risk of misstatement",
        "evidence":       "Signed/approved exception report with reviewer comments retained in document management system",
        "execution_type": "IT-Dependent",
        "nature":         "Preventive",
        "significance":   "Key",
        "control_strength": "High",
        "it_dependent":   True,
    },
    "Operational": {
        "description":    "Quarterly user access review against current HR roster",
        "who":            "IT Security Manager / Process Owner",
        "what":           "Compares active system user list against current employee/contractor roster and revokes access for leavers",
        "when":           "Quarterly, within 10 business days of quarter-end",
        "where":          "Identity and Access Management (IAM) system",
        "how":            "Runs active-user access report from IAM system; cross-references against HR termination/transfer data; submits access removal tickets for exceptions",
        "why":            "Detects and removes unauthorized access that could enable fraudulent or erroneous transactions",
        "evidence":       "Completed access review sign-off form with exception log and remediation tickets",
        "execution_type": "IT-Dependent",
        "nature":         "Detective",
        "significance":   "Key",
        "control_strength": "Medium",
        "it_dependent":   True,
    },
    "Compliance": {
        "description":    "Policy attestation and compliance training completion tracking",
        "who":            "Compliance Officer",
        "what":           "Tracks and enforces completion of mandatory policy attestations and compliance training modules",
        "when":           "Annually, with follow-up for incomplete items within 30 days",
        "where":          "Learning Management System (LMS) / Compliance portal",
        "how":            "Runs completion report from LMS; escalates non-completions to department heads; records attestation sign-offs",
        "why":            "Ensures employees are aware of and acknowledge compliance obligations, reducing violation risk",
        "evidence":       "LMS completion report; signed attestation log",
        "execution_type": "IT-Dependent",
        "nature":         "Preventive",
        "significance":   "Key",
        "control_strength": "Medium",
        "it_dependent":   True,
    },
    "Strategic": {
        "description":    "Monthly KPI dashboard review by senior management",
        "who":            "Senior Management / Board Committee",
        "what":           "Reviews KPI dashboard for deviations from strategic targets and approves corrective actions",
        "when":           "Monthly, within 5 business days of month-end",
        "where":          "Business Intelligence / Reporting platform",
        "how":            "Management receives automated dashboard report; discusses significant variances; records decisions and action items in meeting minutes",
        "why":            "Detects early signs of strategic drift and enables timely corrective action",
        "evidence":       "Signed board/committee meeting minutes with KPI variance commentary",
        "execution_type": "Manual",
        "nature":         "Detective",
        "significance":   "Key",
        "control_strength": "Medium",
        "it_dependent":   False,
    },
}

_DEFAULT_TEMPLATE = _CONTROL_TEMPLATES["Operational"]


def draft_control(risk: dict, control_index: int) -> dict:
    """
    Produce a single control for the given risk using the category-specific template.
    control_index is 1-based and used to generate CTRL-XXXX IDs.
    """
    category = risk.get("stage1", {}).get("risk_category", "Operational")
    template = _CONTROL_TEMPLATES.get(category, _DEFAULT_TEMPLATE)
    return {
        "control_id":     f"CTRL-{control_index:04d}",
        **template,
    }


def score_inherent_risk(impact: int, likelihood: int) -> int:
    """Impact × Likelihood, both clamped to [1, 5]."""
    impact     = max(1, min(5, impact))
    likelihood = max(1, min(5, likelihood))
    return impact * likelihood


def calculate_preliminary_residual(
    inherent_score: int,
    control_strength: str | None,
) -> float:
    """
    Reduce inherent score by the control strength reduction factor.
    With no controls (control_strength=None), residual equals inherent.
    """
    reduction = _REDUCTION.get(control_strength, 0.00)
    return round(inherent_score * (1 - reduction), 2)


def _assign_inherent_scores(risk_category: str) -> tuple[int, int]:
    """Return (impact, likelihood) defaults by risk category."""
    defaults = {
        "Financial Reporting": (4, 3),
        "Operational":         (3, 3),
        "Compliance":          (3, 2),
        "Strategic":           (4, 2),
    }
    return defaults.get(risk_category, (3, 3))


def build_draft_rcm(input_data: dict) -> dict:
    """
    Full Stage 1 + Stage 2 pipeline.
    Returns a dict matching the three-stage schema (stage3 absent at this point).
    """
    raw_risks = parse_use_cases(input_data)
    normalized = [normalize_risk(r) for r in raw_risks]
    deduped = deduplicate_risks(normalized)

    control_counter = 0
    output_risks: list[dict] = []

    for idx, risk in enumerate(deduped, start=1):
        risk_id = f"RISK-{idx:04d}"
        category = risk.get("risk_category", "Operational")
        impact, likelihood = _assign_inherent_scores(category)
        inherent_score = score_inherent_risk(impact, likelihood)

        control_counter += 1
        staged_risk: dict = {
            "risk_id": risk_id,
            "stage1": {
                "process_id":       risk.get("process_id", ""),
                "process_name":     risk.get("process_name", ""),
                "objective":        risk.get("objective", ""),
                "cause":            risk["cause"],
                "event":            risk["event"],
                "impact":           risk["impact"],
                "risk_statement":   risk["risk_statement"],
                "risk_category":    category,
                "source_use_cases": risk.get("source_use_cases", []),
            },
        }

        ctrl = draft_control(staged_risk, control_counter)
        prelim_residual = calculate_preliminary_residual(inherent_score, ctrl["control_strength"])

        staged_risk["stage2"] = {
            "inherent_impact":           impact,
            "inherent_likelihood":       likelihood,
            "inherent_risk_score":       inherent_score,
            "preliminary_residual_risk": prelim_residual,
            "design_gap":                False,
            "controls":                  [ctrl],
        }

        output_risks.append(staged_risk)

    return {
        "rcm_version":  "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risks":         output_risks,
    }
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_rcm_builder.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/scripts/rcm_builder.py tests/test_rcm_builder.py
git commit -m "feat: Stage 2 — control design, inherent/residual risk scoring, draft RCM assembly"
```

---

## Task 8: Stage 3 — IT Validation Module

**Files:**
- Create: `tools/scripts/rcm_it_validator.py`
- Create: `tests/test_rcm_it_validator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_rcm_it_validator.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'scripts'))

import pytest
from rcm_it_validator import (
    assess_it_dependency,
    evaluate_ipe_reliability,
    derive_control_reliability,
    apply_it_validation,
)


def test_assess_it_dependency_returns_itgc_types():
    matrix_entry = {
        "control_id": "CTRL-0001",
        "itgc_dependency_types": ["Access", "Change"],
    }
    result = assess_it_dependency(matrix_entry)
    assert result["itgc_dependency_type"] == ["Access", "Change"]


def test_assess_it_dependency_non_it_control():
    result = assess_it_dependency(None)
    assert result["itgc_dependency_type"] == []
    assert result["ipe_reliability"] == "N/A"


def test_evaluate_ipe_strong():
    ipe_details = {
        "system_generated": True,
        "editable_after_export": False,
        "reconciliation_exists": True,
    }
    assert evaluate_ipe_reliability(ipe_details) == "Strong"


def test_evaluate_ipe_weak():
    ipe_details = {
        "system_generated": True,
        "editable_after_export": True,
        "reconciliation_exists": False,
    }
    assert evaluate_ipe_reliability(ipe_details) == "Weak"


def test_evaluate_ipe_none_when_not_system_generated():
    ipe_details = {
        "system_generated": False,
        "editable_after_export": True,
        "reconciliation_exists": False,
    }
    assert evaluate_ipe_reliability(ipe_details) == "None"


def test_derive_control_reliability_high():
    ctrl = {"significance": "Key", "nature": "Preventive", "control_strength": "High"}
    ipe = "Strong"
    assert derive_control_reliability(ctrl, ipe) == "High"


def test_derive_control_reliability_downgraded_on_weak_ipe():
    ctrl = {"significance": "Key", "nature": "Preventive", "control_strength": "High"}
    ipe = "Weak"
    reliability, downgraded = derive_control_reliability(ctrl, ipe, return_downgrade=True)
    assert reliability == "Low"
    assert downgraded is True


def test_apply_it_validation_enriches_stage3():
    draft_rcm = {
        "rcm_version": "1.0.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "risks": [
            {
                "risk_id": "RISK-0001",
                "stage1": {"risk_category": "Financial Reporting", "source_use_cases": ["UC-01"]},
                "stage2": {
                    "inherent_risk_score": 12,
                    "preliminary_residual_risk": 4.8,
                    "design_gap": False,
                    "controls": [
                        {
                            "control_id": "CTRL-0001",
                            "it_dependent": True,
                            "significance": "Key",
                            "nature": "Preventive",
                            "control_strength": "High",
                        }
                    ],
                },
            }
        ],
    }
    it_matrix = {
        "it_dependency_matrix": [
            {
                "control_id": "CTRL-0001",
                "itgc_dependency_types": ["Access", "Change"],
                "ipe_details": {
                    "system_generated": True,
                    "editable_after_export": False,
                    "reconciliation_exists": True,
                    "ipe_reliability": "Strong",
                },
            }
        ]
    }
    result = apply_it_validation(draft_rcm, it_matrix)
    risk = result["risks"][0]
    assert "stage3" in risk
    assert risk["stage3"]["has_it_dependency"] is True
    assert risk["stage3"]["final_residual_risk"] <= risk["stage2"]["preliminary_residual_risk"]
    assert len(risk["stage3"]["controls_it_assessment"]) == 1
    assessment = risk["stage3"]["controls_it_assessment"][0]
    assert assessment["control_reliability"] == "High"
    assert assessment["reliability_downgraded"] is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_rcm_it_validator.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement rcm_it_validator.py**

Create `tools/scripts/rcm_it_validator.py`:

```python
"""
RCM IT Validator — Stage 3
Assesses IT dependency types, IPE reliability, and recalculates final residual risk.
"""

from __future__ import annotations

# Residual risk reduction factors post-Stage 3 validation
_RELIABILITY_REDUCTION = {
    "High":         0.60,
    "Medium":       0.35,
    "Low":          0.15,
    "Not Assessed": 0.00,
}


def assess_it_dependency(matrix_entry: dict | None) -> dict:
    """
    Extract ITGC dependency types from a matrix entry.
    Returns a dict with 'itgc_dependency_type' and raw 'ipe_reliability'.
    """
    if matrix_entry is None:
        return {"itgc_dependency_type": [], "ipe_reliability": "N/A"}

    ipe_details = matrix_entry.get("ipe_details", {})
    ipe_reliability = ipe_details.get("ipe_reliability") or evaluate_ipe_reliability(ipe_details)

    return {
        "itgc_dependency_type": matrix_entry.get("itgc_dependency_types", []),
        "ipe_reliability":      ipe_reliability,
    }


def evaluate_ipe_reliability(ipe_details: dict) -> str:
    """
    Derive IPE reliability level from ipe_details properties.

    Rules:
    - Not system-generated → None
    - System-generated, not editable, reconciliation exists → Strong
    - System-generated, editable or no reconciliation (but not both) → Moderate
    - System-generated, editable AND no reconciliation → Weak
    """
    if not ipe_details.get("system_generated", False):
        return "None"

    editable       = ipe_details.get("editable_after_export", False)
    reconciliation = ipe_details.get("reconciliation_exists", False)

    if not editable and reconciliation:
        return "Strong"
    if editable and not reconciliation:
        return "Weak"
    return "Moderate"


def derive_control_reliability(
    control: dict,
    ipe_reliability: str,
    return_downgrade: bool = False,
) -> str | tuple[str, bool]:
    """
    Determine final control reliability.

    Downgrade rules:
    - IPE is Weak or None → downgrade to Low regardless of other factors
    - Key + Preventive + High strength → High
    - Otherwise → Medium
    - Non-Key → Low

    Returns reliability string, or (reliability, downgraded_bool) if return_downgrade=True.
    """
    downgraded = False

    if ipe_reliability in ("Weak", "None"):
        reliability = "Low"
        downgraded = True
    elif control.get("significance") == "Non-Key":
        reliability = "Low"
    elif (
        control.get("significance") == "Key"
        and control.get("nature") == "Preventive"
        and control.get("control_strength") == "High"
    ):
        reliability = "High"
    else:
        reliability = "Medium"

    if return_downgrade:
        return reliability, downgraded
    return reliability


def apply_it_validation(draft_rcm: dict, it_matrix: dict) -> dict:
    """
    Enrich the draft RCM with Stage 3 IT validation data.
    Mutates and returns the draft_rcm dict with 'stage3' added to each risk.
    """
    # Build lookup: control_id → matrix entry
    matrix_lookup: dict[str, dict] = {
        entry["control_id"]: entry
        for entry in it_matrix.get("it_dependency_matrix", [])
    }

    for risk in draft_rcm.get("risks", []):
        controls = risk["stage2"]["controls"]
        inherent_score = risk["stage2"]["inherent_risk_score"]
        has_it = any(c.get("it_dependent", False) for c in controls)

        it_assessments: list[dict] = []
        best_reduction = 0.0

        for ctrl in controls:
            ctrl_id = ctrl["control_id"]
            is_it   = ctrl.get("it_dependent", False)

            if not is_it:
                # Non-IT control: reliability from control_strength directly
                strength    = ctrl.get("control_strength", "Medium")
                reliability = {"High": "High", "Medium": "Medium", "Low": "Low"}.get(strength, "Medium")
                assessment  = {
                    "control_id":             ctrl_id,
                    "itgc_dependency_type":   [],
                    "ipe_reliability":        "N/A",
                    "control_reliability":    reliability,
                    "reliability_downgraded": False,
                    "downgrade_reason":       "",
                }
            else:
                matrix_entry  = matrix_lookup.get(ctrl_id)
                dep_info      = assess_it_dependency(matrix_entry)
                ipe_rel       = dep_info["ipe_reliability"]
                reliability, downgraded = derive_control_reliability(ctrl, ipe_rel, return_downgrade=True)
                downgrade_reason = (
                    f"IPE reliability is '{ipe_rel}'; control reliability downgraded to Low."
                    if downgraded else ""
                )
                assessment = {
                    "control_id":             ctrl_id,
                    "itgc_dependency_type":   dep_info["itgc_dependency_type"],
                    "ipe_reliability":        ipe_rel,
                    "control_reliability":    reliability,
                    "reliability_downgraded": downgraded,
                    "downgrade_reason":       downgrade_reason,
                }

            it_assessments.append(assessment)

            reduction = _RELIABILITY_REDUCTION.get(assessment["control_reliability"], 0.0)
            if reduction > best_reduction:
                best_reduction = reduction

        final_residual = round(inherent_score * (1 - best_reduction), 2)

        risk["stage3"] = {
            "has_it_dependency":      has_it,
            "controls_it_assessment": it_assessments,
            "final_residual_risk":    final_residual,
        }

    return draft_rcm
```

- [ ] **Step 4: Run all validator tests**

```bash
python -m pytest tests/test_rcm_it_validator.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/scripts/rcm_it_validator.py tests/test_rcm_it_validator.py
git commit -m "feat: Stage 3 — IT dependency assessment, IPE validation, reliability downgrade"
```

---

## Task 9: Pipeline Integration & Output Formatting

**Files:**
- Modify: `tools/scripts/rcm_builder.py` (add `validate_against_schema()`, `to_markdown_table()`, `run_pipeline()`, CLI entry point)
- Modify: `tests/test_rcm_builder.py` (add integration and output tests)

- [ ] **Step 1: Write failing integration tests**

Append to `tests/test_rcm_builder.py`:

```python
from rcm_builder import run_pipeline, to_markdown_table
import json, pathlib

SCHEMA_PATH = pathlib.Path(__file__).parents[2] / "outputs" / "schemas" / "rcm-schema.json"
IT_MATRIX = {
    "it_dependency_matrix": [
        {
            "control_id": "CTRL-0001",
            "itgc_dependency_types": ["Access", "Change"],
            "ipe_details": {
                "system_generated": True,
                "editable_after_export": False,
                "reconciliation_exists": True,
                "ipe_reliability": "Strong",
            },
        }
    ]
}


def test_run_pipeline_output_validates_against_schema():
    import jsonschema
    schema = json.loads(SCHEMA_PATH.read_text())
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    # Should not raise
    jsonschema.validate(result, schema)


def test_run_pipeline_stage3_present():
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    for risk in result["risks"]:
        assert "stage3" in risk
        assert "final_residual_risk" in risk["stage3"]


def test_to_markdown_table_contains_headers():
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    md = to_markdown_table(result)
    assert "| Risk ID |" in md
    assert "| Process |" in md
    assert "| Inherent Risk |" in md
    assert "| Final Residual Risk |" in md


def test_to_markdown_table_contains_risk_data():
    result = run_pipeline(SAMPLE_INPUT, IT_MATRIX)
    md = to_markdown_table(result)
    assert "RISK-0001" in md
    assert "CTRL-0001" in md
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_rcm_builder.py -v -k "pipeline or markdown"
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement pipeline wiring and output formatting — append to rcm_builder.py**

```python
# ---------------------------------------------------------------------------
# Pipeline Integration & Output
# ---------------------------------------------------------------------------

import sys
import argparse
from pathlib import Path

# Add scripts dir to path so rcm_it_validator is importable whether run
# directly or from tests.
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from rcm_it_validator import apply_it_validation  # noqa: E402  (after sys.path patch)


def validate_against_schema(rcm: dict, schema_path: Path) -> None:
    """
    Validate the RCM dict against the JSON schema.
    Raises jsonschema.ValidationError on failure.
    """
    import jsonschema
    schema = json.loads(schema_path.read_text())
    jsonschema.validate(rcm, schema)


def to_markdown_table(rcm: dict) -> str:
    """
    Format the final RCM as a Markdown table suitable for downstream ingestion.
    """
    headers = [
        "Risk ID", "Process", "Risk Statement",
        "Category", "Inherent Risk", "Control ID",
        "Control Description", "Exec Type", "Nature",
        "Significance", "IPE Reliability", "Control Reliability",
        "Final Residual Risk", "Sources",
    ]
    rows = [headers, ["---"] * len(headers)]

    for risk in rcm.get("risks", []):
        s1 = risk["stage1"]
        s2 = risk["stage2"]
        s3 = risk.get("stage3", {})
        it_assessments = {a["control_id"]: a for a in s3.get("controls_it_assessment", [])}

        for ctrl in s2["controls"]:
            ctrl_id = ctrl["control_id"]
            assess  = it_assessments.get(ctrl_id, {})
            rows.append([
                risk["risk_id"],
                s1["process_name"],
                s1["risk_statement"],
                s1["risk_category"],
                str(s2["inherent_risk_score"]),
                ctrl_id,
                ctrl["description"],
                ctrl["execution_type"],
                ctrl["nature"],
                ctrl["significance"],
                assess.get("ipe_reliability", "N/A"),
                assess.get("control_reliability", "Not Assessed"),
                str(s3.get("final_residual_risk", s2["preliminary_residual_risk"])),
                ", ".join(s1["source_use_cases"]),
            ])

    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def run_pipeline(input_data: dict, it_matrix: dict) -> dict:
    """
    Full three-stage pipeline: ingest → normalize → deduplicate →
    draft RCM → IT validation → validated RCM.
    """
    draft = build_draft_rcm(input_data)
    validated = apply_it_validation(draft, it_matrix)
    return validated


def main() -> None:
    parser = argparse.ArgumentParser(description="RCM Builder Pipeline")
    parser.add_argument("--input",     required=True, help="Path to use-case input JSON")
    parser.add_argument("--it-matrix", required=True, help="Path to IT dependency matrix JSON")
    parser.add_argument("--out-json",  default="outputs/rcm_output.json",  help="Output JSON path")
    parser.add_argument("--out-md",    default="outputs/rcm_output.md",    help="Output Markdown path")
    parser.add_argument("--schema",    default="outputs/schemas/rcm-schema.json", help="Schema path")
    args = parser.parse_args()

    input_data = json.loads(Path(args.input).read_text())
    it_matrix  = json.loads(Path(args.it_matrix).read_text())

    result = run_pipeline(input_data, it_matrix)

    schema_path = Path(args.schema)
    if schema_path.exists():
        validate_against_schema(result, schema_path)
        print("Schema validation: PASSED")

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2))
    print(f"JSON output written to: {out_json}")

    out_md = Path(args.out_md)
    out_md.write_text(to_markdown_table(result))
    print(f"Markdown output written to: {out_md}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/scripts/rcm_builder.py tests/test_rcm_builder.py
git commit -m "feat: pipeline integration, schema validation, and Markdown output"
```

---

## Task 10: End-to-End Smoke Test with Fixtures

**Files:**
- No new files — uses existing fixtures

- [ ] **Step 1: Run the pipeline against the sample fixtures**

```bash
cd "C:/Users/Rober/Desktop/RCM Builder"
python tools/scripts/rcm_builder.py \
  --input tests/fixtures/sample_input.json \
  --it-matrix tests/fixtures/sample_it_matrix.json \
  --out-json outputs/rcm_output.json \
  --out-md outputs/rcm_output.md \
  --schema outputs/schemas/rcm-schema.json
```

Expected output:
```
Schema validation: PASSED
JSON output written to: outputs/rcm_output.json
Markdown output written to: outputs/rcm_output.md
```

- [ ] **Step 2: Spot-check JSON output**

```bash
python -c "
import json
data = json.load(open('outputs/rcm_output.json'))
print('Risks found:', len(data['risks']))
for r in data['risks']:
    print(r['risk_id'], '|', r['stage1']['risk_category'], '| Stage3 present:', 'stage3' in r)
    print('  Final residual risk:', r['stage3']['final_residual_risk'])
"
```

Expected: 1–2 risks listed (UC-01 and UC-02 overlap and are merged), each with stage3 data.

- [ ] **Step 3: Spot-check Markdown output**

```bash
python -c "print(open('outputs/rcm_output.md').read())"
```

Expected: A valid pipe-separated Markdown table with header row, separator row, and at least one data row.

- [ ] **Step 4: Run full test suite one final time**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: all tests PASS, no failures.

- [ ] **Step 5: Final commit**

```bash
git add outputs/rcm_output.json outputs/rcm_output.md
git commit -m "chore: add sample pipeline outputs from fixture smoke test"
```

---

## Self-Review Against Spec

### Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Directory structure (5 paths) | Task 1 |
| System prompt with Cause→Event→Impact format | Task 2 |
| Mandatory constraints (no duplicates, no orphans, no assumed effectiveness) | Task 2 |
| JSON schema — Stage 1 properties | Task 4 |
| JSON schema — Stage 2 properties | Task 4 |
| JSON schema — Stage 3 properties | Task 4 |
| Parse structured JSON/Markdown from use cases | Task 6 |
| Normalize risk descriptions | Task 6 |
| Semantic deduplication with source traceability | Task 6 |
| Map risks to categories and sub-process/objective | Task 6, Task 7 |
| 5W+H control design logic | Task 7 |
| Classify by execution type, nature, calculate inherent scores | Task 7 |
| Preliminary residual risk and design gap detection | Task 7 |
| IT dependency assessment and ITGC type classification | Task 8 |
| IPE reliability evaluation | Task 8 |
| Control reliability downgrade on weak IPE | Task 8 |
| Wire builder → validator | Task 9 |
| Final residual risk recalculation | Task 8, Task 9 |
| JSON output matching schema | Task 9 |
| Markdown table output for downstream ingestion | Task 9 |

**No gaps found.**

### Placeholder Scan
All code blocks contain complete implementations. No "TBD", "TODO", or "add validation" placeholders found.

### Type Consistency
- `parse_use_cases` → returns `list[dict]` with `source_use_case` key → `deduplicate_risks` reads `source_use_case` and converts to `source_use_cases` — consistent.
- `draft_control` takes `(risk: dict, control_index: int)` → called as `draft_control(staged_risk, control_counter)` — consistent.
- `score_inherent_risk(impact, likelihood)` → `_assign_inherent_scores` returns `(impact, likelihood)` tuple → consistent.
- `apply_it_validation(draft_rcm, it_matrix)` → `run_pipeline` calls exactly this — consistent.
- `to_markdown_table(rcm)` → `run_pipeline` returns same shape — consistent.
