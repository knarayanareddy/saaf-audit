"""The gate must not trust a report's own ``verdict``: it checks it against the report's data and run."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from no_silent_pass import Guard, Verdict
from no_silent_pass.cli import main
from no_silent_pass.gate import assess_report

NOW = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)


def good_report(**over):
    r = {
        "schema_version": 1, "guard": "x", "run_id": "run-1", "generated_at": NOW.isoformat(),
        "verdict": "PASS", "exit_code": 0, "coverage": 1.0, "min_coverage": 1.0, "min_checks": 1,
        "items_total": 3, "items_skipped": [], "checks_run": 3, "checks_failed": [],
        "not_assessed_reasons": [], "claims_granted": [], "claims_denied": [],
    }
    r.update(over)
    return r


def verdict_of(report, **kw):
    return assess_report(report, now=NOW, **kw)[0]


def write(tmp_path, report, name="r.json"):
    p = tmp_path / name
    p.write_text(json.dumps(report))
    return str(p)


# --- the failures found on 10 November: a PASS with nothing behind it ------------------------------
def test_bare_pass_is_not_assessed(tmp_path):
    assert main(["gate", write(tmp_path, {"verdict": "PASS"})]) == 2


def test_pass_without_any_check_or_coverage_is_not_assessed(tmp_path):
    r = good_report(coverage=0.0, checks_run=0, items_total=0, not_assessed_reasons=["no input items were assessed"])
    assert main(["gate", write(tmp_path, r)]) == 2


def test_pass_that_lists_a_failed_check_is_a_fail(tmp_path):
    r = good_report(checks_failed=[{"name": "qty", "ok": False, "item": "row 1", "detail": "|3 - 5| <= 0"}])
    assert main(["gate", write(tmp_path, r)]) == 1


def test_consistent_pass_still_passes(tmp_path):
    assert main(["gate", write(tmp_path, good_report())]) == 0


def test_a_report_written_by_the_guard_itself_passes(tmp_path):
    g = Guard("x")
    g.mark_assessed("a")
    g.check("c", True, "a")
    p = tmp_path / "r.json"
    g.write(str(p))
    assert main(["gate", str(p)]) == 0


# --- recomputing ----------------------------------------------------------------------------------------
def test_not_assessed_claim_with_failed_checks_is_a_fail():
    r = good_report(verdict="NOT_ASSESSED", checks_failed=[{"name": "c", "ok": False}])
    assert verdict_of(r) is Verdict.FAIL  # a violation dominates, as in Guard.verdict()


def test_pass_with_reasons_left_over_is_not_assessed():
    v, reasons, problems = assess_report(good_report(not_assessed_reasons=["row 2: nan"]), now=NOW)
    assert v is Verdict.NOT_ASSESSED
    assert "row 2: nan" in reasons
    assert any("says PASS" in p for p in problems)


def test_coverage_below_the_reports_own_threshold_is_not_assessed():
    assert verdict_of(good_report(coverage=0.5)) is Verdict.NOT_ASSESSED
    assert verdict_of(good_report(coverage=0.5, min_coverage=0.5)) is Verdict.PASS


def test_the_gate_can_be_stricter_than_the_report_but_not_laxer():
    assert verdict_of(good_report(coverage=0.8, min_coverage=0.5)) is Verdict.PASS
    assert verdict_of(good_report(coverage=0.8, min_coverage=0.5), min_coverage=0.9) is Verdict.NOT_ASSESSED
    assert verdict_of(good_report(min_coverage=1.0, coverage=0.5), min_coverage=0.1) is Verdict.NOT_ASSESSED
    assert verdict_of(good_report(checks_run=2), min_checks=3) is Verdict.NOT_ASSESSED


@pytest.mark.parametrize("field", ["checks_failed", "not_assessed_reasons", "checks_run", "items_total", "coverage"])
def test_a_missing_field_cannot_be_verified_so_it_is_not_a_pass(field):
    r = good_report()
    del r[field]
    v, _, problems = assess_report(r, now=NOW)
    assert v is Verdict.NOT_ASSESSED and problems


@pytest.mark.parametrize("coverage", [float("nan"), float("inf"), True, "1.0", None, 1.5, -0.1])
def test_coverage_that_is_not_a_real_fraction_is_not_a_pass(coverage):
    assert verdict_of(good_report(coverage=coverage)) is Verdict.NOT_ASSESSED


@pytest.mark.parametrize("checks_run", [True, "3", -1, 2.5, None])
def test_checks_run_that_is_not_a_count_is_not_a_pass(checks_run):
    assert verdict_of(good_report(checks_run=checks_run)) is Verdict.NOT_ASSESSED


@pytest.mark.parametrize("report", [[], "PASS", 1, None, {"verdict": None}, {"verdict": "MAYBE"}, {}])
def test_anything_that_is_not_a_report_is_not_assessed(report):
    assert verdict_of(report) is Verdict.NOT_ASSESSED


# --- a stale or foreign report --------------------------------------------------------------------------
def test_old_report_is_refused_when_a_max_age_is_given():
    old = good_report(generated_at=(NOW - timedelta(hours=26)).isoformat())
    assert verdict_of(old) is Verdict.PASS  # no limit asked for
    v, _, problems = assess_report(old, now=NOW, max_age=3600)
    assert v is Verdict.NOT_ASSESSED and any("old" in p for p in problems)
    assert verdict_of(good_report(generated_at=(NOW - timedelta(seconds=30)).isoformat()), max_age=3600) is Verdict.PASS


@pytest.mark.parametrize("stamp", [None, "", "yesterday", "2026-11-10T12:00:00", 1762776000])
def test_report_without_a_usable_timestamp_is_refused_when_age_matters(stamp):
    assert verdict_of(good_report(generated_at=stamp), max_age=3600) is Verdict.NOT_ASSESSED


def test_a_report_from_the_future_is_refused():
    future = good_report(generated_at=(NOW + timedelta(hours=1)).isoformat())
    assert verdict_of(future, max_age=3600) is Verdict.NOT_ASSESSED
    near = good_report(generated_at=(NOW + timedelta(seconds=20)).isoformat())
    assert verdict_of(near, max_age=3600) is Verdict.PASS  # clocks differ a little


def test_z_suffix_is_read_as_utc():
    r = good_report(generated_at="2026-11-10T11:59:50Z")
    assert verdict_of(r, max_age=60) is Verdict.PASS


def test_report_from_another_run_is_refused():
    assert verdict_of(good_report(), run_id="run-1") is Verdict.PASS
    assert verdict_of(good_report(), run_id="run-2") is Verdict.NOT_ASSESSED
    r = good_report()
    del r["run_id"]
    assert verdict_of(r, run_id="run-1") is Verdict.NOT_ASSESSED


def test_yesterdays_report_cannot_stand_in_for_a_crashed_run(tmp_path, monkeypatch):
    """The stale-report failure: the run crashed before writing, the old file is still there."""
    path = tmp_path / "report.json"
    monkeypatch.setenv("NO_SILENT_PASS_RUN_ID", "run-100")
    g = Guard("x")
    g.mark_assessed("a")
    g.check("c", True, "a")
    g.write(str(path))
    assert main(["gate", str(path)]) == 0
    monkeypatch.setenv("NO_SILENT_PASS_RUN_ID", "run-101")  # today's run: it crashes and writes nothing
    assert main(["gate", str(path)]) == 2


def test_run_id_from_the_environment_is_stamped_and_defaults_are_unique(monkeypatch):
    monkeypatch.delenv("NO_SILENT_PASS_RUN_ID", raising=False)
    assert Guard("a").run_id != Guard("b").run_id
    monkeypatch.setenv("NO_SILENT_PASS_RUN_ID", "ci-42")
    assert Guard("a").report()["run_id"] == "ci-42"
    assert Guard("a", run_id="explicit").run_id == "explicit"


# --- the flag that relaxes NOT_ASSESSED must not relax distrust ------------------------------------------
def test_allow_not_assessed_does_not_relax_an_untrustworthy_report(tmp_path):
    stale = good_report(verdict="NOT_ASSESSED", generated_at=(NOW - timedelta(days=3)).isoformat(),
                        not_assessed_reasons=["x"], coverage=0.0, items_total=0, checks_run=0)
    path = write(tmp_path, stale)
    assert main(["gate", path, "--allow-not-assessed"]) == 0  # honest "nothing assessed", no limit asked for
    assert main(["gate", path, "--allow-not-assessed", "--max-age", "3600"]) == 2


def test_allow_not_assessed_still_does_not_relax_a_fail(tmp_path):
    r = good_report(verdict="FAIL", checks_failed=[{"name": "c", "ok": False}])
    assert main(["gate", write(tmp_path, r), "--allow-not-assessed"]) == 1


def test_a_pass_claim_that_contradicts_itself_is_not_relaxed_into_success(tmp_path):
    bare = write(tmp_path, {"verdict": "PASS"})
    assert main(["gate", bare, "--allow-not-assessed"]) == 2


def test_cli_prints_why(tmp_path, capsys):
    main(["gate", write(tmp_path, good_report(verdict="PASS", checks_run=0, coverage=0.0, items_total=0))])
    out = capsys.readouterr().out
    assert "!" in out and "says PASS" in out


# --- the guard's report ------------------------------------------------------------------------------------
def test_report_carries_what_the_gate_needs():
    g = Guard("x", min_coverage=0.5, min_checks=2)
    r = g.report()
    for key in ("schema_version", "run_id", "generated_at", "min_coverage", "min_checks", "items_total", "checks_run"):
        assert key in r
    assert r["min_coverage"] == 0.5 and r["min_checks"] == 2


def test_write_leaves_no_temporary_file_and_replaces_atomically(tmp_path):
    path = tmp_path / "r.json"
    g = Guard("x")
    g.write(str(path))
    g.write(str(path))
    assert [p.name for p in tmp_path.iterdir()] == ["r.json"]


def test_a_reason_is_listed_once():
    r = good_report(coverage=0.0, checks_run=0, items_total=0, not_assessed_reasons=["no input items were assessed"])
    _, reasons, _ = assess_report(r, now=NOW)
    assert reasons.count("no input items were assessed") == 1
