"""Audit Planning Orchestrator — the LLM 'command' agent.

Runs UC7 (RCM) -> UC8 (Work Program) -> UC9 (Quality & Resource Guard) by giving
the three sub-agents to a Claude model as tools and letting it decide the order,
while this loop enforces the structural schema gates and the bounded No-Go
recovery budget, and records a full audit trail.

Usage (run from the repo root):

    # Full run — calls the Claude API (needs ANTHROPIC_API_KEY):
    python -m tools.scripts.audit_planning_orchestrator.orchestrator \\
        --input tools/scripts/audit_planning_orchestrator/sample_data/accounts_payable.json

    # Real orchestrator reasoning, cheap deterministic sub-agents (needs a key):
    python -m tools.scripts.audit_planning_orchestrator.orchestrator --mock-subagents

    # Fully offline — deterministic controller, no API call, proves the wiring:
    python -m tools.scripts.audit_planning_orchestrator.orchestrator --simulate

Design: plans/hackathon-4/p-papen-audit-planning-orchestrator.md
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Support both "python -m tools.scripts...orchestrator" and direct execution.
if __package__:
    from . import prompts, schemas, sub_agents
    from .run_logger import RunLogger, new_run_id
else:  # pragma: no cover - direct-script convenience
    sys.path.insert(0, str(Path(__file__).parent))
    import prompts  # type: ignore
    import schemas  # type: ignore
    import sub_agents  # type: ignore
    from run_logger import RunLogger, new_run_id  # type: ignore

logger = logging.getLogger("orchestrator")

ORCHESTRATOR_MODEL = "claude-opus-5"
MAX_RETRIES = 2          # No-Go correction cycles before escalating to a human
MAX_TURNS = 12           # hard ceiling on orchestrator turns (runaway guard)


class RunState:
    """Mutable pipeline state shared across sub-agent calls in one run."""

    def __init__(self, bundle: Dict[str, Any]) -> None:
        self.process_map: Dict[str, Any] = bundle.get("process_map", {})
        self.rcm: List[Dict[str, Any]] = []
        self.work_program: List[Dict[str, Any]] = []
        self.resource_report: Dict[str, Any] = {}
        self.last_quality: Dict[str, Any] = {}


def dispatch(
    tool_name: str,
    tool_input: Dict[str, Any],
    state: RunState,
    run_log: RunLogger,
    client: Optional[Any],
    mock: bool,
) -> Tuple[Dict[str, Any], str]:
    """Run one sub-agent, apply the structural gate, persist the artifact.

    Returns (result, status) where status is "ok" or "error". On "error" the
    result carries an "error" message and must not be passed downstream.
    """
    try:
        if mock:
            result = sub_agents.mock_subagent(tool_name, tool_input)
        else:
            result = sub_agents.call_subagent(client, tool_name, tool_input)
    except (ValueError, KeyError) as exc:
        result = {"status": "error", "error": f"{tool_name} produced unparseable output: {exc}"}
        run_log.log_tool_call(tool_name, result, status="error", errors=[str(exc)])
        return result, "error"

    errors = schemas.validate(tool_name, result)
    if errors:
        result = {"status": "error", "error": "schema validation failed", "details": errors}
        run_log.log_tool_call(tool_name, result, status="error", errors=errors)
        return result, "error"

    # Gate passed — record state and persist the hand-off artifact.
    if tool_name == "run_rcm_builder":
        state.rcm = result["rcm"]
    elif tool_name == "run_work_program":
        state.work_program = result["work_program"]
        state.resource_report = result.get("resource_report", {})
    elif tool_name == "run_quality_guard":
        state.last_quality = result

    result.setdefault("status", "ok")
    run_log.log_tool_call(tool_name, result, status="ok")
    return result, "ok"


def _build_summary(run_id: str, engagement: str, state: RunState, cycles: int) -> Dict[str, Any]:
    verdict = state.last_quality.get("verdict", "No-Go")
    return {
        "run_id": run_id,
        "engagement": engagement,
        "final_verdict": verdict,
        "cycles": cycles,
        "outstanding_gaps": [] if verdict == "Go" else state.last_quality.get("gaps", []),
        "rcm": state.rcm,
        "work_program": state.work_program,
        "resource_report": state.resource_report,
    }


# --------------------------------------------------------------------------- #
# LLM orchestrator (manual agentic loop)
# --------------------------------------------------------------------------- #

def run_llm(bundle: Dict[str, Any], mock: bool) -> Dict[str, Any]:
    """Drive the pipeline with a Claude orchestrator making the tool decisions."""
    client = sub_agents.make_client()  # honors ANTHROPIC_WORKSPACE_ID for org-scoped keys
    engagement = bundle.get("engagement", "engagement")
    run_id = new_run_id(engagement)
    run_log = RunLogger(run_id, engagement)
    state = RunState(bundle)

    tools = sub_agents.tool_definitions()
    kickoff = (
        "Run the audit planning pipeline for the "
        f"'{engagement}' engagement using these consolidated inputs:\n\n"
        f"{json.dumps(bundle, indent=2)}\n\n"
        "Produce the full planning package and report the final UC9 verdict."
    )
    messages: List[Dict[str, Any]] = [{"role": "user", "content": kickoff}]

    retries = 0
    turns = 0
    while turns < MAX_TURNS:
        turns += 1
        response = client.messages.create(
            model=ORCHESTRATOR_MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=prompts.ORCHESTRATOR_PROMPT,
            tools=tools,
            messages=messages,
        )

        reasoning = "".join(b.text for b in response.content if b.type == "text").strip()
        if reasoning:
            run_log.log_reasoning(reasoning)

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        if response.stop_reason == "end_turn":
            break

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in tool_uses:
            result, status = dispatch(block.name, dict(block.input), state, run_log, client, mock)

            # Bounded recovery budget: count UC9 No-Go verdicts.
            if block.name == "run_quality_guard" and status == "ok" and result.get("verdict") == "No-Go":
                retries += 1
                if retries > MAX_RETRIES:
                    result["escalate_to_human"] = True

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                    "is_error": status == "error",
                }
            )
        messages.append({"role": "user", "content": tool_results})

    summary = _build_summary(run_id, engagement, state, cycles=retries)
    run_log.finalize(summary)
    return summary


# --------------------------------------------------------------------------- #
# Deterministic controller (offline; no LLM) — proves the wiring
# --------------------------------------------------------------------------- #

def run_simulated(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Same order, gates and recovery loop as the LLM path, but scripted.

    No model is called (implies mock sub-agents), so the full orchestration —
    including the UC9 No-Go -> re-run UC7 -> UC9 Go recovery — runs offline.
    """
    engagement = bundle.get("engagement", "engagement")
    run_id = new_run_id(engagement)
    run_log = RunLogger(run_id, engagement)
    state = RunState(bundle)
    retries = 0

    def gate(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result, status = dispatch(name, payload, state, run_log, client=None, mock=True)
        if status == "error":
            raise RuntimeError(f"{name} failed the schema gate: {result}")
        return result

    run_log.log_reasoning("No RCM exists yet; calling UC7 RCM Builder.")
    gate("run_rcm_builder", {"process_map": state.process_map, "risks": bundle.get("risks", [])})

    run_log.log_reasoning("Valid RCM available; calling UC8 Work Program.")
    gate(
        "run_work_program",
        {"rcm": state.rcm, "auditor_directory": bundle.get("auditor_directory", []),
         "available_hours": bundle.get("available_hours", 160)},
    )

    while True:
        run_log.log_reasoning("Package complete; calling UC9 Quality & Resource Guard.")
        quality = gate(
            "run_quality_guard",
            {"process_map": state.process_map, "rcm": state.rcm,
             "work_program": state.work_program, "resource_report": state.resource_report},
        )
        if quality["verdict"] == "Go" or retries >= MAX_RETRIES:
            break

        retries += 1
        gap = "; ".join(quality.get("gaps", []))
        if any("work program" in g.lower() for g in quality.get("gaps", [])):
            run_log.log_reasoning(f"UC9 No-Go (work-program gap); re-running UC8. Gap: {gap}")
            gate(
                "run_work_program",
                {"rcm": state.rcm, "auditor_directory": bundle.get("auditor_directory", []),
                 "available_hours": bundle.get("available_hours", 160), "correction": gap},
            )
        else:
            run_log.log_reasoning(f"UC9 No-Go (RCM/scoping gap); re-running UC7. Gap: {gap}")
            gate(
                "run_rcm_builder",
                {"process_map": state.process_map, "risks": bundle.get("risks", []), "correction": gap},
            )
            run_log.log_reasoning("RCM changed; rebuilding the work program.")
            gate(
                "run_work_program",
                {"rcm": state.rcm, "auditor_directory": bundle.get("auditor_directory", []),
                 "available_hours": bundle.get("available_hours", 160)},
            )

    summary = _build_summary(run_id, engagement, state, cycles=retries)
    run_log.finalize(summary)
    return summary


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _load_bundle(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Planning Orchestrator (UC7 -> UC8 -> UC9).")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent / "sample_data" / "accounts_payable.json",
        help="Path to the risk-input bundle JSON.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run the deterministic controller with mock sub-agents (no API call).",
    )
    parser.add_argument(
        "--mock-subagents",
        action="store_true",
        help="Use the real Claude orchestrator but stub UC7/UC8/UC9 with fixtures.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not args.input.exists():
        logger.error("Input bundle not found: %s", args.input)
        return 2
    bundle = _load_bundle(args.input)

    if args.simulate:
        summary = run_simulated(bundle)
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.error(
                "ANTHROPIC_API_KEY is not set. Set it, or run with --simulate for an offline demo."
            )
            return 2
        summary = run_llm(bundle, mock=args.mock_subagents)

    print(json.dumps({k: summary[k] for k in ("run_id", "engagement", "final_verdict", "cycles", "outstanding_gaps")}, indent=2))
    logger.info("Full package written under runs/%s/", summary["run_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
