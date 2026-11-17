"""Tests for the joiners-movers-leavers agent. Run: python3 -m pytest -q

Each test maps to an acceptance criterion in AUDIT-CRITERIA.md (see the AC tags).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import ai.claude_runner as runner
from engine.findings import FINDING_SCHEMA, deterministic_findings, validate_draft
from engine.jml_checks import public_review, run_review
from engine.pseudonymise import Pseudonymiser, allowed_references, build_payload
from engine.sources import load_sources

REPO = Path(__file__).parents[1]

EXPECTED = {
    ("J1", "daan.smit"), ("J2", "sara.koch"), ("J3", "emma.jansen"), ("J4", "noah.visser"), ("J5", "mila.peters"),
    ("M1", "julia.dekker"), ("M1", "lucas.mulder"), ("M2", "lucas.mulder"), ("M3", "julia.dekker"),
    ("L1", "ruben.hendriks"), ("L2", "anna.vos"), ("L3", "ruben.hendriks"), ("L4", "kevin.meijer"),
    ("B1", "ext.consultant01"), ("B4", "yvonne.smits"),
}
CLEAN = {"lotte.willems", "omar.haddad", "sem.bos", "chris.vermeulen", "bas.groen", "pieter.vandam"}


@pytest.fixture(scope="module")
def review() -> dict:
    return run_review(load_sources())


def test_planted_exceptions_found_exactly(review):  # AC CO-2.1
    found = {(e["test_id"], e["username"]) for e in review["exceptions"]}
    assert found == EXPECTED


def test_clean_records_pass(review):  # AC CO-2.2
    flagged = {e["username"] for e in review["exceptions"]}
    assert not (flagged & CLEAN)


def test_service_account_excluded(review):  # AC CO-2.2
    assert "svc_backup" not in {e["username"] for e in review["exceptions"]}


def test_review_is_deterministic(review):  # AC CO-2.3
    again = run_review(load_sources())
    strip = lambda r: json.dumps({k: v for k, v in public_review(r).items() if k != "generated_at"}, sort_keys=True)
    assert strip(again) == strip(review)


def test_every_exception_traces_to_source_rows(review):  # AC CO-1.1 and CO-1.2
    files = {p.name: list(csv.reader(p.open(encoding="utf-8"))) for p in (REPO / "sample_data").glob("*.csv")}
    for e in review["exceptions"]:
        assert e["evidence"], e["id"]
        for ev in e["evidence"]:
            name, line = ev["ref"].rsplit(":", 1)
            row = files[name][int(line) - 1]
            if name != "jira_access_requests.csv":
                assert row[0] == e["username"] or row[1] == e["username"], (e["id"], ev["ref"])
            else:
                assert ev["ticket_id"] in e["tickets"] and row[0] == ev["ticket_id"]


def test_each_exception_has_a_risk_and_controls(review):  # AC CO-1.3
    for e in review["exceptions"]:
        assert e["risk_rating"] in ("High", "Medium", "Low")
    for t in review["tests"]:
        assert t["control_refs"], t["id"]


def test_payload_contains_no_names(review):  # AC CO-5.1
    pz = Pseudonymiser(review["_anon_map"], review["_people"])
    text = json.dumps(build_payload(review, pz))
    for key, name in review["_people"].items():
        if key in ("svc_backup",):
            continue
        assert key not in text, key
        if name and name != key:
            assert name not in text, name


def test_reveal_restores_names_locally(review):  # AC CO-5.2
    pz = Pseudonymiser(review["_anon_map"], review["_people"])
    ref = review["_anon_map"]["lucas.mulder"]
    assert pz.reveal(f"{ref} holds two roles") == f"Lucas Mulder ({ref}) holds two roles"


def _payload(review):
    pz = Pseudonymiser(review["_anon_map"], review["_people"])
    p = build_payload(review, pz)
    return p, allowed_references(p), [e["id"] for e in review["exceptions"]]


def _finding(**kw):
    f = {"id": "F-01", "title": "Test", "risk_rating": "High", "observation": "x", "recommendation": "y",
         "evidence_references": ["EX-01"]}
    f.update(kw)
    return f


def test_finding_citing_unknown_record_is_rejected(review):  # AC CO-3.1
    _, allowed, ids = _payload(review)
    res = validate_draft({"findings": [_finding(evidence_references=["EX-01", "IAM-9999"])], "assessments": []},
                         allowed, ids)
    assert res["checks"]["findings_kept"] == 0
    assert "IAM-9999" in " ".join(res["checks"]["issues"])


def test_finding_mentioning_unknown_id_in_text_is_rejected(review):  # AC CO-3.2
    _, allowed, ids = _payload(review)
    res = validate_draft({"findings": [_finding(observation="See ticket IAM-4242.")], "assessments": []}, allowed, ids)
    assert res["checks"]["findings_kept"] == 0


def test_finding_outside_schema_is_rejected(review):  # AC CO-3.3
    _, allowed, ids = _payload(review)
    bad = [_finding(id="FIND-1"), _finding(risk_rating="Severe"), _finding(extra_field="x"), _finding(title="t" * 101)]
    res = validate_draft({"findings": bad, "assessments": []}, allowed, ids)
    assert res["checks"]["findings_kept"] == 0 and res["checks"]["findings_rejected"] == 4


def test_uncovered_exceptions_are_reported(review):  # AC CO-3.4
    _, allowed, ids = _payload(review)
    res = validate_draft({"findings": [_finding()], "assessments": []}, allowed, ids)
    assert not res["checks"]["passed"]
    assert any("not covered" in i for i in res["checks"]["issues"])


def test_deterministic_findings_follow_schema(review):  # AC CO-3.3
    _, allowed, ids = _payload(review)
    findings = deterministic_findings(review, runner.LIFECYCLE_OF)
    res = validate_draft({"findings": findings, "assessments": [{"exception_id": i} for i in ids]}, allowed, ids)
    assert res["checks"]["passed"], res["checks"]["issues"]
    for f in findings:
        assert set(f) <= set(FINDING_SCHEMA["properties"])


@pytest.mark.parametrize("lang", ["en", "nl"])
def test_prepared_results_match_sample_and_pass_checks(review, lang):  # AC CO-4.3
    prep = runner.load_prepared(review["fingerprint"], lang)
    assert prep is not None, "prepared result does not match the sample data fingerprint"
    _, allowed, ids = _payload(review)
    assert validate_draft(prep["draft"], allowed, ids)["checks"]["passed"]
    for f in prep["draft"]["findings"]:
        assert f["status"] == "Open" and f["ai_assisted"] is True


def test_fallback_without_claude_uses_prepared(review, monkeypatch, tmp_path):  # AC CO-4.3
    monkeypatch.setattr(runner, "find_claude", lambda: None)
    res = runner.draft_findings(review, tmp_path, language="en")
    assert res["mode"] == "prepared" and "not installed" in res["error"]


def test_fallback_on_other_data_is_deterministic(review, monkeypatch, tmp_path):  # AC CO-4.3
    monkeypatch.setattr(runner, "find_claude", lambda: None)
    other = {**review, "fingerprint": "0000000000000000"}
    res = runner.draft_findings(other, tmp_path, language="en")
    assert res["mode"] == "deterministic"
    assert res["checks"]["exceptions_covered"] == len(review["exceptions"])


def test_model_call_has_no_tools(monkeypatch):  # AC CO-5.3
    seen = {}

    class P:
        returncode, stdout, stderr = 0, json.dumps({"is_error": False, "structured_output": {"summary": "",
                                                    "assessments": [], "findings": []}}), ""

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return P()

    monkeypatch.setattr(runner, "find_claude", lambda: "claude")
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    runner.call_claude("sys", "user", "sonnet", 5)
    cmd = seen["cmd"]
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in cmd and "--no-session-persistence" in cmd
    assert "--dangerously-skip-permissions" not in cmd


def test_sample_data_is_reproducible(tmp_path, monkeypatch):  # AC CO-2.3
    import tools.generate_sample_data as gen

    monkeypatch.setattr(gen, "OUT_DIR", tmp_path)
    gen.main()
    for p in tmp_path.iterdir():
        assert p.read_bytes() == (REPO / "sample_data" / p.name).read_bytes(), p.name


def test_web_flow_requires_signoff_before_final(monkeypatch):  # AC CO-4.1 and CO-4.2
    from fastapi.testclient import TestClient

    import web.app as webapp

    monkeypatch.setattr(runner, "find_claude", lambda: None)
    c = TestClient(webapp.app)
    assert c.post("/api/draft", json={"lang": "en"}).status_code == 409  # no review yet
    assert c.post("/api/load").status_code == 200
    run = c.post("/api/run").json()
    assert len(run["exceptions"]) == len(EXPECTED)
    assert "_anon_map" not in run
    assert c.post("/api/signoff", json={"reviewer": "A", "statement": "s"}).status_code == 409  # no draft yet
    d = c.post("/api/draft", json={"lang": "en", "mode": "auto"}).json()
    assert d["mode"] == "prepared"
    draft_report = c.get("/report").text
    assert "Draft. Not signed off" in draft_report and 'class="watermark"' in draft_report
    assert c.post("/api/signoff", json={"reviewer": "", "statement": "s"}).status_code == 422
    so = c.post("/api/signoff", json={"reviewer": "Test Reviewer", "statement": "s"}).json()
    assert so["draft_mode"] == "prepared"
    signed_report = c.get("/report").text
    assert "Signed off by Test Reviewer" in signed_report and 'class="watermark"' not in signed_report
    assert c.get("/report?lang=nl").status_code == 200
    assert c.get("/?lang=nl").status_code == 200


def test_i18n_keys_match():
    en = json.loads((REPO / "web/i18n/en.json").read_text(encoding="utf-8"))
    nl = json.loads((REPO / "web/i18n/nl.json").read_text(encoding="utf-8"))
    assert set(en) == set(nl)
