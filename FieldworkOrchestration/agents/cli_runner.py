"""Deterministic, allowlist-enforcing CLI command runner.

Built from the CLI Audit System Wrapper plan (Track 2 — Evidence Collection,
plans/hackathon-3/cli-audit-system-wrapper.md) for audit-relevant systems
that expose a CLI but no REST API (AD PowerShell/dsquery, Splunk CLI,
ServiceNow CLI export, SAP audit log export).

Deliberately NOT an agentic tool-use loop: Claude never decides which
command to run. The caller — a human, or code a human wrote and reviewed —
picks a command name and parameters explicitly; this module is the only
thing that touches ``subprocess``, and it refuses anything not in the
allowlist. The allowlist is the actual security control, not the model's
judgement. Use ``cli_evidence_analysis`` (an ordinary Claude agent — see
agents/cli_evidence_analysis.py) to turn this module's raw output into
structured audit evidence; that concern is kept out of this module
deliberately, so the security-critical path here stays small and easy to
review on its own.

    from agents.cli_runner import run_command
    result = run_command("echo_placeholder", {"message": "hello"})
    # -> {"command_name": ..., "command_executed": "echo hello", "stdout": "hello\\n", ...}

Every parameter value is shell-quoted (``shlex.quote``) before being
substituted into the command's template, so a parameter value cannot break
out of its argument position — only the trusted template (from the
allowlist file, never from a parameter) determines what actually runs.
Enforcing "read-only, no state changes" is a governance rule for whoever
edits the allowlist file, not something this code can verify — it can only
guarantee that nothing outside the allowlist runs at all.

Default allowlist: ``agents/cli_allowlist.json``, which ships with only a
placeholder ``echo`` entry — there is no real target system in this repo to
test against.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ALLOWLIST_PATH = Path(__file__).resolve().parent / "cli_allowlist.json"
DEFAULT_TIMEOUT_SECONDS = 30


def load_allowlist(path: Path | None = None) -> dict:
    """Load the command allowlist from JSON. No caching — always the current file on disk."""
    path = path or DEFAULT_ALLOWLIST_PATH
    allowlist = json.loads(path.read_text(encoding="utf-8"))
    allowlist.pop("_comment", None)
    return allowlist


def run_command(
    command_name: str,
    params: dict[str, Any] | None = None,
    *,
    allowlist: dict | None = None,
    allowlist_path: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Run one allowlisted command and return its structured, raw result.

    Refuses anything not in the allowlist by returning an ``error`` result
    rather than raising, so a caller running several commands in a row
    doesn't need a try/except around every call — check ``result["error"]``.
    """
    params = params or {}
    allowlist = allowlist if allowlist is not None else load_allowlist(allowlist_path)

    if command_name not in allowlist:
        return _error_result(
            command_name, f"{command_name!r} is not in the allowlist — refusing to run it."
        )

    template = allowlist[command_name]["template"]
    try:
        quoted_params = {k: shlex.quote(str(v)) for k, v in params.items()}
        command = template.format(**quoted_params)
    except KeyError as exc:
        return _error_result(command_name, f"Missing required parameter: {exc}")

    executed_at = datetime.now(timezone.utc)
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        stdout, stderr, returncode, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\n[timed out after {timeout}s]"
        returncode, timed_out = None, True

    return {
        "command_name": command_name,
        "error": None,
        "command_executed": command,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": returncode,
        "timed_out": timed_out,
        "executed_at": executed_at.isoformat(),
        "duration_ms": round((time.monotonic() - started) * 1000, 1),
    }


def log_command(entry: dict, *, run_id: str | None = None, log_path: Path | None = None) -> Path:
    """Append one ``run_command()`` result to a JSONL command log.

    Defaults to ``runs/<run_id>/cli_commands.jsonl`` — the same ``runs/``
    location as the Claude audit trail (gitignored), but its own file: a
    command execution doesn't fit the Claude-call audit trail's schema, so
    it isn't forced into it. Pass ``log_path`` directly to use another
    location.
    """
    if log_path is None:
        if run_id is None:
            raise ValueError("pass either run_id or log_path")
        from agents.audit_trail import RUNS_DIR

        log_path = RUNS_DIR / run_id / "cli_commands.jsonl"

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return log_path


def _error_result(command_name: str, error: str) -> dict:
    return {
        "command_name": command_name,
        "error": error,
        "command_executed": None,
        "stdout": None,
        "stderr": None,
        "returncode": None,
        "timed_out": False,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 0,
    }
