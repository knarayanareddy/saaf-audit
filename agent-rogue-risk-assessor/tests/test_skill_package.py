import re
from pathlib import Path
import yaml

SKILL = Path(__file__).resolve().parents[1] / "skills" / "agent-rogue-risk-assessor"


def frontmatter():
    text = (SKILL / "SKILL.md").read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with YAML frontmatter"
    return yaml.safe_load(m.group(1)), text


def test_frontmatter_valid():
    fm, _ = frontmatter()
    assert fm["name"] == "agent-rogue-risk-assessor"
    assert 50 < len(fm["description"]) <= 1024


def test_referenced_files_exist():
    _, text = frontmatter()
    for ref in set(re.findall(r"`((?:references|scripts|assets)/[\w./-]+)`", text)):
        assert (SKILL / ref).exists(), ref


def test_versions_in_sync():
    fm, _ = frontmatter()
    v = fm["metadata"]["version"]
    assert f'SCANNER_VERSION = "{v}"' in (SKILL / "scripts" / "scan_repo.py").read_text()
    assert f"v{v}" in (SKILL / "references" / "rubric.md").read_text()


def test_consent_gate_wording_present():
    _, text = frontmatter()
    assert "literal \"Yes\"" in text and "treated as **No**" in text
