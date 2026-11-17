"""Deterministic graders — scoring without asking a model for an opinion.

An LLM-as-judge would be the easy way to score these. It is also the way to
build an evaluation that drifts when the judge changes and cannot be defended to
anyone. Everything here is arithmetic and string matching over known answers, so
two runs a month apart are comparable and a regression is a fact rather than a
vibe.

Three families:

* `grade_retrieval` — did the layer surface the passage that answers the
  question, and did it beat the near-misses written to confuse it.
* `grade_file` — properties of a real engagement's own artifacts that ought to
  hold regardless of which agent produced them. These double as a quality
  scorecard for an audit file, which is why they read as audit statements
  ("every accepted risk is tested") rather than as assertions.
* `grade_governance_output` — for the live mode: given an agent's actual answer
  on a case with a known correct conclusion, was it right, and did it cite a
  passage that exists.
"""
from dataclasses import dataclass

from services.retrieval import rank, retrieve, split_document, verify_citation


@dataclass
class Score:
    """One graded thing: passed or not, with the number behind it.

    `skipped` is for a check with nothing to check — no evidence items, no
    findings. It used to report PASS, which inflated every percentage in the
    flattering direction: an engagement with no evidence at all scored full
    marks for "evidence points at a source document". A scorecard that rewards
    an empty file is worse than no scorecard.
    """
    name: str
    passed: bool
    detail: str
    value: float | None = None
    skipped: bool = False

    def line(self) -> str:
        mark = "n/a " if self.skipped else ("PASS" if self.passed else "FAIL")
        return f"  {mark}  {self.name} — {self.detail}"


# ── Retrieval ────────────────────────────────────────────────────────────────
def grade_retrieval(case, budget_chars: int = 8_000, stuffing: int = 1) -> list[Score]:
    """Was the answer put in front of the model, and did it outrank its decoys?"""
    from evals.golden_set import corpus_for

    docs = corpus_for(case, stuffing)
    main_text = docs[0][2]
    found = retrieve(docs, case.question, budget_chars=budget_chars)
    scores: list[Score] = []

    # The needle must be in the document at all — a case that fails here is a
    # broken case, not a broken retriever, and should say so plainly.
    assert case.needle in main_text, f"{case.id}: the needle is not in its own document"

    in_block = case.needle in found.block
    scores.append(Score(
        f"{case.id}: the answer reaches the model", in_block,
        f"depth={case.depth}, {found.coverage.percentage}% of {found.coverage.chars_total:,} chars read",
    ))

    # Where did it rank, and did it beat the distractors written to look like it?
    passages = split_document(main_text, "d", "doc")
    ranked = rank(passages, case.question)
    needle_rank = next((i for i, (_s, p) in enumerate(ranked, 1) if case.needle in p.text), None)
    scores.append(Score(
        f"{case.id}: ranks in the top three", bool(needle_rank and needle_rank <= 3),
        f"rank {needle_rank} of {len(ranked)}", float(needle_rank or 0),
    ))

    needle_score = next((s for s, p in ranked if case.needle in p.text), 0.0)
    decoy_scores = [s for s, p in ranked
                    if any(d.lower() in (p.section or "").lower() for d in case.distractors)]
    beat = not decoy_scores or needle_score > max(decoy_scores)
    scores.append(Score(
        f"{case.id}: beats its near-misses", beat,
        (f"needle {needle_score:.1f} vs best decoy {max(decoy_scores):.1f}"
         if decoy_scores else "no decoy sections were matched"),
    ))

    if case.extra_documents:
        # The answer is in the main document; a second file on an adjacent topic
        # must not be the one that wins the budget.
        main_share = sum(len(p.text) for p in found.passages if p.doc_id == docs[0][0])
        total = sum(len(p.text) for p in found.passages) or 1
        scores.append(Score(
            f"{case.id}: picks the right file", main_share / total >= 0.5,
            f"{100 * main_share / total:.0f}% of the budget went to the document holding the answer",
            main_share / total,
        ))

    return scores


def grade_head_clip_baseline(case, clip: int = 4_000) -> bool:
    """Would the old head-of-document clip have found this answer?

    Kept so the scorecard can say what actually changed rather than only how
    good the current number is.
    """
    from evals.golden_set import corpus_for

    return case.needle in corpus_for(case)[0][2][:clip]


# ── A real engagement's own file ─────────────────────────────────────────────
async def grade_file(engagement_id: str, db) -> list[Score]:
    """Properties an audit file ought to have, measured on the stored artifacts.

    These are the checks the silent `[:10]` context truncations used to make
    impossible to notice: a work program built from the first ten of twenty-five
    accepted risks looks perfectly normal until somebody counts.
    """
    import json

    from sqlalchemy import select
    from models.planning import BackgroundRiskAssessment, WorkProgram, FieldworkObservation
    from models.racm import RacmTest, RacmEvidence
    from models.reporting import Finding

    def loads(raw, default):
        try:
            return json.loads(raw) if raw else default
        except (ValueError, TypeError):
            return default

    scores: list[Score] = []

    bra = (await db.execute(select(BackgroundRiskAssessment)
                            .where(BackgroundRiskAssessment.engagement_id == engagement_id))).scalar_one_or_none()
    wp = (await db.execute(select(WorkProgram)
                           .where(WorkProgram.engagement_id == engagement_id))).scalar_one_or_none()
    accepted = [r for r in loads(bra.risk_items if bra else None, []) if r.get("is_accepted")]
    wp_rows = loads(wp.rows if wp else None, [])

    if accepted and wp_rows:
        # A risk counts as covered when its own words show up in a row. Crude on
        # purpose: anything cleverer would need a model, and then the grader
        # would have the same failure mode as the thing it grades.
        blob = " ".join(
            f"{r.get('process', '')} {r.get('activity', '')} {r.get('risk_description', '')} "
            f"{r.get('control_objective', '')}" for r in wp_rows
        ).lower()
        covered = 0
        for r in accepted:
            terms = [w for w in (r.get("description") or "").lower().split() if len(w) > 6]
            if terms and sum(1 for t in terms[:8] if t in blob) >= 2:
                covered += 1
        ratio = covered / len(accepted)
        scores.append(Score(
            "every accepted risk is reflected in the work program", ratio >= 0.8,
            f"{covered} of {len(accepted)} accepted risks", ratio,
        ))

    tests = (await db.execute(select(RacmTest)
                              .where(RacmTest.engagement_id == engagement_id))).scalars().all()
    evidence = (await db.execute(select(RacmEvidence)
                                 .where(RacmEvidence.engagement_id == engagement_id))).scalars().all()
    if tests:
        concluded = [t for t in tests if (t.result or "pending") != "pending"]
        with_ev = {e.test_id for e in evidence if e.test_id}
        backed = [t for t in concluded if t.id in with_ev]
        scores.append(Score(
            "a concluded test has evidence attached",
            bool(concluded) and len(backed) / len(concluded) >= 0.8,
            f"{len(backed)} of {len(concluded)} concluded tests",
            len(backed) / len(concluded) if concluded else None,
            skipped=not concluded,
        ))
        linked = [e for e in evidence if e.source_document_id]
        scores.append(Score(
            "evidence points at a source document",
            bool(evidence) and len(linked) / len(evidence) >= 0.5,
            f"{len(linked)} of {len(evidence)} evidence items",
            len(linked) / len(evidence) if evidence else None,
            skipped=not evidence,
        ))

    findings = (await db.execute(select(Finding)
                                 .where(Finding.engagement_id == engagement_id))).scalars().all()
    if findings:
        complete = [f for f in findings
                    if all((getattr(f, c) or "").strip()
                           for c in ("condition", "criteria", "cause", "effect", "recommendation"))]
        scores.append(Score(
            "every finding states all five C's", len(complete) == len(findings),
            f"{len(complete)} of {len(findings)} findings",
            len(complete) / len(findings),
        ))
        traced = [f for f in findings if f.racm_test_id or f.source_observation_id]
        scores.append(Score(
            "every finding traces back to a test or an observation",
            len(traced) / len(findings) >= 0.8,
            f"{len(traced)} of {len(findings)} findings", len(traced) / len(findings),
        ))
        challenged = [f for f in findings if f.rating_challenge]
        scores.append(Score(
            "every finding's rating has been challenged",
            len(challenged) / len(findings) >= 0.8,
            f"{len(challenged)} of {len(findings)} findings", len(challenged) / len(findings),
        ))

    obs = (await db.execute(select(FieldworkObservation)
                            .where(FieldworkObservation.engagement_id == engagement_id))).scalars().all()
    if obs:
        linked = [o for o in obs if o.linked_wp_row_id]
        scores.append(Score(
            "an observation is linked to the work-program step it came from",
            len(linked) / len(obs) >= 0.5,
            f"{len(linked)} of {len(obs)} observations", len(linked) / len(obs),
        ))

    return scores


# ── Live mode ────────────────────────────────────────────────────────────────
def grade_governance_output(case, result: dict, by_cid: dict) -> list[Score]:
    """Given the assessor's real answer on a case whose answer we know.

    The case's needle states a requirement that IS met by the document, so an
    assessor that reads what it was given must not call it a gap — and it must
    cite a passage that exists.
    """
    items = result.get("items") or []
    scores = [Score(f"{case.id}: returns an assessment", bool(items), f"{len(items)} item(s)")]
    if not items:
        return scores

    topic_words = {w.lower() for w in case.question.split() if len(w) > 5}
    relevant = [i for i in items
                if topic_words & {w.lower() for w in (i.get("requirement") or "").split()}]
    scores.append(Score(
        f"{case.id}: addresses the question asked", bool(relevant),
        f"{len(relevant)} of {len(items)} items are on topic",
    ))

    if relevant:
        wrong = [i for i in relevant if i.get("coverage") == "gap"]
        scores.append(Score(
            f"{case.id}: does not report a gap the document answers", not wrong,
            f"{len(wrong)} item(s) wrongly marked gap",
        ))
        cited = [i for i in relevant
                 if verify_citation(str(i.get("evidence") or ""), by_cid)["has_citation"]]
        scores.append(Score(
            f"{case.id}: cites a passage that exists", bool(cited),
            f"{len(cited)} of {len(relevant)} on-topic items carry a resolvable citation",
        ))

    invented = [i for i in items
                if verify_citation(str(i.get("evidence") or ""), by_cid)["unresolved"]]
    scores.append(Score(
        f"{case.id}: invents no citations", not invented,
        f"{len(invented)} item(s) cite a passage id that does not exist",
    ))
    return scores
