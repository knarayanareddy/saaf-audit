"""Board / portfolio report — a governance-level view across ALL engagements.

Everything here is DETERMINISTIC: portfolio counts, cross-engagement findings,
control effectiveness, and the "high risk x weak control" candidate hotspots are
all computed from existing data — no AI, no invented figures. A deterministic
executive summary is always available so the page and the Word export are never
empty. The ONLY optional AI step (`draft_board_narrative`) rephrases those same
aggregates into board language and may not introduce new numbers.

Honesty over green: hotspots are flagged as *candidates to verify*, not verdicts;
coverage gaps mean "no audit recorded", not a control failure.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.reporting import Finding, BoardReport
from models.racm import RacmRisk, RacmControl, RacmTest
from organization import ORG
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT

ACTIVE = {"in_planning", "in_fieldwork", "in_reporting"}
_RATINGS = ("high", "medium", "low")


def _tally(items, key):
    out = {}
    for it in items:
        k = key(it) or "unknown"
        out[k] = out.get(k, 0) + 1
    return out


async def compute_board(db) -> dict:
    """Aggregate the whole portfolio deterministically. No AI."""
    engagements = (await db.execute(select(Engagement))).scalars().all()
    eng_by_id = {e.id: e for e in engagements}
    findings = (await db.execute(select(Finding))).scalars().all()
    risks = (await db.execute(select(RacmRisk))).scalars().all()
    controls = (await db.execute(select(RacmControl))).scalars().all()
    tests = (await db.execute(select(RacmTest))).scalars().all()

    # ── Portfolio ───────────────────────────────────────────────────────────────
    by_status = _tally(engagements, lambda e: e.status)
    by_entity = _tally(engagements, lambda e: e.entity)
    by_type = _tally(engagements, lambda e: e.audit_type)
    timeline = sorted(
        [{"id": e.id, "name": e.name, "entity": e.entity, "status": e.status, "start_date": e.start_date}
         for e in engagements if e.status in ACTIVE and e.start_date],
        key=lambda r: r["start_date"] or "",
    )[:12]

    # ── Findings posture (across engagements) ────────────────────────────────────
    f_by_rating = {lvl: sum(1 for f in findings if (f.rating or "unrated") == lvl) for lvl in _RATINGS}
    f_by_rating["unrated"] = sum(1 for f in findings if f.rating not in _RATINGS)
    ent_findings = {}
    for f in findings:
        e = eng_by_id.get(f.engagement_id)
        code = e.entity if e else "unknown"
        row = ent_findings.setdefault(code, {"key": code, "value": 0, "high": 0, "medium": 0, "low": 0})
        row["value"] += 1
        if f.rating in _RATINGS:
            row[f.rating] += 1
    top_findings = [
        {"engagement_id": f.engagement_id,
         "engagement_name": (eng_by_id.get(f.engagement_id).name if eng_by_id.get(f.engagement_id) else ""),
         "entity": (eng_by_id.get(f.engagement_id).entity if eng_by_id.get(f.engagement_id) else ""),
         "title": f.title, "rating": f.rating or "unrated"}
        for f in findings if f.rating == "high"
    ][:8]

    # ── Control effectiveness ────────────────────────────────────────────────────
    ctrl = {
        "total": len(controls),
        "effective": sum(1 for c in controls if c.design_conclusion == "effective"),
        "deficient": sum(1 for c in controls if c.design_conclusion == "deficient"),
        "not_assessed": sum(1 for c in controls if c.design_conclusion in (None, "not_assessed")),
        "tests": {r: sum(1 for t in tests if t.result == r) for r in ("pass", "fail", "exceptions", "pending")},
    }

    # ── Candidate hotspots: high risk x weak control ─────────────────────────────
    risk_by_id = {r.id: r for r in risks}
    controls_by_risk = {}
    for c in controls:
        controls_by_risk.setdefault(c.risk_id, []).append(c)
    tests_by_control = {}
    for t in tests:
        tests_by_control.setdefault(t.control_id, []).append(t)

    hotspots = []

    def eng_ref(rid):
        e = eng_by_id.get(rid)
        return (e.name if e else ""), (e.entity if e else "")

    for r in risks:
        if r.inherent_rating != "high":
            continue
        name, entity = eng_ref(r.engagement_id)
        rcontrols = controls_by_risk.get(r.id, [])
        if not rcontrols:
            hotspots.append({
                "engagement_id": r.engagement_id, "engagement_name": name, "entity": entity,
                "risk_ref": r.ref, "risk_title": r.title, "control_ref": None, "control_title": None,
                "reason": "High inherent risk with no control", "severity": "high",
            })
            continue
        for c in rcontrols:
            if c.design_conclusion == "deficient":
                hotspots.append({
                    "engagement_id": r.engagement_id, "engagement_name": name, "entity": entity,
                    "risk_ref": r.ref, "risk_title": r.title, "control_ref": c.ref, "control_title": c.title,
                    "reason": "Deficient control on a high inherent risk", "severity": "high",
                })
                continue
            results = {t.result for t in tests_by_control.get(c.id, [])}
            if results & {"fail", "exceptions"}:
                hotspots.append({
                    "engagement_id": r.engagement_id, "engagement_name": name, "entity": entity,
                    "risk_ref": r.ref, "risk_title": r.title, "control_ref": c.ref, "control_title": c.title,
                    "reason": "Testing exceptions on a control mitigating a high risk", "severity": "medium",
                })
    hotspots.sort(key=lambda h: 0 if h["severity"] == "high" else 1)

    # ── Assurance coverage whitespace ────────────────────────────────────────────
    covered_entities = {e.entity for e in engagements}
    org_entities = [ent.get("code") for ent in ORG.to_dict().get("entities", [])]
    entity_whitespace = [code for code in org_entities if code not in covered_entities]

    return {
        "portfolio": {
            "total": len(engagements),
            "active": sum(1 for e in engagements if e.status in ACTIVE),
            "closed": sum(1 for e in engagements if e.status == "closed"),
            "by_status": [{"key": k, "value": v} for k, v in by_status.items()],
            "by_entity": [{"key": k, "value": v} for k, v in by_entity.items()],
            "by_audit_type": sorted(
                [{"key": k, "value": v} for k, v in by_type.items()], key=lambda x: -x["value"]
            ),
            "timeline": timeline,
        },
        "findings": {
            "total": len(findings),
            "by_rating": f_by_rating,
            "by_entity": sorted(ent_findings.values(), key=lambda x: -x["value"]),
            "engagements_with_findings": len({f.engagement_id for f in findings}),
            "top": top_findings,
        },
        "controls": ctrl,
        "hotspots": hotspots,
        "coverage": {"entity_whitespace": entity_whitespace, "entities_total": len(org_entities)},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def board_signature(board: dict) -> str:
    """A stable hash of the aggregates the narrative actually talks about. When the
    portfolio moves on (new findings, more hotspots, changed coverage), this changes
    and a previously-drafted AI summary is flagged stale."""
    f, c = board["findings"], board["controls"]
    salient = {
        "findings_total": f["total"],
        "by_rating": f["by_rating"],
        "engagements_with_findings": f["engagements_with_findings"],
        "hotspots": len(board["hotspots"]),
        "hotspot_engagements": sorted({h["engagement_id"] for h in board["hotspots"]}),
        "controls_deficient": c["deficient"],
        "portfolio_total": board["portfolio"]["total"],
        "whitespace": sorted(board["coverage"]["entity_whitespace"]),
    }
    return hashlib.sha1(json.dumps(salient, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _opinion(board: dict) -> str:
    high_f = board["findings"]["by_rating"].get("high", 0)
    med_f = board["findings"]["by_rating"].get("medium", 0)
    hot = len(board["hotspots"])
    if high_f or any(h["severity"] == "high" for h in board["hotspots"]):
        return "needs_improvement" if high_f + hot <= 2 else "unsatisfactory"
    if med_f or hot:
        return "needs_improvement"
    return "satisfactory"


def deterministic_summary(board: dict) -> dict:
    """A plain-language executive summary assembled from the aggregates. No AI —
    guarantees the page/export are never empty."""
    p, f = board["portfolio"], board["findings"]
    hot = board["hotspots"]
    ws = board["coverage"]["entity_whitespace"]
    exec_summary = (
        f"The internal-audit portfolio holds {p['total']} engagement(s): "
        f"{p['active']} active and {p['closed']} closed. "
        f"{f['total']} finding(s) are recorded across {f['engagements_with_findings']} engagement(s) "
        f"({f['by_rating'].get('high', 0)} high, {f['by_rating'].get('medium', 0)} medium). "
        f"{len(hot)} candidate risk-and-control hotspot(s) warrant board attention"
        + (f", concentrated where high inherent risks meet weak or untested controls." if hot else ".")
    )
    key_messages = []
    if hot:
        key_messages.append(f"{len(hot)} high-risk lines have weak, missing or failing controls — verify and prioritise.")
    if f["by_rating"].get("high"):
        key_messages.append(f"{f['by_rating']['high']} high-severity finding(s) are open across the portfolio.")
    if ws:
        key_messages.append(f"No audit is recorded for {len(ws)} organisational unit(s): {', '.join(ws)} — an assurance-coverage gap.")
    if board["controls"]["deficient"]:
        key_messages.append(f"{board['controls']['deficient']} assessed control(s) are design-deficient.")
    if not key_messages:
        key_messages.append("No material portfolio-level concerns detected in the current data.")
    return {"overall_opinion": _opinion(board), "exec_summary": exec_summary,
            "key_messages": key_messages, "generated_by": "deterministic"}


# ── Optional AI narrative (opt-in; rephrase aggregates, never add figures) ───────

_BOARD_SYSTEM = BASE_SYSTEM_PROMPT + """

BOARD-NARRATIVE ROLE:
You write a concise executive summary of an internal-audit portfolio for the audit committee, from the
deterministic aggregates provided. STRICT RULES:
- Do NOT introduce any number, entity, engagement or finding not present in the aggregates. Only interpret them.
- Be balanced and evidence-based; the opinion must follow from the data. Neutral, board-appropriate tone.
- The auditor reviews and signs. You propose.
"""


async def draft_board_narrative(board: dict) -> dict:
    """One AI call: an executive summary + key messages grounded in the aggregates."""
    prompt = (
        "Write the audit-committee executive summary for this portfolio. Return ONLY a JSON object:\n"
        '{"overall_opinion":"satisfactory|needs_improvement|unsatisfactory",'
        ' "exec_summary":"4-6 sentences","key_messages":["3-5 short bullets"]}\n\n'
        "PORTFOLIO AGGREGATES (do not introduce figures beyond these):\n"
        + json.dumps({k: board[k] for k in ("portfolio", "findings", "controls", "hotspots", "coverage")},
                     ensure_ascii=False, default=str)
    )
    out = await run_agent_to_json(_BOARD_SYSTEM, prompt, max_tokens=1500)
    if not isinstance(out, dict):
        raise ValueError("board narrative returned no object")
    opinion = out.get("overall_opinion")
    if opinion not in ("satisfactory", "needs_improvement", "unsatisfactory"):
        opinion = _opinion(board)
    msgs = out.get("key_messages")
    if not isinstance(msgs, list) or not msgs:
        msgs = deterministic_summary(board)["key_messages"]
    return {"overall_opinion": opinion, "exec_summary": (out.get("exec_summary") or "").strip(),
            "key_messages": [str(m) for m in msgs][:6], "generated_by": "ai"}


async def draft_board_narrative_task():
    """Opt-in background task: compute the board, draft the AI narrative, persist
    the latest BoardReport. Falls back to the deterministic summary on failure."""
    async with AsyncSessionLocal() as db:
        board = await compute_board(db)
    sig = board_signature(board)
    try:
        narrative = await draft_board_narrative(board)
    except Exception:  # noqa: BLE001
        narrative = deterministic_summary(board)
    async with AsyncSessionLocal() as db:
        from uuid import uuid4
        r = (await db.execute(select(BoardReport).order_by(BoardReport.created_at.desc()))).scalars().first()
        if not r:
            r = BoardReport(id=str(uuid4()))
            db.add(r)
        r.overall_opinion = narrative["overall_opinion"]
        r.exec_summary = narrative["exec_summary"]
        r.key_messages = json.dumps(narrative["key_messages"])
        r.generated_by = narrative["generated_by"]
        r.based_on_sig = sig
        r.status = "ready"
        await db.commit()


async def latest_narrative(db, board: dict | None = None) -> dict | None:
    r = (await db.execute(select(BoardReport).order_by(BoardReport.created_at.desc()))).scalars().first()
    if not r:
        return None
    try:
        msgs = json.loads(r.key_messages) if r.key_messages else []
    except (ValueError, TypeError):
        msgs = []
    # Stale = the portfolio has moved on since this summary was drafted (or the
    # summary predates signature tracking, so it can't be verified → treat as stale).
    try:
        current = board_signature(board if board is not None else await compute_board(db))
        stale = r.based_on_sig != current
    except Exception:  # noqa: BLE001
        stale = False
    return {"overall_opinion": r.overall_opinion, "exec_summary": r.exec_summary,
            "key_messages": msgs, "generated_by": r.generated_by, "status": r.status,
            "created_at": str(r.created_at), "stale": stale}
