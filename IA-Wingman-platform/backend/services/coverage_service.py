"""Coverage / consistency check — a deterministic assurance sweep over the
planning chain. Cross-references risk areas → scope → key questions → work
program → frameworks and flags where the chain breaks. No AI cost; degrades
gracefully when upstream data is thin.

Checks 6-10 extend this same sweep past the work program into RACM/Fieldwork/
Findings/Report — see the module-level note above _kw below for why they use
a different (fuller) stopword list and matching threshold than checks 1-5.
"""
import json
import re
import hashlib

from sqlalchemy import select
from models.planning import (
    TopicIntelligence, ScopeObjectives, ScopeItem, KeyAuditQuestion,
    ApplicableFramework, WorkProgram, RegRequirement,
)
from models.racm import RacmControl, RacmObjective, RacmRisk, RacmTest
from services import scope_sources
from services.work_program_view import rows_for as _wp_rows
from models.reporting import Finding, AuditReport
from models.ai_analysis import AiAnalysis
from services.audit_memory import _STOP as _AM_STOP


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


_STOP = {"the", "and", "for", "with", "risk", "audit", "review", "process", "of", "to", "in", "a", "an", "is", "are"}


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in _STOP}


def _check(status, label, detail, gap=None):
    return {"label": label, "status": status, "detail": detail, "gap": gap}


# ── Engagement-wide coherence matching (checks 6-10 below) ──────────────────
# Checks 1-5 above were left unchanged when 6-10 were added — except check 2,
# which moved onto a reference once scope items started recording the risk area
# that produced them, and now reports how many it answered each way.
# Checks 6-10 instead reuse audit_memory.py's fuller
# stopword list and its title-weighted score-with-threshold (score = 2x
# shared title words + shared body words, threshold >=2), built for exactly
# this kind of broad, heterogeneous comparison (tens of RACM risks vs. a
# handful of TI risk areas) — checks 1-5's "one shared word = covered" rule is
# too coarse here: two items that only share generic words (e.g. both mention
# "process controls" but concern unrelated topics) must NOT read as covered.

def _kw(*texts) -> set[str]:
    """audit_memory's tokenizer + fuller stopword list, reused (not
    duplicated) for checks 6-10's broader matching. Deliberately a separate
    name from this module's own _keywords (checks 1-5)."""
    out = set()
    for t in texts:
        if not t:
            continue
        for w in re.split(r"[^a-z0-9]+", str(t).lower()):
            if len(w) >= 3 and w not in _AM_STOP:
                out.add(w)
    return out


def _title_weighted_score(title_a: str, text_a: str, title_b: str, text_b: str) -> int:
    """score = 2x shared title words + shared body words (title overlap not
    double-counted). audit_memory._score compares one flattened query set
    against one candidate's title/body; this adapts the same idiom to a
    two-sided comparison where BOTH items have their own title + body."""
    ta, tb = _kw(title_a), _kw(title_b)
    ba, bb = _kw(text_a), _kw(text_b)
    t_hit = ta & tb
    b_hit = (ba & bb) - t_hit
    return 2 * len(t_hit) + len(b_hit)


_OPINION_RANK = {"satisfactory": 0, "needs_improvement": 1, "unsatisfactory": 2}


def _opinion_floor(findings) -> str:
    """A small, engagement-scoped severity floor from Finding.rating counts —
    deliberately NOT board_report._opinion(), which is portfolio-shaped.
    Forcing one engagement's findings through a portfolio-shaped function
    would be the same kind of wrong-scope trap as the earlier
    regulatory_run_id bug in this codebase."""
    high = sum(1 for f in findings if f.rating == "high")
    medium = sum(1 for f in findings if f.rating == "medium")
    if high >= 3:
        return "unsatisfactory"
    if high or medium:
        return "needs_improvement"
    return "satisfactory"


def _coherence_ref_signature(kind: str, obj) -> str:
    """A stable signature for one artifact cited by a coherence observation —
    reused when a run is first stored (review_service.py), when its staleness
    is recomputed at read time (routers/review.py), and by check 10 below's
    own cheap staleness read. `obj` is a Finding ORM row for kind='finding'
    (so explainability_annex._finding_signature can be reused directly,
    rather than reinvented); a plain {"title", "description"/"rationale"}
    dict for 'ti_risk_area'/'racm_risk' — neither has an existing signature
    helper, so a small sha1 over their own title+body is defined here."""
    if kind == "finding":
        from services.explainability_annex import _finding_signature
        return _finding_signature(obj)
    if kind == "ti_risk_area":
        return hashlib.sha1(f"{obj.get('title', '')}␟{obj.get('rationale', '')}".encode("utf-8")).hexdigest()
    if kind == "racm_risk":
        return hashlib.sha1(f"{obj.get('title', '')}␟{obj.get('description', '')}".encode("utf-8")).hexdigest()
    return ""


def coherence_run_signature(refs_and_objs: list[tuple[str, object]]) -> str:
    """ONE signature for a whole coherence run — deliberately run-level, not
    per-observation (there is no per-item staleness slot anywhere in the UI;
    this mirrors board_signature(), the one proven precedent for a
    whole-run signature). sha1 over the sorted per-ref signatures of every
    artifact any confirmed observation cited."""
    sigs = sorted(_coherence_ref_signature(kind, obj) for kind, obj in refs_and_objs)
    return hashlib.sha1(json.dumps(sigs).encode("utf-8")).hexdigest()


async def recompute_coherence_signature(engagement_id: str, cited_refs: list[dict], db) -> str:
    """Refetch each cited artifact CURRENT and recompute the run signature —
    the read-time half of the coherence staleness check, mirroring
    board_report.latest_narrative()'s recompute-and-compare pattern. A ref
    whose artifact no longer exists (e.g. a finding was deleted) can never
    match its stored signature again, so the run correctly reads stale rather
    than silently skipping it. `cited_refs`: [{"kind","id"}, ...] as stored in
    the coherence AiAnalysis result by review_service._run_coherence_check."""
    if not cited_refs:
        return ""
    ti_areas_by_id = None
    refs_and_objs = []
    for ref in cited_refs:
        kind, rid = ref.get("kind"), ref.get("id")
        if kind == "finding":
            f = await db.get(Finding, rid)
            if f is not None:
                refs_and_objs.append(("finding", f))
        elif kind == "racm_risk":
            r = await db.get(RacmRisk, rid)
            if r is not None:
                refs_and_objs.append(("racm_risk", {"title": r.title, "description": r.description or ""}))
        elif kind == "ti_risk_area":
            if ti_areas_by_id is None:
                ti = (await db.execute(
                    select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
                )).scalar_one_or_none()
                ti_areas_by_id = {a.get("id"): a for a in _loads(ti.key_risk_areas if ti else None, [])}
            area = ti_areas_by_id.get(rid)
            if area is not None:
                refs_and_objs.append(("ti_risk_area", area))
    return coherence_run_signature(refs_and_objs)


async def compute_coverage(engagement_id: str, db) -> dict:
    ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
    risk_areas = _loads(ti.key_risk_areas if ti else None, [])

    scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))).scalar_one_or_none()
    items, questions = [], []
    if scope:
        items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
        questions = (await db.execute(select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars().all()
    in_scope = [i for i in items if i.item_type == "in_scope"]

    fws = (await db.execute(select(ApplicableFramework).where(ApplicableFramework.engagement_id == engagement_id))).scalars().all()
    rr = (await db.execute(select(RegRequirement).where(RegRequirement.engagement_id == engagement_id))).scalar_one_or_none()
    requirements = _loads(rr.items if rr else None, [])

    wp_rows = await _wp_rows(engagement_id, db)

    checks = []

    # 1. Scope defined
    if not in_scope:
        checks.append(_check("empty", "Scope defined", "No in-scope items yet", "Define scope from Topic Intelligence."))
    else:
        checks.append(_check("ok", "Scope defined", f"{len(in_scope)} in-scope, {len(items) - len(in_scope)} out-of-scope"))

    # 2. Risk areas translated to scope — by reference where there is one.
    #
    # A scope item cascaded from Topic Intelligence now records the risk area
    # that produced it (`source_ref`, see services/scope_sources.py), so this
    # question has a real answer for every item written since. The word overlap
    # survives only for items that predate the field, and the check says how
    # many of each it used rather than presenting a guess as a finding.
    if risk_areas:
        cited = {i.source_ref for i in in_scope
                 if i.source_ref and scope_sources.normalise(i.source)
                 == scope_sources.TOPIC_INTELLIGENCE}
        # The fallback reads every in-scope item, not only the ones with no
        # reference. A risk area can be covered by an item that came from the
        # frameworks agent, and narrowing the word pass to legacy items alone
        # would have turned those into fresh gaps — a stricter check dressed up
        # as a more precise one.
        scope_kw = set().union(*[_keywords(i.description) for i in in_scope]) if in_scope else set()

        uncovered, by_ref = [], 0
        for r in risk_areas:
            if r.get("id") and r["id"] in cited:
                by_ref += 1
            elif not (_keywords(r.get("title", "")) & scope_kw):
                uncovered.append(r)
        guessed = len(risk_areas) - by_ref - len(uncovered)
        how = f"{by_ref} by reference" + (f", {guessed} on wording" if guessed else "")

        if uncovered:
            checks.append(_check("gap", "Risk areas in scope",
                                 f"{len(risk_areas) - len(uncovered)}/{len(risk_areas)} key risk areas reflected in scope ({how})",
                                 f"Not clearly in scope: {', '.join(r.get('title', '?') for r in uncovered[:3])}"))
        else:
            checks.append(_check("ok", "Risk areas in scope",
                                 f"All {len(risk_areas)} key risk areas reflected in scope ({how})"))

    # 3. Key audit questions
    if not questions:
        checks.append(_check("empty", "Key audit questions", "None defined yet"))
    else:
        checks.append(_check("ok", "Key audit questions", f"{len(questions)} question(s) defined"))

    # 4. Frameworks
    if not fws:
        checks.append(_check("empty", "Applicable frameworks", "None identified yet"))
    else:
        accepted = sum(1 for f in fws if f.is_accepted)
        checks.append(_check("ok", "Applicable frameworks", f"{len(fws)} framework(s), {accepted} accepted"))

    # 5. Work program covers the questions — on wording, and nothing better
    # exists. Nothing links a key audit question to a test, so unlike check 2
    # this one cannot be put on a reference; what it can do is say so, rather
    # than reading like the checks that can.
    if not wp_rows:
        if questions or in_scope:
            checks.append(_check("gap", "Tests cover questions", "No work-program rows yet",
                                 "Generate the work program to cover scope and questions."))
        else:
            checks.append(_check("empty", "Tests cover questions", "No work program yet"))
    elif questions:
        # An objective records which key audit questions the rows beneath it
        # help answer — the generator is given the questions and says so per
        # row. An objective the scoping engine built from a question carries
        # that question's id instead. Either way the answer is a reference.
        #
        # "Covered" means a question reaches an objective that has at least one
        # test under it. An objective naming a question and testing nothing is
        # not an answer to it, which is the case this check exists to catch.
        async def _all(model):
            return (await db.execute(
                select(model).where(model.engagement_id == engagement_id)
            )).scalars().all()

        objectives = await _all(RacmObjective)
        controls_by_id = {c.id: c for c in await _all(RacmControl)}
        risks_by_id = {r.id: r for r in await _all(RacmRisk)}

        tested_objectives = set()
        for t in await _all(RacmTest):
            control = controls_by_id.get(t.control_id)
            risk = risks_by_id.get(control.risk_id) if control else None
            if risk and risk.objective_id:
                tested_objectives.add(risk.objective_id)

        answered = set()
        for o in objectives:
            if o.id not in tested_objectives:
                continue
            prov = _loads(o.provenance, {}) or {}
            for qid in (prov.get("answers") or []):
                answered.add(qid)
            if prov.get("source_id"):
                answered.add(prov["source_id"])

        wp_kw = set().union(*[_keywords(f"{r.get('process','')} {r.get('activity','')} {r.get('risk_description','')}") for r in wp_rows])
        uncovered_q, by_ref = [], 0
        for q in questions:
            if q.id in answered:
                by_ref += 1
            elif len(_keywords(q.question_text) & wp_kw) < 2:
                uncovered_q.append(q)
        worded = len(questions) - by_ref - len(uncovered_q)
        how = f"{by_ref} by reference" + (f", {worded} on wording" if worded else "")

        if uncovered_q:
            checks.append(_check("gap", "Tests cover questions",
                                 f"{len(questions) - len(uncovered_q)}/{len(questions)} questions have related tests ({how})",
                                 f"{len(uncovered_q)} question(s) have no clearly related test procedure."))
        else:
            checks.append(_check("ok", "Tests cover questions",
                                 f"All {len(questions)} questions have related tests ({how})"))
    else:
        checks.append(_check("ok", "Work program", f"{len(wp_rows)} test row(s)"))

    # ── 6-10: engagement-wide coherence (RACM/Fieldwork/Findings/Report) ────
    racm_risks = (await db.execute(select(RacmRisk).where(RacmRisk.engagement_id == engagement_id))).scalars().all()
    racm_tests = (await db.execute(select(RacmTest).where(RacmTest.engagement_id == engagement_id))).scalars().all()
    all_findings = (await db.execute(select(Finding).where(Finding.engagement_id == engagement_id))).scalars().all()
    report = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == engagement_id))).scalar_one_or_none()

    # 6. Key risks reflected in RACM scoping (fuzzy — see _title_weighted_score).
    ti_risk_areas = [r for r in risk_areas if r.get("included") is not False]
    if not racm_risks:
        # empty (not gap) regardless of TI state: RACM scoping simply hasn't
        # started yet. A "gap" here would resurface quality_coverage's "done"
        # signal as false all the way to RACM scoping for every engagement —
        # exactly the regression this empty/gap idiom exists to avoid.
        checks.append(_check("empty", "Key risks reflected in RACM scoping", "RACM risk register not started yet"))
    elif not ti_risk_areas:
        checks.append(_check("empty", "Key risks reflected in RACM scoping", "No key risk areas defined in Topic Intelligence yet"))
    else:
        # A risk the scoping engine proposed records the id of the row it came
        # from, so for those the answer is a fact. The score survives for risks
        # written by hand or by an agent that does not record one.
        cited = set()
        for r in racm_risks:
            sid = (_loads(r.provenance, {}) or {}).get("source_id")
            if sid:
                cited.add(sid)

        racm_pairs = [(r.title, r.description or "") for r in racm_risks]
        uncovered, by_ref = [], 0
        for r in ti_risk_areas:
            if r.get("id") and r["id"] in cited:
                by_ref += 1
            elif max((_title_weighted_score(r.get("title", ""), r.get("rationale", ""), t, d)
                      for t, d in racm_pairs), default=0) < 2:
                uncovered.append(r)
        scored = len(ti_risk_areas) - by_ref - len(uncovered)
        how = f"{by_ref} by reference" + (f", {scored} on wording" if scored else "")

        if uncovered:
            checks.append(_check("gap", "Key risks reflected in RACM scoping",
                                 f"{len(ti_risk_areas) - len(uncovered)}/{len(ti_risk_areas)} key risk areas reflected in RACM scoping ({how})",
                                 f"Not clearly scoped in RACM: {', '.join(r.get('title', '?') for r in uncovered[:3])}"))
        else:
            checks.append(_check("ok", "Key risks reflected in RACM scoping",
                                 f"All {len(ti_risk_areas)} key risk areas reflected in RACM scoping ({how})"))

    # 7. RACM testing failures captured as findings — exact ID join, no fuzzy
    # matching: the most solid of these five checks.
    failed_tests = [t for t in racm_tests if t.result in ("fail", "exceptions")]
    if not failed_tests:
        checks.append(_check("empty", "RACM testing failures captured as findings", "No failed/exception test results yet"))
    else:
        finding_test_ids = {f.racm_test_id for f in all_findings if f.racm_test_id}
        uncovered_tests = [t for t in failed_tests if t.id not in finding_test_ids]
        if uncovered_tests:
            checks.append(_check("gap", "RACM testing failures captured as findings",
                                 f"{len(failed_tests) - len(uncovered_tests)}/{len(failed_tests)} failed test(s) promoted to a finding",
                                 f"No finding yet for: {', '.join((t.ref or t.title) for t in uncovered_tests[:3])}"))
        else:
            checks.append(_check("ok", "RACM testing failures captured as findings", f"All {len(failed_tests)} failed test(s) are captured as findings"))

    # 8. Report opinion consistent with findings — only meaningful once the
    # report is ready. Deliberately NOT board_report._opinion() (portfolio-
    # shaped) — see _opinion_floor's own docstring.
    if not report or report.status != "ready":
        checks.append(_check("empty", "Report opinion consistent with findings", "Report not finalised yet"))
    else:
        floor = _opinion_floor(all_findings)
        actual = report.overall_opinion
        if actual not in _OPINION_RANK or _OPINION_RANK[actual] < _OPINION_RANK[floor]:
            checks.append(_check("gap", "Report opinion consistent with findings",
                                 f"Report opinion '{actual or 'not set'}' vs. findings-implied floor '{floor}'",
                                 f"The findings suggest at least '{floor}' — the report opinion reads weaker."))
        else:
            checks.append(_check("ok", "Report opinion consistent with findings", f"Report opinion '{actual}' is consistent with the findings (floor: '{floor}')"))

    # 9. Report narrative reflects the findings — condition+effect ONLY
    # (factual fields). NEVER cause/recommendation: those are the auditor's
    # own reasoning/judgement, not a checkable fact (same claim-kind
    # distinction grounded_validator._CLAIM_META already makes). No natural
    # "title" exists on the report side, so this is a plain union-keyword
    # overlap — same stopword list + >=2 threshold as check 6, without the
    # title-weighting (which needs a title on both sides to mean anything).
    if not report or report.status != "ready":
        checks.append(_check("empty", "Report narrative reflects the findings", "Report not finalised yet"))
    elif not all_findings:
        checks.append(_check("empty", "Report narrative reflects the findings", "No findings recorded yet"))
    else:
        narrative_kw = _kw(report.exec_summary or "", report.conclusion or "")
        findings_kw = set()
        for f in all_findings:
            findings_kw |= _kw(f.condition or "", f.effect or "")
        shared = narrative_kw & findings_kw
        if len(shared) < 2:
            checks.append(_check("gap", "Report narrative reflects the findings",
                                 "The report narrative shares little vocabulary with the findings' condition/effect",
                                 "Check that the exec summary and conclusion actually reflect what was found."))
        else:
            checks.append(_check("ok", "Report narrative reflects the findings", f"Report narrative shares {len(shared)} keyword(s) with the findings"))

    # 10. Findings cross-checked for consistency — a cheap READ of the AI
    # coherence check's persisted status (Part 2b), no keyword logic of its
    # own. Staleness reuses recompute_coherence_signature, only computed when
    # comments are empty (a non-empty result already settles "gap" on its own)
    # — genuinely cheap here, a handful of point lookups at most.
    coherence_row = (await db.execute(
        select(AiAnalysis).where(
            AiAnalysis.engagement_id == engagement_id,
            AiAnalysis.kind == "quality_review",
            AiAnalysis.artifact == "coherence",
        )
    )).scalar_one_or_none()
    if not coherence_row or coherence_row.status in ("running", "no_data"):
        checks.append(_check("empty", "Findings cross-checked for consistency", "Coherence check not run yet"))
    elif coherence_row.status == "failed":
        checks.append(_check("gap", "Findings cross-checked for consistency", "Coherence check failed to run",
                             "Re-run the coherence check from the Quality Hub."))
    else:
        data = _loads(coherence_row.result, {})
        comments = data.get("comments") or []
        if comments:
            checks.append(_check("gap", "Findings cross-checked for consistency",
                                 f"{len(comments)} coherence observation(s) flagged",
                                 "Review the flagged observations in the Quality Hub."))
        else:
            cited_refs = data.get("cited_refs") or []
            current_sig = await recompute_coherence_signature(engagement_id, cited_refs, db) if cited_refs else ""
            stale = bool(cited_refs) and current_sig != data.get("based_on_sig")
            if stale:
                checks.append(_check("gap", "Findings cross-checked for consistency",
                                     "Coherence check is stale — cited data changed since it last ran",
                                     "Re-run the coherence check from the Quality Hub."))
            else:
                checks.append(_check("ok", "Findings cross-checked for consistency", "No coherence conflicts flagged, and the check is current"))

    gaps = sum(1 for c in checks if c["status"] == "gap")
    empties = sum(1 for c in checks if c["status"] == "empty")
    if gaps:
        summary = f"{gaps} coverage gap(s) to address across the planning chain."
    elif empties:
        summary = "Planning is still being built — some links are not in place yet."
    else:
        summary = "The planning chain is coherent — risks, scope, questions and tests line up."

    return {"summary": summary, "checks": checks, "gaps": gaps}


async def select_coherence_candidates(engagement_id: str, db) -> list[dict]:
    """Pure, read-only candidate selection for the opt-in AI coherence
    explainer (orchestrator_agent.explain_coherence) — NOT on the hot path,
    only called from the review-run button handler
    (review_service._run_coherence_check). Two candidate kinds:

      - ti_racm_gap: a TI key risk area with no matching RACM risk (score < 2,
        same matching helper as check 6) that has at least one "near miss"
        (0 < score < 2) worth an AI explanation. A risk area with literally
        nothing close in RACM needs no AI nuance — check 6 already says so
        plainly — so those are deliberately left out here.
      - finding_pair_conflict: two findings whose condition+effect overlap
        (score >= 2) but whose rating differs — a possible inconsistency.
        Capped to a small top-N (8), same idea as audit_memory.recall's limit.

    Each candidate carries a stable identity ("id") and enough raw fields for
    the caller to build a quote-verification corpus and a run signature.
    """
    ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
    risk_areas = [r for r in _loads(ti.key_risk_areas if ti else None, []) if r.get("included") is not False]
    racm_risks = (await db.execute(select(RacmRisk).where(RacmRisk.engagement_id == engagement_id))).scalars().all()
    findings = (await db.execute(select(Finding).where(Finding.engagement_id == engagement_id))).scalars().all()

    candidates: list[dict] = []

    for area in risk_areas:
        if not area.get("id"):
            continue
        scored = sorted(
            ((_title_weighted_score(area.get("title", ""), area.get("rationale", ""), r.title, r.description or ""), r)
             for r in racm_risks),
            key=lambda pair: -pair[0],
        )
        if scored and scored[0][0] >= 2:
            continue  # check 6 already reads this as covered
        near_misses = [r for score, r in scored if 0 < score < 2][:3]
        if not near_misses:
            continue  # nothing close enough to explain against — check 6's plain gap already says enough
        candidates.append({
            "id": area["id"], "kind": "ti_racm_gap",
            "ti_risk_area": {"id": area["id"], "title": area.get("title", ""), "rationale": area.get("rationale", "")},
            "near_miss_racm_risks": [
                {"id": r.id, "title": r.title, "description": r.description or ""} for r in near_misses
            ],
        })

    pairs = []
    for i in range(len(findings)):
        for j in range(i + 1, len(findings)):
            fa, fb = findings[i], findings[j]
            if (fa.rating or None) == (fb.rating or None):
                continue
            score = _title_weighted_score(
                fa.title, f"{fa.condition or ''} {fa.effect or ''}",
                fb.title, f"{fb.condition or ''} {fb.effect or ''}",
            )
            if score >= 2:
                pairs.append((score, fa, fb))
    pairs.sort(key=lambda p: -p[0])
    for score, fa, fb in pairs[:8]:
        candidates.append({
            "id": ":".join(sorted([fa.id, fb.id])), "kind": "finding_pair_conflict",
            "findings": [
                {"id": fa.id, "title": fa.title, "condition": fa.condition or "", "effect": fa.effect or "", "rating": fa.rating},
                {"id": fb.id, "title": fb.title, "condition": fb.condition or "", "effect": fb.effect or "", "rating": fb.rating},
            ],
        })

    return candidates
