"""Explainability annex — a defensible, traceable account of every finding.

For each finding we assemble a five-question annex, anchored in the EU AI Act
Art. 13/14 transparency & human-oversight principles, that answers "how did you
arrive at this?" the way a management response demands:

    1. What is this finding based on?          (grounding)
    2. How was it produced?                     (provenance + human oversight)
    3. What was assumed or inferred?            (assumptions / limits)
    4. How confident is it, and what limits?    (coverage + second opinion)
    5. How can it be challenged?                (management-response readiness)

DETERMINISTIC-FIRST: the annex is built entirely from data already on the finding
and the RACM spine (5C fields, rating, second-opinion challenge, the test/control/
risk/objective lineage, evidence, coverage). No AI is needed and the grounding
trail is real — it points at existing evidence, never invented. An optional,
opt-in `sharpen_annex` step rephrases the answers into crisp language WITHOUT
adding facts. The GET endpoint rebuilds the scaffold fresh every time, so it never
goes stale; only the sharpened answers are persisted.

The strength meter measures how much *traceable support* exists — NOT whether the
finding is correct. That honesty is deliberate (see the Assurance Center's
"honesty over green" principle).
"""
from __future__ import annotations

import json
import hashlib

from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT


def _finding_signature(finding) -> str:
    """A stable hash of the finding's SUBSTANTIVE content. Sharpened answers are
    flagged stale when this changes — independent of the explainability write,
    which itself bumps updated_at."""
    parts = [
        _s(getattr(finding, k, None)) for k in
        ("title", "condition", "criteria", "cause", "effect", "recommendation", "rating", "rating_rationale")
    ]
    challenge = getattr(finding, "rating_challenge", None)
    parts.append(challenge if isinstance(challenge, str) else json.dumps(challenge, sort_keys=True) if challenge else "")
    return hashlib.sha1("␟".join(parts).encode("utf-8")).hexdigest()

# Human-readable labels for the RACM agent that first proposed a promoted finding.
_SOURCE_LABELS = {
    "data_analysis": "Data-analysis agent",
    "control_testing": "Control-testing agent",
    "governance_assessor": "Governance-document assessor",
    "scoping_engine": "Scoping engine",
}

_STRENGTH_FACTORS = [
    ("grounded", "Linked to evidence or a tested control", 25),
    ("full_population", "Full-population coverage (no sampling risk)", 20),
    ("second_opinion", "Independent second opinion on the rating", 15),
    ("human_accepted", "Confirmed by a human (oversight)", 15),
    ("five_c_complete", "All five C's are stated", 15),
    ("criteria_present", "An explicit norm/criterion is given", 10),
]

QUESTIONS = [
    "What is this finding based on?",
    "How was it produced?",
    "What was assumed or inferred?",
    "How confident is it, and what are the limits?",
    "How can it be challenged?",
]


def _s(v) -> str:
    return (v or "").strip() if isinstance(v, str) else ""


def _short(v, n=160) -> str:
    t = _s(v)
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _g(node):
    """Safe attribute reader — works for ORM objects and plain stubs."""
    return node if node is not None else None


def build_annex(
    finding,
    *,
    objective=None,
    risk=None,
    control=None,
    test=None,
    evidence=None,
    source_observation=False,
    sharpened=None,
) -> dict:
    """Assemble the deterministic annex. `sharpened` (optional) is a dict of
    {question_index_str: rewritten_answer} that overlays the scaffold answers."""
    evidence = list(evidence or [])
    ex = getattr(test, "exceptions_count", None) if test else None
    sample = getattr(test, "sample_size", None) if test else None
    method = _s(getattr(test, "method", None)) if test else ""
    full_pop = method == "full_population"

    condition = _s(getattr(finding, "condition", None))
    criteria = _s(getattr(finding, "criteria", None))
    cause = _s(getattr(finding, "cause", None))
    effect = _s(getattr(finding, "effect", None))
    recommendation = _s(getattr(finding, "recommendation", None))
    rating = _s(getattr(finding, "rating", None)) or "unrated"
    rationale = _s(getattr(finding, "rating_rationale", None))

    challenge_raw = getattr(finding, "rating_challenge", None)
    challenge = None
    if isinstance(challenge_raw, dict):
        challenge = challenge_raw
    elif isinstance(challenge_raw, str) and challenge_raw:
        try:
            challenge = json.loads(challenge_raw)
        except (ValueError, TypeError):
            challenge = None

    # Provenance of the promoting agent, if this came off the RACM spine.
    prov = {}
    if test is not None:
        praw = getattr(test, "provenance", None)
        if isinstance(praw, dict):
            prov = praw
        elif isinstance(praw, str) and praw:
            try:
                prov = json.loads(praw) or {}
            except (ValueError, TypeError):
                prov = {}
    source_type = prov.get("source_type") or (_s(getattr(test, "method", None)) and "control_testing")
    agent_label = _SOURCE_LABELS.get(source_type)

    ai_drafted = bool(_s(getattr(finding, "drafter_run_id", None)))
    ai_proposed = bool(test is not None and getattr(test, "origin", None) == "ai")
    ai_involved = ai_drafted or ai_proposed or challenge is not None

    accepted_refs = [
        getattr(n, "ref", None)
        for n in (objective, risk, control, test)
        if n is not None and getattr(n, "accepted", False)
    ]
    accepted_refs = [r for r in accepted_refs if r]

    grounding_trail = [
        getattr(n, "ref", None) for n in (objective, risk, control, test) if n is not None and getattr(n, "ref", None)
    ]
    grounding_trail += [getattr(e, "ref", None) for e in evidence if getattr(e, "ref", None)]

    # ── grounding chips (SourceChip kinds the frontend maps) ────────────────────
    def chips_for_evidence():
        out = []
        kind_map = {"document": "document", "data": "data", "interview": "interview", "observation": "observation"}
        for e in evidence:
            out.append({"kind": kind_map.get(_s(getattr(e, "kind", None)), "document"),
                        "label": _short(getattr(e, "title", None) or "Evidence", 48)})
        return out

    # ── Q1 — What is this finding based on? ─────────────────────────────────────
    q1_parts, q1_chips = [], []
    if test is not None:
        cov = f"full population of {sample}" if (full_pop and sample) else (f"a sample of {sample}" if sample else "the tested items")
        q1_parts.append(
            f"Derived from control test {getattr(test, 'ref', '') or ''} "
            f"“{_short(getattr(test, 'title', None) or 'test', 80)}”, which examined {cov}"
            + (f" and found {ex} exception(s)." if ex is not None else ".")
        )
        q1_chips.append({"kind": "data", "label": f"Test {getattr(test, 'ref', '') or ''}".strip()})
    if evidence:
        q1_parts.append("Supporting evidence: " + ", ".join(_short(getattr(e, "title", None) or "item", 48) for e in evidence) + ".")
        q1_chips += chips_for_evidence()
    if source_observation:
        q1_parts.append("It originates from a recorded fieldwork observation.")
        q1_chips.append({"kind": "observation", "label": "Fieldwork observation"})
    if not q1_parts:
        q1_parts.append(
            f"Based on the auditor's recorded condition: “{_short(condition, 140) or 'not yet stated'}”."
        )
        q1_chips.append({"kind": "model", "label": "Auditor-entered"})
    q1 = " ".join(q1_parts)

    # ── Q2 — How was it produced? ───────────────────────────────────────────────
    q2_parts = []
    if ai_proposed:
        q2_parts.append(
            f"Proposed by the {agent_label or 'AI agent'} on the RACM spine, then promoted to a 5C finding."
        )
    if ai_drafted:
        q2_parts.append("The 5C structure and rating were drafted by AI.")
    if challenge is not None:
        verdict = "upheld the rating" if challenge.get("agrees") else f"suggested a rating of {challenge.get('suggested_rating', '')}"
        q2_parts.append(f"A second, independent agent {verdict}.")
    if accepted_refs:
        q2_parts.append(f"A human confirmed the underlying spine nodes ({', '.join(accepted_refs)}) — human oversight per EU AI Act Art. 14.")
    if not ai_involved:
        q2_parts = ["Human-authored; no AI proposal was involved."]
    elif not accepted_refs:
        q2_parts.append("Every AI proposal remains subject to the auditor's confirmation — the human decides.")
    q2 = " ".join(q2_parts)

    # ── Q3 — What was assumed or inferred? ──────────────────────────────────────
    q3_parts = []
    if rationale:
        q3_parts.append(f"Rating inference: {rationale}")
    if risk is not None and _s(getattr(risk, "inherent_rating", None)) == rating:
        q3_parts.append("The rating is inferred from the inherent risk rating, not yet from tested residual risk.")
    missing = [name for name, val in (("cause", cause), ("effect", effect), ("recommendation", recommendation)) if not val]
    if missing:
        q3_parts.append("Still assumed rather than established: " + ", ".join(missing) + ".")
    if not q3_parts:
        q3_parts.append("No material assumptions beyond the stated evidence; the 5C are grounded in the recorded facts.")
    q3 = " ".join(q3_parts)

    # ── Q4 — How confident is it, and what are the limits? ──────────────────────
    q4_parts = []
    if test is not None:
        if full_pop and sample:
            q4_parts.append(f"Coverage: the full population of {sample} item(s) was examined — no sampling risk.")
        elif sample:
            q4_parts.append(f"Coverage: a sample of {sample} item(s); conclusions carry the usual sampling risk and may not generalise.")
    if challenge is not None:
        if challenge.get("agrees"):
            q4_parts.append("A second reviewer independently agreed with the rating.")
        else:
            q4_parts.append(f"A second reviewer disagreed and suggested “{challenge.get('suggested_rating', '')}”, so the rating is contested and warrants extra scrutiny.")
    if not criteria:
        q4_parts.append("The criterion/norm is not yet fully specified, which limits the strength of the conclusion.")
    if not q4_parts:
        q4_parts.append("Confidence rests on the recorded evidence; no independent second opinion is attached yet.")
    q4 = " ".join(q4_parts)

    # ── Q5 — How can it be challenged? ──────────────────────────────────────────
    q5_parts = ["The auditee could dispute this finding by showing that"]
    challenges = []
    if test is not None and not full_pop and sample:
        challenges.append("the sample was unrepresentative or the exceptions were isolated")
    if ex is not None:
        challenges.append("the exceptions were already remediated or fall outside the audit period")
    if criteria:
        challenges.append("the stated criterion does not apply to the process as designed")
    else:
        challenges.append("no binding criterion actually requires the expected condition")
    q5_parts.append("; ".join(challenges) + ".")
    q5_parts.append(
        "It would be refuted by evidence that the control operated effectively across the population, "
        "or by a documented, approved exception to the criterion."
    )
    q5 = " ".join(q5_parts)

    scaffold = [q1, q2, q3, q4, q5]

    # ── strength meter (grounding, not correctness) ─────────────────────────────
    flags = {
        "grounded": bool(test is not None or evidence or source_observation),
        "full_population": bool(full_pop and sample),
        "second_opinion": challenge is not None,
        "human_accepted": bool(accepted_refs) or _s(getattr(finding, "status", None)) in ("ready",),
        "five_c_complete": all([condition, criteria, cause, effect, recommendation]),
        "criteria_present": bool(criteria),
    }
    score = sum(w for key, _label, w in _STRENGTH_FACTORS if flags.get(key))
    # sampling coverage earns partial credit for the full-population factor.
    if not flags["full_population"] and test is not None and sample:
        score += 10
    score = max(0, min(100, score))
    label = "Well-grounded" if score >= 70 else ("Partially grounded" if score >= 40 else "Thinly grounded")
    factors = [{"key": k, "label": lbl, "present": bool(flags.get(k)), "weight": w} for k, lbl, w in _STRENGTH_FACTORS]

    signs = ["check", "info", "gap", "info", "info"]
    questions = []
    for i, (q, a, sign) in enumerate(zip(QUESTIONS, scaffold, signs), start=1):
        ans = a
        if sharpened and sharpened.get(str(i)):
            ans = _s(sharpened.get(str(i)))
        questions.append({
            "n": i, "q": q, "answer": ans, "sign": sign,
            "grounding": q1_chips if i == 1 else [],
        })

    return {
        "finding_id": getattr(finding, "id", None),
        "ai_involved": ai_involved,
        "questions": questions,
        "grounding_trail": grounding_trail,
        "strength": {"score": score, "label": label, "factors": factors},
        "reference": "Aligned with EU AI Act Art. 13/14 — transparency & human-oversight principles",
    }


# ── Optional AI sharpening (opt-in; rephrase only, never add facts) ─────────────

_SHARPEN_SYSTEM = BASE_SYSTEM_PROMPT + """

EXPLAINABILITY-SHARPEN ROLE:
You rewrite the answers of a finding's explainability annex into crisp, professional
management-response language. STRICT RULES:
- Do NOT introduce any new fact, number, name, control, or claim. Only rephrase what is given.
- Keep every figure, rating, reference code and evidence name exactly as-is.
- Keep each answer to 1-3 sentences, neutral and precise. Do not overstate.
"""


async def sharpen_annex(annex: dict) -> dict:
    """Rewrite the five answers via one AI call. Returns {index_str: answer}.
    Best-effort — the caller keeps the deterministic scaffold on failure."""
    payload = {str(q["n"]): q["answer"] for q in annex.get("questions", [])}
    prompt = (
        "Rewrite each answer below into crisp management-response language, following the rules. "
        "Return ONLY a JSON object mapping the same keys to the rewritten answers.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    out = await run_agent_to_json(_SHARPEN_SYSTEM, prompt, max_tokens=1500)
    if not isinstance(out, dict):
        raise ValueError("sharpen returned no object")
    cleaned = {k: _s(v) for k, v in out.items() if str(k) in {"1", "2", "3", "4", "5"} and _s(v)}
    if not cleaned:
        raise ValueError("sharpen returned no usable answers")
    return cleaned


# ── DB-aware assembly (reads the RACM spine; no router coupling) ────────────────

async def _fetch_lineage(db, finding):
    """Walk test → control → risk → objective + evidence for a finding, if it was
    promoted off the RACM spine. Returns a dict of the resolved nodes."""
    from models.racm import RacmObjective, RacmRisk, RacmControl, RacmTest, RacmEvidence
    from models.planning import FieldworkObservation
    from sqlalchemy import select

    test = await db.get(RacmTest, finding.racm_test_id) if getattr(finding, "racm_test_id", None) else None
    control = await db.get(RacmControl, test.control_id) if test and test.control_id else None
    risk = await db.get(RacmRisk, control.risk_id) if control and control.risk_id else None
    objective = await db.get(RacmObjective, risk.objective_id) if risk and risk.objective_id else None
    evidence = []
    if test is not None:
        evidence = (await db.execute(
            select(RacmEvidence).where(RacmEvidence.test_id == test.id).order_by(RacmEvidence.sort_order)
        )).scalars().all()
    source_observation = False
    if getattr(finding, "source_observation_id", None):
        source_observation = await db.get(FieldworkObservation, finding.source_observation_id) is not None
    return {"objective": objective, "risk": risk, "control": control, "test": test,
            "evidence": evidence, "source_observation": source_observation}


def _persisted_answers(finding):
    raw = getattr(finding, "explainability", None)
    if not raw:
        return None, None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None, None
    return data.get("answers"), data


async def assemble(db, finding) -> dict:
    """Build a fresh deterministic annex and overlay any persisted sharpened
    answers, flagging them stale if the finding changed after sharpening."""
    parts = await _fetch_lineage(db, finding)
    answers, meta = _persisted_answers(finding)
    annex = build_annex(finding, sharpened=answers, **parts)
    if meta and answers:
        annex["sharpened_at"] = meta.get("sharpened_at")
        annex["sharpen_stale"] = meta.get("based_on_sig") != _finding_signature(finding)
    return annex


async def sharpen_finding_annex(finding_id: str, engagement_id: str):
    """Opt-in background task: build the annex, sharpen its answers via one AI
    call, and persist ONLY the sharpened answers. Best-effort."""
    from database import AsyncSessionLocal
    from models.reporting import Finding

    async with AsyncSessionLocal() as db:
        f = await db.get(Finding, finding_id)
        if not f or f.engagement_id != engagement_id:
            return
        annex = await assemble(db, f)
    try:
        answers = await sharpen_annex(annex)
    except Exception:  # noqa: BLE001
        return  # keep the deterministic scaffold on failure
    async with AsyncSessionLocal() as db:
        f = await db.get(Finding, finding_id)
        if not f:
            return
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        f.explainability = json.dumps({
            "answers": answers, "sharpened_at": now, "based_on_sig": _finding_signature(f),
        })
        await db.commit()
