"""Draft findings with Claude Code in headless mode, with a prepared fallback.

The call uses the auditor's own Claude Code login (no API key in this repo):

    claude -p --output-format json --json-schema <schema> --tools "" --strict-mcp-config ...

All tools are disabled, so the model can only read the pseudonymised input on stdin.
If Claude Code is missing, not logged in, offline or too slow, the agent falls back to:
  1. a prepared result for the exact same data set (matched by fingerprint), or
  2. a deterministic draft built from the test results (no model).
The UI always shows which of the three was used.

Prepare the fallback for the sample data (run once, with Claude Code logged in):
    python3 -m ai.claude_runner --prepare --lang en
    python3 -m ai.claude_runner --prepare --lang nl
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from engine.findings import FINDING_SCHEMA, deterministic_assessments, deterministic_findings, validate_draft
from engine.jml_checks import TESTS, BASELINE_TESTS
from engine.pseudonymise import Pseudonymiser, allowed_references, build_payload

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parents[1]
PROMPT_PATH = REPO_ROOT / "prompts" / "draft-findings.md"
PREPARED_DIR = REPO_ROOT / "demo"
LANGUAGES = {"en": "English", "nl": "Dutch (Nederlands)"}
DEFAULT_MODEL = os.environ.get("JML_CLAUDE_MODEL", "sonnet")
DEFAULT_TIMEOUT = int(os.environ.get("JML_CLAUDE_TIMEOUT", "180"))

LIFECYCLE_OF = {t["id"]: t["lifecycle"] for t in TESTS}
LIFECYCLE_OF.update({b["id"]: "baseline" for b in BASELINE_TESTS.values()})

_finding_props = {k: v for k, v in FINDING_SCHEMA["properties"].items()
                  if k in ("id", "title", "risk_rating", "control_objective", "observation", "root_cause", "impact",
                           "recommendation", "status", "ai_assisted", "evidence_references")}
OUTPUT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "assessments", "findings"],
    "properties": {
        "summary": {"type": "string"},
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["exception_id", "conclusion", "rationale"],
                "properties": {
                    "exception_id": {"type": "string"},
                    "conclusion": {"type": "string", "enum": ["Confirmed exception", "Needs follow-up"]},
                    "rationale": {"type": "string"},
                    "follow_up": {"type": "string"},
                },
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "risk_rating", "control_objective", "observation", "root_cause",
                             "impact", "recommendation", "status", "ai_assisted", "evidence_references"],
                "properties": _finding_props,
            },
        },
    },
}

CLAUDE_CANDIDATES = [
    Path.home() / ".local" / "bin" / "claude",
    Path.home() / ".claude" / "local" / "claude",
    Path("/opt/homebrew/bin/claude"),
    Path("/usr/local/bin/claude"),
]


def find_claude() -> Optional[str]:
    found = shutil.which("claude")
    if found:
        return found
    for p in CLAUDE_CANDIDATES:
        if p.exists():
            return str(p)
    return None


def claude_status() -> dict:
    """Is Claude Code installed and logged in? Free to call: no model request is made."""
    exe = find_claude()
    if not exe:
        return {"installed": False, "logged_in": False, "version": "", "message": "Claude Code is not installed."}
    status = {"installed": True, "logged_in": False, "version": "", "message": ""}
    try:
        v = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=15)
        status["version"] = v.stdout.strip()
        a = subprocess.run([exe, "auth", "status"], capture_output=True, text=True, timeout=15)
        data = json.loads(a.stdout or "{}")
        status["logged_in"] = bool(data.get("loggedIn"))
        status["message"] = "Ready." if status["logged_in"] else "Claude Code is installed but not logged in."
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        status["message"] = f"Could not check Claude Code: {exc}"
    return status


def load_prompt() -> tuple[str, str]:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    system = re.search(r"<!-- system:start -->(.*?)<!-- system:end -->", text, re.S).group(1).strip()
    user = re.search(r"<!-- user:start -->(.*?)<!-- user:end -->", text, re.S).group(1).strip()
    return system, user


def render_user_prompt(template: str, payload: dict, language: str) -> str:
    r = payload["review"]
    values = {
        "organisation": r["organisation"],
        "period_start": r["audit_period"]["start"],
        "period_end": r["audit_period"]["end"],
        "extraction_date": r["extraction_date"],
        "language": LANGUAGES.get(language, "English"),
        "payload_json": json.dumps(payload, indent=1, ensure_ascii=False),
    }
    out = template
    for k, v in values.items():
        out = out.replace(f"[{k}]", str(v))
    return out


def call_claude(system: str, user: str, model: str, timeout: int) -> tuple[dict, dict]:
    """Run one headless Claude Code request. Returns (structured_output, call metadata)."""
    exe = find_claude()
    if not exe:
        raise RuntimeError("Claude Code is not installed")
    cmd = [
        exe, "-p",
        "--output-format", "json",
        "--json-schema", json.dumps(OUTPUT_SCHEMA),
        "--system-prompt", system,
        "--tools", "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--setting-sources", "",
        "--model", model,
    ]
    started = time.monotonic()
    proc = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=timeout,
                          cwd=str(REPO_ROOT / "runs"))
    duration = round(time.monotonic() - started, 1)
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Claude Code returned no JSON (exit {proc.returncode}): {proc.stderr.strip()[:300]}")
    if envelope.get("is_error") or proc.returncode != 0:
        raise RuntimeError(f"Claude Code error: {str(envelope.get('result', proc.stderr))[:300]}")
    out = envelope.get("structured_output")
    if not isinstance(out, dict):
        raise RuntimeError("Claude Code returned no structured output")
    models = list((envelope.get("modelUsage") or {}).keys())
    meta = {"duration_s": duration, "model": models[0] if models else model,
            "cost_usd": envelope.get("total_cost_usd"), "session_id": envelope.get("session_id")}
    return out, meta


def prepared_path(language: str) -> Path:
    return PREPARED_DIR / f"prepared_findings.{language}.json"


def load_prepared(fingerprint: str, language: str) -> Optional[dict]:
    path = prepared_path(language)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("fingerprint") != fingerprint:
        log.info("Prepared result %s is for another data set, not used", path.name)
        return None
    return data


def _write(run_dir: Optional[Path], name: str, data: object) -> None:
    if run_dir is None:
        return
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / name
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def draft_findings(review: dict, run_dir: Optional[Path] = None, language: str = "en", mode: str = "auto",
                   model: str = DEFAULT_MODEL, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Draft findings. mode: auto (live, then fallback) | prepared | deterministic."""
    pz = Pseudonymiser(review["_anon_map"], review["_people"])
    payload = build_payload(review, pz)
    allowed = allowed_references(payload)
    exception_ids = [e["id"] for e in review["exceptions"]]
    system, user_tpl = load_prompt()
    user = render_user_prompt(user_tpl, payload, language)
    _write(run_dir, "model_input.json", payload)
    (REPO_ROOT / "runs").mkdir(exist_ok=True)

    result: dict = {"mode": None, "language": language, "error": None, "model": None, "duration_s": None,
                    "fingerprint": review["fingerprint"]}

    if mode == "auto":
        try:
            out, meta = call_claude(system, user, model, timeout)
            _write(run_dir, "model_output_raw.json", out)
            checked = validate_draft(out, allowed, exception_ids)
            if checked["checks"]["findings_kept"] == 0:
                raise RuntimeError("no finding passed validation: " + "; ".join(checked["checks"]["issues"]))
            result.update(mode="live", **meta, **checked["draft"], checks=checked["checks"])
        except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
            log.warning("Live Claude draft failed, falling back: %s", exc)
            result["error"] = str(exc)

    if result["mode"] is None and mode in ("auto", "prepared"):
        prep = load_prepared(review["fingerprint"], language)
        if prep:
            checked = validate_draft(prep["draft"], allowed, exception_ids)
            result.update(mode="prepared", model=prep.get("model"), duration_s=None,
                          prepared_at=prep.get("created_at"), **checked["draft"], checks=checked["checks"])

    if result["mode"] is None:
        det = {"summary": f"{len(exception_ids)} exceptions were found by the deterministic tests. "
                          "No model draft is available; these findings are generated from templates.",
               "findings": deterministic_findings(review, LIFECYCLE_OF),
               "assessments": deterministic_assessments(review)}
        checked = validate_draft(det, allowed | {e["id"] for e in review["exceptions"]}, exception_ids)
        result.update(mode="deterministic", **checked["draft"], checks=checked["checks"])

    _write(run_dir, "draft.json", {k: v for k, v in result.items()})
    return result


def main() -> None:
    from engine.jml_checks import run_review
    from engine.sources import load_sources

    parser = argparse.ArgumentParser(description="Draft JML findings with Claude Code")
    parser.add_argument("--sources", default=None, help="sources YAML (default: sources.sample.yaml)")
    parser.add_argument("--lang", default="en", choices=sorted(LANGUAGES))
    parser.add_argument("--prepare", action="store_true", help="save a live result as the prepared fallback")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    review = run_review(load_sources(args.sources))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = REPO_ROOT / "runs" / f"{stamp}-draft"
    res = draft_findings(review, run_dir, language=args.lang)
    print(f"mode={res['mode']} findings={len(res['findings'])} checks={res['checks']}")
    if args.prepare:
        if res["mode"] != "live" or not res["checks"]["passed"]:
            raise SystemExit("Not saved: the live draft did not pass every check. See the issues above.")
        data = {"fingerprint": review["fingerprint"], "language": args.lang, "model": res["model"],
                "created_at": stamp, "note": "Prepared fallback: a real live Claude Code result on the sample data.",
                "draft": {k: res[k] for k in ("summary", "assessments", "findings")}}
        prepared_path(args.lang).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {prepared_path(args.lang).relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
