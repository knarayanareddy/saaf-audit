# SAAF CUEC Crosscheck Agent

Automatically match Complementary User Entity Controls (CUECs) from a vendor assurance report (ISAE 3402 / SOC 2) to controls in your organization's own control documentation.

Built as part of the [SAAF Project](https://saafproject.com) — a co-creative initiative where IT and internal auditors from 45+ organizations build AI audit agents together.

## What it does

Give it two documents — a vendor's assurance report and your organization's control report. It reads both, extracts every CUEC from the vendor report, matches each one to the most relevant organizational control, and produces four deliverables:

1. **HTML report** — RAG status (Red / Amber / Green), summary statistics, and full match table — open directly in a browser
2. **CUEC match table** — every CUEC with its matched control reference, description, and rationale
3. **CSV export** — for import into Google Sheets or Excel
4. **Gap findings** — unmatched and partially matched CUECs as structured findings conforming to the [SAAF finding schema](https://saafproject.com)

## Why this matters

ISAE 3402 and SOC 2 reports include CUECs — controls that *your* organization must have in place for the vendor's assurance to be meaningful. Manually extracting and matching these across multiple vendor reports is time-consuming and error-prone. This agent automates the substantive matching so auditors can focus on reviewing and judging results rather than hunting through documents.

## Completeness check

Before running the crosscheck, the agent makes a separate, focused call to Claude to inventory every CUEC in the vendor report. After the crosscheck completes, it verifies that every CUEC identified in the pre-check was processed in the output. If any are missing, the agent logs an error with the specific CUEC IDs that were dropped. This guards against silent omissions in the AI output.

## Audit log and AI reasoning

Every run produces a `cuec_crosscheck.log` file alongside the other outputs. The log captures:

- **Input provenance** — absolute file paths and byte sizes of both input documents
- **System prompt version** — SHA-256 of the prompt used, so you can tell if the prompt changed between runs
- **API call metadata** — Anthropic message ID, model, stop reason, input/output token counts, and elapsed time for each call
- **Chain-of-thought reasoning** — Claude's reasoning prose (written before the structured JSON output) is captured verbatim at DEBUG level, giving auditors a traceable record of how each matching decision was reached
- **Per-match decisions** — CUEC ID, match status, org control reference, and rationale logged individually
- **Completeness check result** — PASSED / FAILED with a diff of missing or unexpected CUEC IDs

The console shows INFO-level progress. The log file captures everything at DEBUG level and is written to the same output directory as the other artefacts, so it can be included in the evidence package.

## Supported input formats

PDF, DOCX, TXT

## Setup

```bash
git clone https://github.com/SAAF-Project/CUEC_Crosscheck.git
cd CUEC_Crosscheck
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Usage

```bash
# Using the included sample inputs
python3 cuec_crosscheck.py \
  --vendor-report sample_inputs/vendor_soc2_excerpt.txt \
  --org-report sample_inputs/org_controls_excerpt.txt \
  --output-dir output

# With your own documents
python3 cuec_crosscheck.py \
  --vendor-report vendor-soc2-report.pdf \
  --org-report org-control-testing-q4-2025.pdf \
  --output-dir output/vendor-name
```

## Output files

| File | Format | Purpose |
|---|---|---|
| `report.html` | HTML | RAG status banner, stats, and full match table — open in browser |
| `cuec_matches.md` | Markdown | Full match table for review or documentation |
| `cuec_matches.csv` | CSV | Import into Google Sheets / Excel |
| `gap_findings.json` | JSON | Structured gap findings (SAAF finding schema) |
| `cuec_crosscheck.log` | Text | Full audit log incl. CoT reasoning (DEBUG) |

## RAG status

The HTML report shows an overall Red / Amber / Green status:

| Status | Condition |
|---|---|
| Red | One or more CUECs have no matching organizational control |
| Amber | One or more CUECs are only partially covered |
| Green | All CUECs are matched to organizational controls |

## Match statuses

| Status | Meaning |
|---|---|
| Matched | A control in the organizational report substantively covers the CUEC |
| Partial | A related control exists but does not fully cover the CUEC intent |
| No match | No matching control was found in the organizational report |

## Gap finding risk ratings

| Risk | Condition |
|---|---|
| High | CUEC has no matching control (No match) |
| Medium | CUEC is only partially covered (Partial) |

## Applicable standards

- **ISAE 3402 / ISAE 3000** — vendor assurance report (source of CUECs)
- **SOC 2 (AICPA AT-C 320)** — vendor assurance report (source of CUECs)
- **ISO 27001:2022 Annex A** — common basis for organizational controls

## Important notes

- The agent only references controls explicitly present in the provided documents. It cannot assess controls that exist but are undocumented.
- Determining whether a matched control is *sufficient* requires auditor judgement.
- The completeness check compares CUEC IDs by exact string match. If the pre-check and the crosscheck assign different IDs to the same control (which can happen when the source document has no explicit IDs), a false mismatch may be logged — review the log before treating a FAILED result as conclusive.
- Do not submit real client names, personal data, or sensitive financial figures to the API. Use anonymised or synthetic documents for testing.
- AI-assisted output. Results require auditor review before reliance.

## Sample inputs

`sample_inputs/` contains synthetic test documents for a fictional vendor (SynthCloud B.V.) and a fictional organization. No real audit evidence.

## SAAF Project

This agent is part of the [SAAF Project](https://saafproject.com) — a vendor-agnostic, open-source framework where auditors co-build AI audit agents. Contributions and feedback welcome.
