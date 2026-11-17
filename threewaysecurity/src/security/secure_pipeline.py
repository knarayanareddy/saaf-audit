"""Secure pipeline wrapper — integrates all security controls.

Wraps each pipeline step with OWASP security checks:
- Pre-intake: sanitization, schema validation, rate limiting
- Per-step: integrity verification, anomaly detection
- Post-pipeline: hash chain verification, file manifest
"""

import json
from pathlib import Path

import pandas as pd

from src.security.crypto import CryptoProvider
from src.security.input_sanitizer import InputSanitizer, SecurityViolation
from src.security.schema_validator import InvoiceSchema, validate_cross_references
from src.security.integrity import IntegrityChecker
from src.security.config_hardening import ConfigHardening
from src.security.anomaly_detector import AnomalyDetector
from src.security.rate_limiter import RateLimiter
from src.security.security_audit import SecurityAuditLogger


class SecurePipeline:
    """Wraps the entire pipeline with OWASP security controls."""

    def __init__(self, settings: dict) -> None:
        self.settings = settings
        self.root = Path(__file__).resolve().parents[2]
        self.output_dir = self.root / settings["output_dir"]
        self.invoice_dir = self.root / settings["invoice_dir"]

        # Initialize security components
        self.crypto = CryptoProvider()
        self.sanitizer = InputSanitizer()
        self.integrity = IntegrityChecker(self.crypto)
        self.hardening = ConfigHardening()
        self.anomaly = AnomalyDetector()
        self.rate_limiter = RateLimiter()
        self.security_log = SecurityAuditLogger(self.crypto)

    def run_config_hardening(self) -> bool:
        """Phase 0: Validate configuration against hard limits."""
        valid, warnings = self.hardening.validate_settings(self.settings)
        for w in warnings:
            self.security_log.log_event("CONFIG_OVERRIDE_ATTEMPT", "HIGH", w)
            print(f"    CONFIG WARNING: {w}")

        # Enforce tolerance ceiling
        original_tol = self.settings.get("price_tolerance_pct", 0.5)
        enforced_tol = self.hardening.enforce_tolerance(original_tol)
        if enforced_tol != original_tol:
            self.settings["price_tolerance_pct"] = enforced_tol

        return valid

    def run_pre_intake_security(self) -> dict:
        """Phase 1: Sanitize and validate all invoices before intake."""
        stats = {"sanitized": 0, "rejected": 0, "pdf_safe": 0, "pdf_rejected": 0,
                 "schema_valid": 0, "schema_invalid": 0, "duplicates": 0}

        json_files = sorted(self.invoice_dir.glob("INV-*.json"))

        # Rate limit check
        ok, msg = self.rate_limiter.check_batch_size(len(json_files))
        if not ok:
            self.security_log.log_event("RATE_LIMIT_EXCEEDED", "HIGH", msg)
            print(f"    RATE LIMIT: {msg}")

        for json_file in json_files:
            invoice_id = json_file.stem

            # Duplicate check
            ok, msg = self.rate_limiter.check_duplicate(invoice_id)
            if not ok:
                self.security_log.log_event("DUPLICATE_INVOICE", "HIGH", msg, invoice_id)
                stats["duplicates"] += 1
                continue

            # File size check
            ok, msg = self.rate_limiter.check_file_size(json_file)
            if not ok:
                self.security_log.log_event("RATE_LIMIT_EXCEEDED", "MEDIUM", msg, invoice_id)

            # Load and sanitize JSON
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                self.sanitizer.sanitize_invoice(data)
                stats["sanitized"] += 1
            except SecurityViolation as e:
                self.security_log.log_event(
                    "SECURITY_VIOLATION", "HIGH",
                    f"Input sanitization failed: {e}", invoice_id
                )
                stats["rejected"] += 1
                continue
            except Exception as e:
                self.security_log.log_event(
                    "SECURITY_VIOLATION", "MEDIUM",
                    f"JSON load failed: {e}", invoice_id
                )
                stats["rejected"] += 1
                continue

            # Schema validation
            try:
                InvoiceSchema(**{
                    k: data[k] for k in [
                        "invoice_id", "supplier_id", "part_id", "po_ref",
                        "quantity", "unit_price", "total_amount",
                        "invoice_date", "due_date", "iban", "vat_number"
                    ] if k in data
                })
                stats["schema_valid"] += 1
            except Exception as e:
                self.security_log.log_event(
                    "SCHEMA_VIOLATION", "MEDIUM",
                    f"Schema validation failed: {e}", invoice_id
                )
                stats["schema_invalid"] += 1

            # PDF safety check
            pdf_path = json_file.with_suffix(".pdf")
            if pdf_path.exists():
                safe, msg = self.sanitizer.validate_pdf(pdf_path)
                if safe:
                    stats["pdf_safe"] += 1
                else:
                    self.security_log.log_event(
                        "PDF_REJECTED", "HIGH",
                        f"PDF safety check failed: {msg}", invoice_id
                    )
                    stats["pdf_rejected"] += 1

        return stats

    def run_cross_reference_check(self) -> dict:
        """Phase 3: Verify IBAN, VAT, PO cross-references."""
        stats = {"checked": 0, "violations": 0}

        suppliers_path = self.output_dir / "01_suppliers.csv"
        po_path = self.output_dir / "04_purchase_orders.csv"
        parsed_path = self.output_dir / "parsed_records.json"

        if not all(p.exists() for p in [suppliers_path, po_path, parsed_path]):
            return stats

        df_suppliers = pd.read_csv(suppliers_path)
        df_po = pd.read_csv(po_path)

        with open(parsed_path, encoding="utf-8") as f:
            records = json.load(f)

        for record in records:
            if record.get("intake_status") != "PARSED":
                continue
            violations = validate_cross_references(record, df_suppliers, df_po)
            stats["checked"] += 1
            for v in violations:
                severity = "CRITICAL" if "IBAN" in v else "HIGH"
                self.security_log.log_event(
                    "IBAN_MISMATCH" if "IBAN" in v else "SECURITY_VIOLATION",
                    severity, v, record.get("invoice_id", "")
                )
                stats["violations"] += 1

        return stats

    def run_anomaly_detection(self) -> dict:
        """Phase 4: Statistical anomaly detection on matched records."""
        stats = {"checked": 0, "alerts": 0}

        matched_path = self.output_dir / "matched_contracts.json"
        if not matched_path.exists():
            return stats

        with open(matched_path, encoding="utf-8") as f:
            records = json.load(f)

        # Load reference data
        suppliers_df = pd.read_csv(self.output_dir / "01_suppliers.csv")
        contracts_df = pd.read_csv(self.output_dir / "03_contracts.csv")
        po_df = pd.read_csv(self.output_dir / "04_purchase_orders.csv")
        processed = set()

        for record in records:
            if record.get("contract_status") not in ("MATCHED", "CONTRACT_EXPIRED"):
                continue
            alerts = self.anomaly.run_all_checks(
                record, suppliers_df, contracts_df, po_df, processed
            )
            processed.add(record.get("invoice_id", ""))
            stats["checked"] += 1
            for alert in alerts:
                self.security_log.log_event(
                    "ANOMALY_DETECTED", alert.severity,
                    f"{alert.alert_type}: {alert.details}",
                    alert.invoice_id
                )
                stats["alerts"] += 1

        return stats

    def run_post_pipeline_verification(self) -> dict:
        """Phase 10: Verify audit trail hash chain and file manifest."""
        stats = {"chain_valid": False, "manifest_valid": False, "chain_violations": 0}

        # Verify audit trail hash chain
        trail_path = self.output_dir / "audit_trail.jsonl"
        if trail_path.exists():
            records = []
            with open(trail_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

            valid, violations = self.integrity.verify_chain(records)
            stats["chain_valid"] = valid
            stats["chain_violations"] = len(violations)
            if not valid:
                for v in violations[:5]:
                    self.security_log.log_event("INTEGRITY_FAILURE", "CRITICAL", v)

        # Verify manifest
        manifest_path = self.output_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            valid, violations = self.integrity.verify_manifest(manifest, self.output_dir)
            stats["manifest_valid"] = valid
            if not valid:
                for v in violations[:5]:
                    self.security_log.log_event("INTEGRITY_FAILURE", "HIGH", v)

        return stats

    def write_security_report(self) -> dict:
        """Write security events and print summary."""
        events_path = self.output_dir / "security_events.jsonl"
        count = self.security_log.write_events(events_path)
        summary = self.security_log.get_summary()

        print()
        print("  " + "=" * 50)
        print("  SECURITY SUMMARY")
        print("  " + "=" * 50)
        print(f"  Total security events: {summary['total']}")
        if summary.get("CRITICAL", 0) > 0:
            print(f"  CRITICAL: {summary['CRITICAL']}")
        if summary.get("HIGH", 0) > 0:
            print(f"  HIGH:     {summary['HIGH']}")
        if summary.get("MEDIUM", 0) > 0:
            print(f"  MEDIUM:   {summary['MEDIUM']}")
        if summary.get("LOW", 0) > 0:
            print(f"  LOW:      {summary['LOW']}")
        print(f"  Security events written to: security_events.jsonl")
        print("  " + "=" * 50)

        return summary
