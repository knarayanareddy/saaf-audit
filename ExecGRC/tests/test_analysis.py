from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execsummary_grc.analysis import analyze_dataset  # noqa: E402
from execsummary_grc.audit import AuditTrail  # noqa: E402
from execsummary_grc.config import Settings  # noqa: E402
from execsummary_grc.io import load_records, normalize_dataset  # noqa: E402


def test_settings() -> Settings:
    return Settings(
        environment="test",
        report_language="nl",
        log_level="INFO",
        high_risk_threshold=15.0,
        critical_risk_threshold=20.0,
        risk_score_max=25.0,
        ineffective_statuses={"ineffective", "partially effective", "not effective", "onvoldoende"},
        require_human_approval=True,
        audit_hash_chain=True,
        default_output_dir="reports",
        llm_provider="offline",
    )


class AnalysisTests(unittest.TestCase):
    def test_sample_dataset_normalizes_controls_and_risks(self) -> None:
        records, source_files = load_records(ROOT / "data/synthetic/grc_sample.csv")
        dataset = normalize_dataset(records, source_files)

        self.assertEqual(len(dataset.controls), 5)
        self.assertEqual(len(dataset.risks), 5)
        self.assertEqual(dataset.skipped_records, [])
        self.assertEqual(source_files[0]["records_loaded"], 10)
        self.assertEqual(dataset.controls[0].process, "Identity and Access")
        self.assertEqual(dataset.controls[0].risk_ids, ["R-001", "R-004"])
        self.assertEqual(dataset.risks[0].impact, 4.0)
        self.assertEqual(dataset.risks[0].likelihood, 4.0)

    def test_analysis_detects_critical_posture_and_traceability(self) -> None:
        records, source_files = load_records(ROOT / "data/synthetic/grc_sample.csv")
        dataset = normalize_dataset(records, source_files)
        analysis = analyze_dataset(dataset, test_settings())

        self.assertEqual(analysis.posture, "Critical")
        self.assertEqual(analysis.metrics["high_risks"], 3)
        self.assertEqual(analysis.metrics["critical_risks"], 1)
        self.assertGreaterEqual(analysis.metrics["direct_correlations"], 3)
        self.assertIn("risk_matrix", analysis.metrics)
        self.assertIn("process_effectiveness", analysis.metrics)
        self.assertIn("trend_counts", analysis.metrics)
        self.assertIn("risk_impact_by_process", analysis.metrics)
        self.assertTrue(any(row["source_refs"] for row in analysis.traceability))
        self.assertTrue(any(finding.severity == "Critical" for finding in analysis.findings))


class AuditTests(unittest.TestCase):
    def test_audit_events_are_hash_chained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditTrail(Path(tmp), "unit-test", hash_chain=True)
            first = audit.record("one", "first step")
            second = audit.record("two", "second step", outputs={"count": 1})

            self.assertEqual(second["previous_hash"], first["event_hash"])
            lines = [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[1]["previous_hash"], lines[0]["event_hash"])


if __name__ == "__main__":
    unittest.main()
