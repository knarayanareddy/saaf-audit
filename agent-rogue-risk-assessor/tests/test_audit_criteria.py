import re
from pathlib import Path

REF = Path(__file__).resolve().parents[1] / "skills" / "agent-rogue-risk-assessor" / "references"
TEXT = (REF / "audit-criteria.md").read_text()
IDS = [f"AC-{i:02d}" for i in range(1, 11)]


def sections():
    parts = re.split(r"^### (AC-\d\d)", TEXT, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def test_all_ten_criteria_present_once():
    assert list(sections()) == IDS


def test_each_criterion_has_required_elements():
    for cid, body in sections().items():
        for element in ("**Objective**", "**Criterion**", "**Test procedures**", "**Evidence**", "**Rating**", "**Links**"):
            assert element in body, f"{cid} missing {element}"


def test_scored_criteria_link_to_rubric_items():
    for cid, body in sections().items():
        if cid == "AC-10":
            continue
        assert re.search(r"\b(RF[1-6]|C[1-5])\b", body), cid


def test_every_flag_and_control_covered():
    links = " ".join(re.findall(r"\*\*Links\*\*:(.*)", TEXT))
    for item in [f"RF{i}" for i in range(1, 7)] + [f"C{i}" for i in range(1, 6)]:
        assert item in links, item


def test_version_matches_rubric():
    v = re.search(r"\(v(\d+\.\d+\.\d+)\)", TEXT).group(1)
    assert f"v{v}" in (REF / "rubric.md").read_text()


def test_mapping_tables_cover_all_criteria():
    for table_header in ("## 4. Mapping to the rubric", "## 6. Framework references"):
        section = TEXT.split(table_header, 1)[1].split("\n## ", 1)[0]
        for cid in IDS:
            assert f"| {cid} |" in section, f"{cid} missing from {table_header}"
