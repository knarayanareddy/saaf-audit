import json

from no_silent_pass import Guard
from no_silent_pass.cli import main


def _report(tmp_path, g):
    p = tmp_path / "report.json"
    g.write(str(p))
    return str(p)


def test_gate_exit_codes(tmp_path):
    ok = Guard("ok")
    ok.mark_assessed("a")
    ok.check("c", True, "a")
    bad = Guard("bad")
    bad.check("c", False)
    empty = Guard("empty")
    assert main(["gate", _report(tmp_path, ok)]) == 0
    assert main(["gate", _report(tmp_path, bad)]) == 1
    assert main(["gate", _report(tmp_path, empty)]) == 2


def test_allow_not_assessed_only_relaxes_not_assessed(tmp_path):
    bad = Guard("bad")
    bad.check("c", False)
    assert main(["gate", _report(tmp_path, Guard("e")), "--allow-not-assessed"]) == 0
    assert main(["gate", _report(tmp_path, bad), "--allow-not-assessed"]) == 1


def test_missing_or_malformed_report_fails_closed(tmp_path):
    assert main(["gate", str(tmp_path / "nope.json")]) == 2
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert main(["gate", str(broken)]) == 2
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"verdict": "MAYBE"}))
    assert main(["gate", str(wrong)]) == 2


def test_demo_runs(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "MATCH" in out and "NOT_ASSESSED" in out
