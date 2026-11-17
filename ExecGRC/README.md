# ExecSummary GRC Reporting Agent

Auditable MVP for Governance, Risk & Compliance reporting. The agent loads structured GRC datasets, normalizes controls and risks, identifies correlations between ineffective controls and elevated residual risks, and generates tactical and executive reports with traceability.

## What It Builds

- Deterministic GRC analysis engine for CSV, JSON and basic XLSX files.
- Tactical dashboard report for risk or department managers, including correlations and improvement measures.
- Executive dashboard report with strategic insights, risk impact and decision support.
- Static HTML dashboard with offline visualizations, including a risk matrix, process effectiveness and trend analysis.
- Append-only audit trail with hash chaining, source file hashes, configuration snapshot and generated artifact manifest.
- Prompt pack for the tactical and executive reporting agent.
- Synthetic sample dataset and unit tests.

## Quick Start

```bash
python3 tools/scripts/grc-board-reporting-agent.py \
  --input data/synthetic/grc_sample.csv \
  --output reports/demo \
  --run-id demo \
  --feedback "Management bevestigt dat vendor access recertificatie prioriteit heeft."
```

Generated files are written to `reports/demo/`:

- `tactical_report.html`
- `executive_report.html`
- `dashboard.html`
- `analysis_result.json`
- `audit_trail.ndjson`
- `audit_summary.md`
- `manifest.json`

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

## Configuration

Copy `.env.example` to `.env` for local settings. Secrets must stay in environment variables and are redacted in audit output.

Important variables:

- `EXEC_SUMMARY_HIGH_RISK_THRESHOLD`: residual risk score at which risks are treated as high.
- `EXEC_SUMMARY_CRITICAL_RISK_THRESHOLD`: residual risk score at which risks are treated as critical.
- `EXEC_SUMMARY_INEFFECTIVE_STATUSES`: comma-separated statuses treated as ineffective.
- `EXEC_SUMMARY_REQUIRE_HUMAN_APPROVAL`: marks reports as draft pending validation.
- `EXEC_SUMMARY_LLM_PROVIDER`: default `offline`; deterministic reporting works without an external API.

## Dataset Shape

The loader accepts a single file or a directory containing CSV, JSON or basic XLSX files. It recognizes common aliases for fields such as `record_type`, `control_id`, `risk_id`, `effectiveness`, `residual_risk_score`, `risk_rating`, `impact`, `likelihood`, `trend`, `department`, `process`, `framework`, `related_control_ids` and `related_risk_ids`.

Rows with control effectiveness fields are treated as controls. Rows with residual risk scores or risk ratings are treated as risks. Direct links are derived from `related_control_ids` and `related_risk_ids`; contextual links use shared process, department or framework.

## Auditability

Every run produces an append-only `audit_trail.ndjson` file. Each event contains:

- timestamp, run id, step name and action;
- redacted configuration and environment snapshot;
- source file hashes and record counts;
- rule decisions and thresholds used;
- generated artifacts and SHA-256 hashes;
- previous event hash and current event hash.

The hash chain makes later changes visible. `audit_summary.md` provides a readable overview for reviewers.
