"""
Model access for every agent, behind one function: complete().

Two backends, chosen with the VENDORGUARD_BACKEND environment variable
(or `main.py --backend`):

- "api" (default): the Anthropic API via the `anthropic` SDK, authenticated
  with ANTHROPIC_API_KEY.
- "claude-code": the Claude Agent SDK, which runs Claude Code under the user's
  own account: their Claude login, or their API key if one is set. Vendor Guard
  never handles credentials; Claude Code does. Install with
  `pip install --only-binary :all: -r requirements-claude-code.txt`.

The claude-code backend is locked down for untrusted vendor documents: no
built-in tools, no MCP servers, none of the user's Claude Code settings, hooks
or CLAUDE.md files, and a single turn.
"""
import asyncio
import os

import anthropic

BACKENDS = ("api", "claude-code")
DEFAULT_BACKEND = "api"
ENV_VAR = "VENDORGUARD_BACKEND"

# Used when a caller has no system prompt: an empty one would make Claude Code
# fall back to its own coding-assistant prompt.
NEUTRAL_SYSTEM_PROMPT = "Follow the user's instructions exactly."


class ModelCallError(RuntimeError):
    """A model call failed or returned no usable answer."""


def get_backend() -> str:
    backend = os.environ.get(ENV_VAR, DEFAULT_BACKEND).strip().lower()
    if backend not in BACKENDS:
        raise ValueError(f"{ENV_VAR}={backend!r} is not one of {', '.join(BACKENDS)}")
    return backend


def complete(*, model: str, system: str | None, user: str, max_tokens: int) -> str:
    """Send one system + user prompt to Claude and return the response text."""
    if get_backend() == "claude-code":
        return _complete_claude_code(model=model, system=system, user=user)
    return _complete_api(model=model, system=system, user=user, max_tokens=max_tokens)


def _complete_api(*, model: str, system: str | None, user: str, max_tokens: int) -> str:
    client = anthropic.Anthropic()
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        kwargs["system"] = system
    message = client.messages.create(**kwargs)
    return message.content[0].text


def _complete_claude_code(*, model: str, system: str | None, user: str) -> str:
    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            query,
        )
    except ImportError as exc:
        raise ModelCallError(
            "The claude-code backend needs the Claude Agent SDK. Install it with: "
            "pip install --only-binary :all: -r requirements-claude-code.txt"
        ) from exc

    options = ClaudeAgentOptions(
        system_prompt=system or NEUTRAL_SYSTEM_PROMPT,
        model=model,
        tools=[],                 # no Bash/Read/Edit/WebFetch: documents can't trigger actions
        setting_sources=[],       # ignore the user's settings, hooks and CLAUDE.md
        strict_mcp_config=True,   # no MCP servers beyond the (empty) set passed here
        max_turns=1,
    )

    async def run() -> str:
        texts: list[str] = []
        result = None
        async for message in query(prompt=user, options=options):
            if isinstance(message, AssistantMessage):
                if message.error:
                    raise ModelCallError(_explain_error(message.error))
                texts.extend(block.text for block in message.content if isinstance(block, TextBlock))
            elif isinstance(message, ResultMessage):
                result = message
        if result is None:
            raise ModelCallError("Claude Code ended without a result.")
        if result.is_error:
            detail = "; ".join(result.errors or []) or result.subtype
            status = f" (HTTP {result.api_error_status})" if result.api_error_status else ""
            raise ModelCallError(f"Claude Code reported an error{status}: {detail}")
        text = result.result if result.result is not None else "".join(texts)
        if not text.strip():
            raise ModelCallError("Claude Code returned an empty response.")
        return text

    return asyncio.run(run())


def _explain_error(error: str) -> str:
    if error == "authentication_failed":
        return ("Claude Code is not logged in. Run `claude` once and sign in with your own "
                "account (or set ANTHROPIC_API_KEY), then retry.")
    if error == "billing_error":
        return "Claude Code reported a billing problem on your account."
    if error == "rate_limit":
        return "Claude Code hit your account's rate limit. Wait and retry."
    return f"Claude Code returned an error: {error}"
