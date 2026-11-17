"""Grading the agents — and running them, through the same code the platform uses.

Two rules hold everywhere in this file:

1. **The prompt is the agent's own.** Every runner calls the builder the agent
   itself calls (`frameworks_prompt`, `finding_prompt`, `qa_review_prompt`,
   `_build_lensN_prompt`, `_build_user_blocks`, `propose_mapping`). The older
   governance eval in run.py rebuilt its prompt in its own words, which means
   it would go on scoring a prompt the agent had stopped sending.

2. **The ledger is the account of what it cost.** Each case runs under its own
   `run_id`, and cost, model and repairs are read back from the rows the calls
   wrote — not recomputed here, where a second copy of the arithmetic could
   disagree with the first.

A refusal is graded as what it is. A case marked `may_be_refused` that is
declined does not count as a wrong answer — it counts as a refusal, reported
separately, because that is the event the migration has to be able to see.
"""
from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy import select

from evals.agent_cases import (
    CHALLENGE_CASES, FINDING_CASES, FRAMEWORKS_CASES, GOVERNANCE_CASES, LENS_CASES, QA_CASES,
    RCSA_CASES,
)
from evals.graders import Score

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


# ── Text helpers ─────────────────────────────────────────────────────────────
def _term_found(text: str, term: str) -> bool:
    """A short all-caps acronym must match as a word ("SEC" is not "section"),
    with a version number allowed after it ("AMLD6" is AMLD, "PSD2" is PSD);
    anything else matches case-insensitively as a substring."""
    if term.isupper() and len(term) <= 5:
        return re.search(rf"\b{re.escape(term)}\d*\b", text) is not None
    return term.lower() in text.lower()


def _any_found(text: str, terms) -> bool:
    return any(_term_found(text, t) for t in terms)


def _flatten(value) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(v) for v in value)
    return "" if value is None else str(value)


# ── Graders ──────────────────────────────────────────────────────────────────
def grade_lens(case, result) -> list[Score]:
    scores: list[Score] = []
    shaped = isinstance(result, dict) and bool(str(result.get("summary") or "").strip())
    scores.append(Score(f"{case.id}: an object with a summary", shaped,
                        "summary present" if shaped else f"got {type(result).__name__} without a summary"))
    if not shaped:
        return scores
    summary = str(result["summary"])
    for group in case.must_mention:
        found = _any_found(summary, group)
        scores.append(Score(f"{case.id}: mentions {' / '.join(group)}", found,
                            "found" if found else "absent from the summary"))
    stray = [t for t in case.must_not_mention if _term_found(summary, t)]
    scores.append(Score(f"{case.id}: stays inside {'+'.join(case.jurisdictions)}", not stray,
                        "no out-of-scope regulator named" if not stray else f"names {', '.join(stray)}"))
    sources = result.get("sources") or []
    scores.append(Score(f"{case.id}: names its sources", bool(sources), f"{len(sources)} source(s)"))
    return scores


def grade_frameworks(case, frameworks: list[dict]) -> list[Score]:
    scores: list[Score] = []
    text = _flatten(frameworks)
    for group in case.must_include:
        found = _any_found(text, group)
        scores.append(Score(f"{case.id}: includes {' / '.join(group)}", found,
                            "found" if found else "missing from the frameworks"))
    stray = [t for t in case.must_not_include if _term_found(text, t)]
    scores.append(Score(f"{case.id}: nothing from outside the scope", not stray,
                        "clean" if not stray else f"includes {', '.join(stray)}"))
    allowed = set(case.jurisdictions) | {"EU", "International"}
    outside = sorted({f.get("jurisdiction") for f in frameworks} - allowed - {None})
    scores.append(Score(f"{case.id}: every item's jurisdiction is in scope", not outside,
                        "all in scope" if not outside else f"also {', '.join(outside)}"))
    specific = [f for f in frameworks if re.search(r"\d", str(f.get("specific_provision") or ""))]
    ratio = len(specific) / len(frameworks) if frameworks else 0.0
    scores.append(Score(f"{case.id}: provisions are specific (article numbers)", ratio >= 0.8,
                        f"{len(specific)}/{len(frameworks)} name a numbered provision", value=ratio))
    return scores


def grade_governance(case, items: list[dict], by_cid: dict) -> list[Score]:
    from services.retrieval import verify_citation

    scores = [Score(f"{case.id}: at most three requirements, as the prompt asks", 0 < len(items) <= 3,
                    f"{len(items)} item(s)")]
    unsupported, invented = [], []
    for item in items:
        cited = verify_citation(str(item.get("evidence") or ""), by_cid)
        invented += cited["unresolved"]
        if item.get("coverage") == "covered" and not cited["has_citation"]:
            unsupported.append(str(item.get("requirement") or "")[:60])
    scores.append(Score(f"{case.id}: every 'covered' cites a real passage", not unsupported,
                        "all supported" if not unsupported else f"unsupported: {unsupported}"))
    scores.append(Score(f"{case.id}: no invented passage ids", not invented,
                        "none" if not invented else f"cites {invented}, which do not exist"))
    for keyword, allowed in case.expected_coverage.items():
        hits = [i for i in items if keyword.lower() in str(i.get("requirement") or "").lower()]
        if not hits:
            scores.append(Score(f"{case.id}: '{keyword}' requirement", False,
                                "not assessed", skipped=True))
            continue
        wrong = [i.get("coverage") for i in hits if i.get("coverage") not in allowed]
        scores.append(Score(f"{case.id}: '{keyword}' rated {'/'.join(allowed)}", not wrong,
                            "as expected" if not wrong else f"rated {wrong}"))
    return scores


def grade_finding(case, draft: dict) -> list[Score]:
    fields = ("title", "condition", "criteria", "cause", "effect", "recommendation")
    empty = [f for f in fields if not str(draft.get(f) or "").strip()]
    scores = [
        Score(f"{case.id}: all five C's and a title", not empty,
              "complete" if not empty else f"empty: {', '.join(empty)}"),
        Score(f"{case.id}: rated {'/'.join(case.allowed_ratings)}",
              draft.get("rating") in case.allowed_ratings, f"rated {draft.get('rating')}"),
    ]
    # The factual fields may only carry numbers the auditor gave. Criteria may
    # cite an article from knowledge; a condition may not invent a sample size.
    given = set(_NUMBER.findall(_flatten(case.seed)))
    factual = f"{draft.get('condition') or ''} {draft.get('effect') or ''}"
    stated = set(_NUMBER.findall(factual))
    # Only a number written AS a percentage may be a derived one. Without this
    # "23 of 60 customers" passed because 23 is close to 14/60 as a percentage.
    percentages = set(re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:%|percent)", factual))
    invented = sorted(n for n in stated - given
                      if not (n in percentages and _is_derived(n, given))
                      and not _is_remainder(n, given))
    detail = "none invented"
    if invented:
        where = [m.group(0) for n in invented[:3]
                 for m in [re.search(rf".{{0,40}}\b{re.escape(n)}\b.{{0,40}}", factual)] if m]
        detail = f"introduces {', '.join(invented)} — in: {where}"
    scores.append(Score(f"{case.id}: no numbers the auditor did not give", not invented, detail))
    return scores


def _is_remainder(number: str, given: set[str]) -> bool:
    """"2 of 25 lacked a signature; the remaining 23 had one" — a difference of
    two given counts is arithmetic too. Found when the 5.5 run wrote exactly that
    and the grader called 23 invented."""
    try:
        value = int(number)
    except ValueError:
        return False
    counts = [int(g) for g in given if g.isdigit()]
    return any(a - b == value for a in counts for b in counts if a > b)


def _is_derived(number: str, given: set[str]) -> bool:
    """A percentage correctly worked out from two given numbers is arithmetic,
    not invention: "9 of 40" may be written "22.5%". The first baseline counted
    those as made up, which would have scored a correct finding as wrong. A
    percentage that does NOT match the given numbers still counts as invented."""
    try:
        value = float(number.replace(",", "."))
    except ValueError:
        return False
    counts = [float(g.replace(",", ".")) for g in given]
    for a in counts:
        for b in counts:
            if b and a < b and abs(100 * a / b - value) < 0.6:
                return True
    return False


def grade_qa(case, result) -> list[Score]:
    if not isinstance(result, dict):
        return [Score(f"{case.id}: a review object", False, f"got {type(result).__name__}")]
    comments = result.get("comments") or []
    text = _flatten(comments) + " " + str(result.get("summary") or "")
    scores: list[Score] = []
    for name, terms in case.planted:
        found = _any_found(text, terms)
        scores.append(Score(f"{case.id}: finds '{name}'", found, "found" if found else "missed"))
    if case.max_must_fix is not None:
        must = sum(1 for c in comments if c.get("severity") == "must_fix")
        scores.append(Score(f"{case.id}: no false alarms on a clean artifact",
                            must <= case.max_must_fix, f"{must} must-fix comment(s)"))
    if case.planted:
        verdict = result.get("overall_quality")
        scores.append(Score(f"{case.id}: does not call a defective artifact good",
                            verdict != "good", f"overall: {verdict}"))
    return scores


def grade_rcsa(case, proposal: dict) -> list[Score]:
    columns = proposal.get("columns") or []
    scores = [Score(f"{case.id}: one proposal per column", len(columns) == len(case.names),
                    f"{len(columns)} for {len(case.names)} columns")]
    right, wrong = 0, []
    for idx, allowed in case.expected.items():
        target = columns[idx].get("target") if idx < len(columns) else None
        if target in allowed:
            right += 1
        else:
            wrong.append(f"{case.names[idx]}→{target}")
    ratio = right / len(case.expected)
    scores.append(Score(f"{case.id}: columns mapped to the right field", ratio >= 0.85,
                        f"{right}/{len(case.expected)}" + (f"; wrong: {wrong[:6]}" if wrong else ""),
                        value=ratio))
    return scores


# ── Runners: one case, the agent's own code path ─────────────────────────────
async def _run_lens(case):
    from services import lens_regulatory_agent as l1, lens_supervisory_agent as l2, lens_society_agent as l3
    from services.agent_schemas import LensSynthesis, SocietyLensSynthesis
    from services.lens_call import synthesise

    kwargs = dict(eng_name=case.audit, entity=case.entity, audit_type=case.audit_type,
                  manual_keyword=None, use_web_search=False, jurisdictions=list(case.jurisdictions))
    if case.lens == 1:
        system, prompt, schema = l1.LENS1_SYSTEM, l1._build_lens1_prompt(url_context="", **kwargs), LensSynthesis
    elif case.lens == 2:
        system, prompt, schema = l2.LENS2_SYSTEM, l2._build_lens2_prompt(url_context="", **kwargs), LensSynthesis
    else:
        system, prompt, schema = l3.LENS3_SYSTEM, l3._build_lens3_prompt(**kwargs), SocietyLensSynthesis
    # Built-in knowledge, no live search: the eval measures the model, and a
    # web search would make two runs of the same case read different pages.
    # The same call the lens agents make (services/lens_call.synthesise).
    # IA_WINGMAN_EVAL_LENS_TIER=previous runs it on the previous draft model
    # (Sonnet 5) instead of the lenses' own tier, so the two stay comparable.
    import os
    from services.model_tiers import PREVIOUS
    tier = PREVIOUS["draft"] if os.environ.get("IA_WINGMAN_EVAL_LENS_TIER") == "previous" else None
    result = await synthesise(system, prompt, schema, use_web_search=False, tier=tier)
    return grade_lens(case, result)


async def _run_frameworks(case):
    from services.agent_contract import run_agent
    from services.agent_schemas import Frameworks
    from services.framework_requirements_agent import FRAMEWORKS_SYSTEM, frameworks_prompt

    result = await run_agent(FRAMEWORKS_SYSTEM,
                             frameworks_prompt(case.audit, case.entity, case.audit_type,
                                               list(case.jurisdictions)),
                             Frameworks, max_tokens=3000,
                             description="Return the applicable frameworks.")
    return grade_frameworks(case, [f.model_dump() for f in result.data.frameworks])


async def _run_governance(case):
    from services.governance_assessor import _DOC_BUDGET, _assess_one
    from services.prompt_safety import wrap_untrusted
    from services.retrieval import retrieve

    # The agent's own budget and wrapping, so the passages the model reads are
    # the ones the assessor would hand it.
    found = retrieve(list(case.documents), case.question, budget_chars=_DOC_BUDGET)
    items, _meta, error = await _assess_one(
        case.framework, wrap_untrusted(found.block, "uploaded governance documents"), [])
    if error:
        # _assess_one never raises; it names the framework that failed. Re-raised
        # here so a refusal is graded as a refusal, not as an empty assessment.
        raise RuntimeError(error)
    return grade_governance(case, items, found.by_cid)


async def _run_finding(case):
    from services.agent_contract import run_agent
    from services.agent_schemas import FindingDraft
    from services.finding_drafter import DRAFTER_SYSTEM, finding_prompt

    result = await run_agent(DRAFTER_SYSTEM,
                             finding_prompt(case.audit, case.entity, case.audit_type, case.seed),
                             FindingDraft, max_tokens=2000,
                             description="Return the finding as the 5 C's, with a severity rating.")
    return grade_finding(case, result.data.model_dump())


async def _run_qa(case):
    from services.review_service import review_artifact

    result = await review_artifact(case.audit, case.entity, case.audit_type, case.label, case.content)
    return grade_qa(case, result)


async def _run_rcsa(case):
    from services.rcsa_mapping import propose_mapping

    proposal = await propose_mapping(list(case.names), [list(r) for r in case.samples],
                                     list(case.bands))
    return grade_rcsa(case, proposal)


def grade_challenge(case, result: dict) -> list[Score]:
    agrees = result.get("agrees")
    suggestion = result.get("suggested_rating")
    return [
        Score(f"{case.id}: {'agrees' if case.expect_agrees else 'disagrees'} with the proposed rating",
              agrees is case.expect_agrees, f"agrees={agrees}"),
        Score(f"{case.id}: suggests {'/'.join(case.allowed_suggestions)}",
              suggestion in case.allowed_suggestions, f"suggests {suggestion}"),
        Score(f"{case.id}: gives a reason", len(str(result.get("rationale") or "").strip()) >= 20,
              f"{len(str(result.get('rationale') or ''))} characters"),
    ]


async def _run_challenge(case):
    import os
    from services.agent_contract import run_agent
    from services.agent_schemas import RatingChallenge
    from services.finding_drafter import CHALLENGE_SYSTEM, challenge_prompt
    from services.model_tiers import JUDGE, PREVIOUS

    # IA_WINGMAN_EVAL_GENERATION=previous runs the same code on the previous
    # judge model, so the two can be compared on identical requests.
    tier = PREVIOUS["judge"] if os.environ.get("IA_WINGMAN_EVAL_GENERATION") == "previous" else JUDGE
    result = await run_agent(CHALLENGE_SYSTEM, challenge_prompt(case.draft), RatingChallenge,
                             max_tokens=600, tier=tier)
    return grade_challenge(case, result.data.model_dump())


AGENTS = {
    "topic_intelligence": (LENS_CASES, _run_lens),
    "frameworks": (FRAMEWORKS_CASES, _run_frameworks),
    "governance": (GOVERNANCE_CASES, _run_governance),
    "finding": (FINDING_CASES, _run_finding),
    "qa_review": (QA_CASES, _run_qa),
    "rcsa_mapping": (RCSA_CASES, _run_rcsa),
    "rating_challenge": (CHALLENGE_CASES, _run_challenge),
}


async def _ledger_for(run_id: str) -> dict:
    from database import AsyncSessionLocal
    from models.agent_call import AgentCall

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(AgentCall).where(AgentCall.run_id == run_id))).scalars().all()
    return {
        "calls": len(rows),
        "cost_usd": round(sum(r.cost_usd or 0.0 for r in rows), 5),
        "models": sorted({r.model for r in rows if r.model}),
        "repairs": [r.repair for r in rows if r.repair],
        "refused": [r.error for r in rows if (r.error or "").startswith("refused")],
    }


async def run_case(agent: str, case, attempt: int) -> dict:
    """One case, once. Never raises: a crash is a graded failure with its reason."""
    from services.agent_contract import AgentRefused
    from services.agent_ledger import agent_context

    _cases, runner = AGENTS[agent]
    run_id = f"eval-{agent}-{case.id}-{attempt}-{uuid4().hex[:6]}"
    refused = None
    with agent_context(agent=f"eval:{agent}", run_id=run_id):
        try:
            scores = await runner(case)
        except AgentRefused as exc:
            refused = exc.category
            scores = []
        except Exception as exc:  # noqa: BLE001
            text = f"{type(exc).__name__}: {exc}"
            if "refused" in text.lower() or "AgentRefused" in text:
                refused = "unspecified"
                scores = []
            else:
                scores = [Score(f"{case.id}: the run completed", False, text[:200])]
    ledger = await _ledger_for(run_id)
    if refused == "unspecified" and ledger["refused"]:
        # A runner that swallows exceptions (the governance assessor names the
        # failed framework instead of raising) loses the category; the ledger
        # row written at the moment of refusal still has it.
        refused = ledger["refused"][0].split(": ", 1)[-1]
    if refused is not None and not getattr(case, "may_be_refused", False):
        # Declined where no refusal was expected: that is a failure of the
        # migration, not of the case, and it is graded as one.
        scores = [Score(f"{case.id}: not refused", False, f"declined ({refused})")]
    return {
        "agent": agent, "case": case.id, "attempt": attempt, "refused": refused,
        "needs_review": getattr(case, "needs_review", True),
        "scores": [{"name": s.name, "passed": s.passed, "detail": s.detail,
                    "skipped": s.skipped} for s in scores],
        **ledger,
    }
