"""Deterministic security-posture computation for the Assurance Center.

Honesty first: this reports a control CHECKLIST with explicit statuses and
residual risks, plus the static suite's coverage — it deliberately does NOT emit
a single fabricated "security score". Empirical resistance (whether the model
actually withstands injection) is a separate section, sourced only from real
live red-team runs.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import select

from config import settings
from models.planning import UploadedDocument
from models.assurance import AssuranceRun
from services.assurance.red_team_suite import run_static, hydrate_report, _note
from services.injection_scan import scan_summary


def _max_sev(flags: list[dict]) -> str | None:
    order = {"high": 3, "medium": 2, "low": 1}
    return max((f.get("severity") for f in flags), key=lambda s: order.get(s, 0), default=None)


async def flagged_documents(db) -> list[dict]:
    rows = (await db.execute(
        select(UploadedDocument).where(UploadedDocument.injection_flags.isnot(None))
    )).scalars().all()
    out = []
    for d in rows:
        try:
            flags = json.loads(d.injection_flags) or []
        except (ValueError, TypeError):
            flags = []
        if flags:
            out.append({
                "id": d.id, "engagement_id": d.engagement_id,
                "filename": d.original_filename,
                "flag_count": len(flags), "max_severity": _max_sev(flags),
            })
    return out


async def compute_posture(db) -> dict:
    static = run_static()  # deterministic, no AI
    injection_ok = all(r["passed"] for r in static["results"])
    flagged = await flagged_documents(db)

    if not settings.APP_PASSWORD and settings.IA_WINGMAN_DEV_OPEN:
        auth_status = "residual"
        auth_ev = "Running with authentication DISABLED (IA_WINGMAN_DEV_OPEN)."
    elif not settings.APP_PASSWORD:
        auth_status = "implemented"
        auth_ev = "No password set — API is fail-closed (all requests denied)."
    else:
        auth_status = "implemented"
        auth_ev = "Shared login, fail-closed default, constant-time compare, delay-based throttling."

    controls = [
        {"id": "prompt_injection_isolation",
         "name": "Prompt-injection isolation",
         "defends": "Agent prompts against instructions hidden in untrusted content.",
         "status": "implemented" if injection_ok else "partial",
         "evidence": f"Static suite verifies {static['passed']}/{static['total']} payloads are fenced + detected.",
         "residual": "Defense-in-depth, not a guarantee — a persuasive injection may still steer the model. See empirical resistance."},
        {"id": "untrusted_scanning",
         "name": "Untrusted-content scanning",
         "defends": "Surfaces suspected injection payloads in uploaded documents.",
         "status": "implemented",
         "evidence": f"{len(flagged)} document(s) currently flagged for review.",
         "residual": "Heuristic signal, not a verdict; informational only (never blocks)."},
        {"id": "web_search_isolation",
         "name": "Web-search result isolation",
         "defends": "Treats fetched search results as data, not instructions.",
         "status": "partial",
         "evidence": "Tavily results are fenced before synthesis.",
         "residual": "Anthropic server-side web_search injects results provider-side — not isolatable by this app."},
        {"id": "authentication",
         "name": "Authentication",
         "defends": "Unauthorised API access.",
         "status": auth_status,
         "evidence": auth_ev,
         "residual": "Rate-limiting is per-IP delay-based; behind the dev proxy all traffic shares one IP."},
        {"id": "upload_parser_limits",
         "name": "Upload & parser limits",
         "defends": "Resource exhaustion via malicious PDF/DOCX files.",
         "status": "implemented",
         "evidence": "PDF page cap, DOCX zip-bomb guard, streaming size cap, parser timeout.",
         "residual": None},
        {"id": "ssrf_egress",
         "name": "SSRF egress filtering",
         "defends": "Server-side request forgery via user-supplied URLs.",
         "status": "implemented",
         "evidence": "All resolved IPv4/IPv6 checked; loopback/private/CGNAT/link-local/mapped blocked.",
         "residual": "DNS-rebinding not fully pinned (validation at resolve time)."},
        {"id": "tenant_isolation",
         "name": "Tenant isolation",
         "defends": "Cross-engagement data access between users.",
         "status": "residual",
         "evidence": "Single-tenant shared login by design.",
         "residual": "Any valid login can access every engagement — user accounts & per-engagement authorisation are future work."},
    ]

    counts: dict[str, int] = {}
    for c in controls:
        counts[c["status"]] = counts.get(c["status"], 0) + 1

    last_live = (await db.execute(
        select(AssuranceRun).where(AssuranceRun.mode == "live")
        .order_by(AssuranceRun.started_at.desc()).limit(1)
    )).scalars().first()

    resistance = None
    if last_live:
        try:
            summ = json.loads(last_live.summary)
        except (ValueError, TypeError):
            summ = {}
        try:
            results = json.loads(last_live.results)
        except (ValueError, TypeError):
            results = []
        verdicts, headline = hydrate_report(
            last_live.mode, last_live.passed, last_live.total, results, summ)
        resistance = {
            "passed": last_live.passed, "total": last_live.total,
            "score_pct": summ.get("score_pct"),
            "at": last_live.started_at.isoformat() if last_live.started_at else None,
            "verdicts": verdicts, "headline": headline,
            "note": _note("live"),  # generic boilerplate — always current, honest wording
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "controls": controls,
        "counts": counts,
        "coverage": {
            "suite": "static",
            "passed": static["passed"], "total": static["total"],
            "by_category": static["by_category"], "note": static["note"],
        },
        "resistance": resistance,
        "flagged_documents": flagged,
    }
