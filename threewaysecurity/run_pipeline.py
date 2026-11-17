"""ASML Procurement Audit Agent — Secure Pipeline Runner.

Runs all 14 steps sequentially with integrated OWASP security controls.
Usage: python run_pipeline.py
"""

import io
import sys
import time
import traceback
from pathlib import Path

import yaml

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def load_settings() -> dict:
    """Load settings from config/settings.yaml."""
    root = Path(__file__).resolve().parent
    with open(root / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    """Run all pipeline steps with security controls."""
    settings = load_settings()
    seed = settings["seed"]

    print("=" * 60)
    print("  ASML Procurement Audit Agent — Secure Pipeline")
    print("  OWASP Top 10 Security Controls Enabled")
    print("=" * 60)
    print()

    # Import modules
    from src.generators import gen_stamdata, gen_transactions, gen_invoices, gen_labels
    from src.agent import (
        intake_agent, contract_agent, threeway_agent,
        decision_agent, payment_agent, escalation_agent, audit_logger,
    )
    from src.evaluator import evaluate
    from src.security.secure_pipeline import SecurePipeline

    # Initialize security wrapper
    secure = SecurePipeline(settings)

    steps: list[tuple[str, str, object]] = [
        # Data generation
        ("gen_stamdata", "Master data generation", lambda s: gen_stamdata.generate_all(s)),
        ("gen_transactions", "Transaction generation", lambda s: gen_transactions.generate_all(s)),
        ("gen_invoices", "Invoice generation (JSON + PDF)", lambda s: gen_invoices.generate_all(s)),
        ("gen_labels", "Ground truth label generation", lambda s: gen_labels.generate_all(s)),

        # Security pre-check
        ("config_hardening", "Config hardening (OWASP A05)",
         lambda s: secure.run_config_hardening()),
        ("pre_intake_security", "Input sanitization & schema validation (OWASP A03/A04)",
         lambda s: secure.run_pre_intake_security()),

        # Agent steps with security
        ("intake_agent", "Invoice intake (Step 01)", lambda s: intake_agent.run(s)),
        ("cross_ref_check", "Cross-reference verification (OWASP A07)",
         lambda s: secure.run_cross_reference_check()),
        ("contract_agent", "Contract matching (Step 02)", lambda s: contract_agent.run(s)),
        ("anomaly_detection", "Anomaly detection (OWASP A07)",
         lambda s: secure.run_anomaly_detection()),
        ("threeway_agent", "Three-way match (Step 03)", lambda s: threeway_agent.run(s)),
        ("decision_agent", "Decision engine (Step 04)", lambda s: decision_agent.run(s)),
        ("payment_agent", "Payment instruction (Step 05)", lambda s: payment_agent.run(s)),
        ("escalation_agent", "Escalation routing (Step 06)", lambda s: escalation_agent.run(s)),
        ("audit_logger", "Audit trail — hash-chained (Step 07)", lambda s: audit_logger.run(s)),
        ("evaluate", "Evaluation vs. ground truth", lambda s: evaluate.run(s)),

        # Post-pipeline security verification
        ("post_verification", "Hash chain & manifest verification (OWASP A08)",
         lambda s: secure.run_post_pipeline_verification()),
        ("security_report", "Security summary report (OWASP A09)",
         lambda s: secure.write_security_report()),
    ]

    results: list[tuple[str, float, bool, str]] = []
    total_start = time.time()

    for i, (name, description, func) in enumerate(steps, 1):
        print(f"\u25b6 Step {i:2d} \u2014 {description} started...")
        step_start = time.time()
        try:
            func(settings)
            elapsed = time.time() - step_start
            results.append((name, elapsed, True, ""))
            print(f"  \u2713 Completed in {elapsed:.1f}s")
            print()
        except Exception as e:
            elapsed = time.time() - step_start
            results.append((name, elapsed, False, str(e)))
            print(f"  \u2717 FAILED in {elapsed:.1f}s")
            print()
            traceback.print_exc()
            print()
            print(f"Pipeline stopped at step {i} ({name})")
            sys.exit(1)

    total_elapsed = time.time() - total_start

    # Print summary
    print()
    print("=" * 60)
    print("  ASML Audit Agent Pipeline \u2014 Completed")
    print("  Security-by-Design | OWASP Top 10 Mitigated")
    print("=" * 60)

    for i, (name, elapsed, success, _) in enumerate(results, 1):
        status = "\u2713" if success else "\u2717"
        print(f"  Step {i:2d}  {name:<25s} {elapsed:>5.1f}s  {status}")

    print("  " + "\u2500" * 56)
    print(f"  Total: {total_elapsed:.1f}s  |  Seed: {seed}")
    print("=" * 60)

    # Print file summary
    print()
    print("Generated files:")
    root = Path(__file__).resolve().parent
    output_dir = root / settings["output_dir"]
    invoice_dir = root / settings["invoice_dir"]
    label_dir = root / settings["label_dir"]

    for f in sorted(output_dir.glob("*.csv")) + sorted(output_dir.glob("*.json")) + sorted(output_dir.glob("*.jsonl")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.relative_to(root)}  ({size_kb:.1f} KB)")

    n_json = len(list(invoice_dir.glob("*.json")))
    n_pdf = len(list(invoice_dir.glob("*.pdf")))
    print(f"  {invoice_dir.relative_to(root)}/  ({n_json} JSON + {n_pdf} PDF files)")

    for f in sorted(label_dir.glob("*.csv")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.relative_to(root)}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
