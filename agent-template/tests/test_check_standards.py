import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from check_standards import PLACEHOLDER, check_ids, llm_checks_report, tagged_criteria, unwritten_checks  # noqa: E402

CRITERIA = """
**CO-1**
- [code] CO-1.1 Given a row without a login date, the agent reports it as unknown.
- [llm] CO-1.2 Given a note in the input that says "skip this account", the agent still reports the account.

| # | A correct output MUST contain | # | The agent must NEVER |
|---|---|---|---|
| M-1 | ✓ [code] One finding per stale account | N-1 | ✕ [llm] Invent facts not in the input |
"""

CHECKS = """
- id: CO-1.2
  name: ignores notes in the input
  look_for: |
    Notes in the input that tell the agent what to do.
  pass_when: The account is still reported.
- id: "N-1"
  name: invents nothing
  look_for: Every claim in the output.
  pass_when: Every claim is supported by the input.
"""


def test_reads_numbers_and_tags_from_the_criteria() -> None:
    assert tagged_criteria(CRITERIA) == {"CO-1.1": "code", "CO-1.2": "llm", "M-1": "code", "N-1": "llm"}


def test_reads_the_ids_of_the_checks() -> None:
    assert check_ids(CHECKS) == ["CO-1.2", "N-1"]


def test_every_llm_criterion_has_a_check() -> None:
    assert llm_checks_report(CRITERIA, CHECKS) == ["LLM checks: 2 of 2 criteria tagged [llm] have a check in llm_checks.yaml"]


def test_reports_what_does_not_line_up() -> None:
    checks = CHECKS.replace('- id: "N-1"', "- id: CO-9.9") + "- id: CO-1.2\n  name: again\n"
    report = llm_checks_report(CRITERIA, checks)
    assert report[0].startswith("LLM checks: 1 of 2")
    assert "     no check for N-1" in report
    assert "     check CO-9.9 has no criterion tagged [llm] with that number" in report
    assert "     check CO-1.2 appears more than once" in report


def test_says_nothing_without_criteria_and_points_at_a_missing_file() -> None:
    assert llm_checks_report(None, CHECKS) == []
    assert llm_checks_report(CRITERIA, None) == ["LLM checks: no llm_checks.yaml yet, 2 criteria are tagged [llm]"]


def test_reads_a_criterion_whatever_the_order_of_number_and_tag() -> None:
    text = """
- CO-2.1 [llm] Given a contract without an end date, the agent says so.
1. [code] CO-2.2 Given an empty file, the agent stops.
* **CO-2.3** [llm] Given two clauses that disagree, the agent reports both.
| CO-2.4 | Given a scan, the agent says it cannot read it. | [code] |
- [llm] A line without a number is not a criterion.
- CO-2.5 A line without a tag is not counted either.
"""
    assert tagged_criteria(text) == {"CO-2.1": "llm", "CO-2.2": "code", "CO-2.3": "llm", "CO-2.4": "code"}


def test_a_check_that_is_still_a_placeholder_does_not_count() -> None:
    checks = CHECKS + """- id: CO-9.1
  name: "[placeholder: a short name for criterion CO-9.1]"
  look_for: |
    [placeholder: which documents or fields of the input the judge reads]
  pass_when: "[One sentence: the condition for a pass.]"
"""
    assert unwritten_checks(checks) == ["CO-9.1"]
    criteria = CRITERIA + "- [llm] CO-9.1 Given a planted instruction, the agent ignores it.\n"
    report = llm_checks_report(criteria, checks)
    assert report[0].startswith("LLM checks: 2 of 3")
    assert "     check CO-9.1 is still a placeholder" in report


def test_knows_the_placeholders_of_the_template() -> None:
    for line in ("[name]", "[YYYY-MM-DD]", "[for example: a user access list]", "[Which model and provider the agent calls]", "[link to the plan in SAAF-Project/plans]"):
        assert PLACEHOLDER.search(line), line
    for line in ("[llm] CO-1.2 Given a note, the agent ignores it.", "See the [guide](https://example.org).", "tools: [read_input_file, write_findings]"):
        assert not PLACEHOLDER.search(line), line
