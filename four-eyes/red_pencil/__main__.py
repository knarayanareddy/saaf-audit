"""Command line: python -m red_pencil PATH [PATH ...]"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from . import __version__
from .rules import RULES, SEVERITY_ORDER
from .scanner import ScanResult, scan

RISK_RATING = {"high": "High", "medium": "Medium", "low": "Low"}
SAAF_COLUMNS = ["title", "repo", "risk_rating", "observation", "recommendation", "verified", "team"]


def _text_report(results: list[ScanResult]) -> str:
    out = io.StringIO()
    for r in results:
        out.write(f"Red Pencil {__version__}: {r.repo}  ({r.files_scanned} files scanned)\n")
        if not r.findings:
            out.write("  no findings\n")
        for f in r.findings:
            out.write(
                f"  {f.rule.severity.upper():<7}{f.rule.id} {f.rule.name}  {f.path}:{f.line}\n"
                f"         {f.rule.title}: {f.detail}\n"
                f"         fix: {f.rule.fix}\n"
            )
        for path, reason in r.skipped:
            out.write(f"  skipped {path}: {reason}\n")
        out.write("\n")
    return out.getvalue()


def _json_report(results: list[ScanResult]) -> str:
    payload = {
        "tool": "red-pencil",
        "version": __version__,
        "results": [
            {
                "repo": r.repo,
                "root": r.root,
                "files_scanned": r.files_scanned,
                "skipped": [{"path": p, "reason": why} for p, why in r.skipped],
                "findings": [
                    {
                        "rule": f.rule.id,
                        "name": f.rule.name,
                        "severity": f.rule.severity,
                        "path": f.path,
                        "line": f.line,
                        "title": f.rule.title,
                        "detail": f.detail,
                        "fix": f.rule.fix,
                    }
                    for f in r.findings
                ],
            }
            for r in results
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def _saaf_csv(results: list[ScanResult], team: str) -> str:
    """Rows in the SAAF Security Challenge hand-in format.

    `verified` is always "no": a tool found it, a person must confirm it.
    """
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(SAAF_COLUMNS)
    for r in results:
        for f in r.findings:
            writer.writerow(
                [
                    f"{f.rule.title} in {f.path}",
                    r.repo,
                    RISK_RATING[f.rule.severity],
                    f"{f.path}:{f.line}: {f.detail}. {f.rule.why} "
                    f"Found by Red Pencil rule {f.rule.id} ({f.rule.name}).",
                    f.rule.fix,
                    "no",
                    team,
                ]
            )
    return out.getvalue()


def _rules_table() -> str:
    lines = [f"{'ID':<6} {'SEVERITY':<8} {'NAME':<28} SEEN IN"]
    for rule in RULES.values():
        lines.append(f"{rule.id:<6} {rule.severity:<8} {rule.name:<28} {rule.seen_in}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="red-pencil",
        description="Mark unsafe output and prompt-handling patterns in SAAF agent repos.",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="Folders or files to scan")
    parser.add_argument("--format", choices=["text", "json", "saaf-csv"], default="text")
    parser.add_argument(
        "--fail-on",
        choices=["high", "medium", "low", "none"],
        default="high",
        help="Lowest severity that makes the exit code 1 (default: high)",
    )
    parser.add_argument("--repo-name", help="Repo name to report (default: folder name; one path only)")
    parser.add_argument("--team", default="", help="Team name for --format saaf-csv")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="Skip files whose relative path matches, e.g. 'tests/*'")
    parser.add_argument("--output", type=Path, help="Write the report to this file (UTF-8)")
    parser.add_argument("--list-rules", action="store_true", help="Show the rules and exit")
    parser.add_argument("--version", action="version", version=f"red-pencil {__version__}")
    args = parser.parse_args(argv)

    if args.list_rules:
        sys.stdout.write(_rules_table())
        return 0
    if not args.paths:
        parser.error("give at least one folder or file to scan")
    if args.repo_name and len(args.paths) > 1:
        parser.error("--repo-name works with one path only")
    missing = [str(p) for p in args.paths if not p.exists()]
    if missing:
        parser.error(f"not found: {', '.join(missing)}")

    results = [scan(p, args.exclude, args.repo_name) for p in args.paths]

    if args.format == "json":
        report = _json_report(results)
    elif args.format == "saaf-csv":
        report = _saaf_csv(results, args.team)
    else:
        report = _text_report(results)

    if args.output:
        # Written directly as UTF-8: shell redirection on Windows PowerShell 5.1
        # would produce UTF-16, which the SAAF hand-in does not accept.
        args.output.write_text(report, encoding="utf-8", newline="")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(report)

    findings = [f for r in results for f in r.findings]
    counts = {s: sum(f.rule.severity == s for f in findings) for s in ("high", "medium", "low")}
    failing = args.fail_on != "none" and any(
        SEVERITY_ORDER[f.rule.severity] >= SEVERITY_ORDER[args.fail_on] for f in findings
    )
    sys.stderr.write(
        f"red-pencil: {len(findings)} findings ({counts['high']} high, {counts['medium']} medium, "
        f"{counts['low']} low) in {len(results)} path(s); fail-on {args.fail_on}: "
        f"{'FAIL' if failing else 'pass'}\n"
    )
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
