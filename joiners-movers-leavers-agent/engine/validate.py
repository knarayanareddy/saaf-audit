"""Validate a findings draft against the model input of a run.

    python3 -m engine.validate runs/<stamp>                 # checks draft_agent.json (or draft.json)
    python3 -m engine.validate runs/<stamp> --draft my.json

Uses the same checks as the web UI: finding schema, valid ids, every cited identifier
present in model_input.json, every exception assessed and covered by a finding.
Exit code 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.findings import validate_draft
from engine.pseudonymise import allowed_references


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a JML findings draft")
    parser.add_argument("run_dir", help="run folder containing model_input.json")
    parser.add_argument("--draft", default=None, help="draft file (default: draft_agent.json, then draft.json)")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    payload = json.loads((run_dir / "model_input.json").read_text(encoding="utf-8"))
    candidates = [Path(args.draft)] if args.draft else [run_dir / "draft_agent.json", run_dir / "draft.json"]
    draft_path = next((p for p in candidates if p.exists()), None)
    if draft_path is None:
        sys.exit(f"No draft found in {run_dir} (looked for {', '.join(p.name for p in candidates)})")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))

    ids = [e["exception_id"] for e in payload["exceptions"]]
    result = validate_draft(draft, allowed_references(payload), ids)
    checks = result["checks"]
    print(f"{draft_path.name}: {checks['findings_kept']} of {checks['findings_received']} findings kept, "
          f"{checks['exceptions_assessed']}/{checks['exceptions_total']} exceptions assessed, "
          f"{checks['exceptions_covered']}/{checks['exceptions_total']} covered")
    for issue in checks["issues"]:
        print(f"  issue: {issue}")
    print("All checks passed." if checks["passed"] else "Checks failed. Fix the draft; do not add identifiers.")
    sys.exit(0 if checks["passed"] else 1)


if __name__ == "__main__":
    main()
