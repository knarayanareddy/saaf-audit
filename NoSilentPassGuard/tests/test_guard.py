import pytest

from no_silent_pass import Guard, Verdict


def test_nothing_assessed_is_not_a_pass():
    assert Guard("x").verdict() is Verdict.NOT_ASSESSED


def test_pass_needs_a_check_and_full_coverage():
    g = Guard("x")
    g.mark_assessed("a")
    assert g.verdict() is Verdict.NOT_ASSESSED  # coverage ok, but no check ran
    g.check("c", True, "a")
    assert g.verdict() is Verdict.PASS


def test_skipped_item_blocks_pass():
    g = Guard("x")
    g.mark_assessed("a")
    g.check("c", True, "a")
    g.skip("b", "unparsable")
    assert g.verdict() is Verdict.NOT_ASSESSED
    assert g.report()["items_skipped"][0]["item"] == "b"


def test_coverage_threshold_can_be_relaxed_explicitly():
    g = Guard("x", min_coverage=0.5)
    g.mark_assessed("a")
    g.check("c", True, "a")
    g.skip("b", "unparsable")
    assert g.verdict() is Verdict.PASS


def test_violation_dominates_not_assessed():
    g = Guard("x")
    g.not_assessed("something unreadable")
    g.check("c", False, detail="bad")
    assert g.verdict() is Verdict.FAIL
    assert g.report()["not_assessed_reasons"]  # still reported


def test_non_bool_check_outcome_is_not_a_pass():
    g = Guard("x")
    g.mark_assessed("a")
    g.check("c", None, "a")  # a check that "returned nothing" must not count
    assert g.verdict() is Verdict.NOT_ASSESSED


def test_within_rejects_nan_inf_and_negative_tolerance():
    g = Guard("x")
    assert g.within("t", "nan", 1, 0, "r1") is None
    assert g.within("t", 1, "inf", 0, "r2") is None
    assert g.within("t", 1, 1, -1, "r3") is None
    assert g.verdict() is Verdict.NOT_ASSESSED
    assert g.coverage == 0.0


def test_within_detects_real_difference():
    g = Guard("x")
    g.within("t", "10", "13", "0", "r1")
    g.mark_assessed("r1")
    assert g.verdict() is Verdict.FAIL


def test_require_unique_flags_disagreeing_alias_columns():
    g = Guard("x")
    assert g.require_unique({"qty": "10", "quantity": "10.0"}, ("qty", "quantity"), "q") == "10"
    assert g.require_unique({"qty": "10", "quantity": "13"}, ("qty", "quantity"), "q", "r") is None
    assert g.require_unique({}, ("qty",), "q", "r2") is None
    assert len(g.report()["items_skipped"]) == 2


def test_claim_requires_checks_that_actually_ran():
    g = Guard("x")
    assert g.claim("verified", ["evidence_quote"]) is False
    assert g.verdict() is Verdict.NOT_ASSESSED
    g.check("evidence_quote", True, "a")
    assert g.claim("verified", ["evidence_quote"]) is True
    assert "verified" in g.report()["claims_granted"]


def test_claim_denied_when_check_failed():
    g = Guard("x")
    g.check("evidence_quote", False, "a")
    assert g.claim("verified", ["evidence_quote"]) is False


def test_exception_is_recorded_and_not_swallowed():
    g = Guard("x")
    g.mark_assessed("a")
    g.check("c", True, "a")
    with pytest.raises(RuntimeError):
        with g:
            raise RuntimeError("boom")
    assert g.verdict() is Verdict.NOT_ASSESSED


def test_report_is_written(tmp_path):
    g = Guard("x")
    g.mark_assessed("a")
    g.check("c", True, "a")
    out = tmp_path / "r.json"
    assert g.write(str(out)) is Verdict.PASS
    assert '"verdict": "PASS"' in out.read_text()


def test_a_none_column_is_empty_not_the_text_none():
    g = Guard("x")
    assert g.require_unique({"qty": None, "quantity": "10"}, ("qty", "quantity"), "q", "r1") == "10"
    assert not any("no column" in r or "ambiguous" in r for r in g.report()["not_assessed_reasons"])  # r1 is fine
    assert g.require_unique({"qty": None, "quantity": ""}, ("qty", "quantity"), "q", "r2") is None
    reasons = g.report()["not_assessed_reasons"]
    assert any("no column for 'q'" in r for r in reasons)
    assert not any("ambiguous" in r for r in reasons)  # it used to be reported as a disagreement with "None"


def test_require_present_treats_none_and_blank_alike():
    g = Guard("x")
    assert g.require_present({"sku": None}, "sku", "r1") is None
    assert g.require_present({"sku": "  "}, "sku", "r2") is None
    assert g.require_present({"sku": "A1"}, "sku", "r3") == "A1"
    assert len(g.report()["items_skipped"]) == 2
