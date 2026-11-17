"""
Risk Aggregator (S4)
====================

Reduce a list of per-claim verdicts to an overall risk score.
Pure Python, no API call.

Decision D2: HIGH risk triggers a warning only. It does NOT block the
finding. The auditor retains final responsibility (IIA Std 2310).

Rules:
    any LIKELY_HALLUCINATED + High confidence  -> HIGH
    >= 2 UNVERIFIED                            -> MEDIUM
    otherwise                                  -> LOW
"""

from __future__ import annotations

from typing import TypedDict

from .verifier import ClaimVerdict


class RiskAssessment(TypedDict):
    overall_risk: str
    blocked: bool
    warning: bool
    flagged_claims: list[ClaimVerdict]
    unverified_claims: list[ClaimVerdict]
    summary: str


def aggregate(claim_results: list[ClaimVerdict]) -> RiskAssessment:
    """Reduce per-claim verdicts to an overall risk assessment.

    Args:
        claim_results: Output of verifier.verify_claims().

    Returns:
        RiskAssessment dict. Always returns a valid object; never raises.
    """
    flagged = [
        v for v in claim_results
        if v["verdict"] == "LIKELY_HALLUCINATED" and v["confidence"] == "High"
    ]
    unverified = [v for v in claim_results if v["verdict"] == "UNVERIFIED"]

    if flagged:
        risk = "HIGH"
    elif len(unverified) >= 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "overall_risk": risk,
        "blocked": False,
        "warning": risk in ("HIGH", "MEDIUM"),
        "flagged_claims": flagged,
        "unverified_claims": unverified,
        "summary": _summary_sentence(risk, flagged, unverified, len(claim_results)),
    }


def _summary_sentence(
    risk: str,
    flagged: list[ClaimVerdict],
    unverified: list[ClaimVerdict],
    total: int,
) -> str:
    if risk == "HIGH":
        first = flagged[0]["claim"] if flagged else ""
        more = f" (+{len(flagged)-1} more)" if len(flagged) > 1 else ""
        return f"HIGH risk: likely-hallucinated claim detected: '{first}'{more}. Auditor review required."
    if risk == "MEDIUM":
        return f"MEDIUM risk: {len(unverified)} unverified claims of {total}. Auditor review recommended."
    if total == 0:
        return "LOW risk: no verifiable factual claims detected in finding."
    return f"LOW risk: all {total} claims supported by regulatory context."
