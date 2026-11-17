"""Aggregator rules (pure Python, no API key).

The three rules from the README's risk table, plus the two guarantees the
AUDIT-CRITERIA.md relies on (CO-3): never blocked, warning only.
"""
from hallucination.aggregator import aggregate


def _v(verdict, confidence="High", claim="x"):
    return {"claim": claim, "verdict": verdict, "confidence": confidence,
            "reason": "", "corrected_reference": ""}


def test_high_when_any_claim_is_hallucinated_with_high_confidence():
    out = aggregate([_v("SUPPORTED"), _v("LIKELY_HALLUCINATED", "High", "ISO 27001 clause 8.9.4")])
    assert out["overall_risk"] == "HIGH"
    assert out["warning"] is True
    assert out["blocked"] is False
    assert out["flagged_claims"][0]["claim"] == "ISO 27001 clause 8.9.4"
    assert "8.9.4" in out["summary"]


def test_hallucinated_with_low_confidence_is_not_high():
    out = aggregate([_v("LIKELY_HALLUCINATED", "Low")])
    assert out["overall_risk"] == "LOW"
    assert out["flagged_claims"] == []


def test_medium_when_two_or_more_unverified():
    out = aggregate([_v("UNVERIFIED", "Low", "a"), _v("UNVERIFIED", "Low", "b"), _v("SUPPORTED")])
    assert out["overall_risk"] == "MEDIUM"
    assert out["warning"] is True
    assert out["blocked"] is False
    assert len(out["unverified_claims"]) == 2


def test_one_unverified_is_still_low():
    out = aggregate([_v("UNVERIFIED", "Low"), _v("SUPPORTED")])
    assert out["overall_risk"] == "LOW"
    assert out["warning"] is False


def test_all_supported_is_low():
    out = aggregate([_v("SUPPORTED"), _v("SUPPORTED")])
    assert out["overall_risk"] == "LOW"
    assert out["summary"].startswith("LOW risk: all 2 claims")


def test_no_claims_is_low_with_explicit_summary():
    out = aggregate([])
    assert out["overall_risk"] == "LOW"
    assert "no verifiable factual claims" in out["summary"]


def test_never_blocks_whatever_the_input():
    for verdicts in ([], [_v("LIKELY_HALLUCINATED")], [_v("UNVERIFIED", "Low")] * 5):
        assert aggregate(verdicts)["blocked"] is False
