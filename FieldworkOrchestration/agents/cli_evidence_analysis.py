"""cli_evidence_analysis agent — interprets raw CLI command output as audit evidence.

Ported (from a plan, not existing code — see agents/cli_runner.py's
docstring) from the CLI Audit System Wrapper plan. Pairs with
``agents.cli_runner.run_command``: that module runs an allowlisted command
and returns raw stdout/stderr; this agent turns that raw output into
structured, cited evidence and flags anomalies. Kept as a separate module on
purpose — this agent never touches ``subprocess``, so the security-critical
command-execution path in ``cli_runner.py`` stays small and independently
reviewable.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.cli_evidence_analysis import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.cli_evidence_analysis import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the cli_evidence_analysis agent and return its structured result.

    ``inputs`` keys:
        system (str — e.g. "Active Directory"), command_result (dict — the
        output of ``cli_runner.run_command()``), analysis_instructions (str
        — what to extract/flag, e.g. "Flag any accounts belonging to former
        employees").

    If ``command_result["error"]`` is set (the command was refused or failed
    to run), no Claude call is made — there is nothing to interpret.
    """
    command_result = inputs["command_result"]

    if command_result.get("error"):
        return {
            "system": inputs.get("system", "unknown"),
            "command": command_result.get("command_executed"),
            "executed_at": command_result.get("executed_at"),
            "records": [],
            "flagged": [],
            "finding_seed": f"Command could not be run: {command_result['error']}",
        }

    stderr_section = (
        f"Stderr:\n{command_result['stderr']}\n" if command_result.get("stderr") else ""
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        system=inputs.get("system", "unknown"),
        command=command_result["command_executed"],
        executed_at=command_result["executed_at"],
        stdout=command_result["stdout"] or "(empty output)",
        stderr_section=stderr_section,
        analysis_instructions=inputs["analysis_instructions"],
    )

    client = client or ClaudeClient()
    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="cli_evidence_analysis",
    )

    return extract_json_block(text_from_message(message))
