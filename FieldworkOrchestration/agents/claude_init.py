"""Claude client initialization for the Fieldwork Orchestration agents.

A thin, reusable wrapper over the Anthropic SDK where the **model is a dynamic
input** -- chosen per client instance, per call, or via the ``CLAUDE_MODEL``
environment variable -- rather than hardcoded at the call site.

Auth resolves from the environment (``ANTHROPIC_API_KEY`` or an ``ant auth
login`` profile); no key is ever hardcoded here.

Example::

    from agents.claude_init import ClaudeClient

    claude = ClaudeClient()                             # defaults to claude-opus-4-8
    claude = ClaudeClient(model="claude-sonnet-4-6")    # or pick at construction

    msg = claude.message("Summarize the field report", model="claude-haiku-4-5")
    print(next(b.text for b in msg.content if b.type == "text"))
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

import anthropic

try:
    from dotenv import load_dotenv

    load_dotenv()  # pull ANTHROPIC_API_KEY / CLAUDE_MODEL from a .env if present
except ImportError:  # python-dotenv is optional
    pass

try:  # local import works both as a script and as ``agents.claude_init``
    from agents.audit_trail import AuditTrail
    from agents.prompts.basic import BASIC_PROMPT
except ModuleNotFoundError:
    from audit_trail import AuditTrail
    from prompts.basic import BASIC_PROMPT

# Default to the most capable Claude model. Override per-call, per-instance, or
# with the CLAUDE_MODEL environment variable.
DEFAULT_MODEL = "claude-opus-4-8"

# Environment variable consulted when no explicit model is passed.
MODEL_ENV_VAR = "CLAUDE_MODEL"


def resolve_model(model: str | None = None) -> str:
    """Resolve the model id: explicit argument > ``CLAUDE_MODEL`` env var > default."""
    return model or os.environ.get(MODEL_ENV_VAR) or DEFAULT_MODEL


def get_client(api_key: str | None = None, **kwargs: Any) -> anthropic.Anthropic:
    """Create an Anthropic client.

    Credentials resolve from the environment by default; pass ``api_key`` only
    when you must inject a specific key. Extra keyword arguments (``base_url``,
    ``timeout``, ``max_retries``, ...) are forwarded to the SDK constructor.
    """
    if api_key is not None:
        kwargs["api_key"] = api_key
    return anthropic.Anthropic(**kwargs)


def text_from_message(message: anthropic.types.Message) -> str:
    """Concatenate the text blocks of a ``Message`` (skips thinking blocks)."""
    return "".join(block.text for block in message.content if block.type == "text")


def reasoning_from_message(message: anthropic.types.Message) -> str | None:
    """Concatenate the thinking blocks of a ``Message``, or ``None`` if there are none.

    The counterpart to ``text_from_message``, which explicitly skips these —
    call this too wherever the audit trail should also capture *why* the
    model answered the way it did (the extended-thinking trace), not just
    what it answered. Returns ``None`` when ``thinking`` wasn't enabled for
    the call, when the model produced no thinking blocks even though it
    was, or when adaptive thinking judged the call trivial enough to emit
    only an empty thinking block (observed for e.g. simple arithmetic) —
    never an empty string, so a caller can tell "no reasoning was captured"
    apart from "reasoning was captured and happened to be empty". A
    ``redacted_thinking`` block (returned instead of plaintext when
    Anthropic's safety systems flag the content) becomes a placeholder
    rather than being silently dropped — its presence is itself worth an
    auditor knowing about, and always counts even if every plain thinking
    block alongside it was empty.
    """
    parts = []
    for block in message.content:
        if block.type == "thinking" and block.thinking.strip():
            parts.append(block.thinking)
        elif block.type == "redacted_thinking":
            parts.append("[redacted thinking block — content withheld by Anthropic's safety systems]")
    return "\n\n".join(parts) if parts else None


def extract_json_block(text: str) -> Any:
    """Parse the first JSON object/array found in ``text``.

    Looks inside a fenced ```json code block first, then falls back to the
    first ``{...}`` or ``[...]`` span. Raises ``ValueError`` if neither is
    found.
    """
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"No JSON found in response:\n{text}")


def _prompt_for_log(prompt: str | list[dict[str, Any]]) -> Any:
    """Summarize a multimodal prompt for the audit trail.

    A plain string passes through unchanged. A content-block list (used for
    vision input) has every image block's base64 data replaced with a short
    placeholder — the audit trail is meant to stay a readable, grep-able
    record of *what was asked*, not a store of raw image bytes; logging
    megabytes of base64 per page would defeat that. The real API call always
    gets the untouched ``prompt`` — only what gets written to the trail is
    summarized.
    """
    if isinstance(prompt, str):
        return prompt
    summarized = []
    for block in prompt:
        if isinstance(block, dict) and block.get("type") == "image":
            source = block.get("source", {})
            data_len = len(source.get("data", ""))
            summarized.append(
                f"[image: {source.get('media_type', 'unknown')}, "
                f"{data_len} base64 chars — not logged]"
            )
        else:
            summarized.append(block)
    return summarized


def _retry_on_connection_error(fn: Any, *, max_retries: int = 5, backoff: float = 2.0) -> Any:
    """Call ``fn()``, retrying a few times on a transient network error.

    Batch polling (see ``ClaudeClient.message_batch``) makes dozens of HTTP
    calls over up to ``timeout`` (default 30 minutes) — losing one
    connection along the way is a normal, expected event on a real network,
    not a reason to discard an otherwise still-running (or by now already
    finished) batch. Only retries ``anthropic.APIConnectionError`` (which
    ``APITimeoutError`` is a subtype of) — anything else (a real API error,
    a malformed request) fails immediately, unretried.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except anthropic.APIConnectionError:
            if attempt == max_retries:
                raise
            time.sleep(backoff)


def _normalize_thinking(
    thinking: str | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Accept an ``"adaptive"`` / ``"disabled"`` shorthand or a full config dict."""
    if thinking is None:
        return None
    if isinstance(thinking, str):
        return {"type": thinking}
    return thinking


class _AuditedStreamManager:
    """Wraps the SDK's streaming context manager to log the completed call.

    Delegates ``__enter__``/``__exit__`` to the real manager so callers get
    the exact same ``MessageStream`` they would from the SDK directly; the
    only added behaviour is recording the finished call to ``audit_trail`` on
    a clean exit (an exception means the call never completed, so nothing is
    recorded — same as ``message()``, which never logs a failed call either).
    """

    def __init__(
        self,
        manager: Any,
        *,
        audit_trail: AuditTrail,
        agent: str | None,
        item_ref: str | None,
        system: str | None,
        prompt: str,
        model: str,
        max_tokens: int,
        thinking: Any,
        started_at: datetime,
    ) -> None:
        self._manager = manager
        self._audit_trail = audit_trail
        self._agent = agent
        self._item_ref = item_ref
        self._system = system
        self._prompt = prompt
        self._model = model
        self._max_tokens = max_tokens
        self._thinking = thinking
        self._started_at = started_at
        self._stream: Any = None

    def __enter__(self) -> Any:
        self._stream = self._manager.__enter__()
        return self._stream

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Any:
        final_message = None
        if exc_type is None:
            # get_final_message() consumes any remaining stream events itself,
            # so this works whether or not the caller iterated text_stream —
            # call it before the manager closes the underlying response.
            final_message = self._stream.get_final_message()

        result = self._manager.__exit__(exc_type, exc, tb)

        if exc_type is None and final_message is not None:
            finished_at = datetime.now(timezone.utc)
            usage = getattr(final_message, "usage", None)
            self._audit_trail.record(
                agent=self._agent,
                item_ref=self._item_ref,
                system_prompt=self._system,
                user_prompt=_prompt_for_log(self._prompt),
                model=self._model,
                max_tokens=self._max_tokens,
                thinking=self._thinking,
                response_text=text_from_message(final_message),
                reasoning_text=reasoning_from_message(final_message),
                started_at=self._started_at,
                finished_at=finished_at,
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                stop_reason=getattr(final_message, "stop_reason", None),
            )

        return result

    def __getattr__(self, name: str) -> Any:
        # e.g. `async with` support, or any SDK manager attribute callers reach for
        return getattr(self._manager, name)


class ClaudeClient:
    """Reusable Claude client with a dynamically configurable model.

    The model is set once at construction and can be overridden on any call, so
    the same client can fan work out across models (e.g. Opus for planning,
    Haiku for cheap classification).
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        client: anthropic.Anthropic | None = None,
        audit_trail: AuditTrail | None = None,
    ) -> None:
        self.client = client or get_client(api_key=api_key)
        self.model = resolve_model(model)
        self.audit_trail = audit_trail

    def message(
        self,
        prompt: str | list[dict[str, Any]],
        *,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int = 16000,
        thinking: str | dict[str, Any] | None = None,
        agent: str | None = None,
        item_ref: str | None = None,
        **kwargs: Any,
    ) -> anthropic.types.Message:
        """Send a single-turn prompt and return the full ``Message``.

        ``prompt`` is usually plain text, but accepts a content-block list
        for multimodal input — e.g. ``[{"type": "image", "source": {...}},
        {"type": "text", "text": "..."}]`` for vision. Image data is sent to
        the API in full but never written to the audit trail verbatim — see
        ``_prompt_for_log``.

        ``model`` overrides the instance default for this call only. Pass
        ``thinking="adaptive"`` for anything that benefits from reasoning.
        Pass ``agent`` (the calling agent's slug) so this call is attributed
        correctly if ``self.audit_trail`` is set — every call is recorded
        there regardless, but unattributed if ``agent`` is omitted. Pass
        ``item_ref`` too when this call is about one specific item (a PBC
        id, say) — see ``AuditTrail.entries_for_item``.
        """
        params: dict[str, Any] = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        if system is not None:
            params["system"] = system
        normalized = _normalize_thinking(thinking)
        if normalized is not None:
            params["thinking"] = normalized

        started_at = datetime.now(timezone.utc)
        response = self.client.messages.create(**params)
        finished_at = datetime.now(timezone.utc)

        if self.audit_trail is not None:
            usage = getattr(response, "usage", None)
            self.audit_trail.record(
                agent=agent,
                item_ref=item_ref,
                system_prompt=system,
                user_prompt=_prompt_for_log(prompt),
                model=params["model"],
                max_tokens=max_tokens,
                thinking=normalized,
                response_text=text_from_message(response),
                reasoning_text=reasoning_from_message(response),
                started_at=started_at,
                finished_at=finished_at,
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                stop_reason=getattr(response, "stop_reason", None),
            )

        return response

    def stream(
        self,
        prompt: str | list[dict[str, Any]],
        *,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int = 64000,
        thinking: str | dict[str, Any] | None = None,
        agent: str | None = None,
        item_ref: str | None = None,
        **kwargs: Any,
    ):
        """Open a streaming response -- use for long or high-``max_tokens`` calls.

        If ``self.audit_trail`` is set, the completed call (full response
        text, timing, token usage) is recorded the same way as ``message()``
        once the ``with`` block exits cleanly — pass ``agent`` to attribute
        it correctly, same as ``message()``.

        Returns a context manager with the same interface as the SDK's::

            with claude.stream("Write a long brief") as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                final = stream.get_final_message()
        """
        params: dict[str, Any] = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        if system is not None:
            params["system"] = system
        normalized = _normalize_thinking(thinking)
        if normalized is not None:
            params["thinking"] = normalized

        manager = self.client.messages.stream(**params)

        if self.audit_trail is None:
            return manager

        return _AuditedStreamManager(
            manager,
            audit_trail=self.audit_trail,
            agent=agent,
            item_ref=item_ref,
            system=system,
            prompt=prompt,
            model=params["model"],
            max_tokens=max_tokens,
            thinking=normalized,
            started_at=datetime.now(timezone.utc),
        )

    def message_batch(
        self,
        requests: list[dict[str, Any]],
        *,
        poll_interval: float = 5.0,
        timeout: float = 1800.0,
    ) -> list[anthropic.types.Message]:
        """Submit independent prompts as one Batches API call; ~half the per-token cost.

        Use this only when the calls don't depend on each other's results —
        one request per page/control/item, not a chain where request 2 needs
        request 1's answer (see ``.message()`` for that). Each entry in
        ``requests`` takes the same keys as a ``.message()`` call: required
        ``prompt``; optional ``model``, ``system``, ``max_tokens``,
        ``thinking``, ``agent``, ``item_ref``.

        Blocks, polling every ``poll_interval`` seconds, until every request
        in the batch has finished or ``timeout`` seconds have passed (batches
        can legitimately take anywhere from seconds to hours depending on
        load — this is not for latency-sensitive calls). Raises
        ``RuntimeError`` if any individual request in the batch did not
        succeed (no partial-success handling — a caller relying on every
        item, e.g. every control's evidence, should not silently proceed
        with some missing).

        Returns the resulting ``Message`` objects in the same order as
        ``requests``. If ``self.audit_trail`` is set, every request is
        still recorded there individually (tagged by its own ``agent``) —
        but timing is per-*batch*, not per-request: every entry from one
        ``message_batch()`` call shares the same recorded
        ``started_at``/``finished_at`` (the batch's submit/completion time),
        since the API does not report individual request processing time.
        """
        batch_params: list[dict[str, Any]] = []
        for req in requests:
            params: dict[str, Any] = {
                "model": req.get("model") or self.model,
                "max_tokens": req.get("max_tokens", 16000),
                "messages": [{"role": "user", "content": req["prompt"]}],
            }
            if req.get("system") is not None:
                params["system"] = req["system"]
            normalized = _normalize_thinking(req.get("thinking"))
            if normalized is not None:
                params["thinking"] = normalized
            batch_params.append(params)

        started_at = datetime.now(timezone.utc)
        batch = _retry_on_connection_error(
            lambda: self.client.messages.batches.create(
                requests=[
                    {"custom_id": f"req-{i}", "params": params}
                    for i, params in enumerate(batch_params)
                ]
            )
        )

        deadline = time.monotonic() + timeout
        while batch.processing_status != "ended":
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"batch {batch.id} did not finish within {timeout}s "
                    f"(status: {batch.processing_status})"
                )
            time.sleep(poll_interval)
            # A poll can span up to `timeout` (default 30 min) worth of
            # requests, one every `poll_interval` — losing one connection
            # out of dozens of polls is normal on a real network and must
            # not throw away an otherwise still-running (or by now already
            # finished) batch.
            batch = _retry_on_connection_error(lambda: self.client.messages.batches.retrieve(batch.id))
        finished_at = datetime.now(timezone.utc)

        results_by_id = {
            entry.custom_id: entry
            for entry in _retry_on_connection_error(
                lambda: list(self.client.messages.batches.results(batch.id))
            )
        }

        messages: list[anthropic.types.Message] = []
        for i, req in enumerate(requests):
            custom_id = f"req-{i}"
            entry = results_by_id.get(custom_id)
            if entry is None or entry.result.type != "succeeded":
                detail = getattr(getattr(entry, "result", None), "error", None) if entry else "no result returned"
                raise RuntimeError(
                    f"batch request {custom_id} (agent={req.get('agent')!r}) did not succeed: {detail}"
                )
            message = entry.result.message
            messages.append(message)

            if self.audit_trail is not None:
                usage = getattr(message, "usage", None)
                params = batch_params[i]
                self.audit_trail.record(
                    agent=req.get("agent"),
                    item_ref=req.get("item_ref"),
                    system_prompt=params.get("system"),
                    user_prompt=_prompt_for_log(req["prompt"]),
                    model=params["model"],
                    max_tokens=params["max_tokens"],
                    thinking=params.get("thinking"),
                    response_text=text_from_message(message),
                    reasoning_text=reasoning_from_message(message),
                    started_at=started_at,
                    finished_at=finished_at,
                    input_tokens=getattr(usage, "input_tokens", None),
                    output_tokens=getattr(usage, "output_tokens", None),
                    stop_reason=getattr(message, "stop_reason", None),
                )

        return messages

    def message_many(
        self,
        requests: list[dict[str, Any]],
        *,
        batch_threshold: int = 150,
        poll_interval: float = 5.0,
        timeout: float = 1800.0,
    ) -> list[anthropic.types.Message]:
        """Run independent requests the fast way or the cheap way, based on how many there are.

        The Batches API is not latency-optimized: a batch goes through the
        same asynchronous processing queue regardless of size, so even a
        handful of requests can take minutes — a bad trade when something
        (a person, a UI) is waiting on the result, and a good one for a
        genuinely bulk, non-interactive operation where the ~50% cost saving
        is worth a wait nobody is watching.

        ``batch_threshold`` defaults high (150) rather than low: measured
        against a real ~104-item batch, queue wait wasn't proportional to
        batch size — it sat "in_progress" for longer than this method's own
        30-minute default timeout. Queue latency is apparently unpredictable
        regardless of how many requests are in a batch, so for a prototype
        where a person is actively waiting, defaulting to the fast,
        predictable path at any size this project currently produces (single
        engagements — tens to ~100 items) is the safer choice. Pass a lower
        ``batch_threshold`` explicitly for a call you know is a genuinely
        large, non-interactive, background-style job where that risk is
        acceptable for the cost saving.

        Below ``batch_threshold`` requests, calls ``.message()`` for each
        one in turn — same interface as ``.message_batch()`` (list of dicts
        with ``prompt`` and optional ``model``/``system``/``max_tokens``/
        ``thinking``/``agent``/``item_ref``), same return order, each
        already recorded to the audit trail individually with its own real
        timing. At or above the threshold, delegates to ``.message_batch()``.
        """
        if len(requests) < batch_threshold:
            return [
                self.message(
                    req["prompt"],
                    model=req.get("model"),
                    system=req.get("system"),
                    max_tokens=req.get("max_tokens", 16000),
                    thinking=req.get("thinking"),
                    agent=req.get("agent"),
                    item_ref=req.get("item_ref"),
                )
                for req in requests
            ]
        return self.message_batch(requests, poll_interval=poll_interval, timeout=timeout)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Send a prompt to Claude.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default=BASIC_PROMPT,
        help="Prompt to send (defaults to the basic connection-check prompt).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Model id (default: ${MODEL_ENV_VAR} or {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    claude = ClaudeClient(model=args.model)
    response = claude.message(args.prompt)
    for block in response.content:
        if block.type == "text":
            print(block.text)
