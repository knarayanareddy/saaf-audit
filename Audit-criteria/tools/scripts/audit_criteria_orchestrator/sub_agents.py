"""Sub-agents for the Audit Criteria Orchestrator.

Deterministic (no model): ``read_pr`` and the execution half of ``stress_test``.
LLM-backed: questions, draft, review, adversarial stress, revise. Each LLM stage
has an offline fixture so ``--simulate`` runs end to end without an API key.

Security note: the stress tester EXECUTES verification commands from the
document, i.e. code from the PR under review. It only runs ``python -m
tools.scripts.*`` or ``python <file>.py`` inside the repo root, never through a
shell, with a timeout and with secrets stripped from the environment. Live runs
require ``--allow-exec``; run it in CI or a sandbox, not on a workstation that
holds credentials.
"""

import json
import logging
import os
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import prompts, schemas

logger = logging.getLogger(__name__)

SYNTHESIS_MODEL = "claude-opus-5"
VALIDATION_MODEL = "claude-sonnet-5"
EXEC_TIMEOUT_S = 60
_SAFE_ENV = {"PATH", "HOME", "LANG", "LC_ALL", "SYSTEMROOT", "TEMP", "TMP", "PYTHONIOENCODING"}
_TEXT_EXT = {".py", ".md", ".json", ".txt", ".toml", ".yaml", ".yml", ".cfg"}
_SKIP_DIRS = {".git", "runs", "__pycache__", "node_modules", ".venv"}
CONTEXT_BUDGET = 80_000

# Offline knob: when True the mock reviser never discloses a failing AC, so the
# retry budget is exhausted and the code-enforced bound becomes visible.
MOCK_STUBBORN = False


# --------------------------------------------------------------------------- #
# Model plumbing (same pattern as audit_planning_orchestrator/sub_agents.py)
# --------------------------------------------------------------------------- #

def make_client() -> Any:
    import anthropic

    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    return anthropic.Anthropic(default_headers={"anthropic-workspace-id": workspace} if workspace else None)


def _extract_json(text: str) -> Dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model response")
    return json.loads(text[start: end + 1])


def ask(client: Any, system: str, payload: Dict[str, Any], model: str = SYNTHESIS_MODEL) -> Dict[str, Any]:
    response = client.messages.create(
        model=model, max_tokens=16000, thinking={"type": "adaptive"}, system=system,
        messages=[{"role": "user", "content": json.dumps(payload, indent=2, ensure_ascii=False)}],
    )
    return _extract_json("".join(b.text for b in response.content if b.type == "text"))


# --------------------------------------------------------------------------- #
# 1. Read PR  (deterministic)
# --------------------------------------------------------------------------- #

def _safe_extract(zip_path: Path) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="pr-zip-"))
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (dest / member.filename).resolve()
            if not str(target).startswith(str(dest.resolve())) or member.external_attr >> 28 == 0xA:
                raise ValueError(f"unsafe path in archive: {member.filename}")
        zf.extractall(dest)
    tops = [p for p in dest.iterdir()]
    return tops[0] if len(tops) == 1 and tops[0].is_dir() else dest


def _collect(root: Path) -> List[Dict[str, str]]:
    files, used = [], 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in _TEXT_EXT or _SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")[:12_000]
        if used + len(text) > CONTEXT_BUDGET:
            files.append({"path": str(path.relative_to(root)), "content": "[omitted: context budget]"})
            continue
        used += len(text)
        files.append({"path": str(path.relative_to(root)), "content": text})
    return files


def _github_get(url: str, raw: bool = False) -> Any:
    headers = {"Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return body if raw else json.loads(body)


def read_pr(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Read the component under review: --repo-dir, --zip, or GitHub PR (read-only)."""
    if payload.get("github"):
        repo, number = payload["github"], payload["pr"]
        files = _github_get(f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page=100")
        readme = _github_get(f"https://api.github.com/repos/{repo}/readme", raw=True)
        return {"source": f"github:{repo}#{number}", "root": payload.get("repo_dir"), "readme": readme,
                "files": [{"path": f["filename"], "content": f.get("patch", "")[:12_000]} for f in files]}
    root = Path(payload["repo_dir"]) if payload.get("repo_dir") else _safe_extract(Path(payload["zip"]))
    readme = root / "README.md"
    return {"source": f"local:{root.name}", "root": str(root),
            "readme": readme.read_text(encoding="utf-8") if readme.exists() else "",
            "files": _collect(root)}


# --------------------------------------------------------------------------- #
# 2. Q&A  (LLM asks, human answers)
# --------------------------------------------------------------------------- #

def questions(client: Optional[Any], pr: Dict[str, Any]) -> List[str]:
    if client is None:
        return list(MOCK_ANSWERS)
    return ask(client, prompts.QUESTIONS_PROMPT, {"readme": pr["readme"], "files": [f["path"] for f in pr["files"]]}
               ).get("questions", [])


# --------------------------------------------------------------------------- #
# 3-6. Draft / review / stress / revise
# --------------------------------------------------------------------------- #

def draft(client: Optional[Any], pr: Dict[str, Any], qa: List[Dict[str, str]]) -> Dict[str, Any]:
    if client is None:
        return {"document": MOCK_DRAFT}
    return ask(client, prompts.DRAFTER_PROMPT, {"pr": pr, "qa": qa})


def review(client: Optional[Any], pr: Dict[str, Any], document: str) -> Dict[str, Any]:
    if client is None:
        return {"verdict": "No-Go", "findings": [{
            "id": "RV-1", "severity": "Medium",
            "issue": "Never-do list does not forbid continuing past the retry budget.",
            "fix": "Add: 'Never keep correcting after MAX_RETRIES; escalate to a human.'"}]}
    return ask(client, prompts.REVIEWER_PROMPT, {"files": pr["files"], "document": document}, VALIDATION_MODEL)


def _allowed(argv: List[str], root: Path) -> bool:
    if len(argv) < 2 or argv[0] not in {"python", "python3"}:
        return False
    if argv[1] == "-m":
        return len(argv) > 2 and argv[2].startswith("tools.scripts.")
    target = (root / argv[1]).resolve()
    return argv[1].endswith(".py") and str(target).startswith(str(root.resolve())) and target.is_file()


def execute_criteria(document: str, root: Optional[str], allow_exec: bool) -> List[Dict[str, Any]]:
    """Run every AC's verification command. Real subprocess, no shell."""
    results = []
    env = {k: v for k, v in os.environ.items() if k in _SAFE_ENV}
    for ac in schemas.parse(document)["acs"]:
        rec: Dict[str, Any] = {"ac": ac["ac"], "command": ac["command"]}
        argv = shlex.split(ac["command"])
        if not root or not allow_exec:
            rec["outcome"] = "not-run"
        elif not _allowed(argv, Path(root)):
            rec["outcome"] = "blocked"
        else:
            try:
                proc = subprocess.run([sys.executable] + argv[1:], cwd=root, env=env, capture_output=True,
                                      text=True, timeout=EXEC_TIMEOUT_S, shell=False)
                rec["exit_code"] = proc.returncode
                rec["outcome"] = {0: "pass", 1: "fail"}.get(proc.returncode, "untestable")
                rec["output"] = (proc.stdout + proc.stderr).strip()[-400:]
            except subprocess.TimeoutExpired:
                rec["outcome"] = "untestable"
                rec["output"] = f"timed out after {EXEC_TIMEOUT_S}s"
        results.append(rec)
    return results


def stress_test(client: Optional[Any], pr: Dict[str, Any], document: str, allow_exec: bool) -> Dict[str, Any]:
    results = execute_criteria(document, pr.get("root"), allow_exec)
    if client is None:
        adversarial = [{"id": "ST-1", "severity": "Low",
                        "issue": "No criterion covers prompt injection via the input bundle.",
                        "fix": "List it under Coverage gaps."}]
    else:
        adversarial = ask(client, prompts.STRESS_PROMPT, {"document": document, "executed": results},
                          VALIDATION_MODEL).get("adversarial", [])
    return {"results": results, "adversarial": adversarial}


def revise(client: Optional[Any], document: str, review_out: Dict[str, Any], stress_out: Dict[str, Any],
           gate_findings: List[str]) -> Dict[str, Any]:
    if client is not None:
        return ask(client, prompts.REVISER_PROMPT, {"document": document, "review": review_out,
                                                    "stress": stress_out, "gate_findings": gate_findings})
    doc, log = document, []
    if "--check retry_bound" in doc:
        doc = doc.replace("--check retry_bound", "--check retry-bound")
        log.append("AC-2: fixed verification command (exit 2: unknown check 'retry_bound').")
    if "MAX_RETRIES; escalate" not in doc:
        doc = doc.replace("## 6. Known deviations",
                          "- Never keep correcting after MAX_RETRIES; escalate to a human.\n\n## 6. Known deviations")
        log.append("RV-1: added retry-budget item to Never do.")
    if "prompt injection" not in doc:
        doc = doc.replace("## 8. How to re-verify",
                          "2. Prompt injection via the input bundle is not tested.\n\n## 8. How to re-verify")
        log.append("ST-1: added prompt-injection coverage gap.")
    if any("not disclosed" in g for g in gate_findings) and not MOCK_STUBBORN:
        doc = doc.replace("None at time of drafting.",
                          "| ID | AC | Severity | Finding | Recommended fix |\n|---|---|---|---|---|\n"
                          "| D-1 | AC-2 | High | Retry budget is prompt-enforced only; toy agent "
                          "exceeds it. | Enforce the bound in code. |")
        log.append("Gate: disclosed failing AC-2 as D-1.")
    return {"document": doc, "changelog": log}


# --------------------------------------------------------------------------- #
# Offline fixtures (target: sample_data/toy_repo)
# --------------------------------------------------------------------------- #

MOCK_ANSWERS = {
    "What is the component for, and who relies on its output?":
        "A toy planning agent; auditors rely on its Go/No-Go verdict.",
    "What must never happen?": "An unbounded correction loop, or a verdict without a trail.",
    "Which frameworks matter most?": "IIA Standards, OWASP LLM/AI, ISO 27001.",
    "What is explicitly out of scope?": "Live model quality; only the orchestration layer.",
}

MOCK_DRAFT = """\
# AUDIT-CRITERIA — Toy Planning Agent

## 1. Scope

The toy agent's orchestration layer (sample_data/toy_repo/toy_agent.py).

## 2. Control objectives

### CO-1 — Hand-off integrity

**Frameworks:** COSO Principle 10; OWASP LLM05

**Objective:** Malformed output never reaches the next stage.

### CO-2 — Bounded autonomy

**Frameworks:** OWASP LLM06; IIA Standards 12.3

**Objective:** Correction loops stop after the retry budget, in code.

### CO-3 — Audit trail

**Frameworks:** ISO 27001 A.8.15; IIA Standards 14.6

**Objective:** Every run leaves a complete trail.

## 3. Acceptance criteria

| AC | CO | Criterion (pass/fail) | Verification | Result |
|---|---|---|---|---|
| AC-1 | CO-1 | Malformed hand-off is rejected | `python toy_agent.py --check schema` | |
| AC-2 | CO-2 | Loop stops at MAX_RETRIES in code | `python toy_agent.py --check retry_bound` | |
| AC-3 | CO-3 | Trail has run_start and run_end | `python toy_agent.py --check trail` | |

## 4. Good output

- A verdict plus a complete trail.

## 5. Never do

- Never pass invalid output downstream.

## 6. Known deviations

None at time of drafting.

## 7. Coverage gaps

1. Live model behaviour is not tested.

## 8. How to re-verify

Run each command in the table from the repo root.
"""
