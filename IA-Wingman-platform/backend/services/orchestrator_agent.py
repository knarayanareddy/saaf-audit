"""Orchestrator Agent — advisory-only AI layer inside a single engagement.

Contract (non-negotiable, applies to every function here): this module may
only SYNTHESISE, ORDER, and EXPLAIN. It never bypasses a STAGE_GRAPH gate,
never exceeds the semaphore/budget the deterministic engine already enforces,
and never starts anything the deterministic engine did not already allow. On
any error, timeout, or malformed model response, every entry point fails open
to the exact current deterministic behaviour — callers rely on this and use a
bare `except Exception` around each call, mirroring the existing primer-call
pattern in services/orchestrator.py. The one exception is explain_coherence
(opt-in, click-only — never on an autonomous path), which raises instead; see
its own docstring.
"""
import logging
from uuid import uuid4

from models.engagement import Engagement, jurisdictions_or_default
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services.prompt_safety import wrap_untrusted, safe_label
from services.grounded_validator import _verify_quotes
from services.model_tiers import JUDGE

logger = logging.getLogger("ia.wingman")


# ── Topic Intelligence synthesis ────────────────────────────────────────────

_SYNTHESIS_SYSTEM = BASE_SYSTEM_PROMPT + (
    "\n\nYou are the Orchestrator Agent. You reconcile three independent research "
    "lenses on one audit topic into a single scoping proposal. You never invent a "
    "fact, regulation, or incident beyond what the lenses already reported — you "
    "organise, merge overlap, and surface tension; you do not add new claims."
)

_SYNTHESIS_KEYS = {"key_risk_areas", "excluded_areas", "interview_agenda", "conclusion", "proposed_frameworks"}
_AGENDA_KEYS = {"sponsor", "sme", "ia_prework"}
# Optional: a scan stored before this group existed still validates and loads.
_AGENDA_OPTIONAL_KEYS = {"key_audit_questions"}
# Where each kind of question goes once the auditor accepts the memo. The memo used
# to send sponsor and SME questions to Scope as key audit questions, which they are
# not: a sponsor question is asked at the kick-off, an SME question in an interview,
# and a key audit question is what the audit as a whole has to answer.
#   sponsor -> kick-off notes (questions_for_auditor)   sme -> interview guide
#   key_audit_questions -> Scope & Objectives           ia_prework -> stays a checklist
FRAMEWORK_TIERS = ("core", "supporting", "optional")
#: A short list the auditor starts from, not ten boxes to untick.
MAX_CORE_FRAMEWORKS = 5
# Top-level list-of-object fields the model returns already-shaped; only id +
# included get added post-validation. interview_agenda.sponsor/sme are the
# same idea one level deeper (see _stamp below) — ia_prework is NOT here, it
# stays a flat string list (read-only in the UI, never cascades, needs no id).
_STAMPED_LIST_FIELDS = ("key_risk_areas", "excluded_areas", "proposed_frameworks")


def _build_synthesis_prompt(
    eng: Engagement,
    lens1_summary: str | None,
    lens2_summary: str | None,
    lens3_summary: str | None,
    lens3_materiality_signal: str | None,
    verified: str | None = None,
) -> str:
    juris = ", ".join(jurisdictions_or_default(eng))
    parts = [
        f"Engagement: {eng.name} ({eng.entity}, {eng.audit_type}). Jurisdictions in scope: {juris}.",
        "Three independent research lenses have each studied this audit topic. "
        "Reconcile them into ONE scoping proposal.",
        wrap_untrusted(lens1_summary or "(no output from this lens)", "Lens 1 — Normative & Regulatory summary"),
        wrap_untrusted(lens2_summary or "(no output from this lens)", "Lens 2 — Supervisory & Enforcement summary"),
        wrap_untrusted(lens3_summary or "(no output from this lens)", "Lens 3 — Society, Trends & Incidents summary"),
    ]
    if lens3_materiality_signal:
        parts.append(wrap_untrusted(lens3_materiality_signal, "Lens 3 — materiality signal"))
    if verified:
        parts.append(wrap_untrusted(verified, "Verification of statements the lenses left open"))
        parts.append("The verification above is later and more specific than the lenses. Where it CORRECTS a lens, "
                     "follow the verification and say so in the item's rationale. Where it says NOT SETTLED, keep the "
                     "point open and name it as unconfirmed.")

    parts.append(f"""
Reconcile the three lenses above into a scoping proposal for this audit.

RULES:
- Base every claim ONLY on what the three lenses above actually said — never invent
  a fact, regulation, or incident that is not already present in one of them.
- When two or more lenses raise the same risk area, merge it into ONE entry and set
  "source" to "multiple" instead of listing it more than once.
- When lenses conflict (e.g. one downplays a risk another treats as material), name
  that tension explicitly inside the relevant item's rationale — never silently pick a side.
- Every key risk area needs a specific, actionable title an auditor could scope work around.
- If a lens produced no output ("(no output from this lens)"), reason from the other two only.

Produce ONLY this JSON (no markdown, no text before or after):
{{
  "key_risk_areas": [
    {{"title": "...", "rationale": "...", "basis": "e.g. WWFT Art. 3, or empty string if none", "source": "Lens 1|Lens 2|Lens 3|multiple", "confidence": "high|medium|low"}}
  ],
  "excluded_areas": [
    {{"title": "...", "rationale": "why this is out of scope for this engagement"}}
  ],
  "interview_agenda": {{
    "sponsor": [{{"question_text": "question for the audit sponsor"}}],
    "sme": [{{"question_text": "question for a subject-matter expert"}}],
    "ia_prework": ["preparation task for the audit team itself", "..."],
    "key_audit_questions": [{{"question_text": "a question the audit as a whole must be able to answer"}}]
  }},
  "conclusion": "Recommended scope in 2-3 sentences",
  "proposed_frameworks": [
    {{"framework_code": "e.g. WWFT", "framework_name": "full framework name", "applicability_rationale": "...", "jurisdiction": "NL|BE|UK|ES|EU|International", "is_primary": true, "confidence": "high|medium|low", "tier": "core|supporting|optional"}}
  ]
}}

Propose 4-6 key risk areas, 1-3 excluded areas, 2-4 sponsor questions, 2-4 SME
questions, 3-5 key audit questions, 1-3 IA prework tasks, and every framework a lens
actually named as applicable (omit "proposed_frameworks" entries the lenses never mentioned).

Questions go to three different places, so write each for its place:
- sponsor questions are put to the audit sponsor at the kick-off meeting: intent,
  expectations, scope boundaries, risk appetite, known issues.
- sme questions are put to a subject-matter expert in an interview: how the topic
  works in practice, where it is hard, what the expert would test.
- key audit questions are the questions the audit itself must be able to answer by its
  end (for example "Does the bank know every AI system it uses, and who owns each?").
  They are not interview questions.

Give every framework a "tier":
- "core": the audit cannot be done without it. At most 5, and only laws that apply to
  this bank directly.
- "supporting": relevant, to be tested selectively.
- "optional": adjacent or only relevant if the scope grows.
Do NOT include "id" or "included" fields anywhere — those are added afterwards.""")
    return "\n\n".join(parts)


def _valid_items(value, required_keys: set) -> bool:
    """True if value is a list of dicts, each containing every key in required_keys."""
    if not isinstance(value, list):
        return False
    return all(isinstance(item, dict) and required_keys.issubset(item.keys()) for item in value)


def _valid_questions(value) -> bool:
    """sponsor/sme items: a list of dicts, each with a non-empty string question_text."""
    if not isinstance(value, list):
        return False
    return all(
        isinstance(item, dict) and isinstance(item.get("question_text"), str) and item["question_text"].strip()
        for item in value
    )


def _valid_strings(value) -> bool:
    """ia_prework: a list of non-empty strings."""
    if not isinstance(value, list):
        return False
    return all(isinstance(s, str) and s.strip() for s in value)


def _validate_synthesis(result) -> bool:
    """Pure structural gate for synthesize_topic_intelligence's raw LLM output,
    BEFORE stamping — so the stamping step below never crashes trying to
    treat a malformed element as a dict.

    Deliberately strict at the top level: an exact 5-key match (missing,
    extra, or wrongly-typed top-level fields all fail) so a malformed
    synthesis can never reach persistence half-shaped — mirrors
    _validate_order's set()-based rigor. Item-level checks require only each
    item's load-bearing identifying field(s), not every optional field (e.g.
    "confidence") — the downstream cascade already treats those as optional
    via .get(...). Never raises; returns True/False.
    """
    if not isinstance(result, dict) or set(result.keys()) != _SYNTHESIS_KEYS:
        return False

    if not _valid_items(result["key_risk_areas"], {"title"}):
        return False
    if not _valid_items(result["excluded_areas"], {"title"}):
        return False
    if not _valid_items(result["proposed_frameworks"], {"framework_code", "framework_name"}):
        return False

    agenda = result["interview_agenda"]
    if not isinstance(agenda, dict) or not _AGENDA_KEYS <= set(agenda.keys()) <= _AGENDA_KEYS | _AGENDA_OPTIONAL_KEYS:
        return False
    if not _valid_questions(agenda["sponsor"]) or not _valid_questions(agenda["sme"]):
        return False
    if "key_audit_questions" in agenda and not _valid_questions(agenda["key_audit_questions"]):
        return False
    if not _valid_strings(agenda["ia_prework"]):
        return False

    if not isinstance(result["conclusion"], str):
        return False

    return True


def _stamp(item: dict) -> None:
    item["id"] = str(uuid4())
    item["included"] = True


async def synthesize_topic_intelligence(
    eng: Engagement,
    lens1_summary: str | None,
    lens2_summary: str | None,
    lens3_summary: str | None,
    lens3_materiality_signal: str | None = None,
    verified: str | None = None,
) -> dict:
    """Reconcile the 3 lens summaries into a scoping proposal.

    Returns a fully validated, stamped dict with exactly the 5 keys in
    _SYNTHESIS_KEYS. Every item in key_risk_areas/excluded_areas/
    proposed_frameworks, AND every item in interview_agenda.sponsor/.sme,
    carries a stable id=str(uuid4()) and included=True, stamped HERE (not by
    callers) so the first run and any later resynthesize call stamp
    identically. ia_prework stays a flat string list — read-only in the UI,
    never cascades, so it needs no id/included.

    Raises on any failure (network, unparseable JSON, failed validation) —
    callers are responsible for fail-open handling (best-effort try/except),
    exactly like the existing _generate_topic_primer call site.
    """
    prompt = _build_synthesis_prompt(eng, lens1_summary, lens2_summary, lens3_summary, lens3_materiality_signal, verified)
    # 8000, not the more common 4096: this reconciles 5 categories (several of
    # them lists of multi-field objects) from up to 3 real lens summaries —
    # empirically, real (long, web-search-derived) lens summaries pushed a
    # 4096-token completion past the limit mid-array, matching the highest
    # precedent for a comparably rich structured JSON output in this codebase
    # (interview_v2_service.py's guide generation).
    result = await run_agent_to_json(_SYNTHESIS_SYSTEM, prompt, max_tokens=8000)
    if not _validate_synthesis(result):
        raise ValueError("synthesize_topic_intelligence: model output failed schema validation")

    for field in _STAMPED_LIST_FIELDS:
        for item in result[field]:
            _stamp(item)
    apply_framework_tiers(result["proposed_frameworks"])
    agenda = result["interview_agenda"]
    agenda.setdefault("key_audit_questions", [])
    for group in ("sponsor", "sme", "key_audit_questions"):
        for item in agenda[group]:
            _stamp(item)
    return result


def apply_framework_tiers(frameworks: list[dict]) -> None:
    """Put the frameworks in tier order and select only the core ones.

    The model proposes a tier; this decides what is selected, because "at most five"
    is a rule and a model counts badly. A tier it did not give, or gave wrongly, is
    "supporting". More than MAX_CORE_FRAMEWORKS core: the primary ones first, then the
    order given, and the rest become supporting. No core at all: the primary ones,
    else the first one, so the auditor never starts from an empty selection.
    """
    for fw in frameworks:
        if fw.get("tier") not in FRAMEWORK_TIERS:
            fw["tier"] = "supporting"
    core = [f for f in frameworks if f["tier"] == "core"]
    if not core and frameworks:
        core = [f for f in frameworks if f.get("is_primary")] or frameworks[:1]
        for f in core:
            f["tier"] = "core"
    core.sort(key=lambda f: not f.get("is_primary"))
    for f in core[MAX_CORE_FRAMEWORKS:]:
        f["tier"] = "supporting"
    for f in frameworks:
        f["included"] = f["tier"] == "core"
    frameworks.sort(key=lambda f: FRAMEWORK_TIERS.index(f["tier"]))


# ── Stage-order advice ──────────────────────────────────────────────────────

_ORDER_SYSTEM = BASE_SYSTEM_PROMPT + (
    "\n\nYou advise on dispatch order for background drafting stages that are "
    "ALL already approved to run. You decide sequence only — never whether "
    "something runs; that decision was already made before you are consulted."
)


def _build_order_prompt(eng: Engagement, pack_summary: str, stages: list[dict]) -> str:
    # No wrap_untrusted here, deliberately: every input is engagement metadata,
    # a lifecycle-pack summary count, or a STAGE_GRAPH label/detail literal —
    # never document- or web-derived content. Same precedent
    # maybe_ask_proactive_question documents for itself in copilot_orchestrator.py.
    juris = ", ".join(jurisdictions_or_default(eng))
    lines = [
        f"Engagement: {eng.name} ({eng.entity}, {eng.audit_type}). Jurisdictions: {juris}.",
        f"Lifecycle status: {pack_summary}",
        "",
        "The stages below are ALL already approved to run right now — your only job is "
        "to advise which order gives the auditor the most useful work soonest (what "
        "unlocks the most downstream value; what a human would naturally want first).",
        "",
        "Stages eligible right now:",
    ]
    for s in stages:
        lines.append(f'- key="{s["key"]}" label="{s["label"]}" agent="{s["agent"]}" detail="{s["detail"]}"')
    lines.append("""
Produce ONLY this JSON (no markdown, no text before or after):
{
  "order": ["<key>", "<key>", ...],
  "rationale": {"<key>": "one short sentence — why this position", ...}
}

"order" MUST contain EXACTLY the keys listed above, each exactly once, in your
recommended dispatch order. Never invent a key that is not listed above.""")
    return "\n".join(lines)


def _validate_order(result, eligible_keys: list[str]) -> list[str] | None:
    """Pure hard gate: `result["order"]` must be exactly a permutation of
    eligible_keys — set() AND len() both equal, so this catches additions
    (a key outside eligible_keys), omissions, AND duplicates (len() is the
    only thing that catches e.g. eligible=[a,b,c], order=[a,b,c,a]: set()
    alone already matches there). Returns the validated order list, or None
    on any mismatch. Never raises."""
    if not isinstance(result, dict):
        return None
    order = result.get("order")
    if not isinstance(order, list):
        return None
    if set(order) != set(eligible_keys) or len(order) != len(eligible_keys):
        return None
    return order


async def advise_stage_order(eng: Engagement, pack_summary: str, stages: list[dict]) -> dict:
    """stages: [{"key", "label", "agent", "detail"}, ...] — the eligible subset,
    in their original (STAGE_GRAPH-declaration) order.

    Returns {"order": [key, ...], "rationale": {key: str}} — ALWAYS a valid
    permutation of the input keys. Fails open to the original order with an
    empty rationale on any error, timeout, or malformed response; never raises.
    """
    eligible_keys = [s["key"] for s in stages]
    fallback = {"order": eligible_keys, "rationale": {}}
    try:
        raw = await run_agent_to_json(
            _ORDER_SYSTEM, _build_order_prompt(eng, pack_summary, stages), max_tokens=1024,
        )
    except Exception:  # noqa: BLE001
        logger.exception("advise_stage_order: model call failed, falling back to declaration order")
        return fallback

    order = _validate_order(raw, eligible_keys)
    if order is None:
        return fallback

    raw_rationale = raw.get("rationale")
    raw_rationale = raw_rationale if isinstance(raw_rationale, dict) else {}
    rationale = {k: str(v)[:300] for k, v in raw_rationale.items() if k in eligible_keys and v}
    return {"order": order, "rationale": rationale}


# ── Item-order advice ───────────────────────────────────────────────────────
# Fieldwork-item counterpart to the stage-order advice above. Same shape, same
# _validate_order reuse (already generic on list[str] — a composite
# "item_type:item_id" key is just another string to it, no change needed).
#
# Crucial difference from the stage version: stage labels are STAGE_GRAPH
# literals (safe, deliberately unwrapped). Item labels are not — Finding.title
# can be AI-generated document content, InterviewSession.label/.persona is
# free auditor-typed text. Both are exactly the trust class wrap_untrusted()
# exists to contain, so every label here is wrapped in ONE combined call
# (mirrors the Grounded Validator's source-combined fence). The composite key
# is a trusted, server-built prefix placed on each line BEFORE the wrap (the
# model never has to "reproduce" untrusted text to identify an item), and the
# structural `detail` (rating/status only — controlled vocabulary, never free
# text like condition/notes) stays OUTSIDE the wrap entirely.

_ITEM_ORDER_SYSTEM = BASE_SYSTEM_PROMPT + (
    "\n\nYou advise on dispatch order for background-drafting fieldwork items (findings, "
    "interview sessions) that are ALL already approved to run. You decide sequence only — "
    "never whether something runs; that decision was already made before you are consulted."
)


def _build_item_order_prompt(eng: Engagement, pack_summary: str, items: list[dict]) -> str:
    juris = ", ".join(jurisdictions_or_default(eng))
    label_block = "\n".join(f'{it["key"]} — "{it["label"]}"' for it in items)
    detail_lines = [f'- {it["key"]}: {it["detail"]}' for it in items if it.get("detail")]

    parts = [
        f"Engagement: {eng.name} ({eng.entity}, {eng.audit_type}). Jurisdictions: {juris}.",
        f"Lifecycle status: {pack_summary}",
        "",
        "The fieldwork items below are ALL already approved to run right now — your only job is "
        "to advise which order gives the auditor the most useful work soonest (what unlocks the "
        "most downstream value; what a human would naturally want first).",
        "",
        "Items eligible right now (each line: composite key — label):",
        wrap_untrusted(label_block, "fieldwork item labels"),
    ]
    if detail_lines:
        parts.append("Structural status per item (controlled vocabulary, not free text):\n" + "\n".join(detail_lines))
    parts.append("""
Produce ONLY this JSON (no markdown, no text before or after):
{
  "order": ["<key>", "<key>", ...],
  "rationale": {"<key>": "one short sentence — why this position", ...}
}

"order" MUST contain EXACTLY the keys listed above, each exactly once, in your
recommended dispatch order. Never invent a key that is not listed above.""")
    return "\n\n".join(parts)


async def advise_item_order(eng: Engagement, pack_summary: str, items: list[dict]) -> dict:
    """items: [{"key", "item_type", "label", "detail"}, ...] — the eligible subset,
    in their original (DB-natural) order. key = f"{item_type}:{item_id}" (splitting
    on the first ':' is always safe — item_type is one of two fixed literals and a
    UUID4 item_id never contains ':').

    Returns {"order": [key, ...], "rationale": {key: str}} — ALWAYS a valid
    permutation of the input keys. Fails open to the original order with an
    empty rationale on any error, timeout, or malformed response; never raises.
    """
    eligible_keys = [it["key"] for it in items]
    fallback = {"order": eligible_keys, "rationale": {}}
    try:
        raw = await run_agent_to_json(
            _ITEM_ORDER_SYSTEM, _build_item_order_prompt(eng, pack_summary, items), max_tokens=1024,
        )
    except Exception:  # noqa: BLE001
        logger.exception("advise_item_order: model call failed, falling back to declaration order")
        return fallback

    order = _validate_order(raw, eligible_keys)
    if order is None:
        return fallback

    raw_rationale = raw.get("rationale")
    raw_rationale = raw_rationale if isinstance(raw_rationale, dict) else {}
    rationale = {k: str(v)[:300] for k, v in raw_rationale.items() if k in eligible_keys and v}
    return {"order": order, "rationale": rationale}


# ── Engagement coherence explanation (opt-in; click-only, never autonomous) ──
# The third "verb" the module docstring promises (synthesise, order, explain).
# Candidates come from coverage_service.select_coherence_candidates — a CLOSED
# list the model may only confirm or reject, mirroring _validate_order's
# "gate already closed before the model sees it" principle. Unlike everything
# else in this module, this RAISES on failure rather than failing open: it is
# only ever invoked from a human's explicit button click (review_service.py),
# never from an autonomous scan, so there is no deterministic behaviour to
# fall back to — the caller's existing try/except already turns a raise into
# status="failed", exactly like every other review artifact.

_COHERENCE_SYSTEM = BASE_SYSTEM_PROMPT + (
    "\n\nYou are the Orchestrator Agent, explaining candidate coherence issues across an "
    "engagement's Topic Intelligence, RACM spine and Findings. You never decide anything on "
    "your own — you only confirm or reject each candidate a deterministic sweep already "
    "selected, using nothing but the quoted material provided. You never invent a candidate, "
    "artefact, or fact that is not already present below."
)


def _coherence_sides(candidate: dict) -> tuple[list[dict], list[dict]]:
    """Both sides' quote-verification corpus for one coherence candidate — shared
    between prompt assembly and post-hoc verification so the exact same text is
    what a quote is checked against."""
    if candidate["kind"] == "ti_racm_gap":
        area = candidate["ti_risk_area"]
        side_a = [{
            "key": f"ti_risk_area:{area.get('id', '')}",
            "label": f"TI risk area: {safe_label(area.get('title', ''))}",
            "text": f"{area.get('title', '')}. {area.get('rationale', '')}".strip(),
        }]
        side_b = [
            {
                "key": f"racm_risk:{r.get('id', '')}",
                "label": f"RACM risk: {safe_label(r.get('title', ''))}",
                "text": f"{r.get('title', '')}. {r.get('description', '') or ''}".strip(),
            }
            for r in candidate.get("near_miss_racm_risks", [])
        ]
        return side_a, side_b
    if candidate["kind"] == "finding_pair_conflict":
        def _chunk(f):
            return [{
                "key": f"finding:{f.get('id', '')}",
                "label": f"Finding: {safe_label(f.get('title', ''))}",
                "text": f"{f.get('title', '')}. Condition: {f.get('condition', '')} Effect: {f.get('effect', '')}".strip(),
            }]
        fa, fb = candidate["findings"]
        return _chunk(fa), _chunk(fb)
    return [], []


def _build_coherence_prompt(eng: Engagement, pack_summary: str, candidates: list[dict]) -> str:
    juris = ", ".join(jurisdictions_or_default(eng))
    all_chunks: list[dict] = []
    cand_lines = []
    for i, c in enumerate(candidates, start=1):
        side_a, side_b = _coherence_sides(c)
        all_chunks += side_a + side_b
        if c["kind"] == "ti_racm_gap":
            cand_lines.append(
                f'{i}. TI risk area "{safe_label(c["ti_risk_area"].get("title", ""))}" — possibly NOT '
                f"actually reflected in the nearest RACM risk(s) shown below it."
            )
        else:
            fa, fb = c["findings"]
            cand_lines.append(
                f'{i}. Finding "{safe_label(fa.get("title", ""))}" (rating: {fa.get("rating") or "unrated"}) vs. '
                f'finding "{safe_label(fb.get("title", ""))}" (rating: {fb.get("rating") or "unrated"}) — similar '
                f"subject matter, but a different rating."
            )

    corpus_block = "\n\n".join(f"[{c['label']}]\n{c['text']}" for c in all_chunks)
    fenced = wrap_untrusted(corpus_block, "engagement coherence source material")

    parts = [
        f"Engagement: {eng.name} ({eng.entity}, {eng.audit_type}). Jurisdictions: {juris}.",
        f"Lifecycle status: {pack_summary}",
        "",
        "A deterministic sweep already selected the CLOSED list of candidate coherence issues "
        "below. Your only job is to confirm or reject EACH one using ONLY the source material, "
        "and to cite one verbatim quote per side when you confirm a real conflict/gap.",
        "",
        fenced,
        "",
        "CANDIDATES (closed list — never invent one that is not here):",
        "\n".join(cand_lines),
        """
For EACH candidate above, decide if there is a genuine conflict/gap, using ONLY the quoted
material. Produce ONLY this JSON (no markdown, no text before or after):
{
  "observations": [
    {"candidate_id": 1, "conflict": true|false, "explanation": "one short sentence",
     "side_a_quote": "verbatim substring from the first side, or empty if conflict is false",
     "side_b_quote": "verbatim substring from the second side, or empty if conflict is false"}
  ]
}
Include exactly one entry per candidate number listed above, using that exact number as
candidate_id. Never invent a candidate_id that is not listed. If a candidate does not hold up
under scrutiny, set conflict to false.""",
    ]
    return "\n\n".join(parts)


def _verify_observation(side_a_corpus, side_b_corpus, verdict_a: dict, verdict_b: dict) -> dict | None:
    """Both sides of a coherence observation must independently verify — a single
    verbatim, in-source quote each. Reuses grounded_validator._verify_quotes
    directly (already fully generic on any corpus/verdict shape), called once
    per side. Deliberately STRICTER than that function's own single-claim
    precedent (which downgrades an unverified quote but still shows it): here,
    if EITHER side fails to verify, the WHOLE observation is dropped rather than
    shown half-verified — the stakes of a cross-artifact "this conflicts" claim
    are higher than a single finding's claim check."""
    va = _verify_quotes(side_a_corpus, [verdict_a])
    vb = _verify_quotes(side_b_corpus, [verdict_b])
    if not va or not vb:
        return None
    a, b = va[0], vb[0]
    if a["quote_unverified"] or b["quote_unverified"] or not a["quote"] or not b["quote"]:
        return None
    return {"side_a": a, "side_b": b}


async def explain_coherence(eng: Engagement, pack_summary: str, candidates: list[dict]) -> list[dict]:
    """candidates: coverage_service.select_coherence_candidates()'s output — a
    CLOSED list the model may only confirm or reject, never extend.

    Opt-in, click-triggered only (see review_service._run_coherence_check) —
    unlike every other function in this module, this RAISES on any failure
    (network, unparseable JSON, validation) instead of failing open: there is
    no autonomous path here to protect, and the caller's existing try/except
    already turns a raise into status="failed", exactly like peer_review and
    every other review artifact.

    Returns only the VERIFIED observations, each as
    {"candidate": <original candidate dict>, "explanation": str,
     "side_a": <verified quote dict>, "side_b": <verified quote dict>} — a
    candidate the model flagged but could not verify on BOTH sides is dropped
    entirely (see _verify_observation).
    """
    if not candidates:
        return []
    raw = await run_agent_to_json(  # judge tier: see model_tiers.py
        _COHERENCE_SYSTEM, _build_coherence_prompt(eng, pack_summary, candidates), max_tokens=3000,
        tier=JUDGE,
    )
    model_obs = raw.get("observations") if isinstance(raw, dict) else None
    if not isinstance(model_obs, list):
        return []

    out = []
    for mo in model_obs:
        if not isinstance(mo, dict) or not mo.get("conflict"):
            continue
        cid = mo.get("candidate_id")
        if not isinstance(cid, int) or isinstance(cid, bool) or not (1 <= cid <= len(candidates)):
            continue
        candidate = candidates[cid - 1]
        side_a_corpus, side_b_corpus = _coherence_sides(candidate)
        if not side_a_corpus or not side_b_corpus:
            continue  # nothing to verify a quote against on one side — cannot confirm
        verified = _verify_observation(
            side_a_corpus, side_b_corpus,
            {"key": "a", "found": "yes", "quote": str(mo.get("side_a_quote") or "")},
            {"key": "b", "found": "yes", "quote": str(mo.get("side_b_quote") or "")},
        )
        if verified is None:
            continue
        out.append({
            "candidate": candidate,
            "explanation": str(mo.get("explanation") or "")[:300],
            "side_a": verified["side_a"],
            "side_b": verified["side_b"],
        })
    return out
