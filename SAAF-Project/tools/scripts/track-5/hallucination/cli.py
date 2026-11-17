"""
Hallucination Detection — CLI Entry Point
=========================================

Usage:
    python -m hallucination <finding.json>
    python -m hallucination <finding.json> --output annotated.json
    python -m hallucination <finding.json> --quiet

Exit codes:
    0 — OK (regardless of risk level)
    1 — usage error (bad args, missing file)
    2 — environment error (API key missing)
    3 — runtime error (API failure, malformed response)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .annotator import check_finding
from .finding_io import load_finding, save_finding


def main(argv: list[str] | None = None) -> int:
    """Parse args, run the pipeline, print a summary."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        finding = load_finding(args.finding_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        annotated = check_finding(finding)
    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — CLI boundary
        print(f"ERROR during processing: {type(e).__name__}: {e}", file=sys.stderr)
        return 3

    output_path = args.output or args.finding_path.with_name(
        args.finding_path.stem + "_checked" + args.finding_path.suffix
    )
    save_finding(annotated, output_path)

    if not args.quiet:
        check = annotated["hallucination_check"]
        print(f"Finding:      {annotated.get('id', '?')}")
        print(f"Risk:         {check['overall_risk']}  (warning={check['warning']})")
        print(f"Claims:       {check['claims_checked']} total, {check['claims_verifiable']} verifiable")
        print(f"Flagged:      {len(check['flagged_claims'])}")
        print(f"Unverified:   {len(check['unverified_claims'])}")
        print(f"Summary:      {check['summary']}")
        print(f"Written to:   {output_path}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hallucination",
        description="Run hallucination detection on a SAAF audit finding.",
    )
    parser.add_argument("finding_path", type=Path, help="Path to a finding JSON file.")
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Where to write the annotated finding. Default: <input>_checked.json next to input.",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress stdout summary.")
    return parser


if __name__ == "__main__":
    sys.exit(main())
