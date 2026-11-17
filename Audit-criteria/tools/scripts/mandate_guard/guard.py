"""Mandate guard: check an agent's output against its input and its mandate.

Schema gates prove a hand-off is well formed. This guard proves it is
faithful: nothing the input required was dropped, nothing was invented, and no
instruction hidden in the input steered the agent. It checks what the agent
did on this run, not what its documents say it does.

Pure standard library, so it runs on system Python with no install step.

Each invariant in the mandate maps to one check below. A check returns a list
of failure strings; an empty list means the invariant held. Adapters translate
an agent's own input/output shape into the rows these checks read, so the same
mandate works for the orchestrator's UC8 wrapper and for the standalone UC8
repo.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Tuple

KNOWN_INVARIANTS = {
    "high_risk_has_test_of_effectiveness",
    "fields_match_input",
    "no_instructions_in_input",
}

# Phrases that address the agent rather than describe a control. Deliberately
# narrow: a false positive holds a run for a human, it never blocks silently.
_INSTRUCTION_PATTERNS = [
    r"\b(ignore|disregard|override)\b.{0,40}\b(instructions?|prompt|rules?|above|previous)\b",
    r"\b(return|output|respond with|produce|set)\b.{0,40}\b(empty|no|zero)\b.{0,30}\b(tests?|lists?|steps?|findings?)\b",
    r"\bno (further )?(tests?|testing|tests of effectiveness)\b.{0,40}\b(required|needed|necessary)\b",
    r"\b(skip|omit|remove|drop)\b.{0,30}\b(tests?|testing|steps?)\b",
    r"\bmark\b.{0,40}\b(as )?(effective|passed|compliant|tested)\b",
    r"\b(auditor note|note to the (model|ai|assistant|agent))\b",
    r"\b(you are now|as an ai|system prompt)\b",
]
_INSTRUCTION_RE = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INSTRUCTION_PATTERNS]


# --------------------------------------------------------------------------- #
# Mandate loading
# --------------------------------------------------------------------------- #
def load_mandate(path: Path) -> Dict[str, Any]:
    """Load a mandate from JSON, or YAML when PyYAML happens to be installed.

    Accepts either a bare mandate or a full agent manifest with a ``mandate``
    key (the agent.yaml shape from saaf-living-map).
    """
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith((".yaml", ".yml")):
        import yaml  # optional; JSON mandates need no third-party package
        doc = yaml.safe_load(text)
    else:
        doc = json.loads(text)
    mandate = doc.get("mandate", doc)
    unknown = [i.get("id") for i in mandate.get("output_invariants", [])
               if i.get("id") not in KNOWN_INVARIANTS]
    if unknown:
        raise ValueError(f"mandate names unknown invariants: {unknown}")
    if not mandate.get("output_invariants"):
        raise ValueError("mandate declares no output_invariants; refusing a guard that checks nothing")
    return mandate


# --------------------------------------------------------------------------- #
# Normalised view the checks read
# --------------------------------------------------------------------------- #
@dataclass
class ControlView:
    """One control as the input defined it, and what the output did with it."""

    control_id: str
    high_risk: bool
    input_fields: Dict[str, Any]
    output_fields: Dict[str, Any]
    tests_of_effectiveness: int
    covered: bool = True


@dataclass
class Observation:
    controls: List[ControlView]
    input_doc: Any
    invented_control_ids: List[str] = field(default_factory=list)
    duplicate_control_ids: List[str] = field(default_factory=list)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def observe_orchestrator(rcm_rows: List[Dict[str, Any]], work_program: List[Dict[str, Any]]) -> Observation:
    """Adapter for the orchestrator hand-off: RCM rows in, flat task list out."""
    tasks_by_control: Dict[str, List[Dict[str, Any]]] = {}
    for task in work_program:
        tasks_by_control.setdefault(task.get("control_id"), []).append(task)
    rcm_ids = {row.get("control_id") for row in rcm_rows}
    controls = []
    for row in rcm_rows:
        cid = row.get("control_id")
        tasks = tasks_by_control.get(cid, [])
        risk = row.get("inherent_risk")
        rating = risk.get("rating") if isinstance(risk, dict) else risk
        controls.append(ControlView(
            control_id=cid,
            # Fail closed: a rating the guard cannot read is treated as High.
            high_risk=rating not in ("Medium", "Low"),
            input_fields={"control_id": cid},
            output_fields={"control_id": cid} if tasks else {},
            tests_of_effectiveness=sum(1 for t in tasks if t.get("test_type") == "ToE"),
            covered=bool(tasks),
        ))
    invented = sorted({str(t.get("control_id")) for t in work_program} - {str(i) for i in rcm_ids})
    seen, dupes = set(), set()
    for row in rcm_rows:
        cid = str(row.get("control_id"))
        (dupes if cid in seen else seen).add(cid)
    return Observation(controls=controls, input_doc=rcm_rows, invented_control_ids=invented,
                       duplicate_control_ids=sorted(dupes))


def observe_uc8_entry(control: Dict[str, Any], entry: Dict[str, Any]) -> Observation:
    """Adapter for the standalone UC8 repo: one flattened RCM control, one entry."""
    fields = ("control_id", "control_owner", "control_frequency")
    view = ControlView(
        control_id=control.get("control_id"),
        high_risk=control.get("significance") == "High",
        input_fields={f: control.get(f) for f in fields},
        output_fields={f: entry.get(f) for f in fields},
        tests_of_effectiveness=len(entry.get("tests_of_effectiveness") or []),
    )
    return Observation(controls=[view], input_doc=control)


# --------------------------------------------------------------------------- #
# Invariant checks
# --------------------------------------------------------------------------- #
def _strings(obj: Any, path: str = "") -> Iterator[Tuple[str, str]]:
    if isinstance(obj, str):
        yield path or "$", obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")


def scan_for_instructions(doc: Any) -> List[str]:
    """Return 'path: matched text' for every input string that addresses the agent."""
    hits = []
    for path, text in _strings(doc):
        for rx in _INSTRUCTION_RE:
            m = rx.search(text)
            if m:
                hits.append(f"{path}: \"{m.group(0)[:80]}\"")
                break
    return hits


def check_high_risk_has_toe(obs: Observation, _spec: Dict[str, Any]) -> List[str]:
    return [f"{c.control_id}: High-risk control has no test of effectiveness"
            for c in obs.controls if c.high_risk and c.tests_of_effectiveness == 0]


def check_fields_match_input(obs: Observation, spec: Dict[str, Any]) -> List[str]:
    failures = [f"{cid}: output names a control that is not in the input" for cid in obs.invented_control_ids]
    failures += [f"{cid}: control ID appears more than once in the trusted input" for cid in obs.duplicate_control_ids]
    wanted = spec.get("fields") or ["control_id"]
    for c in obs.controls:
        if not c.covered:
            failures.append(f"{c.control_id}: control from the input is missing from the output")
            continue
        for f in wanted:
            if f in c.input_fields and f in c.output_fields and _norm(c.input_fields[f]) != _norm(c.output_fields[f]):
                failures.append(f"{c.control_id}: {f} changed from {c.input_fields[f]!r} to {c.output_fields[f]!r}")
    return failures


def check_no_instructions(obs: Observation, _spec: Dict[str, Any]) -> List[Tuple[str, str]]:
    # (detail, evidence): the matched text is evidence for the log only, so a
    # held hand-off never echoes the injected instruction back to a model.
    return [(f"instruction-like text in input at {hit.split(':', 1)[0]}", hit)
            for hit in scan_for_instructions(obs.input_doc)]


CHECKS: Dict[str, Callable[[Observation, Dict[str, Any]], List[Any]]] = {
    "high_risk_has_test_of_effectiveness": check_high_risk_has_toe,
    "fields_match_input": check_fields_match_input,
    "no_instructions_in_input": check_no_instructions,
}


# --------------------------------------------------------------------------- #
# Verdict
# --------------------------------------------------------------------------- #
@dataclass
class Verdict:
    passed: bool
    action: str  # "pass" or the approval-gate action, e.g. "hold_for_human"
    failures: List[Dict[str, str]]

    def to_record(self) -> Dict[str, Any]:
        return {"passed": self.passed, "action": self.action, "failures": self.failures}


def evaluate(mandate: Dict[str, Any], obs: Observation) -> Verdict:
    """Run every invariant the mandate names and apply its approval gate."""
    failures = []
    for spec in mandate.get("output_invariants", []):
        for item in CHECKS[spec["id"]](obs, spec):
            detail, evidence = item if isinstance(item, tuple) else (item, None)
            failure = {"invariant": spec["id"], "detail": detail}
            if evidence:
                failure["evidence"] = evidence
            failures.append(failure)
    if not failures:
        return Verdict(True, "pass", [])
    gate = next((g for g in mandate.get("approval_gates", []) if g.get("when") == "any_invariant_fails"), None)
    # No gate declared still fails closed: an unchecked failure must reach a human.
    return Verdict(False, (gate or {}).get("action", "hold_for_human"), failures)
