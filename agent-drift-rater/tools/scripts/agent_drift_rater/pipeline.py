"""Rate one unit end to end: signals -> mandate cross-check -> optional Claude pass -> score.

Kept separate from cli.py so selftest can call it directly.
"""

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from . import checks, config, mandate as mandate_mod, outputs, scoring
from .inventory import Unit
from .judge import MockJudge, build_payload, validate_and_merge

logger = logging.getLogger(__name__)


def _excerpts(unit: Unit, sigs: checks.UnitSignals) -> List[Tuple[str, int, str]]:
    windows: List[Tuple[str, int, str]] = []
    budget = 0
    for s in sigs.signals:
        if s.line <= 1 or s.path not in unit.files:
            continue
        lines = unit.files[s.path].splitlines()
        lo = max(0, s.line - 1 - config.EXCERPT_CONTEXT_LINES)
        hi = min(len(lines), s.line + config.EXCERPT_CONTEXT_LINES)
        window = "\n".join(lines[lo:hi])
        budget += hi - lo
        if budget > config.MAX_EXCERPT_LINES_PER_UNIT:
            break
        windows.append((s.path, s.line, window))
    return windows


def _prompt_texts(unit: Unit) -> List[Tuple[str, str]]:
    out = []
    for path, text in unit.files.items():
        if path.lower().endswith((".md", ".txt", ".prompt")) and "prompt" in path.lower():
            out.append((path, text))
    return out[:4]


def _mandate_cross_check(mandate: Optional[mandate_mod.Mandate], sigs: checks.UnitSignals,
                         action_capable: bool) -> Tuple[int, List[str]]:
    """Return (prompt_only_rule_count, refs). A rule is prompt-only when no code guard covers it."""
    if not mandate or not mandate.hard_rules:
        return 0, []
    has_code_enforcement = any(
        s.dimension == "C1" and s.rule in ("guard_call", "guard_test", "allowlist")
        for s in sigs.signals)
    if has_code_enforcement:
        return 0, []
    if not action_capable:
        return len(mandate.hard_rules), [r["source"] for r in mandate.hard_rules[:3]]
    return len(mandate.hard_rules), [r["source"] for r in mandate.hard_rules[:3]]


def rate_unit(unit: Unit, mandate: Optional[mandate_mod.Mandate], judge, run_log,
              truncated: bool = False) -> Tuple[scoring.UnitRating, List[Dict[str, Any]], List[Dict[str, str]]]:
    sigs = checks.run_checks(unit.files)
    prompt_only, rule_refs = _mandate_cross_check(mandate, sigs, sigs.action_capable)

    baseline = {dim: scoring._score_dimension(dim, sigs, unit.coverage, sigs.action_capable).score
                for dim in scoring.DRIVERS + scoring.CONTROLS}
    llm_ran = False
    llm_notes: List[str] = []
    injections: List[str] = []
    merged: Optional[Dict[str, int]] = None
    if judge is not None:
        payload = build_payload(unit.unit_id, _mandate_summary(mandate), sigs,
                                _excerpts(unit, sigs), _prompt_texts(unit))
        valid_refs = {f"{s.path}#L{s.line}" for s in sigs.signals} | set(unit.files)
        try:
            raw = judge.judge(unit.unit_id, payload, baseline)
            merged, llm_notes, injections = validate_and_merge(raw, baseline, valid_refs)
            llm_ran = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s: judge failed (%s)", unit.unit_id, exc)

    status = mandate.status if mandate else "none"
    rating = scoring.score_unit(
        unit.unit_id, unit.classification, unit.coverage, sigs,
        mandate_status=status, prompt_only_rules=prompt_only, llm_ran=llm_ran,
        truncated=truncated, notes=(mandate.mandate_gaps if mandate else ["No mandate profile"]) + llm_notes,
        llm_scores=merged)
    if injections:
        rating.notes.append("injection attempts reported: " + "; ".join(injections))

    injection_refs = sorted({f"{s.path}#L{s.line}" for s in sigs.by_dim("INJ")})
    findings = outputs.build_findings(rating, unit.repo.name, None, rule_refs, injection_refs)
    advice = outputs.build_advice(rating)
    if run_log:
        run_log.event("unit_rated", unit=unit.unit_id, residual=rating.residual,
                      inherent=rating.inherent, controls=rating.control_strength,
                      coverage=unit.coverage, llm=llm_ran)
    return rating, findings, advice


def _mandate_summary(mandate: Optional[mandate_mod.Mandate]) -> str:
    if not mandate:
        return "No mandate profile available."
    rules = "; ".join(r["rule"] for r in mandate.hard_rules[:6]) or "(none documented)"
    return (f"Purpose: {mandate.purpose or '(unknown)'}\nAutonomy: {mandate.autonomy_level}\n"
            f"Hard rules: {rules}\nApproval points: {len(mandate.human_approval_points)}\n"
            f"Status: {mandate.status}")


def unit_report(unit: Unit, rating: scoring.UnitRating, findings: List[Dict[str, Any]],
                advice: List[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "unit_id": unit.unit_id, "repo": unit.repo.name, "unit_path": unit.root,
        "commit_sha": unit.repo.head_sha, "classification": rating.classification,
        "provisional": rating.provisional,
        "ratings": {
            "inherent": rating.inherent, "control_strength": rating.control_strength,
            "residual": rating.residual, "confidence": rating.confidence, "agency": rating.agency,
            "dimensions": {d: asdict(s) for d, s in rating.dimensions.items()},
        },
        "red_flags": [asdict(f) for f in rating.red_flags],
        "findings": findings, "advice": advice, "notes": rating.notes,
    }
