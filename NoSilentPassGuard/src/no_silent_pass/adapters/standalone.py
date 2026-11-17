"""Standalone-readiness verdict where "no signals" means NOT_ASSESSED, not "yes".

Pattern fixed: a scanner returning an empty list for unparsable files, and a verdict of
"yes" whenever nothing was detected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from ..guard import Guard, Verdict


@dataclass(frozen=True)
class Signal:
    kind: str  # "llm_client" (positively identified client) or "blocker"
    name: str
    severity: str = "high"  # for blockers: "high" | "medium"


LABELS = {Verdict.PASS: "yes", Verdict.FAIL: "no", Verdict.NOT_ASSESSED: "not assessed"}


def assess_repo(files: Iterable[Tuple[str, bool]], signals: Iterable[Signal]) -> Guard:
    """``files`` is (path, parsed_ok); ``signals`` is what the scanner positively found."""
    g = Guard("standalone-readiness")
    for path, parsed_ok in files:
        if parsed_ok:
            g.mark_assessed(path)
        else:
            g.skip(path, "file could not be parsed; treated as unassessed, not clean")

    sigs = list(signals)
    if not any(s.kind == "llm_client" for s in sigs):
        g.not_assessed("no LLM client was positively identified; absence of signals is not evidence")
    else:
        g.check("llm_client_identified", True)

    for s in sigs:
        if s.kind == "blocker":
            g.check(f"no_{s.severity}_blocker:{s.name}", False, detail=s.name)
    if any(s.kind == "llm_client" for s in sigs) and not any(s.kind == "blocker" for s in sigs):
        g.check("no_blockers_found", True)
    return g


def label(g: Guard) -> str:
    return LABELS[g.verdict()]
