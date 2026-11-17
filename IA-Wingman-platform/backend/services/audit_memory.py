"""Audit Memory — cross-engagement recall of precedents.

When an auditor builds a new engagement's RACM spine, this surfaces what *prior*
audits found on the same topic: past findings, risks, controls and scope calls
from OTHER engagements, matched by transparent keyword overlap. The auditor can
adopt a risk/control precedent as a proposal in the spine (origin='ai',
accepted=False) — propose, never decide.

DETERMINISTIC-FIRST: recall is plain token-overlap scoring (no embeddings — none
exist in this stack), so it is explainable and reproducible. The only optional AI
step (`synthesize`) writes a short prose summary strictly grounded in the recalled
items. Honesty: matches are labelled "from prior audits — verify relevance".
"""
from __future__ import annotations

import re

from sqlalchemy import select

from models.engagement import Engagement
from models.reporting import Finding
from models.racm import RacmObjective, RacmRisk, RacmControl, ScopeDecision
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT

# Generic audit/boilerplate words carry no topic signal — dropping them keeps the
# match about the subject (AML, sanctions, access, backup…), not the vocabulary.
_STOP = {
    "the", "and", "for", "with", "not", "are", "was", "were", "that", "this", "from", "has", "have",
    "its", "their", "any", "all", "may", "can", "must", "should", "would", "could", "per", "via",
    "audit", "auditor", "review", "reviewed", "assessment", "assess", "process", "processes",
    "management", "manage", "control", "controls", "risk", "risks", "framework", "engagement",
    "internal", "policy", "policies", "requirement", "requirements", "finding", "findings",
    "evidence", "test", "testing", "scope", "objective", "objectives", "organisation", "organization",
    "customers", "customer", "system", "systems", "before", "after", "during", "without", "several",
    "documented", "documentation", "required", "require", "requires", "inconsistent", "consistent",
    "evidenced", "incomplete", "complete", "timely", "ageing", "backlog", "defined", "existing",
}


def _tokenize(*texts) -> set[str]:
    """Normalised keyword set: lowercase, split on non-alphanumerics, drop stopwords
    and tokens shorter than 3 characters."""
    out = set()
    for t in texts:
        if not t:
            continue
        for w in re.split(r"[^a-z0-9]+", str(t).lower()):
            if len(w) >= 3 and w not in _STOP:
                out.add(w)
    return out


async def _context_terms(db, engagement) -> set[str]:
    """Topic terms describing the current engagement: its metadata plus the titles
    of any accepted objectives/risks and its scope decisions."""
    terms = _tokenize(engagement.name, engagement.summary, engagement.audit_type, engagement.entity)
    risks = (await db.execute(
        select(RacmRisk).where(RacmRisk.engagement_id == engagement.id)
    )).scalars().all()
    for r in risks:
        terms |= _tokenize(r.title, r.category)
    objs = (await db.execute(
        select(RacmObjective).where(RacmObjective.engagement_id == engagement.id)
    )).scalars().all()
    for o in objs:
        terms |= _tokenize(o.title)
    return terms


def _score(query: set[str], title_terms: set[str], body_terms: set[str]) -> tuple[int, list[str]]:
    """Title matches weigh double. Returns (score, shared terms)."""
    t_hit = query & title_terms
    b_hit = (query & body_terms) - t_hit
    return 2 * len(t_hit) + len(b_hit), sorted(t_hit | b_hit)


async def recall(db, engagement_id: str, limit: int = 8) -> dict:
    """Deterministically recall topic-matched precedents from OTHER engagements."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        return {"terms": [], "items": []}
    query = await _context_terms(db, eng)
    names = {e.id: (e.name, e.status) for e in (await db.execute(select(Engagement))).scalars().all()}

    items = []

    def consider(kind, source_id, title, body, extra, adoptable):
        if source_id == engagement_id:
            return  # never recall the current engagement
        score, shared = _score(query, _tokenize(title), _tokenize(body))
        if score < 2:
            return
        src_name, src_status = names.get(source_id, ("", ""))
        items.append({
            "kind": kind, "title": title, "summary": (body or "")[:200],
            "score": score, "shared": shared[:6], "adoptable": adoptable,
            "source_engagement_id": source_id, "source_engagement_name": src_name,
            "source_status": src_status, **extra,
        })

    for f in (await db.execute(select(Finding))).scalars().all():
        consider("finding", f.engagement_id, f.title, f"{f.condition or ''} {f.effect or ''}",
                 {"rating": f.rating}, adoptable=False)
    for r in (await db.execute(select(RacmRisk))).scalars().all():
        consider("risk", r.engagement_id, r.title, r.description, {
            "rating": r.inherent_rating, "category": r.category,
            "adopt_payload": {"kind": "risk", "title": r.title, "description": r.description,
                              "category": r.category, "inherent_rating": r.inherent_rating},
        }, adoptable=True)
    for c in (await db.execute(select(RacmControl))).scalars().all():
        consider("control", c.engagement_id, c.title, c.description, {
            "control_type": c.control_type,
            "adopt_payload": {"kind": "control", "title": c.title, "description": c.description,
                              "control_type": c.control_type},
        }, adoptable=True)
    for s in (await db.execute(select(ScopeDecision))).scalars().all():
        consider("scope", s.engagement_id, s.summary, s.rationale,
                 {"decision_type": s.decision_type}, adoptable=False)

    items.sort(key=lambda x: -x["score"])
    return {"terms": sorted(query)[:20], "items": items[:limit]}


# ── Optional AI synthesis (opt-in; grounded strictly in the recalled items) ─────

_SYNTH_SYSTEM = BASE_SYSTEM_PROMPT + """

AUDIT-MEMORY-SYNTHESIS ROLE:
You summarise what PRIOR audits found on a topic, from the recalled precedents provided. STRICT RULES:
- Use ONLY the precedents given. Do NOT invent findings, controls, numbers or audits.
- 2-4 sentences, neutral. Note which precedents look most relevant and why. The auditor decides.
"""


async def synthesize(recall_result: dict, engagement) -> str:
    """One AI call: a short 'what prior audits found on this topic' note."""
    items = recall_result.get("items", [])
    if not items:
        return "No prior-audit precedents matched this engagement's topic yet."
    lines = [
        f"- [{it['kind']}] {it['title']} (from {it['source_engagement_name']}, {it.get('rating') or it.get('decision_type') or ''})"
        for it in items
    ]
    prompt = (
        f"Engagement: {engagement.name} ({engagement.audit_type}). Summarise what prior audits found on this "
        "topic, from these recalled precedents only. Return ONLY a JSON object {\"summary\":\"2-4 sentences\"}.\n\n"
        "PRECEDENTS:\n" + "\n".join(lines)
    )
    out = await run_agent_to_json(_SYNTH_SYSTEM, prompt, max_tokens=600)
    if isinstance(out, dict) and out.get("summary"):
        return str(out["summary"]).strip()
    raise ValueError("synthesis returned no summary")
