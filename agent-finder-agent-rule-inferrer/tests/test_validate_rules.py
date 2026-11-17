import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_rules", ROOT / "tools" / "validate_rules.py")
vr = importlib.util.module_from_spec(spec); spec.loader.exec_module(vr)

GOOD = {
    "Inferred_Rule": "RFIR042",
    "Quote": "no real audit evidence or interviewee data may be used.",
    "Tool": "Read",
    "Parameters": "plans/hackathon-4/uc7.md (L197-198)",
    "Outcome": "Not enforced in code.",
}


def test_repo_rules_are_valid():
    problems, count = vr.validate_dir(ROOT / "rules")
    assert problems == {} and count >= 1


def test_good_record_passes():
    assert vr.validate(GOOD) == []
    assert vr.validate({**GOOD, "Status": "enforced", "Parameters": "Org/repo:a/b.py (L3)"}) == []


def test_missing_field_fails():
    rec = dict(GOOD); del rec["Quote"]
    assert any("Quote" in e for e in vr.validate(rec))


def test_bad_id_location_status_and_extra_field_fail():
    for bad in ({"Inferred_Rule": "R42"}, {"Parameters": "uc7.md line 197"},
                {"Status": "done"}, {"Note": "x"}, {"Quote": 42}):
        assert vr.validate({**GOOD, **bad}), bad


def test_file_name_must_match_id_and_ids_unique(tmp_path):
    (tmp_path / "RFIR001.json").write_text(json.dumps(GOOD))
    (tmp_path / "RFIR042.json").write_text(json.dumps(GOOD))
    problems, _ = vr.validate_dir(tmp_path)
    assert any("file name" in e for e in problems["RFIR001.json"])
    assert any("duplicate" in e for e in problems["RFIR042.json"])
