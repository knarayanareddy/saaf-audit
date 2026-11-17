"""The eval runner — a scorecard, and a threshold it has to clear.

    venv/Scripts/python.exe -m evals.run              # static: free, no AI
    venv/Scripts/python.exe -m evals.run --file       # + the real engagements
    venv/Scripts/python.exe -m evals.run --live       # + real agent calls (costs)
    venv/Scripts/python.exe -m evals.run --json out.json

Same two-mode idiom as the red-team suite in services/assurance: static proves
the deterministic machinery behaves, live spends tokens to find out what the
model actually does. The honesty note carried by that suite applies here too —
static says "retrieval puts the answer in front of the model", not "the agent
gets the answer right". Only --live can say the second thing.

Exit code is 1 below threshold, so this can sit in front of a merge.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone

from evals.golden_set import CASES, corpus_for
from evals.graders import (
    Score, grade_file, grade_governance_output, grade_head_clip_baseline, grade_retrieval,
)

# What "good enough" means, stated up front so a regression is a fact.
#
# Retrieval is split in two on purpose. Blending them into one percentage was the
# first thing this suite got wrong: it produced a "97%" that mixed a hard
# guarantee with a soft diagnostic, and a number like that tells you nothing
# about which of the two moved.
#
#   reach — the answer must end up in the prompt. Non-negotiable: the passage is
#           in the corpus, and an agent that never sees it cannot be right for
#           any reason worth having.
#   rank  — it should also outrank the near-misses. A sharper instrument, and
#           allowed to miss occasionally: when the operative clause sits under a
#           heading that shares none of the question's words while a background
#           section is headed with them, heading weighting pulls the wrong way.
#           That is a real property of lexical ranking, and 90% is where it is
#           worth being told about rather than worth failing the build over.
THRESHOLDS = {
    "retrieval_reach": 1.00,
    "retrieval_rank": 0.90,
    "file": 0.70,        # a demo file is allowed some rough edges, not many
    "live": 0.80,
    # Per agent, over every graded check of every run. Set where a competent
    # agent should land on cases that are, by design, unambiguous — and the
    # first baseline will say whether that is optimistic.
    "agents": 0.80,
}


def _summarise(scores: list[Score]) -> tuple[int, int]:
    """Counted over what was actually checkable — a skipped check is neither a
    pass nor a failure, and including it either way distorts the number."""
    graded = [s for s in scores if not s.skipped]
    return sum(1 for s in graded if s.passed), len(graded)


def run_retrieval(stuffing: int = 1) -> tuple[list[Score], dict]:
    scores: list[Score] = []
    by_depth: dict[str, list[bool]] = {}
    baseline_found = 0

    for case in CASES:
        case_scores = grade_retrieval(case, stuffing=stuffing)
        scores.extend(case_scores)
        reached = case_scores[0].passed
        by_depth.setdefault(case.depth, []).append(reached)
        if grade_head_clip_baseline(case):
            baseline_found += 1

    stats = {
        "cases": len(CASES),
        "reached_by_depth": {d: f"{sum(v)}/{len(v)}" for d, v in sorted(by_depth.items())},
        "old_clip_would_have_found": f"{baseline_found}/{len(CASES)}",
    }
    return scores, stats


async def run_file() -> list[Score]:
    from sqlalchemy import select
    from database import AsyncSessionLocal
    from models.engagement import Engagement

    scores: list[Score] = []
    async with AsyncSessionLocal() as db:
        engagements = (await db.execute(select(Engagement))).scalars().all()
        for eng in engagements:
            eng_scores = await grade_file(eng.id, db)
            if not eng_scores:
                continue
            print(f"\n  {eng.name} ({eng.status})")
            for s in eng_scores:
                print("  " + s.line())
            scores.extend(eng_scores)
    return scores


async def run_live() -> list[Score]:
    """Real agent calls against the golden cases. Costs tokens."""
    from services.agent_contract import run_agent
    from services.agent_schemas import GovernanceAssessment
    from services.governance_assessor import SYSTEM_PROMPT
    from services.prompt_safety import wrap_untrusted
    from services.retrieval import retrieve

    scores: list[Score] = []
    for case in CASES:
        found = retrieve(corpus_for(case), case.question, budget_chars=8_000)
        prompt = (
            f"Assess whether the governance in place covers this requirement.\n\n"
            f"APPLICABLE REQUIREMENT:\n- {case.question}\n\n"
            f"CONTROL ENVIRONMENT (from the RACM):\n(none recorded)\n\n"
            f"UPLOADED GOVERNANCE DOCUMENTS:\n"
            f"{wrap_untrusted(found.block, 'uploaded governance documents')}\n\n"
            f"Return your assessment through the submit_result tool. Cite the passage id [P#] you "
            f"relied on in the evidence field. Do not call something a gap purely because it does "
            f"not appear in the passages you were given."
        )
        try:
            outcome = await run_agent(SYSTEM_PROMPT, prompt, GovernanceAssessment, max_tokens=2000)
            case_scores = grade_governance_output(case, outcome.dump(), found.by_cid)
            print(f"\n  {case.id} — {outcome.meta.sentence()}")
        except Exception as exc:  # noqa: BLE001
            case_scores = [Score(f"{case.id}: the run completed", False, f"{type(exc).__name__}: {exc}")]
            print(f"\n  {case.id} — FAILED: {type(exc).__name__}")
        for s in case_scores:
            print("  " + s.line())
        scores.extend(case_scores)
    return scores


async def run_agents(repeat: int, cap: float, only: str = "") -> dict:
    """Every agent case, `repeat` times, until the money cap is reached.

    Runs four at a time. The cap is checked before each run starts, so the total
    can exceed it by at most the runs already in flight — said here so nobody
    reads the cap as an invoice.
    """
    from evals.agent_graders import AGENTS, run_case

    wanted = [a.strip() for a in only.split(",") if a.strip()] or list(AGENTS)
    jobs = [(agent, case, attempt) for agent in wanted
            for case in AGENTS[agent][0] for attempt in range(1, repeat + 1)]
    spent = 0.0
    skipped = 0
    results: list[dict] = []
    gate = asyncio.Semaphore(4)

    async def one(agent, case, attempt):
        nonlocal spent, skipped
        async with gate:
            if spent >= cap:
                skipped += 1
                return
            outcome = await run_case(agent, case, attempt)
            spent += outcome["cost_usd"]
            results.append(outcome)
            graded = [s for s in outcome["scores"] if not s["skipped"]]
            ok = sum(s["passed"] for s in graded)
            tag = f"REFUSED ({outcome['refused']})" if outcome["refused"] else f"{ok}/{len(graded)}"
            print(f"  {agent:<19} {case.id:<28} #{attempt}  {tag:<16} "
                  f"${outcome['cost_usd']:.4f}  {','.join(outcome['models'])}"
                  + (f"  repairs={outcome['repairs']}" if outcome["repairs"] else ""))
            for s in outcome["scores"]:
                if not s["passed"] and not s["skipped"]:
                    print(f"      FAIL {s['name']} — {s['detail']}")

    await asyncio.gather(*(one(*job) for job in jobs))

    by_agent: dict = {}
    for agent in wanted:
        mine = [r for r in results if r["agent"] == agent]
        graded = [s for r in mine for s in r["scores"] if not s["skipped"]]
        passed = sum(s["passed"] for s in graded)
        by_agent[agent] = {
            "runs": len(mine),
            "passed": passed, "total": len(graded),
            "ratio": passed / len(graded) if graded else 0.0,
            "refusals": sum(1 for r in mine if r["refused"]),
            "cost_usd": round(sum(r["cost_usd"] for r in mine), 4),
            "models": sorted({m for r in mine for m in r["models"]}),
            "repairs": sorted({x for r in mine for x in r["repairs"]}),
        }

    print("\n  per agent:")
    for agent, s in by_agent.items():
        print(f"    {agent:<19} {s['passed']:>3}/{s['total']:<3} ({s['ratio']:.0%})  "
              f"refusals {s['refusals']}  ${s['cost_usd']:.4f}  {', '.join(s['models'])}"
              + (f"  repairs {s['repairs']}" if s["repairs"] else ""))
    print(f"\n  spent ${spent:.4f} of the ${cap:.2f} cap"
          + (f" — {skipped} run(s) not started because the cap was reached" if skipped else ""))
    print("  every case is synthetic and awaits review by an auditor (needs_review)")
    return {"by_agent": by_agent, "runs": results, "spent_usd": round(spent, 4),
            "cap_usd": cap, "not_started": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="IA Wingman agent evaluation suite")
    parser.add_argument("--file", action="store_true", help="also grade the real engagements' artifacts")
    parser.add_argument("--strict", action="store_true",
                        help="let the file scorecard fail the run (it reports only by default)")
    parser.add_argument("--live", action="store_true", help="also make real agent calls (costs tokens)")
    parser.add_argument("--json", metavar="PATH", help="write the full report as JSON")
    parser.add_argument("--agents", action="store_true",
                        help="run the six agents on their eval cases (real calls, costs tokens)")
    parser.add_argument("--repeat", type=int, default=2,
                        help="runs per agent case, so variance is visible (default 2)")
    parser.add_argument("--cap", type=float, default=10.0,
                        help="stop starting new agent runs once this many dollars are spent")
    parser.add_argument("--only", default="",
                        help="comma-separated agents to run, e.g. frameworks,finding")
    args = parser.parse_args()

    report: dict = {"run_at": datetime.now(timezone.utc).isoformat(), "sections": {}}
    failed = False

    print("RETRIEVAL — does the answer reach the model?")
    scores, stats = run_retrieval()
    for s in scores:
        print(s.line())

    reach = [x for x in scores if "reaches the model" in x.name]
    rankish = [x for x in scores if "reaches the model" not in x.name]
    reach_ratio = sum(x.passed for x in reach) / len(reach) if reach else 0
    rank_ratio = sum(x.passed for x in rankish) / len(rankish) if rankish else 0

    print()
    print(f"  reach: {sum(x.passed for x in reach)}/{len(reach)} ({reach_ratio:.0%})"
          f" · threshold {THRESHOLDS['retrieval_reach']:.0%}")
    print(f"  rank:  {sum(x.passed for x in rankish)}/{len(rankish)} ({rank_ratio:.0%})"
          f" · threshold {THRESHOLDS['retrieval_rank']:.0%}")
    for x in rankish:
        if not x.passed:
            print(f"         missed: {x.name} — {x.detail}")
    print(f"  reached by depth: {stats['reached_by_depth']}")
    print(f"  the old 4,000-character clip would have found: {stats['old_clip_would_have_found']}")
    report["sections"]["retrieval"] = {
        "reach": reach_ratio, "rank": rank_ratio, **stats,
        "scores": [{"name": s.name, "passed": s.passed, "detail": s.detail, "value": s.value} for s in scores],
    }
    failed |= reach_ratio < THRESHOLDS["retrieval_reach"]
    failed |= rank_ratio < THRESHOLDS["retrieval_rank"]

    # The adversarial tier. Reported, never gating: it exists to state where
    # lexical ranking gives out, not to be passed. Deleting it would hide the
    # one thing this suite is best placed to say honestly.
    from evals.golden_set import ADVERSARIAL_STUFFING
    adv_scores, _ = run_retrieval(stuffing=ADVERSARIAL_STUFFING)
    adv_reached = [s for s in adv_scores if "reaches the model" in s.name]
    adv_beats = [s for s in adv_scores if "near-misses" in s.name]
    print()
    print("  adversarial tier (near-misses stuffed with the query "
          f"{ADVERSARIAL_STUFFING}x, reported and not gating):")
    print(f"    the answer still reaches the model: {sum(s.passed for s in adv_reached)}/{len(adv_reached)}")
    print(f"    it still outranks the stuffed decoy: {sum(s.passed for s in adv_beats)}/{len(adv_beats)}"
          f"   <- the known limit of lexical ranking")
    report["sections"]["retrieval_adversarial"] = {
        "stuffing": ADVERSARIAL_STUFFING,
        "reached": f"{sum(s.passed for s in adv_reached)}/{len(adv_reached)}",
        "outranked_decoy": f"{sum(s.passed for s in adv_beats)}/{len(adv_beats)}",
        "gating": False,
    }

    if args.file:
        print("\n\nTHE FILE — properties an audit file ought to have")
        scores = asyncio.run(run_file())
        passed, total = _summarise(scores)
        ratio = passed / total if total else 0
        print(f"\n  {passed}/{total} ({ratio:.0%}) · threshold {THRESHOLDS['file']:.0%}"
              + ("" if args.strict else "  (reporting only — pass --strict to gate on this)"))
        report["sections"]["file"] = {
            "passed": passed, "total": total, "ratio": ratio, "gating": args.strict,
            "scores": [{"name": s.name, "passed": s.passed, "skipped": s.skipped,
                        "detail": s.detail, "value": s.value} for s in scores],
        }
        # This section measures the CONTENT of real audit files, which is the
        # auditors' work and the seed data's completeness — not whether this
        # codebase regressed. Gating a build on it would make a thin demo file
        # look like a broken build, so it reports unless asked to do otherwise.
        if args.strict:
            failed |= ratio < THRESHOLDS["file"]

    if args.live:
        print("\n\nLIVE — what the agent actually concludes (this costs tokens)")
        scores = asyncio.run(run_live())
        passed, total = _summarise(scores)
        ratio = passed / total if total else 0
        print(f"\n  {passed}/{total} ({ratio:.0%}) · threshold {THRESHOLDS['live']:.0%}")
        report["sections"]["live"] = {
            "passed": passed, "total": total, "ratio": ratio,
            "scores": [{"name": s.name, "passed": s.passed, "detail": s.detail, "value": s.value} for s in scores],
        }
        failed |= ratio < THRESHOLDS["live"]

    if args.agents:
        print(f"\n\nAGENTS — six agents on their own code paths (this costs tokens; cap ${args.cap:.2f})")
        section = asyncio.run(run_agents(args.repeat, args.cap, args.only))
        report["sections"]["agents"] = section
        for agent, summary in section["by_agent"].items():
            failed |= summary["ratio"] < THRESHOLDS["agents"]

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1)
        print(f"\nreport written to {args.json}")

    print("\n" + ("BELOW THRESHOLD" if failed else "ALL SECTIONS AT OR ABOVE THRESHOLD"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
