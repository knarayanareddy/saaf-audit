"""Command-line entry point: run the JML review over a sources file.

    python3 -m engine.cli                                  # sample data
    python3 -m engine.cli --sources sources.yaml           # your own exports
    python3 -m engine.cli --sources sources.yaml --draft   # also draft findings with Claude Code

Writes a run folder under runs/ with:
    review_local.json   full results, including names (stays on this machine)
    model_input.json    pseudonymised input, the only file a model should read
    summary.txt         short human-readable summary
    draft.json          findings draft (with --draft)
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from engine.jml_checks import public_review, run_review
from engine.pseudonymise import Pseudonymiser, build_payload
from engine.sources import load_sources

REPO_ROOT = Path(__file__).parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Joiners-movers-leavers access review")
    parser.add_argument("--sources", default=None, help="sources YAML (default: sources.sample.yaml)")
    parser.add_argument("--out", default=str(REPO_ROOT / "runs"), help="parent folder for the run output")
    parser.add_argument("--draft", action="store_true", help="draft findings with Claude Code (headless, no tools)")
    parser.add_argument("--lang", default="en", choices=["en", "nl"], help="language of the drafted findings")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    review = run_review(load_sources(Path(args.sources) if args.sources else None))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.out) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    pz = Pseudonymiser(review["_anon_map"], review["_people"])
    (run_dir / "review_local.json").write_text(json.dumps(public_review(review), indent=2, ensure_ascii=False),
                                               encoding="utf-8")
    (run_dir / "model_input.json").write_text(json.dumps(build_payload(review, pz), indent=2, ensure_ascii=False),
                                              encoding="utf-8")

    lines = [f"{review['review_name']}",
             f"Period {review['audit_period']['start']} to {review['audit_period']['end']}, "
             f"extracted {review['extraction_date']}, fingerprint {review['fingerprint']}", ""]
    for t in review["tests"]:
        lines.append(f"{t['id']:<3} {t['name']:<58} tested {t['tested']:>3}  exceptions {t['exceptions']}")
    lines.append("")
    for e in review["exceptions"]:
        lines.append(f"{e['id']} {e['test_id']} {e['risk_rating']:<6} {e['summary']}")
    summary = "\n".join(lines)
    (run_dir / "summary.txt").write_text(summary + "\n", encoding="utf-8")
    print(summary)

    if args.draft:
        from ai.claude_runner import draft_findings

        res = draft_findings(review, run_dir, language=args.lang)
        print(f"\nDraft: mode={res['mode']}, findings kept {res['checks']['findings_kept']}, "
              f"checks passed: {res['checks']['passed']}")
        for issue in res["checks"]["issues"]:
            print(f"  check: {issue}")
        for f in res["findings"]:
            print(f"  {f['id']} [{f['risk_rating']}] {pz.reveal(f['title'])}")
        print("\nDraft only. An auditor must review and sign off before anything is final.")
    print(f"\nRun folder: {run_dir}")


if __name__ == "__main__":
    main()
