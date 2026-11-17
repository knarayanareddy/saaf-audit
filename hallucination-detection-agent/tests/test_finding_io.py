"""Finding I/O (pure Python, no API key).

CO-3 of AUDIT-CRITERIA.md: the original finding is returned unchanged, with
one ``hallucination_check`` key added. The extractor input is the title,
observation and recommendation, nothing else.
"""
import json
from pathlib import Path

import pytest

from hallucination.finding_io import REQUIRED_FIELDS, finding_text, load_finding, save_finding

SAMPLES = Path(__file__).resolve().parents[1] / "hallucination" / "dummy_data" / "sample_findings"


def test_sample_fixtures_exist_and_load():
    names = sorted(p.name for p in SAMPLES.glob("F-000?.json"))
    assert names == ["F-0001.json", "F-0002.json", "F-0003.json", "F-0004.json", "F-0005.json"]
    for name in names:
        f = load_finding(SAMPLES / name)
        assert all(k in f for k in REQUIRED_FIELDS)


def test_missing_required_field_is_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"id": "F-0099", "title": "no observation"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_finding(p)


def test_malformed_json_is_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_finding(p)


def test_save_then_load_preserves_original_plus_one_key(tmp_path):
    original = load_finding(SAMPLES / "F-0001.json")
    annotated = dict(original)
    annotated["hallucination_check"] = {"overall_risk": "HIGH", "blocked": False, "warning": True}
    out = tmp_path / "F-0001_checked.json"
    save_finding(annotated, out)
    reloaded = json.loads(out.read_text(encoding="utf-8"))
    assert set(reloaded) == set(original) | {"hallucination_check"}
    for k, v in original.items():
        assert reloaded[k] == v


def test_finding_text_uses_title_observation_recommendation_only():
    f = {"id": "F-0001", "title": "T", "risk_rating": "High", "observation": "O",
         "recommendation": "R", "root_cause": "SHOULD NOT APPEAR"}
    text = finding_text(f)
    assert text == "T\n\nO\n\nR"
    assert "SHOULD NOT APPEAR" not in text
