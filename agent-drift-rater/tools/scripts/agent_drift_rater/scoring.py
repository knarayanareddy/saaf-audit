"""Turn signals (+ optional LLM judgment and a mandate) into a drift rating.

The overall rating is always computed here in code; the Claude pass may only adjust the 1-5
dimension scores within the asymmetric rule enforced in judge.py. Aggregation follows the
plan: inherent risk (drivers) x control strength -> residual via a 3x3 matrix, then red-flag
floors, with agency conditioning so advisory single-shot agents are not penalised for
controls that only matter once an agent takes actions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .checks import UnitSignals

DRIVERS = ["D1", "D2", "D3", "D4", "D5"]
CONTROLS = ["C1", "C2", "C3", "C4", "C5"]

DIMENSION_NAMES = {
    "D1": "Proxy pressure (target in context)",
    "D2": "Self-editing (writable instructions/memory)",
    "D3": "Context loss (policy drops out)",
    "D4": "Untrusted input",
    "D5": "Permission creep (bounded agency)",
    "C1": "Hard rules enforced in code",
    "C2": "Versioned instructions/memory",
    "C3": "Independent drift review",
    "C4": "Human oversight, rollback & quarantine",
    "C5": "Replayable decision log",
}

# Controls that only matter once the agent takes actions (agency-conditioned).
ACTION_CONDITIONED = {"C1", "C4", "C5", "D4", "D5"}


@dataclass
class DimScore:
    dim: str
    score: int
    evidence: str            # sufficient | partial | none
    basis: str               # deterministic | llm-adjusted | assumed | not-evidenced
    note: str = ""
    signals: List[str] = field(default_factory=list)


@dataclass
class RedFlag:
    rf: str
    status: str              # raised | observation | not-raised | not-assessable
    evidence: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class UnitRating:
    unit_id: str
    classification: str
    agency: str
    action_capable: bool
    dimensions: Dict[str, DimScore]
    inherent: str
    control_strength: str
    residual: str
    confidence: str
    red_flags: List[RedFlag]
    provisional: bool = False
    notes: List[str] = field(default_factory=list)


RESIDUAL_MATRIX = {
    ("High", "Strong"): "Medium", ("High", "Moderate"): "High", ("High", "Weak"): "High",
    ("Medium", "Strong"): "Low", ("Medium", "Moderate"): "Medium", ("Medium", "Weak"): "High",
    ("Low", "Strong"): "Informational", ("Low", "Moderate"): "Low", ("Low", "Weak"): "Low",
}
_ORDER = ["Informational", "Low", "Medium", "High"]


def _bump(rating: str, steps: int = 1) -> str:
    return _ORDER[min(len(_ORDER) - 1, _ORDER.index(rating) + steps)]


def _score_dimension(dim: str, sigs: UnitSignals, coverage: float, action_capable: bool) -> DimScore:
    dim_sigs = sigs.by_dim(dim)
    refs = sorted({f"{s.path}#L{s.line}" for s in dim_sigs if s.line > 1}) or \
        sorted({s.path for s in dim_sigs})
    if dim in CONTROLS:
        if not dim_sigs:
            if dim in ACTION_CONDITIONED and not action_capable:
                return DimScore(dim, 3, "none", "not-applicable",
                                "control not required for an advisory agent")
            return DimScore(dim, 1, "none", "not-evidenced", "no control evidence found")
        level = max(s.level for s in dim_sigs)
        return DimScore(dim, level, "sufficient", "deterministic",
                        "; ".join(sorted({s.note for s in dim_sigs}))[:200], refs)
    # driver
    if not dim_sigs:
        if coverage < 0.60:
            return DimScore(dim, 3, "none", "assumed", "assumed (low file coverage)")
        return DimScore(dim, 1, "sufficient", "deterministic", "no driver evidence")
    level = max(s.level for s in dim_sigs)
    return DimScore(dim, level, "sufficient" if coverage >= 0.6 else "partial", "deterministic",
                    "; ".join(sorted({s.note for s in dim_sigs}))[:200], refs)


def _inherent(scores: Dict[str, DimScore], action_capable: bool) -> str:
    d = {k: scores[k].score for k in DRIVERS}
    if d["D5"] <= 1 and not action_capable:
        # advisory: untrusted input and permission creep cannot drive to High alone
        for k in ("D4", "D5"):
            d[k] = min(d[k], 2)
    level = "Low"
    if max(d.values()) >= 5 or sum(1 for v in d.values() if v >= 4) >= 2:
        level = "High"
    elif max(d.values()) >= 3:
        level = "Medium"
    if d["D5"] >= 4 and any(v >= 3 for k, v in d.items() if k != "D5"):
        level = _bump(level)
    return level


def _control_strength(scores: Dict[str, DimScore]) -> str:
    weights = {"C1": 2, "C2": 1, "C3": 1, "C4": 1, "C5": 2}
    total = sum(scores[c].score * weights[c] for c in CONTROLS)
    mean = total / sum(weights.values())
    hard = min(scores["C1"].score, scores["C5"].score)
    if mean >= 3.5 and hard >= 3:
        return "Strong"
    if mean < 2.5 or hard <= 1:
        return "Weak"
    return "Moderate"


def _red_flags(scores: Dict[str, DimScore], sigs: UnitSignals, action_capable: bool,
               mandate_prompt_only_rules: int) -> List[RedFlag]:
    flags: List[RedFlag] = []

    def refs(dim: str) -> List[str]:
        return scores[dim].signals

    # RF1 self-editing — always escalates
    d2 = [s for s in sigs.by_dim("D2") if s.rule.startswith("write_instruction")]
    flags.append(RedFlag("RF1", "raised" if scores["D2"].score >= 4 else "not-raised",
                         sorted({f"{s.path}#L{s.line}" for s in d2}),
                         "agent can write its own instructions/memory"))
    # RF2 target in context — always
    flags.append(RedFlag("RF2", "raised" if scores["D1"].score >= 4 else "not-raised",
                         refs("D1"), "performance target in the agent's context"))
    # RF3 rules only in prompt — action-conditioned
    if mandate_prompt_only_rules > 0:
        status = "raised" if action_capable else "observation"
    else:
        status = "not-raised"
    flags.append(RedFlag("RF3", status, [],
                         f"{mandate_prompt_only_rules} hard rule(s) not enforced in code"))
    # RF4 escalations falling — proxy only
    has_escalation = any(s.dimension == "C4" for s in sigs.signals)
    if not action_capable:
        flags.append(RedFlag("RF4", "not-assessable", [], "proxy; agent takes no actions"))
    else:
        flags.append(RedFlag("RF4", "observation" if not has_escalation else "not-assessable",
                             [], "proxy: no escalation path detected" if not has_escalation
                             else "proxy; needs runtime data"))
    # RF5 softening in agent-written notes — always
    soft = [s for s in sigs.by_dim("D2") if s.rule == "softening"]
    flags.append(RedFlag("RF5", "raised" if soft else "not-assessable",
                         sorted({f"{s.path}#L{s.line}" for s in soft}),
                         "softened wording in agent-written notes" if soft
                         else "no agent-written notes to assess"))
    # RF6 no replayable log — action/multi-turn conditioned
    if action_capable or any(s.dimension == "C5" for s in sigs.signals):
        flags.append(RedFlag("RF6", "raised" if scores["C5"].score < 4 else "not-raised",
                             refs("C5"), "no per-decision instruction/model version in the log"))
    else:
        flags.append(RedFlag("RF6", "observation" if scores["C5"].score < 4 else "not-raised",
                             [], "advisory agent; replay less critical"))
    return flags


def _confidence(coverage: float, mandate_status: str, llm_ran: bool,
                scores: Dict[str, DimScore], truncated: bool) -> str:
    if truncated:
        return "Low"
    assumed = sum(1 for s in scores.values() if s.basis == "assumed")
    if coverage >= 0.85 and mandate_status == "confirmed" and llm_ran and assumed == 0:
        return "High"
    if coverage < 0.60 or assumed >= 2 or (not llm_ran):
        return "Low"
    return "Medium"


def score_unit(unit_id: str, classification: str, coverage: float, sigs: UnitSignals,
               mandate_status: str = "none", prompt_only_rules: int = 0,
               llm_ran: bool = False, truncated: bool = False,
               notes: Optional[List[str]] = None,
               llm_scores: Optional[Dict[str, int]] = None) -> UnitRating:
    action_capable = sigs.action_capable
    scores = {dim: _score_dimension(dim, sigs, coverage, action_capable)
              for dim in DRIVERS + CONTROLS}
    if llm_scores:
        for dim, value in llm_scores.items():
            if dim in scores and value != scores[dim].score:
                scores[dim].score = value
                scores[dim].basis = "llm-adjusted"
    inherent = _inherent(scores, action_capable)
    control = _control_strength(scores)
    if mandate_status in ("none", "unconfirmed", "stale"):
        control = "Moderate" if control == "Strong" else control  # no confirmed mandate caps at Moderate
    residual = RESIDUAL_MATRIX[(inherent, control)]

    flags = _red_flags(scores, sigs, action_capable, prompt_only_rules)
    raised = [f for f in flags if f.status == "raised"]
    if raised and residual == "Informational":
        residual = "Low"
    if any(f.rf == "RF1" for f in raised) and any(f.rf == "RF3" for f in raised):
        residual = "High"  # the Drift Watch combination

    confidence = _confidence(coverage, mandate_status, llm_ran, scores, truncated)
    note_list = list(notes or [])
    if sigs.syntax_errors:
        note_list.append(f"{len(sigs.syntax_errors)} file(s) unparsed (syntax); regex fallback")
    return UnitRating(
        unit_id=unit_id, classification=classification, agency=sigs.agency,
        action_capable=action_capable, dimensions=scores, inherent=inherent,
        control_strength=control, residual=residual, confidence=confidence,
        red_flags=flags, provisional=(mandate_status != "confirmed"), notes=note_list,
    )
