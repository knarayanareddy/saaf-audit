"""Command line: ``black-knight gate REPORT.json`` and ``black-knight demo`` (also ``no-silent-pass``).

Exit codes: 0 PASS, 1 FAIL, 2 NOT_ASSESSED. A missing, unreadable, malformed, inconsistent or stale report
is NOT_ASSESSED (2), never success.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .gate import assess_report
from .guard import Verdict


def gate(
    path: str,
    allow_not_assessed: bool = False,
    max_age: Optional[float] = None,
    run_id: Optional[str] = None,
    min_coverage: Optional[float] = None,
    min_checks: Optional[int] = None,
) -> int:
    """Exit code for a guard report. The report's own ``verdict`` is checked against its data first."""
    try:
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"NOT_ASSESSED: cannot read a valid guard report from {path}: {e}", file=sys.stderr)
        return Verdict.NOT_ASSESSED.exit_code
    verdict, reasons, problems = assess_report(
        report, max_age=max_age, run_id=run_id, min_coverage=min_coverage, min_checks=min_checks
    )
    if isinstance(report, dict):
        print(f"{report.get('guard', '?')}: {verdict.value} (coverage {report.get('coverage', '?')})")
    else:
        print(f"?: {verdict.value}")
    for r in reasons:
        print(f"  - {r}")
    for pr in problems:
        print(f"  ! {pr}")
    failed = report.get("checks_failed") if isinstance(report, dict) else None
    for c in failed if isinstance(failed, list) else []:
        if isinstance(c, dict):
            print(f"  x {c.get('name')} {c.get('item') or ''} {c.get('detail') or ''}".rstrip())
    # A report that cannot be trusted is never relaxed: --allow-not-assessed is for "nothing was assessed".
    if verdict is Verdict.NOT_ASSESSED and allow_not_assessed and not problems:
        return 0
    return verdict.exit_code


def demo() -> int:
    from .adapters import manifests, standalone, three_way_match as twm

    po = {"A1": {"qty": 10, "price": "5.00"}}
    grn = {"A1": 10}
    decoy = [{"sku": "A1", "quantity": "10", "quantity_billed": "13",
              "unit_price": "5.00", "price": "6.50"}]
    print("1. Invoice with decoy columns (billed 13 x 6.50, decoys say 10 x 5.00)")
    print("   naive first-alias logic :", twm.naive_match(po, grn, decoy))
    print("   Black Knight            :", twm.assess_invoice(po, grn, decoy).verdict().value)

    print("2. Repo with no recognisable LLM client and one unparsable file")
    g = standalone.assess_repo([("agent.py", True), ("broken.py", False)], [])
    print("   naive 'no signals = yes' : yes")
    print("   Black Knight             :", standalone.label(g))

    print("3. Manifest fetch fails with HTTP 403")
    g = manifests.assess_fetches([{"repo": "org/agent", "status": 403, "body": None}])
    print("   naive seed fallback      : green build")
    print("   Black Knight             :", g.verdict().value)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="black-knight", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate", help="turn a guard report into an exit code for CI")
    g.add_argument("report")
    g.add_argument("--allow-not-assessed", action="store_true",
                   help="treat NOT_ASSESSED as success (reasons are still printed); never applies to a report "
                        "that is inconsistent, stale or from another run")
    g.add_argument("--max-age", type=float, metavar="SECONDS",
                   help="refuse a report older than this (or without a timestamp)")
    g.add_argument("--run-id", default=os.environ.get("NO_SILENT_PASS_RUN_ID"),
                   help="refuse a report from another run (default: $NO_SILENT_PASS_RUN_ID)")
    g.add_argument("--min-coverage", type=float, help="require at least this coverage, whatever the report says")
    g.add_argument("--min-checks", type=int, help="require at least this many checks, whatever the report says")
    sub.add_parser("demo", help="show the fail-open vs fail-closed difference")
    args = p.parse_args(argv)
    if args.cmd == "gate":
        return gate(args.report, args.allow_not_assessed, args.max_age, args.run_id, args.min_coverage, args.min_checks)
    return demo()


if __name__ == "__main__":
    sys.exit(main())
