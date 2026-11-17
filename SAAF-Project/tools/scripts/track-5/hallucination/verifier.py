"""
Claim Verifier (S3)
===================

One Sonnet call per finding: verifies ALL verifiable claims in a single
batched request against the retrieved RAG context.

Prompt source: prompts/audit-use-cases/hallucination-claim-verifier.md
"""

from __future__ import annotations

import json
from typing import TypedDict

from .claude_client import MODEL_VERIFIER, call_with_cached_system, load_prompt
from .extractor import Claim, _parse_json_array


PROMPT_PATH = "prompts/audit-use-cases/hallucination-claim-verifier.md"


class ClaimVerdict(TypedDict):
    claim: str
    verdict: str           # "SUPPORTED" | "UNVERIFIED" | "LIKELY_HALLUCINATED"
    confidence: str        # "High" | "Medium" | "Low"
    reason: str
    corrected_reference: str


def verify_claims(claims: list[Claim], rag_context: str) -> list[ClaimVerdict]:
    """Verify a batch of claims in a single Sonnet call.

    Non-verifiable claims (verifiable=False) are returned as UNVERIFIED without
    an API call. Only verifiable claims are sent to the model.

    Args:
        claims: Output of extractor.extract_claims().
        rag_context: Regulatory context from rag.retrieve_context().
            May be empty — caller must expect this (all claims become UNVERIFIED).

    Returns:
        List of ClaimVerdict, one per input claim, order preserved.

    Raises:
        ValueError: If Claude's response cannot be parsed or counts mismatch.
        anthropic.APIError: Propagated from SDK.
    """
    if not claims:
        return []

    verifiable_claims = [c for c in claims if c["verifiable"]]
    if not verifiable_claims:
        return [_unverified_skip(c, "Non-verifiable claim (skipped by extractor).") for c in claims]

    if not rag_context.strip():
        return [
            _unverified_skip(c, "No regulatory context retrieved for this claim.")
            if c["verifiable"]
            else _unverified_skip(c, "Non-verifiable claim (skipped by extractor).")
            for c in claims
        ]

    system_prompt = load_prompt(PROMPT_PATH)
    user_message = _build_user_message(verifiable_claims, rag_context)

    raw = call_with_cached_system(
        model=MODEL_VERIFIER,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=4096,
    )

    parsed = _parse_json_array(raw)
    if len(parsed) != len(verifiable_claims):
        raise ValueError(
            f"Verifier returned {len(parsed)} verdicts for {len(verifiable_claims)} claims."
        )

    verdicts_by_claim: dict[str, ClaimVerdict] = {}
    for claim_in, v in zip(verifiable_claims, parsed):
        verdicts_by_claim[claim_in["claim"]] = _normalise_verdict(v, claim_in["claim"])

    out: list[ClaimVerdict] = []
    for c in claims:
        if c["verifiable"] and c["claim"] in verdicts_by_claim:
            out.append(verdicts_by_claim[c["claim"]])
        else:
            out.append(_unverified_skip(c, "Non-verifiable claim (skipped by extractor)."))
    return out


def _build_user_message(claims: list[Claim], rag_context: str) -> str:
    claims_json = json.dumps(
        [{"claim": c["claim"], "claim_type": c["claim_type"]} for c in claims],
        ensure_ascii=False,
        indent=2,
    )
    return (
        "Verify the following claims extracted from an AI-generated audit finding.\n\n"
        "Claims to verify:\n"
        f"{claims_json}\n\n"
        "Regulatory context retrieved from the SAAF knowledge base:\n"
        f"{rag_context}\n\n"
        "Return a JSON array of verdicts, one per claim, in the same order."
    )


def _normalise_verdict(raw: dict, original_claim: str) -> ClaimVerdict:
    verdict = str(raw.get("verdict", "UNVERIFIED")).strip().upper()
    if verdict not in {"SUPPORTED", "UNVERIFIED", "LIKELY_HALLUCINATED"}:
        verdict = "UNVERIFIED"

    confidence = str(raw.get("confidence", "Low")).strip().title()
    if confidence not in {"High", "Medium", "Low"}:
        confidence = "Low"

    return {
        "claim": str(raw.get("claim", original_claim)).strip() or original_claim,
        "verdict": verdict,
        "confidence": confidence,
        "reason": str(raw.get("reason", "")).strip(),
        "corrected_reference": str(raw.get("corrected_reference", "")).strip(),
    }


def _unverified_skip(claim: Claim, reason: str) -> ClaimVerdict:
    return {
        "claim": claim["claim"],
        "verdict": "UNVERIFIED",
        "confidence": "Low",
        "reason": reason,
        "corrected_reference": "",
    }
