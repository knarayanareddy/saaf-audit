"""
Smoke test for the hallucination detection pipeline.

Exercises every module that can be tested without an API call:
- Module imports
- finding_io load + finding_text
- rag.retrieve_context (markdown fallback)
- aggregator rules (HIGH / MEDIUM / LOW)
- claude_client.load_prompt
- claude_client.get_api_key fail-fast

Run:
    cd tools/scripts/track-5
    python -m hallucination.smoke_test

Exits 0 on success, 1 on failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).parent
    sample = here / "dummy_data" / "sample_findings" / "F-0001.json"

    from . import aggregator, claude_client, finding_io, rag

    print("[1/6] Import all modules...")
    from . import annotator, cli, extractor, verifier  # noqa: F401
    print("      OK")

    print("[2/6] Load sample finding F-0001...")
    f = finding_io.load_finding(sample)
    assert f["id"] == "F-0001", f"Expected F-0001, got {f['id']}"
    text = finding_io.finding_text(f)
    assert len(text) > 100
    print(f"      OK — {len(text)} chars")

    print("[3/6] RAG markdown lookup (ISO 27001 clause 8)...")
    ctx = rag.retrieve_context("ISO 27001 clause 8.9.4 incident 24-hour", top_k=2)
    assert ctx, "RAG returned empty context"
    assert "clause 8" in ctx.lower(), "RAG did not match ISO clause 8 structure file"
    print(f"      OK — retrieved {len(ctx)} chars")

    print("[4/6] Aggregator HIGH / MEDIUM / LOW paths...")
    out_high = aggregator.aggregate([
        {"claim": "x", "verdict": "LIKELY_HALLUCINATED", "confidence": "High",
         "reason": "", "corrected_reference": ""}
    ])
    assert out_high["overall_risk"] == "HIGH"
    assert out_high["blocked"] is False
    assert out_high["warning"] is True

    out_med = aggregator.aggregate([
        {"claim": "a", "verdict": "UNVERIFIED", "confidence": "Low",
         "reason": "", "corrected_reference": ""},
        {"claim": "b", "verdict": "UNVERIFIED", "confidence": "Low",
         "reason": "", "corrected_reference": ""},
    ])
    assert out_med["overall_risk"] == "MEDIUM"

    out_low = aggregator.aggregate([
        {"claim": "c", "verdict": "SUPPORTED", "confidence": "High",
         "reason": "", "corrected_reference": ""}
    ])
    assert out_low["overall_risk"] == "LOW"
    print("      OK")

    print("[5/6] Prompt loader...")
    p1 = claude_client.load_prompt("prompts/audit-use-cases/hallucination-claim-extractor.md")
    p2 = claude_client.load_prompt("prompts/audit-use-cases/hallucination-claim-verifier.md")
    assert "factual claim" in p1.lower()
    assert "SUPPORTED" in p2
    print(f"      OK — extractor {len(p1)} chars, verifier {len(p2)} chars")

    print("[6/6] API-key fail-fast...")
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        try:
            claude_client.get_api_key()
            print("      FAIL — expected EnvironmentError")
            return 1
        except EnvironmentError:
            print("      OK")
    finally:
        if saved:
            os.environ["ANTHROPIC_API_KEY"] = saved

    print("\n*** ALL SMOKE TESTS PASSED ***")
    print("Next step: set ANTHROPIC_API_KEY and run:")
    print("  python -m hallucination dummy_data/sample_findings/F-0001.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
