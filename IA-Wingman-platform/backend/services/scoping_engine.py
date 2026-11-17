"""Engagement Planning & Scoping engine — front-loads the RACM spine from the
planning work the auditor has already done.

By the time an auditor reaches fieldwork they have usually completed the planning
modules: Scope & Objectives (overall objective, key audit questions, in/out-of-
scope items), Topic Intelligence (key risk areas, excluded areas) and the
Background Risk Assessment (a risk register with inherent ratings). All of that
already implies the top of the RACM spine — the objectives, the risks and the
scope decisions. This engine reads those artifacts and proposes them into the
spine so the auditor starts fieldwork from a populated, traceable matrix instead
of a blank one.

Deterministic-first & propose-never-decide:
  - There is NO AI here. Every proposal is a plain, auditable mapping from an
    existing planning row, tagged with its provenance (which module it came from).
  - Proposals are written origin='ai', accepted=False, so they surface as
    "proposed" awaiting the auditor's acceptance — nothing is decided.
  - Idempotent: a re-run first removes this engine's own earlier UNACCEPTED
    proposals (never anything a human accepted or authored), then re-derives.
  - Additive & non-duplicating: objectives are only proposed when the spine has
    none yet; risks/scope decisions already present (by title) are skipped.
"""
import json
import re
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.planning import (
    ScopeObjectives, ScopeItem, KeyAuditQuestion, TopicIntelligence,
    BackgroundRiskAssessment,
)
from models.racm import RacmObjective, RacmRisk, ScopeDecision

AGENT_TYPE = "scoping_engine"
PROVENANCE_SOURCE = "scoping_engine"

_STOP = {"the", "and", "for", "are", "with", "that", "this", "from", "not",
         "all", "new", "any", "its", "into", "onto", "per"}


def _loads(raw, default=None):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _keywords(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in _STOP}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _rating(v):
    s = (v or "").strip().lower()
    if s.startswith("high"):
        return "high"
    if s.startswith("med"):
        return "medium"
    if s.startswith("low"):
        return "low"
    return None


def _next_num(refs, prefix: str) -> int:
    mx = 0
    for r in refs:
        if r and r.startswith(prefix):
            try:
                mx = max(mx, int(r[len(prefix):]))
            except ValueError:
                pass
    return mx + 1


def _prov(source_ref, rationale, run_id, source_id=None):
    """Provenance for one proposed node.

    `source_ref` is for a person to read — "EBA/GL/2021/02 §3", "BRA R4". It is
    what the inspector prints, and a raw row id there would be a downgrade.
    `source_id` is the same fact for a machine: the id of the upstream row, so a
    coverage check can answer "is this key risk area in the matrix?" by looking
    rather than by comparing words. Both, because neither serves both readers.
    """
    return json.dumps({"source_type": PROVENANCE_SOURCE, "source_ref": source_ref,
                       "source_id": source_id,
                       "rationale": rationale, "run_id": run_id})


async def _gather(engagement_id: str, db):
    scope = (await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )).scalars().first()
    kaqs, scope_items = [], []
    if scope:
        kaqs = (await db.execute(
            select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id)
            .order_by(KeyAuditQuestion.sort_order)
        )).scalars().all()
        scope_items = (await db.execute(
            select(ScopeItem).where(ScopeItem.scope_id == scope.id)
            .order_by(ScopeItem.sort_order)
        )).scalars().all()
    ti = (await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )).scalars().first()
    bra = (await db.execute(
        select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id)
    )).scalars().first()
    return scope, kaqs, scope_items, ti, bra


def _plan(scope, kaqs, scope_items, ti, bra, existing_objectives):
    """Pure mapping from planning rows to proposal specs. No DB writes.

    Returns (objective_specs, risk_specs, scope_specs, sources).
    `sources` describes, for the preview, where each set of proposals comes from.
    """
    sources = {}

    # ── Objectives — only when the spine has none yet ────────────────────────
    obj_specs = []
    if existing_objectives:
        sources["objectives"] = {"from": "existing spine objectives (reused)", "count": 0}
    else:
        accepted_kaqs = [k for k in kaqs if k.is_accepted] or list(kaqs)
        if accepted_kaqs:
            for k in accepted_kaqs:
                obj_specs.append({
                    "title": (k.question_text or "").strip(),
                    "description": None,
                    "source_ref": k.regulatory_basis or "Key audit question",
                    "source_id": k.id,
                    "rationale": "Derived from a key audit question.",
                })
            sources["objectives"] = {"from": f"{len(accepted_kaqs)} key audit questions", "count": len(obj_specs)}
        elif scope and scope.overall_objective:
            obj_specs.append({
                "title": scope.overall_objective.strip(),
                "description": None,
                "source_ref": "Overall objective",
                "rationale": "Derived from the overall audit objective.",
            })
            sources["objectives"] = {"from": "the overall objective", "count": 1}
        else:
            sources["objectives"] = {"from": "no scope objectives on file", "count": 0}
    obj_specs = [o for o in obj_specs if o["title"]]

    # ── Risks — the Background Risk Assessment register is canonical; fall
    #    back to Topic Intelligence key risk areas when no BRA exists ─────────
    risk_specs = []
    bra_items = _loads(bra.risk_items, []) if bra else []
    if bra_items:
        for it in bra_items:
            title = (it.get("risk_statement") or it.get("description") or "").strip()
            if not title:
                continue
            risk_specs.append({
                "title": title,
                "description": it.get("description") if it.get("risk_statement") else None,
                "rating": _rating(it.get("inherent_risk")),
                "category": it.get("process"),
                "confidence": None,
                "source_ref": it.get("ref") or "BRA",
                "source_id": it.get("id") or it.get("ref"),
                "rationale": "From the Background Risk Assessment register.",
            })
        sources["risks"] = {"from": f"{len(risk_specs)} Background Risk Assessment items", "count": len(risk_specs)}
    else:
        for it in (_loads(ti.key_risk_areas, []) if ti else []):
            title = (it.get("title") or "").strip()
            if not title:
                continue
            risk_specs.append({
                "title": title,
                "description": it.get("rationale"),
                "rating": None,   # the auditor sets inherent risk
                "category": None,
                "confidence": it.get("confidence"),
                "source_ref": it.get("source") or it.get("basis") or "Topic Intelligence",
                "source_id": it.get("id"),
                "rationale": "From Topic Intelligence key risk areas.",
            })
        if risk_specs:
            sources["risks"] = {"from": f"{len(risk_specs)} Topic Intelligence risk areas", "count": len(risk_specs)}
        else:
            sources["risks"] = {"from": "no risk assessment on file", "count": 0}

    # ── Scope decisions — in/out-of-scope items + TI excluded areas ──────────
    scope_specs = []
    scope_kws = []   # keyword sets of specs already added, to skip near-duplicates

    def _add_scope(decision_type, summary, rationale, source_ref):
        summary = (summary or "").strip()
        if not summary:
            return
        kw = _keywords(summary)
        for existing in scope_kws:
            if len(kw & existing) >= 2:   # same subject already recorded
                return
        scope_kws.append(kw)
        scope_specs.append({"decision_type": decision_type, "summary": summary,
                            "rationale": rationale, "source_ref": source_ref})

    for si in scope_items:
        _add_scope(si.item_type if si.item_type in ("in_scope", "out_of_scope") else "in_scope",
                   si.description, si.rationale, "Scope item")
    for it in (_loads(ti.excluded_areas, []) if ti else []):
        _add_scope("out_of_scope", it.get("title"), it.get("rationale"),
                   "Topic Intelligence excluded area")
    sources["scope_decisions"] = {"from": f"{len(scope_specs)} scope items / excluded areas", "count": len(scope_specs)}

    return obj_specs, risk_specs, scope_specs, sources


def _best_objective(risk_title: str, objective_candidates):
    """Pick the objective whose title shares the most keywords with the risk;
    fall back to the first objective. `objective_candidates` = [(id, keywords)]."""
    if not objective_candidates:
        return None
    rk = _keywords(risk_title)
    best, best_overlap = objective_candidates[0][0], -1
    for oid, okw in objective_candidates:
        overlap = len(rk & okw)
        if overlap > best_overlap:
            best, best_overlap = oid, overlap
    return best


async def _replace_previous(db, engagement_id: str) -> None:
    """Remove this engine's earlier UNACCEPTED proposals so a re-run is clean.
    Accepted or human-authored nodes are never touched."""
    for model in (RacmObjective, RacmRisk):
        rows = (await db.execute(
            select(model).where(
                model.engagement_id == engagement_id,
                model.origin == "ai",
                model.accepted == False,  # noqa: E712
            )
        )).scalars().all()
        for r in rows:
            prov = _loads(r.provenance) or {}
            if prov.get("source_type") == PROVENANCE_SOURCE:
                await db.delete(r)
    sds = (await db.execute(
        select(ScopeDecision).where(
            ScopeDecision.engagement_id == engagement_id,
            ScopeDecision.origin == "ai",
            ScopeDecision.status == "proposed",
        )
    )).scalars().all()
    for s in sds:
        prov = _loads(s.provenance) or {}
        if prov.get("source_type") == PROVENANCE_SOURCE:
            await db.delete(s)
    await db.flush()


async def preview(engagement_id: str) -> dict:
    """Deterministic, read-only: what the planning modules would propose."""
    async with AsyncSessionLocal() as db:
        scope, kaqs, scope_items, ti, bra = await _gather(engagement_id, db)
        existing_obj = (await db.execute(
            select(RacmObjective.id).where(RacmObjective.engagement_id == engagement_id).limit(1)
        )).first()
        obj_specs, risk_specs, scope_specs, sources = _plan(
            scope, kaqs, scope_items, ti, bra, existing_obj)
    total = len(obj_specs) + len(risk_specs) + len(scope_specs)
    return {
        "ready": total > 0,
        "sources": sources,
        "would_propose": {
            "objectives": len(obj_specs),
            "risks": len(risk_specs),
            "scope_decisions": len(scope_specs),
        },
    }


async def front_load(engagement_id: str, run_id: str | None = None) -> dict:
    """Deterministically write the planning-derived proposals into the spine.
    Free (no AI). Idempotent. Returns counts of what was proposed."""
    async with AsyncSessionLocal() as db:
        scope, kaqs, scope_items, ti, bra = await _gather(engagement_id, db)

        await _replace_previous(db, engagement_id)

        # Existing spine context (after the replace, so our own stale proposals
        # are gone) — used for ref numbering, objective reuse and de-duplication.
        existing_objs = (await db.execute(
            select(RacmObjective).where(RacmObjective.engagement_id == engagement_id)
        )).scalars().all()
        existing_risks = (await db.execute(
            select(RacmRisk).where(RacmRisk.engagement_id == engagement_id)
        )).scalars().all()
        existing_sds = (await db.execute(
            select(ScopeDecision).where(ScopeDecision.engagement_id == engagement_id)
        )).scalars().all()

        obj_specs, risk_specs, scope_specs, _ = _plan(
            scope, kaqs, scope_items, ti, bra, existing_objs)

        # ── Objectives ───────────────────────────────────────────────────────
        obj_refs = [o.ref for o in existing_objs]
        onum = _next_num(obj_refs, "O")
        objective_candidates = [(o.id, _keywords(f"{o.title} {o.description or ''}")) for o in existing_objs]
        objectives_created = 0
        for i, spec in enumerate(obj_specs):
            oid = str(uuid4())
            db.add(RacmObjective(
                id=oid, engagement_id=engagement_id, ref=f"O{onum + i}",
                title=spec["title"][:500], description=spec["description"],
                origin="ai", accepted=False, confidence="medium",
                provenance=_prov(spec["source_ref"], spec["rationale"], run_id,
                                 source_id=spec.get("source_id")),
                sort_order=len(existing_objs) + i,
            ))
            objective_candidates.append((oid, _keywords(spec["title"])))
            objectives_created += 1
        await db.flush()

        # ── Risks (linked to the best-matching objective) ────────────────────
        existing_risk_norms = [_norm(r.title) for r in existing_risks]
        existing_risk_kws = [_keywords(r.title) for r in existing_risks]

        def _is_duplicate_risk(title):
            n = _norm(title)
            if n in existing_risk_norms:
                return True
            rk = _keywords(title)
            for ekw in existing_risk_kws:
                if len(rk & ekw) >= 3:   # near-identical wording already present
                    return True
            return False

        rnum = _next_num([r.ref for r in existing_risks], "R")
        risks_created = 0
        for spec in risk_specs:
            if _is_duplicate_risk(spec["title"]):
                continue
            db.add(RacmRisk(
                id=str(uuid4()), engagement_id=engagement_id,
                objective_id=_best_objective(spec["title"], objective_candidates),
                ref=f"R{rnum + risks_created}", title=spec["title"][:500],
                description=spec["description"], category=spec["category"],
                inherent_rating=spec["rating"],
                origin="ai", accepted=False, confidence=spec["confidence"] or "medium",
                provenance=_prov(spec["source_ref"], spec["rationale"], run_id,
                                 source_id=spec.get("source_id")),
                sort_order=len(existing_risks) + risks_created,
            ))
            # so a later spec with the same wording is also de-duplicated
            existing_risk_norms.append(_norm(spec["title"]))
            existing_risk_kws.append(_keywords(spec["title"]))
            risks_created += 1

        # ── Scope decisions ──────────────────────────────────────────────────
        existing_sd_kws = [_keywords(s.summary) for s in existing_sds]
        sd_order = (max([s.sort_order or 0 for s in existing_sds]) + 1) if existing_sds else 0
        scope_created = 0
        for spec in scope_specs:
            kw = _keywords(spec["summary"])
            if any(len(kw & ekw) >= 2 for ekw in existing_sd_kws):
                continue   # this scope subject is already recorded in the spine
            db.add(ScopeDecision(
                id=str(uuid4()), engagement_id=engagement_id,
                decision_type=spec["decision_type"], summary=spec["summary"][:500],
                rationale=spec["rationale"], status="proposed", origin="ai",
                provenance=_prov(spec["source_ref"], "Cascaded from the scope module.", run_id),
                sort_order=sd_order + scope_created,
            ))
            existing_sd_kws.append(kw)
            scope_created += 1

        await db.commit()

    return {
        "objectives": objectives_created,
        "risks": risks_created,
        "scope_decisions": scope_created,
    }
