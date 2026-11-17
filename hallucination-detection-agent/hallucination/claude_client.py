"""
Claude API Client Wrapper
=========================

Thin wrapper around the ``anthropic`` SDK:
- Loads the API key from environment (fails fast if missing).
- Provides a helper for prompt caching on system prompts.
- Centralises model selection and prompt loading.

This is the only module that directly imports ``anthropic`` — keep the rest
of the pipeline dependency-agnostic for easier testing and future swap-out.

Decision reference: D7 (see plans/hackathon-3/table-9-execution-plan.md §0.4).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anthropic


# Model constants — centralised so a single change propagates everywhere.
MODEL_EXTRACTOR = "claude-haiku-4-5"
MODEL_VERIFIER = "claude-sonnet-4-6"

# Repo root — used to resolve prompt paths and the log location.
# Layout since the move to its own repository (October 2026):
#   <repo_root>/hallucination/claude_client.py
#   <repo_root>/prompts/audit-use-cases/*.md   (copies of the SAAF shared prompts)
#   <repo_root>/outputs/logs/hallucination-checks.jsonl
# Before the move the root was four folders up (tools/scripts/track-5/hallucination);
# in its own repo that resolved to /Users. Override with HALLUCINATION_REPO_ROOT.
REPO_ROOT = Path(os.environ.get("HALLUCINATION_REPO_ROOT") or Path(__file__).resolve().parents[1])


def get_api_key() -> str:
    """Return the Anthropic API key from the environment.

    Returns:
        The key string. Guaranteed non-empty.

    Raises:
        EnvironmentError: If ``ANTHROPIC_API_KEY`` is not set. Error message
            points the user to the README for setup instructions.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key or key.startswith("sk-ant-PLACEHOLDER"):
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set (or still the placeholder value).\n"
            "See README.md (API Key Setup) for setup.\n"
            "This tool does not ship with a key — bring your own."
        )
    return key


def _client() -> anthropic.Anthropic:
    """Build an Anthropic client with the resolved API key."""
    return anthropic.Anthropic(api_key=get_api_key())


def call_with_cached_system(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
) -> str:
    """Call the Claude API with prompt caching on the system prompt.

    System prompt is sent as a cache-enabled block so repeated calls within
    ~5 minutes hit the cache at ~10% of normal input cost.

    Args:
        model: Model identifier (use MODEL_EXTRACTOR or MODEL_VERIFIER).
        system_prompt: System prompt text. Will be cached.
        user_message: User-role message content.
        max_tokens: Max output tokens. Default 2048 (extractor/verifier return short JSON).

    Returns:
        The text of the first content block in the response (plain string).

    Raises:
        anthropic.APIError: Propagated from SDK on network / auth / rate errors.
    """
    response = _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def load_prompt(prompt_path: str) -> str:
    """Read a prompt file from the repo's ``prompts/`` tree and return the body.

    Prompt files start with a markdown metadata header followed by a
    ``---`` separator, then a ``## System prompt`` section containing a
    fenced code block with the actual prompt. This function extracts that
    code block.

    Args:
        prompt_path: Path relative to repo root, e.g.
            ``prompts/audit-use-cases/hallucination-claim-extractor.md``.

    Returns:
        The prompt body string.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
        ValueError: If no ``## System prompt`` section or fenced code block found.
    """
    full_path = REPO_ROOT / prompt_path
    if not full_path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {full_path}")

    text = full_path.read_text(encoding="utf-8")

    marker = "## System prompt"
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"Prompt file missing '## System prompt' section: {prompt_path}")

    after_marker = text[idx + len(marker):]

    start = after_marker.find("```")
    if start == -1:
        raise ValueError(f"No fenced code block after '## System prompt' in: {prompt_path}")
    body_start = after_marker.find("\n", start) + 1
    end = after_marker.find("```", body_start)
    if end == -1:
        raise ValueError(f"Unclosed fenced code block in: {prompt_path}")

    return after_marker[body_start:end].strip()
