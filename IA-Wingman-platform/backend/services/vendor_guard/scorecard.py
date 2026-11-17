"""Deterministic RAG scorecard + gap register for Vendor Guard.

No AI: computed purely from the findings.
  Red   — any Critical or High Gap
  Amber — any Medium/Low Gap or any Partial
  Green — all Compliant or Not Applicable
"""

from .models import Finding

_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
_STATUS_ORDER = {"Gap": 0, "Partial": 1, "Not Applicable": 2, "Compliant": 3}


def compute_rag_scorecard(findings: list[Finding]) -> dict:
    """Return {framework: {rag, total, gaps, critical, high, partial, compliant}}."""
    scorecard: dict[str, dict] = {}
    for f in findings:
        s = scorecard.setdefault(f.framework, {
            "total": 0, "gaps": 0, "critical": 0, "high": 0, "partial": 0, "compliant": 0,
        })
        s["total"] += 1
        if f.status == "Gap":
            s["gaps"] += 1
            if f.severity == "Critical":
                s["critical"] += 1
            elif f.severity == "High":
                s["high"] += 1
        elif f.status == "Partial":
            s["partial"] += 1
        elif f.status == "Compliant":
            s["compliant"] += 1

    for s in scorecard.values():
        if s["critical"] > 0 or s["high"] > 0:
            s["rag"] = "Red"
        elif s["gaps"] > 0 or s["partial"] > 0:
            s["rag"] = "Amber"
        else:
            s["rag"] = "Green"
    return scorecard


def gap_register(findings: list[Finding]) -> list[dict]:
    """All findings as dicts, most-material first (gaps, then by severity)."""
    ordered = sorted(
        findings,
        key=lambda f: (_STATUS_ORDER.get(f.status, 9), _SEVERITY_ORDER.get(f.severity, 9)),
    )
    return [f.model_dump() for f in ordered]


def overall_rag(scorecard: dict) -> str:
    """Worst framework RAG across the scorecard."""
    rags = {s.get("rag") for s in scorecard.values()}
    if "Red" in rags:
        return "Red"
    if "Amber" in rags:
        return "Amber"
    return "Green" if rags else "Green"
