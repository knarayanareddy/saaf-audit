"""The client-tool bridge: capture risks during the interview, then build the RCM.

`RcmSession` exposes the two functions registered as ElevenLabs client tools:

- ``capture_control(parameters)`` — records one risk/control pair as the agent
  elicits it, and returns a short spoken confirmation.
- ``build_rcm(parameters)`` — assembles a candidate RCM from the captured items,
  validates it against the UC7 schema gate, optionally refines it through UC7
  (Claude) for deduplication and scoring, writes the artifact, and returns a
  spoken summary (risk count + scoping gaps).

The same two functions are driven live by the voice agent and offline by the
``--simulate`` harness, so the wiring is identical in both paths.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Reuse the UC7 wrapper and the schema gate built for the orchestrator.
try:
    from tools.scripts.audit_planning_orchestrator import schemas, sub_agents
except ImportError:  # pragma: no cover - direct-script convenience
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from tools.scripts.audit_planning_orchestrator import schemas, sub_agents  # type: ignore

logger = logging.getLogger(__name__)

RUNS_DIR = Path(__file__).parent / "runs"

_RATING_SCORE = {"Low": 1, "Medium": 2, "High": 3}
_SCORE_RATING = {1: "Low", 2: "Medium", 3: "High"}


def _rate(impact: str, likelihood: str) -> str:
    """Combine impact and likelihood into a single High/Medium/Low rating."""
    score = max(_RATING_SCORE.get(impact, 2), _RATING_SCORE.get(likelihood, 2))
    return _SCORE_RATING[score]


def _lower(rating: str) -> str:
    """Drop a rating by one band (a control reduces residual likelihood)."""
    return _SCORE_RATING[max(1, _RATING_SCORE.get(rating, 2) - 1)]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RcmSession:
    """Holds walkthrough state and implements the two client tools."""

    def __init__(
        self,
        process_map: Dict[str, Any],
        run_id: str,
        anthropic_client: Optional[Any] = None,
        refine: bool = True,
    ) -> None:
        self.process_map = process_map
        self.captured: List[Dict[str, Any]] = []
        self.client = anthropic_client
        self.refine = refine and anthropic_client is not None
        self.dir = RUNS_DIR / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "transcript.jsonl"
        # Order sub-processes so risk/control ids get a stable P01, P02, ... prefix.
        self._sp_index = {
            sp.get("name"): f"P{i:02d}"
            for i, sp in enumerate(process_map.get("sub_processes", []), start=1)
        }
        self._objectives = {
            sp.get("name"): sp.get("business_objective", "")
            for sp in process_map.get("sub_processes", [])
        }
        self._log({"event": "session_start", "process": process_map.get("process"), "at": _now()})

    # -- logging ---------------------------------------------------------- #

    def _log(self, record: Dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_turn(self, speaker: str, text: str) -> None:
        """Record a spoken turn (used by the live callbacks for the trail)."""
        self._log({"event": "turn", "speaker": speaker, "text": text, "at": _now()})

    # -- client tool 1: capture_control ----------------------------------- #

    def capture_control(self, parameters: Dict[str, Any]) -> str:
        """Record one risk/control pair; return a spoken confirmation."""
        sub_process = parameters.get("sub_process", "")
        item = {
            "sub_process": sub_process,
            "business_objective": parameters.get("business_objective") or self._objectives.get(sub_process, ""),
            "risk_description": parameters.get("risk_description", ""),
            "control_description": parameters.get("control_description", "") or "",
            "control_type": parameters.get("control_type"),
            "control_frequency": parameters.get("control_frequency", ""),
            "impact": parameters.get("impact", "Medium"),
            "likelihood": parameters.get("likelihood", "Medium"),
            "source": parameters.get("source", "Walkthrough — process owner"),
        }
        self.captured.append(item)
        self._log({"event": "capture_control", "item": item, "at": _now()})

        risk = item["risk_description"] or "the risk"
        count = len(self.captured)
        if item["control_description"]:
            return f"Captured '{risk}' with its control. That's {count} item(s) so far."
        return f"Captured '{risk}' with no control - I'll flag that as a gap. {count} item(s) so far."

    # -- client tool 2: build_rcm ----------------------------------------- #

    def build_rcm(self, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Assemble, validate, optionally refine via UC7, and summarise the RCM."""
        if not self.captured:
            return "I haven't captured any risks yet, so there's nothing to build."

        candidate = self._assemble_rcm()
        errors = schemas.validate_rcm(candidate)
        if errors:
            self._log({"event": "build_rcm", "status": "gate_failed", "errors": errors, "at": _now()})
            logger.warning("Assembled RCM failed the schema gate: %s", errors)
            return "I could not assemble a valid RCM from the captured items — please review the log."

        rcm = candidate
        if self.refine:
            refined = self._refine_with_uc7()
            if refined is not None:
                rcm = refined

        (self.dir / "rcm.json").write_text(json.dumps(rcm, indent=2, ensure_ascii=False), encoding="utf-8")
        self._log({"event": "build_rcm", "status": "ok", "rows": len(rcm["rcm"]), "at": _now()})
        return self._summary(rcm)

    # -- internals -------------------------------------------------------- #

    def _assemble_rcm(self) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        seq: Dict[str, int] = {}
        for item in self.captured:
            prefix = self._sp_index.get(item["sub_process"], "P00")
            seq[prefix] = seq.get(prefix, 0) + 1
            n = seq[prefix]
            inherent = _rate(item["impact"], item["likelihood"])
            has_control = bool(item["control_description"])
            residual = _lower(inherent) if has_control else inherent
            rows.append(
                {
                    "risk_id": f"R-{prefix}-{n:03d}",
                    "sub_process": item["sub_process"],
                    "business_objective": item["business_objective"],
                    "risk_description": item["risk_description"],
                    "risk_sources": [item["source"]],
                    "inherent_risk": {"impact": item["impact"], "likelihood": item["likelihood"], "rating": inherent},
                    "control_id": f"C-{prefix}-{n:03d}",
                    "control_description": item["control_description"],
                    "control_type": item["control_type"],
                    "control_frequency": item["control_frequency"],
                    "residual_risk": {"impact": item["impact"], "likelihood": _lower(item["likelihood"]) if has_control else item["likelihood"], "rating": residual},
                }
            )
        return {"rcm": rows}

    def _refine_with_uc7(self) -> Optional[Dict[str, Any]]:
        """Hand the captured risks to UC7 (Claude) for dedup/scoring; None on failure."""
        inputs = {
            "process_map": self.process_map,
            "risks": [
                {
                    "source": item["source"],
                    "sub_process": item["sub_process"],
                    "description": item["risk_description"],
                    "control": item["control_description"],
                    "control_type": item["control_type"],
                }
                for item in self.captured
            ],
            "correction": "These risks come from a live walkthrough; deduplicate and score them.",
        }
        try:
            result = sub_agents.call_subagent(self.client, "run_rcm_builder", inputs)
        except Exception as exc:  # noqa: BLE001 - refine is best-effort; keep the local RCM
            self._log({"event": "refine_uc7", "status": "error", "error": str(exc), "at": _now()})
            logger.warning("UC7 refine failed, keeping locally assembled RCM: %s", exc)
            return None
        if schemas.validate_rcm(result):
            self._log({"event": "refine_uc7", "status": "invalid", "at": _now()})
            return None
        self._log({"event": "refine_uc7", "status": "ok", "rows": len(result["rcm"]), "at": _now()})
        return result

    def _summary(self, rcm: Dict[str, Any]) -> str:
        rows = rcm["rcm"]
        sub_processes = {sp.get("name") for sp in self.process_map.get("sub_processes", []) if sp.get("name")}
        covered = {r["sub_process"] for r in rows}
        gaps = [r["sub_process"] for r in rows if not r.get("control_description")]
        missing = sorted(sub_processes - covered)

        parts = [f"I captured {len(rows)} risk(s) across {len(covered)} sub-process(es)."]
        if gaps:
            parts.append(f"No control on: {', '.join(sorted(set(gaps)))}.")
        if missing:
            parts.append(f"Sub-process(es) with no risk at all: {', '.join(missing)}.")
        if not gaps and not missing:
            parts.append("Every sub-process has a risk and a control.")
        parts.append("Shall I flag the gaps for follow-up?")
        return " ".join(parts)
