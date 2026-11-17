"""
Claim Extractor (S2)
====================

One Haiku call per finding. Parses a finding's title + observation +
recommendation into a structured list of claims.

Prompt source: prompts/audit-use-cases/hallucination-claim-extractor.md
"""

from __future__ import annotations

import json
import re
from typing import TypedDict

from .claude_client import MODEL_EXTRACTOR, call_with_cached_system, load_prompt


PROMPT_PATH = "prompts/audit-use-cases/hallucination-claim-extractor.md"


class Claim(TypedDict):
    claim: str
    claim_type: str
    verifiable: bool


def extract_claims(finding_text: str) -> list[Claim]:
    """Extract all factual claims from finding text via one Haiku call.

    Args:
        finding_text: Concatenated title + observation + recommendation.

    Returns:
        List of Claim dicts. Empty list if no claims found.

    Raises:
        ValueError: If Claude's response is not a parseable JSON array.
        anthropic.APIError: Propagated from SDK.
    """
    system_prompt = load_prompt(PROMPT_PATH)
    user_message = (
        "Extract all factual claims from the following audit finding:\n\n"
        f"{finding_text}"
    )

    raw = call_with_cached_system(
        model=MODEL_EXTRACTOR,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=2048,
    )

    claims = _parse_json_array(raw)
    return [_normalise_claim(c) for c in claims]


def _parse_json_array(text: str) -> list[dict]:
    """Extract the first JSON array from ``text`` and parse it.

    Tolerates responses that wrap the array in prose or markdown fences.
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Expected a JSON array in response; got: {text[:200]!r}")

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Response not valid JSON array: {e}\nRaw: {text[:500]!r}") from e

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    return data


def _normalise_claim(raw: dict) -> Claim:
    """Coerce a raw dict to the Claim TypedDict shape with safe defaults."""
    return {
        "claim": str(raw.get("claim", "")).strip(),
        "claim_type": str(raw.get("claim_type", "other")).strip() or "other",
        "verifiable": bool(raw.get("verifiable", False)),
    }
