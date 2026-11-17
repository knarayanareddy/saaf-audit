"""The golden set, run as part of the ordinary test loop.

    venv/Scripts/python.exe -m tests.test_evals

This is the static tier only — no AI calls, no cost — so it can run on every
change like any other test. The full scorecard, including the real engagements
and the optional live agent calls, lives in `evals.run`:

    venv/Scripts/python.exe -m evals.run --file
    venv/Scripts/python.exe -m evals.run --live

Kept thin on purpose: the thresholds and the graders belong to the eval suite,
and duplicating them here would give two places to move when one of them should
be argued over.
"""
import sys

from evals.golden_set import ADVERSARIAL_STUFFING, CASES, build_document
from evals.graders import grade_head_clip_baseline, grade_retrieval
from evals.run import THRESHOLDS

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def test_the_cases_are_sound():
    """A broken case would quietly make the suite easier, so it is checked first."""
    print("the golden set itself:")
    check(len(CASES) >= 12, f"{len(CASES)} cases")
    check(len({c.id for c in CASES}) == len(CASES), "every case id is unique")

    for case in CASES:
        doc = build_document(case)
        assert case.needle in doc, f"{case.id}: the needle is missing from its own document"
        assert case.distractors, f"{case.id}: a case with no near-miss proves nothing"
    check(True, "every needle is present and every case has at least one near-miss")

    depths = {c.depth for c in CASES}
    check(depths == {"early", "mid", "late"}, f"all three depths are represented: {sorted(depths)}")

    late = [c for c in CASES if c.depth == "late"]
    unreachable = [c for c in late if not grade_head_clip_baseline(c)]
    check(len(unreachable) == len(late),
          f"every 'late' case is one the old 4,000-character clip could not reach "
          f"({len(unreachable)}/{len(late)})")


def test_retrieval_meets_its_thresholds():
    print("retrieval — reach is a guarantee, rank is a diagnostic:")
    scores = [s for case in CASES for s in grade_retrieval(case)]
    reach = [s for s in scores if "reaches the model" in s.name]
    rankish = [s for s in scores if "reaches the model" not in s.name]

    reach_ratio = sum(s.passed for s in reach) / len(reach)
    rank_ratio = sum(s.passed for s in rankish) / len(rankish)

    check(reach_ratio >= THRESHOLDS["retrieval_reach"],
          f"the answer reaches the model in {sum(s.passed for s in reach)}/{len(reach)} cases "
          f"(threshold {THRESHOLDS['retrieval_reach']:.0%})")
    check(rank_ratio >= THRESHOLDS["retrieval_rank"],
          f"ranking holds up in {sum(s.passed for s in rankish)}/{len(rankish)} checks "
          f"(threshold {THRESHOLDS['retrieval_rank']:.0%})")
    for s in rankish:
        if not s.passed:
            print(f"        known miss: {s.name} — {s.detail}")


def test_the_adversarial_tier_is_reported_not_hidden():
    """Keyword stuffing beats lexical ranking. That is a property of BM25, not a
    bug to be tuned away, and the number is asserted here so it cannot silently
    get worse either."""
    print("the adversarial tier — where lexical ranking gives out:")
    scores = [s for case in CASES for s in grade_retrieval(case, stuffing=ADVERSARIAL_STUFFING)]
    reach = [s for s in scores if "reaches the model" in s.name]
    beats = [s for s in scores if "near-misses" in s.name]

    check(all(s.passed for s in reach),
          f"even against stuffed near-misses, the answer still reaches the model "
          f"({sum(s.passed for s in reach)}/{len(reach)})")
    won = sum(s.passed for s in beats)
    check(won >= len(beats) // 2,
          f"it outranks the stuffed decoy in {won}/{len(beats)} cases — recorded, not required")


def main():
    test_the_cases_are_sound()
    test_retrieval_meets_its_thresholds()
    test_the_adversarial_tier_is_reported_not_hidden()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
