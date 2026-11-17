"""Checks a guard report before the CLI turns it into an exit code.

A report is a claim by an earlier run. The gate does not take its ``verdict`` field at face value:
it recomputes the verdict from the report's own data, and refuses a report that may belong to another
run. Anything it cannot verify is NOT_ASSESSED, never success.

What this protects against: an empty or hand-written ``{"verdict": "PASS"}``, a PASS whose own data
contradicts it, and a stale report left behind by a run that crashed before writing. It is not a
signature: someone who forges a complete, consistent, fresh report is out of scope.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Tuple

from .guard import Verdict

__all__ = ["assess_report", "CLOCK_SKEW_SECONDS"]

CLOCK_SKEW_SECONDS = 60  # a report may be at most this far "in the future" (clocks differ)
_RANK = {Verdict.PASS: 0, Verdict.NOT_ASSESSED: 1, Verdict.FAIL: 2}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None  # a time without a zone cannot be compared


def assess_report(
    report: Any,
    *,
    max_age: Optional[float] = None,
    run_id: Optional[str] = None,
    min_coverage: Optional[float] = None,
    min_checks: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Tuple[Verdict, List[str], List[str]]:
    """Return ``(verdict, reasons, problems)``.

    ``reasons`` are why the verdict is not PASS (from the report and recomputed). ``problems`` are
    reasons to distrust the report itself (inconsistent, incomplete, stale, from another run); when
    there are any, the verdict is at least NOT_ASSESSED and ``--allow-not-assessed`` must not relax it.
    ``min_coverage`` / ``min_checks`` can only make the check stricter than the report's own thresholds.
    """
    if not isinstance(report, Mapping):
        return Verdict.NOT_ASSESSED, [], ["the report is not a JSON object"]
    try:
        claimed = Verdict(report["verdict"])
    except (KeyError, ValueError, TypeError):
        return Verdict.NOT_ASSESSED, [], [f"missing or unknown verdict: {report.get('verdict')!r}"]

    problems: List[str] = []
    reasons: List[str] = []

    # -- the data the verdict has to follow from ---------------------------------------------------------
    failed = report.get("checks_failed")
    if not isinstance(failed, list):
        problems.append("'checks_failed' is missing or not a list")
        failed = []
    listed = report.get("not_assessed_reasons")
    if not isinstance(listed, list):
        problems.append("'not_assessed_reasons' is missing or not a list")
        listed = []
    checks_run = report.get("checks_run")
    if not _is_count(checks_run):
        problems.append("'checks_run' is missing or not a count")
    items_total = report.get("items_total")
    if not _is_count(items_total):
        problems.append("'items_total' is missing or not a count")
    coverage = report.get("coverage")
    if not _is_number(coverage) or not 0 <= coverage <= 1:
        problems.append("'coverage' is missing or not a number between 0 and 1")

    stated_cov = report.get("min_coverage")
    stated_chk = report.get("min_checks")
    need_cov = max(float(stated_cov) if _is_number(stated_cov) else 1.0, min_coverage or 0.0)
    need_chk = max(stated_chk if _is_count(stated_chk) else 1, min_checks or 0)

    # -- recompute the verdict ---------------------------------------------------------------------------
    if failed:
        recomputed = Verdict.FAIL
    else:
        recomputed = Verdict.PASS
        reasons.extend(str(r) for r in listed)
        if listed:
            recomputed = Verdict.NOT_ASSESSED
        if _is_count(items_total) and items_total < 1:
            reasons.append("no input items were assessed")
            recomputed = Verdict.NOT_ASSESSED
        if _is_number(coverage) and coverage < need_cov:
            reasons.append(f"coverage {coverage:.0%} is below the required {need_cov:.0%}")
            recomputed = Verdict.NOT_ASSESSED
        if _is_count(checks_run) and checks_run < need_chk:
            reasons.append(f"only {checks_run} check(s) ran, at least {need_chk} required")
            recomputed = Verdict.NOT_ASSESSED
    if problems and recomputed is Verdict.PASS:
        recomputed = Verdict.NOT_ASSESSED

    if claimed is Verdict.PASS and recomputed is not Verdict.PASS:
        problems.append(f"the report says PASS, but its own data says {recomputed.value}")

    # -- is this the report of the run we are gating? ------------------------------------------------------
    if run_id is not None and report.get("run_id") != run_id:
        problems.append(f"the report belongs to another run (run_id {report.get('run_id')!r}, expected {run_id!r})")
    if max_age is not None:
        written = _parse_time(report.get("generated_at"))
        if written is None:
            problems.append("'generated_at' is missing or not a timestamp with a time zone, so its age is unknown")
        else:
            age = ((now or datetime.now(timezone.utc)) - written).total_seconds()
            if age > max_age:
                problems.append(f"the report is {age:.0f} s old, more than the allowed {max_age:g} s")
            elif age < -CLOCK_SKEW_SECONDS:
                problems.append("the report is dated in the future")

    reasons = list(dict.fromkeys(reasons))  # the report's own reasons and the recomputed ones can overlap
    final = max(claimed, recomputed, key=lambda v: _RANK[v])
    if problems and final is Verdict.PASS:
        final = Verdict.NOT_ASSESSED
    return final, reasons, problems
