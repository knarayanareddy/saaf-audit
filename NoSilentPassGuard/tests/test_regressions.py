"""Each test replays a pattern found on the SAAF red team day (see README)."""
from no_silent_pass import Verdict
from no_silent_pass.adapters import manifests, standalone, three_way_match as twm

PO = {"A1": {"qty": 10, "price": "5.00"}}
GRN = {"A1": 10}


# --- invoice matching --------------------------------------------------------------
def test_decoy_columns_naive_logic_matches_but_guard_refuses():
    rows = [{"sku": "A1", "quantity": "10", "quantity_billed": "13",
             "unit_price": "5.00", "price": "6.50"}]
    assert twm.naive_match(PO, GRN, rows) == "MATCH"  # the audited behaviour
    g = twm.assess_invoice(PO, GRN, rows)
    assert g.verdict() is Verdict.NOT_ASSESSED
    assert any("disagree" in r for r in g.report()["not_assessed_reasons"])


def test_nan_quantity_cannot_pass():
    rows = [{"sku": "A1", "quantity": "nan", "unit_price": "5.00"}]
    assert twm.assess_invoice(PO, GRN, rows).verdict() is Verdict.NOT_ASSESSED


def test_thousands_separator_is_not_silently_shrunk():
    po = {"A1": {"qty": 1000, "price": "5.00"}}
    rows = [{"sku": "A1", "quantity": "1,000", "unit_price": "5.00"}]
    assert twm.assess_invoice(po, {"A1": 1000}, rows).verdict() is Verdict.NOT_ASSESSED
    assert twm.assess_invoice(po, {"A1": 1000}, rows, decimal=".").verdict() is Verdict.PASS


def test_missing_goods_receipt_is_a_fail_not_a_warning():
    rows = [{"sku": "A1", "quantity": "10", "unit_price": "5.00"}]
    assert twm.assess_invoice(PO, {}, rows).verdict() is Verdict.FAIL


def test_clean_invoice_passes():
    rows = [{"sku": "A1", "quantity": "10", "unit_price": "5.00"}]
    assert twm.assess_invoice(PO, GRN, rows).verdict() is Verdict.PASS


def test_price_mismatch_fails():
    rows = [{"sku": "A1", "quantity": "10", "unit_price": "6.50"}]
    assert twm.assess_invoice(PO, GRN, rows).verdict() is Verdict.FAIL


def test_empty_invoice_is_not_a_match():
    assert twm.assess_invoice(PO, GRN, []).verdict() is Verdict.NOT_ASSESSED


# --- readiness scanner -------------------------------------------------------------
def test_no_signals_is_not_assessed_instead_of_yes():
    g = standalone.assess_repo([("agent.py", True)], [])
    assert standalone.label(g) == "not assessed"


def test_unparsable_file_is_not_counted_as_clean():
    sigs = [standalone.Signal("llm_client", "openai")]
    g = standalone.assess_repo([("a.py", True), ("broken.py", False)], sigs)
    assert standalone.label(g) == "not assessed"


def test_blocker_gives_no_and_clean_repo_gives_yes():
    client = standalone.Signal("llm_client", "openai")
    blocker = standalone.Signal("blocker", "hardcoded_endpoint")
    assert standalone.label(standalone.assess_repo([("a.py", True)], [client, blocker])) == "no"
    assert standalone.label(standalone.assess_repo([("a.py", True)], [client])) == "yes"


# --- manifest collector ------------------------------------------------------------
def test_failed_fetch_is_visible_and_not_replaced_by_seed_data():
    results = [{"repo": "o/a", "status": 200, "body": "name: a"},
               {"repo": "o/b", "status": 403, "body": None}]
    g = manifests.assess_fetches(results)
    assert g.verdict() is Verdict.NOT_ASSESSED
    assert g.report()["items_skipped"][0]["item"] == "o/b"


def test_all_fetches_ok_passes():
    results = [{"repo": "o/a", "status": 200, "body": "name: a"}]
    assert manifests.assess_fetches(results).verdict() is Verdict.PASS


def test_oversized_manifest_is_refused():
    big = "x" * 10
    g = manifests.assess_fetches([{"repo": "o/a", "status": 200, "body": big}], max_bytes=5)
    assert g.verdict() is Verdict.NOT_ASSESSED
