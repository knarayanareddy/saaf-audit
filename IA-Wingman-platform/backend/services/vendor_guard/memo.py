"""Opt-in AI audit memo for Vendor Guard. Ported from the SAAF memo prompt."""

from services.ai_service import run_text
from services.prompt_safety import safe_label
from .models import Finding

MEMO_SYSTEM = (
    "You are a senior IT audit manager writing a formal third-party (vendor) risk assessment memo. "
    "Use formal audit language, reference specific control IDs and framework names, and do not invent "
    "figures or findings beyond those provided. Do not use em-dashes."
)


def _findings_summary(findings: list[Finding]) -> str:
    return "\n".join(
        f"[{f.framework}] {f.control_id} - {f.status} ({f.severity}): {f.evidence}"
        for f in findings
    ) or "(no findings)"


def _scorecard_summary(scorecard: dict) -> str:
    return "\n".join(
        f"{fw}: {d['rag']} (gaps: {d.get('gaps', 0)}, critical: {d.get('critical', 0)}, "
        f"high: {d.get('high', 0)}, partial: {d.get('partial', 0)})"
        for fw, d in scorecard.items()
    ) or "(no frameworks assessed)"


async def draft_memo(vendor_name: str, findings: list[Finding], scorecard: dict) -> str:
    """Return the memo narrative as plain text (best-effort; caller guards)."""
    user = (
        f"Vendor: {safe_label(vendor_name)}\n\n"
        f"RAG scorecard:\n{_scorecard_summary(scorecard)}\n\n"
        f"Findings:\n{_findings_summary(findings)}\n\n"
        "Write a professional vendor risk assessment memo with these sections:\n"
        "1. Executive Summary (overall risk verdict, most critical issues, overall recommendation)\n"
        "2. Assessment Scope (frameworks assessed, documents reviewed)\n"
        "3. Key Findings (narrative of the most significant gaps, grouped by framework)\n"
        "4. Recommendations (numbered, prioritised by severity)\n"
        "5. Conclusion"
    )
    return await run_text(system_prompt=MEMO_SYSTEM, user_prompt=user, max_tokens=4000)
