"""Structural gates for every hand-off, plus the deterministic DoD check.

Dependency-free, like ``audit_planning_orchestrator/schemas.py``, with one
deliberate difference: ``validate()`` FAILS CLOSED on a tool name it has no
validator for (the existing orchestrator's gate returns ``[]`` there — D-1 in
its AUDIT-CRITERIA.md).
"""

import re
from typing import Any, Dict, List

FRAMEWORKS = {
    "ISO 27001": "ISO 27001", "GDPR": "GDPR", "DORA": "DORA", "NIS2": "NIS2",
    "EU AI Act": "EU AI Act", "COSO": "COSO", "COBIT": "COBIT", "SOx": "SOx/ICFR",
    "ICFR": "SOx/ICFR", "IIA": "IIA Standards", "GIAS": "IIA Standards", "OWASP": "OWASP LLM/AI",
}
REQUIRED_SECTIONS = ["control objectives", "acceptance criteria", "good output",
                     "never do", "known deviations", "coverage gaps"]
_SEVERITIES = {"High", "Medium", "Low"}
_CO_RE = re.compile(r"^###\s+(CO-\d+)\b", re.M)
_AC_RE = re.compile(r"^\|\s*(AC-\d+)\s*\|\s*(CO-\d+)\s*\|(.+?)\|\s*`([^`]+)`\s*\|", re.M)


def _keys(doc: Dict[str, Any], keys: List[str], where: str) -> List[str]:
    return [f"{where}: missing '{k}'" for k in keys if k not in doc]


def validate_pr(doc: Dict[str, Any]) -> List[str]:
    errors = _keys(doc, ["source", "readme", "files"], "pr")
    if not isinstance(doc.get("files"), list) or not doc.get("files"):
        errors.append("pr: 'files' must be a non-empty list")
    return errors


def validate_questions(doc: Dict[str, Any]) -> List[str]:
    qa = doc.get("qa")
    if not isinstance(qa, list) or not qa:
        return ["qa: expected a non-empty list of {question, answer}"]
    return [f"qa[{i}]: needs non-empty question and answer" for i, x in enumerate(qa)
            if not (isinstance(x, dict) and x.get("question") and x.get("answer"))]


def validate_document(doc: Dict[str, Any]) -> List[str]:
    text = doc.get("document")
    if not isinstance(text, str) or len(text) < 200:
        return ["document: expected the full AUDIT-CRITERIA.md text under 'document'"]
    return []


def validate_review(doc: Dict[str, Any]) -> List[str]:
    errors = []
    if doc.get("verdict") not in {"Go", "No-Go"}:
        errors.append("review: verdict must be 'Go' or 'No-Go'")
    findings = doc.get("findings")
    if not isinstance(findings, list):
        return errors + ["review: findings must be a list"]
    for i, f in enumerate(findings):
        errors += _keys(f, ["id", "severity", "issue", "fix"], f"review.findings[{i}]")
        if f.get("severity") not in _SEVERITIES:
            errors.append(f"review.findings[{i}]: severity must be High/Medium/Low")
    if doc.get("verdict") == "No-Go" and not findings:
        errors.append("review: a No-Go must list at least one finding")
    return errors


def validate_stress(doc: Dict[str, Any]) -> List[str]:
    results = doc.get("results")
    if not isinstance(results, list):
        return ["stress: results must be a list"]
    errors = []
    for i, r in enumerate(results):
        errors += _keys(r, ["ac", "command", "outcome"], f"stress.results[{i}]")
        if r.get("outcome") not in {"pass", "fail", "untestable", "blocked", "not-run"}:
            errors.append(f"stress.results[{i}]: invalid outcome {r.get('outcome')!r}")
    if not isinstance(doc.get("adversarial", []), list):
        errors.append("stress: adversarial must be a list")
    return errors


def validate_revision(doc: Dict[str, Any]) -> List[str]:
    return validate_document(doc) + ([] if isinstance(doc.get("changelog"), list)
                                     else ["revision: changelog must be a list"])


VALIDATORS = {
    "read_pr": validate_pr,
    "qa": validate_questions,
    "draft": validate_document,
    "review": validate_review,
    "stress_test": validate_stress,
    "revise": validate_revision,
}


def validate(tool_name: str, doc: Any) -> List[str]:
    """Run the gate for ``tool_name``. Unknown tools FAIL CLOSED."""
    validator = VALIDATORS.get(tool_name)
    if validator is None:
        return [f"no validator registered for tool '{tool_name}' (fail-closed)"]
    if not isinstance(doc, dict):
        return [f"{tool_name}: expected a JSON object"]
    return validator(doc)


# --------------------------------------------------------------------------- #
# Deterministic Definition-of-Done (the final gate before placement)
# --------------------------------------------------------------------------- #

def parse(document: str) -> Dict[str, Any]:
    """Pull control objectives, frameworks and acceptance criteria out of the doc."""
    cos: Dict[str, List[str]] = {}
    for m in _CO_RE.finditer(document):
        block = document[m.end(): m.end() + 800]
        line = next((l for l in block.splitlines() if "frameworks" in l.lower()), "")
        cos[m.group(1)] = sorted({v for k, v in FRAMEWORKS.items() if k.lower() in line.lower()})
    acs = [{"ac": m.group(1), "co": m.group(2), "criterion": m.group(3).strip(), "command": m.group(4).strip()}
           for m in _AC_RE.finditer(document)]
    headings = [l.lstrip("#").strip().lower() for l in document.splitlines() if l.startswith("## ")]
    return {"cos": cos, "acs": acs, "headings": headings}


def _section(document: str, keyword: str) -> str:
    out, on = [], False
    for line in document.splitlines():
        if line.startswith("## "):
            on = keyword in line.lower()
            continue
        if on:
            out.append(line)
    return "\n".join(out)


def dod_check(document: str, stress: Dict[str, Any]) -> List[str]:
    """Return gate findings; empty list means Go."""
    p = parse(document)
    findings = [f"missing section: '{s}'" for s in REQUIRED_SECTIONS
                if not any(s in h for h in p["headings"])]
    if len(p["cos"]) < 3:
        findings.append(f"needs >= 3 control objectives, found {len(p['cos'])}")
    findings += [f"{co}: no recognised framework on its Frameworks line" for co, fw in p["cos"].items() if not fw]
    covered = {a["co"] for a in p["acs"]}
    findings += [f"{co}: has no acceptance criterion" for co in p["cos"] if co not in covered]
    findings += [f"{a['ac']}: references unknown {a['co']}" for a in p["acs"] if a["co"] not in p["cos"]]
    deviations = _section(document, "known deviations")
    for r in stress.get("results", []):
        if r["outcome"] == "untestable":
            findings.append(f"{r['ac']}: verification is not runnable as written (exit 2): {r['command']}")
        elif r["outcome"] in {"blocked", "not-run"}:
            findings.append(f"{r['ac']}: verification was {r['outcome']} — criterion unverified")
        elif r["outcome"] == "fail" and r["ac"] not in deviations:
            findings.append(f"{r['ac']}: fails when executed but is not disclosed under Known deviations")
    return findings
