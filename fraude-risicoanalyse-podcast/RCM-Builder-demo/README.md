# RCM Builder

A three-stage Python pipeline that builds a **Risk Control Matrix (RCM)** from structured audit use-case inputs. It consolidates upstream UC2-UC5 risk sources, normalizes and deduplicates risks, designs risk-specific controls, validates IT dependencies, and outputs both JSON and Markdown artifacts ready for downstream audit consumption.

---

## Pipeline Overview

| Stage | Module | What it does |
|-------|--------|-------------|
| **Stage 1** | `rcm_builder.py` | Ingest UC1-UC5 risk inputs → normalize risks (Cause→Event→Impact) → deduplicate overlapping risks → preserve traceability |
| **Stage 2** | `rcm_builder.py` | Design risk-specific controls (5W+H) → score inherent risk using taxonomy + risk appetite → calculate preliminary residual risk |
| **Stage 3** | `rcm_it_validator.py` | Assess IT dependencies (ITGC) → evaluate IPE validation → classify control reliability → recalculate final residual risk → introduce UC6-derived IT risks when needed |

---

## Installation

Python 3.11+ required.

```bash
pip install -r requirements.txt
```

Dependencies: `jsonschema`, `rapidfuzz`, `pytest`

---

## Usage

### Run the full pipeline

```bash
python tools/scripts/rcm_builder.py \
  --input <path/to/use_cases.json> \
  --it-matrix <path/to/it_matrix.json> \
  --out-json outputs/rcm_output.json \
  --out-md outputs/rcm_output.md \
  --schema outputs/schemas/rcm-schema.json
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--input` | Yes | — | Path to use-case input JSON |
| `--it-matrix` | Yes | — | Path to IT dependency matrix JSON |
| `--out-json` | No | `outputs/rcm_output.json` | Output JSON path |
| `--out-md` | No | `outputs/rcm_output.md` | Output Markdown table path |
| `--schema` | No | `outputs/schemas/rcm-schema.json` | JSON schema for validation |

### Try it with the sample fixtures

```bash
python tools/scripts/rcm_builder.py \
  --input tests/fixtures/sample_input.json \
  --it-matrix tests/fixtures/sample_it_matrix.json
```

Expected output:
```
Schema validation: PASSED
JSON output written to: outputs/rcm_output.json
Markdown output written to: outputs/rcm_output.md
```

---

## Input File Formats

### Use-case input (`--input`)

The pipeline supports both the legacy `use_cases[]` structure and richer UC2-UC5-style collections such as `historical_risks`, `incidents`, `fraud_scenarios`, `regulatory_risks`, and `risk_sources`.

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
          "event": "unauthorized journal entries are recorded",
          "impact": "financial statements are materially misstated",
          "risk_category": "Financial Reporting"
        }
      ]
    }
  ]
}
```

**Canonical `risk_category` values:** `Financial` | `Operational` | `IT` | `Compliance` | `Fraud` | `Strategic`

Legacy aliases such as `Financial Reporting` are normalized automatically.

### IT dependency matrix (`--it-matrix`)

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
    }
  ]
}
```

**`itgc_dependency_types`:** `Access` | `Change` | `Operations`

**`ipe_reliability`** (optional — computed from flags if omitted):

| `system_generated` | `editable_after_export` | `reconciliation_exists` | Result |
|--------------------|------------------------|------------------------|--------|
| false | any | any | `None` |
| true | false | true | `Strong` |
| true | true | false | `Weak` |
| true | true | true | `Moderate` |
| true | false | false | `Moderate` |

---

## Output Files

### JSON (`--out-json`)

Full three-stage structured output validated against `outputs/schemas/rcm-schema.json`.

Each risk entry contains:
- **stage1:** Process context, objective linkage, risk statement (Cause→Event→Impact), canonical category, risk source traceability, and source references
- **stage2:** Inherent impact/likelihood, control designs (5W+H), design effectiveness, design gaps, and preliminary residual risk
- **stage3:** IT dependency types, system/report context, IPE validation, control reliability, additional ITGC control requirements, final residual risk, and optional UC6-derived risk creation

### Markdown (`--out-md`)

Pipe-separated table for human review and downstream ingestion including traceability, design-effectiveness, system/report, and UC6 refinement columns.

---

## Risk Scoring

**Inherent Risk Score** = Impact (1–5) × Likelihood (1–5) → range 1–25

**Default base scores by category (before appetite/source calibration):**

| Category | Impact | Likelihood | Score |
|----------|--------|------------|-------|
| Financial | 4 | 4 | 16 |
| Operational | 3 | 3 | 9 |
| IT | 4 | 3 | 12 |
| Compliance | 4 | 3 | 12 |
| Fraud | 5 | 4 | 20 |
| Strategic | 4 | 2 | 8 |

**Preliminary Residual Risk** = Inherent Score × (1 − Design Effectiveness Reduction)

| Control Design Effectiveness | Reduction |
|-----------------------------|-----------|
| Strong | 60% |
| Moderate | 35% |
| Weak | 15% |

**Final Residual Risk** = Inherent Score × (1 − Reliability Reduction)

| Control Reliability | Reduction |
|--------------------|-----------|
| Reliable | 60% |
| Partially Reliable | 35% |
| Unreliable | 15% |
| Not Assessed | 0% |

**Control reliability is downgraded to Unreliable** when IPE validation is `Weak` or `None`.
**Control reliability is set to Not Assessed** when an IT-dependent control has no entry in the IT matrix.
**Stage 3 may introduce UC6-derived IT risks** when IT dependencies or IPE validation are insufficient.

---

## Project Structure

```
RCM Builder/
├── tools/scripts/
│   ├── rcm_builder.py          # Stage 1 & 2 pipeline + CLI entry point
│   └── rcm_it_validator.py     # Stage 3 IT validation module
├── tests/
│   ├── fixtures/
│   │   ├── sample_input.json       # Sample use-case input
│   │   └── sample_it_matrix.json   # Sample IT dependency matrix
│   ├── test_rcm_builder.py         # Unit + integration tests (Stage 1, 2)
│   └── test_rcm_it_validator.py    # Unit tests (Stage 3)
├── outputs/
│   ├── schemas/
│   │   └── rcm-schema.json         # Three-stage JSON schema
│   ├── rcm_output.json             # Sample pipeline output (JSON)
│   └── rcm_output.md               # Sample pipeline output (Markdown)
├── prompts/audit-use-cases/
│   └── rcm-builder-agent.md        # System prompt for AI-assisted RCM building
├── regulatory/control-mappings/
│   └── rcm-frameworks.md           # COSO/COBIT reference tables
└── requirements.txt
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

29 tests covering: rich source ingestion, traceability, risk normalization, deduplication, risk-specific control design, appetite-aware scoring, IT dependency assessment, IPE evaluation, reliability downgrade logic, UC6-derived risk generation, full pipeline schema validation, and Markdown output.

---

## Using with an AI Agent

The file `prompts/audit-use-cases/rcm-builder-agent.md` contains a system prompt for an LLM-based RCM builder. It enforces:

- Canonical Cause→Event→Impact risk format
- No duplicate or orphan risks
- Mandatory control classification (Execution Type, Nature, Significance)
- IT dependency flagging for Stage 3 validation

The pipeline's JSON output is designed for downstream ingestion by an **Audit Work Program Agent** (Use Case 8).

---

## Reference

See `regulatory/control-mappings/rcm-frameworks.md` for full reference tables:
- COSO ERM risk categories
- Control execution types, nature, and significance criteria
- ITGC dependency types (COBIT)
- IPE reliability levels
- Inherent risk score matrix
- Residual risk reduction factors
