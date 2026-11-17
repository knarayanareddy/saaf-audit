"""Audit Criteria Orchestrator — drafts and hardens AUDIT-CRITERIA.md for a PR.

    read_pr -> Q&A -> draft -> (review || stress_test) -> revise -> gate
                                   ^                                 |
                                   +---- retry (<= MAX_RETRIES) -----+  No-Go: soft block
                                                                     |  human: retry / override / abort
                                                                     v
                                                               place in PR

Stage order, the gate and the retry budget are CODE, not prompt: the LLM
sub-agents shape content only. This answers Open Question 3 of the Audit Planning
Orchestrator plan in favour of a deterministic, reviewable control flow, and it
avoids that component's D-3 finding (retry bound enforced only by the prompt).

Usage (from the repo root):
    # Offline, no API key; executes the toy repo's criteria for real:
    python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate
    python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate --decisions override
    python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate --decisions abort
    python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate --stubborn --decisions retry,retry,retry

    # Live (needs ANTHROPIC_API_KEY); run inside a sandbox/CI because ACs execute PR code:
    python -m tools.scripts.audit_criteria_orchestrator.orchestrator --repo-dir . --allow-exec --place

Design: plans/hackathon-4/p-audit-criteria-orchestrator.md
"""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

from . import prompts, schemas, sub_agents
from .run_logger import RunLogger, digest, new_run_id

logger = logging.getLogger("criteria-orchestrator")

MAX_RETRIES = 2
PKG = Path(__file__).parent
TOY_REPO = PKG / "sample_data" / "toy_repo"

_PROMPTS = {"qa": prompts.QUESTIONS_PROMPT, "draft": prompts.DRAFTER_PROMPT, "review": prompts.REVIEWER_PROMPT,
            "stress_test": prompts.STRESS_PROMPT, "revise": prompts.REVISER_PROMPT}
_MODELS = {"review": sub_agents.VALIDATION_MODEL, "stress_test": sub_agents.VALIDATION_MODEL}


class StageError(RuntimeError):
    """A stage failed its schema gate or produced unparseable output."""


def _retry_options(retries: int) -> List[str]:
    """Options offered at the soft block. 'retry' is structurally removed once
    the budget is spent, so no human or model input can exceed MAX_RETRIES."""
    return ["retry", "override", "abort"] if retries < MAX_RETRIES else ["override", "abort"]


class Ctx:
    def __init__(self, log: RunLogger, client: Optional[Any], allow_exec: bool,
                 decide: Callable[[List[str], List[str]], str], reason: Callable[[], str],
                 answer: Callable[[str], str]) -> None:
        self.log, self.client, self.allow_exec = log, client, allow_exec
        self.decide, self.reason, self.answer = decide, reason, answer

    def dispatch(self, tool: str, payload: Dict[str, Any], fn: Callable[[], Dict[str, Any]],
                 artifact: Optional[str] = None) -> Dict[str, Any]:
        """Run one stage, gate it (fail-closed), log digests, persist the artifact."""
        if payload.get("purpose") == "gate re-execution":  # deterministic, no model involved
            tool_is_llm = False
        else:
            tool_is_llm = tool in _PROMPTS
        llm = self.client is not None and tool_is_llm
        model = _MODELS.get(tool, sub_agents.SYNTHESIS_MODEL) if llm else ("mock" if tool_is_llm else None)
        prompt_hash = digest(_PROMPTS[tool]) if tool_is_llm else None
        try:
            result = fn()
        except (ValueError, KeyError) as exc:
            self.log.tool_call(tool, payload, {}, "error", model, prompt_hash, errors=[str(exc)])
            raise StageError(f"{tool}: unparseable output: {exc}") from exc
        errors = schemas.validate(tool, result)
        if errors:
            self.log.tool_call(tool, payload, result, "error", model, prompt_hash, errors=errors)
            raise StageError(f"{tool}: schema gate failed: {errors}")
        name = self.log.artifact(artifact, result) if artifact else None
        self.log.tool_call(tool, payload, result, "ok", model, prompt_hash, artifact=name)
        return result


def _choose(ctx: Ctx, options: List[str], findings: List[str]) -> str:
    """Ask the human until they pick an offered option; refusals are logged."""
    while True:
        choice = ctx.decide(options, findings)
        if choice in options:
            return choice
        ctx.log.event("decision_rejected", requested=choice, offered=options,
                      reason="retry budget exhausted" if choice == "retry" else "not an offered option")
        if choice == "abort":  # scripted providers fall back to abort when exhausted
            return "abort"


def run(args: argparse.Namespace, ctx: Ctx, run_id: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"run_id": run_id, "outcome": "error", "retries": 0}
    try:
        source = {"repo_dir": args.repo_dir, "zip": args.zip, "github": args.github, "pr": args.pr}
        source = {k: (str(v) if isinstance(v, Path) else v) for k, v in source.items() if v}
        ctx.log.event("orchestrator", reasoning="Reading the PR / component under review.")
        pr = ctx.dispatch("read_pr", source, lambda: sub_agents.read_pr(source), "01_pr_context.json")

        ctx.log.event("orchestrator", reasoning="Interviewing the human on objectives and scope.")
        qs = sub_agents.questions(ctx.client, pr)
        qa = ctx.dispatch("qa", {"questions": qs},
                          lambda: {"qa": [{"question": q, "answer": ctx.answer(q)} for q in qs]}, "02_qa.json")["qa"]

        ctx.log.event("orchestrator", reasoning="Drafting AUDIT-CRITERIA.md from source and Q&A.")
        document = ctx.dispatch("draft", {"pr": pr["source"], "qa": qa},
                                lambda: sub_agents.draft(ctx.client, pr, qa), "03_draft.json")["document"]

        retries, gate_findings = 0, []
        while True:
            n = retries + 1
            ctx.log.event("orchestrator", reasoning=f"Iteration {n}: review and stress test in parallel.")
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_review = pool.submit(ctx.dispatch, "review", {"document": document},
                                       lambda: sub_agents.review(ctx.client, pr, document), f"04_review_{n}.json")
                f_stress = pool.submit(ctx.dispatch, "stress_test", {"document": document},
                                       lambda: sub_agents.stress_test(ctx.client, pr, document, ctx.allow_exec),
                                       f"05_stress_{n}.json")
                review_out, stress_out = f_review.result(), f_stress.result()

            ctx.log.event("orchestrator", reasoning=f"Iteration {n}: revising with review, stress and gate findings.")
            revision = ctx.dispatch("revise", {"document": document, "gate_findings": gate_findings},
                                    lambda: sub_agents.revise(ctx.client, document, review_out, stress_out,
                                                              gate_findings), f"06_revision_{n}.json")
            document = revision["document"]

            final_exec = {"results": sub_agents.execute_criteria(document, pr.get("root"), ctx.allow_exec),
                          "adversarial": []}
            ctx.dispatch("stress_test", {"document": document, "purpose": "gate re-execution"},
                         lambda: final_exec, f"07_gate_exec_{n}.json")
            gate_findings = schemas.dod_check(document, final_exec)
            ctx.log.event("gate", iteration=n, verdict="No-Go" if gate_findings else "Go", findings=gate_findings)
            if not gate_findings:
                summary["outcome"] = "Go"
                break

            options = _retry_options(retries)
            ctx.log.event("soft_block", iteration=n, offered=options, retries_used=retries, max_retries=MAX_RETRIES)
            decision = _choose(ctx, options, gate_findings)
            ctx.log.event("human_decision", decision=decision)
            if decision == "retry":
                retries += 1
                continue
            if decision == "override":
                reason = ctx.reason()
                ctx.log.event("override", reason=reason, open_findings=gate_findings)
                stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                banner = (f"> **Human override ({stamp}):** published with {len(gate_findings)} open gate "
                          f"finding(s). Reason: {reason}\n>\n" + "".join(f"> - {f}\n" for f in gate_findings) + "\n")
                document = banner + document
                summary["outcome"] = "override"
            else:
                summary["outcome"] = "abort"
            break

        summary.update(retries=retries, open_findings=gate_findings, changelog=revision["changelog"],
                       review_findings=review_out["findings"], stress=final_exec["results"])
        if summary["outcome"] in {"Go", "override"}:
            ctx.log.artifact("AUDIT-CRITERIA.md", document)
            ctx.log.artifact("pr_comment.md", _pr_comment(summary))
            if args.place and pr.get("root") and not args.zip:
                target = Path(pr["root"]) / "AUDIT-CRITERIA.md"
                target.write_text(document, encoding="utf-8")
                summary["placed_at"] = str(target)
                ctx.log.event("placed", path=str(target), digest=digest(document))
        else:
            ctx.log.event("not_placed", reason="aborted by human at soft block")
    except StageError as exc:
        summary["error"] = str(exc)
        ctx.log.event("error", error=str(exc))
    except Exception as exc:  # API outage etc.: still close the trail
        summary["error"] = f"{type(exc).__name__}: {exc}"
        ctx.log.event("error", error=summary["error"])
        raise
    finally:
        ctx.log.finalize(summary)
    return summary


def _pr_comment(s: Dict[str, Any]) -> str:
    rows = "\n".join(f"| {r['ac']} | {r['outcome']} | `{r['command']}` |" for r in s.get("stress", []))
    return (f"### AUDIT-CRITERIA.md — {s['outcome']} after {s['retries']} retr{'y' if s['retries'] == 1 else 'ies'}\n\n"
            f"Run `{s['run_id']}` (trail: `runs/{s['run_id']}/log.jsonl`).\n\n"
            f"| AC | Executed result | Command |\n|---|---|---|\n{rows}\n\n"
            "**Changes in final revision:**\n" + "".join(f"- {c}\n" for c in s.get("changelog", []))
            + ("\n**Open gate findings (overridden):**\n" + "".join(f"- {f}\n" for f in s["open_findings"])
               if s["outcome"] == "override" else ""))


# --------------------------------------------------------------------------- #
# Human I/O: scripted (simulate / --answers / --decisions) or interactive
# --------------------------------------------------------------------------- #

def _scripted(items: List[str]) -> Callable[..., str]:
    it: Iterator[str] = iter(items)
    return lambda *_a: next(it, "abort")


def _interactive_decide(options: List[str], findings: List[str]) -> str:
    print("\nGate verdict: No-Go\n" + "\n".join(f"  - {f}" for f in findings))
    try:
        return input(f"Choose [{'/'.join(options)}]: ").strip().lower()
    except EOFError:
        return "abort"


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Draft and harden AUDIT-CRITERIA.md for a PR.")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--repo-dir", type=Path, help="Local checkout of the PR branch.")
    src.add_argument("--zip", type=Path, help="Repo zip (fallback when no GitHub access).")
    src.add_argument("--github", help="owner/repo, read-only via GitHub API (with --pr).")
    p.add_argument("--pr", type=int, help="PR number for --github.")
    p.add_argument("--answers", type=Path, help="JSON {question: answer} instead of interactive Q&A.")
    p.add_argument("--decisions", default="retry", help="Scripted soft-block decisions (simulate), e.g. retry,override")
    p.add_argument("--override-reason", default="Accepted by reviewer; tracked as follow-up.")
    p.add_argument("--allow-exec", action="store_true", help="Execute AC verification commands (sandbox only).")
    p.add_argument("--place", action="store_true", help="Write the final file into --repo-dir.")
    p.add_argument("--simulate", action="store_true", help="Offline: mock LLM stages, real execution on toy repo.")
    p.add_argument("--stubborn", action="store_true", help="Simulate: reviser never fixes the gate finding.")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.simulate:
        args.repo_dir = args.repo_dir or TOY_REPO
        sub_agents.MOCK_STUBBORN = args.stubborn
        client, allow_exec = None, True
        decide = _scripted([d.strip() for d in args.decisions.split(",") if d.strip()])
        answer = lambda q: sub_agents.MOCK_ANSWERS.get(q, "n/a")
        reason = lambda: args.override_reason
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.error("ANTHROPIC_API_KEY is not set. Set it, or use --simulate.")
            return 2
        if not (args.repo_dir or args.zip or args.github):
            logger.error("Give --repo-dir, --zip or --github/--pr.")
            return 2
        client, allow_exec, decide = sub_agents.make_client(), args.allow_exec, _interactive_decide
        canned = json.loads(args.answers.read_text(encoding="utf-8")) if args.answers else {}
        answer = lambda q: canned.get(q) or input(f"\nQ: {q}\nA: ").strip() or "(no answer)"
        reason = lambda: input("Override reason (logged): ").strip() or "(no reason given)"

    label = Path(str(args.repo_dir or args.zip or args.github)).name
    run_id = new_run_id(f"criteria-{label}")
    ctx = Ctx(RunLogger(run_id, label), client, allow_exec, decide, reason, answer)
    summary = run(args, ctx, run_id)
    print(json.dumps({k: summary.get(k) for k in ("run_id", "outcome", "retries", "open_findings", "placed_at", "error")
                      if summary.get(k) is not None}, indent=2))
    return 0 if summary["outcome"] in {"Go", "override", "abort"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
