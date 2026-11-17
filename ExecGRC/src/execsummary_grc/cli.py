from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analysis import analyze_dataset
from .audit import AuditTrail
from .config import Settings, load_reporting_profile, redacted_env_snapshot
from .dashboard import write_dashboard
from .io import load_records, normalize_dataset, sha256_file
from .reports import write_reports


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    run_id = args.run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    settings = Settings.from_env(args.env_file)
    output_dir = args.output or Path(settings.default_output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    audit = AuditTrail(output_dir=output_dir, run_id=run_id, hash_chain=settings.audit_hash_chain)
    profile = load_reporting_profile(args.profile, args.profile_name)
    feedback = _load_feedback(args)

    try:
        audit.record(
            "configuration_loaded",
            "Loaded environment, thresholds and reporting profile.",
            inputs={"environment": redacted_env_snapshot(), "profile_path": str(args.profile)},
            outputs={"settings": settings.public_dict(), "profile": profile},
            decision={
                "llm_mode": settings.llm_provider,
                "note": "The MVP uses deterministic analysis by default; no external API call is required.",
            },
        )

        raw_records, source_files = load_records(args.input)
        audit.record(
            "source_data_loaded",
            "Loaded structured GRC records from input path.",
            inputs={"input_path": str(args.input)},
            outputs={"records_loaded": len(raw_records), "source_files": source_files},
        )

        dataset = normalize_dataset(raw_records, source_files)
        audit.record(
            "data_normalized",
            "Normalized source records into controls and risks.",
            outputs={
                "controls": len(dataset.controls),
                "risks": len(dataset.risks),
                "skipped_records": len(dataset.skipped_records),
            },
            decision={
                "typing_rules": [
                    "Rows with control effectiveness fields are controls.",
                    "Rows with residual risk scores or risk ratings are risks.",
                    "Direct links use related_control_ids and related_risk_ids.",
                ]
            },
        )

        analysis = analyze_dataset(dataset, settings)
        audit.record(
            "analysis_completed",
            "Applied deterministic risk-control correlation rules.",
            outputs={
                "posture": analysis.posture,
                "findings": len(analysis.findings),
                "metrics": analysis.metrics,
            },
            decision={
                "high_risk_threshold": settings.high_risk_threshold,
                "critical_risk_threshold": settings.critical_risk_threshold,
                "ineffective_statuses": sorted(settings.ineffective_statuses),
            },
        )

        report_paths = write_reports(output_dir, dataset, analysis, settings, profile, run_id, feedback)
        audit.record(
            "reports_generated",
            "Generated tactical and executive reports with traceability.",
            outputs={name: str(path) for name, path in report_paths.items()},
            artifacts=[str(path.name) for path in report_paths.values()],
        )

        dashboard_path = write_dashboard(output_dir, analysis, run_id)
        audit.record(
            "dashboard_generated",
            "Generated static dashboard with offline visualizations.",
            outputs={"dashboard": str(dashboard_path)},
            artifacts=[dashboard_path.name],
        )

        audit.record(
            "manifest_prepared",
            "Prepared final manifest after report generation.",
            outputs={"artifact_count": 7},
            artifacts=["manifest.json"],
        )
        audit_summary_path = audit.write_summary()
        manifest_path = _write_manifest(
            output_dir,
            run_id,
            audit,
            [
                *report_paths.values(),
                dashboard_path,
                audit.path,
                audit_summary_path,
            ],
        )

        print(f"Run complete: {run_id}")
        print(f"Output directory: {output_dir}")
        print(f"Tactical report: {report_paths['tactical_report']}")
        print(f"Executive report: {report_paths['executive_report']}")
        print(f"Dashboard: {dashboard_path}")
        print(f"Audit trail: {audit.path}")
        print(f"Manifest: {manifest_path}")
        return 0
    except Exception as exc:  # pragma: no cover - defensive CLI reporting
        audit.record(
            "run_failed",
            "Execution failed before completion.",
            outputs={"error_type": type(exc).__name__, "error": str(exc)},
        )
        audit.write_summary()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate auditable tactical and executive GRC reports from structured datasets."
    )
    parser.add_argument("--input", required=True, type=Path, help="CSV, JSON, XLSX file or directory to analyze.")
    parser.add_argument("--output", type=Path, help="Output directory. Defaults to EXEC_SUMMARY_DEFAULT_OUTPUT_DIR/run-id.")
    parser.add_argument("--run-id", help="Stable identifier for this analysis run.")
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="Optional .env file to load.")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("config/reporting_profiles.json"),
        help="Reporting profile JSON file.",
    )
    parser.add_argument("--profile-name", default="default", help="Profile name inside the profile JSON file.")
    parser.add_argument("--feedback", default="", help="Human feedback or context to include in reports.")
    parser.add_argument("--feedback-file", type=Path, help="File containing human feedback or context.")
    return parser


def _load_feedback(args: argparse.Namespace) -> str:
    feedback = args.feedback or ""
    if args.feedback_file:
        feedback_from_file = args.feedback_file.read_text(encoding="utf-8").strip()
        feedback = "\n\n".join(part for part in [feedback, feedback_from_file] if part)
    return feedback.strip()


def _write_manifest(output_dir: Path, run_id: str, audit: AuditTrail, artifacts: list[Path]) -> Path:
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "final_audit_hash": audit.current_hash,
        "artifacts": [],
        "note": "Manifest is written last and therefore does not include its own hash.",
    }
    for path in artifacts:
        if not path.exists():
            continue
        manifest["artifacts"].append(
            {
                "path": path.relative_to(output_dir).as_posix() if path.is_relative_to(output_dir) else str(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path
