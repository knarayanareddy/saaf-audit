"""The graders grade — checked before a cent is spent on what they grade.

    venv/Scripts/python.exe -m tests.test_agent_graders

A baseline is only as good as the instrument. A grader that passes everything
makes every agent look fine; one that fails a correct answer makes the migration
look like a regression. So each grader is shown a hand-written good answer, which
must pass, and a hand-written bad one, which must fail on the check it targets.
No API calls.
"""
import sys

from evals.agent_cases import FINDING_CASES, FRAMEWORKS_CASES, LENS_CASES, QA_CASES, RCSA_CASES
from evals.agent_graders import (
    _term_found, grade_finding, grade_frameworks, grade_lens, grade_qa, grade_rcsa,
)

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def _all_pass(scores):
    return all(s.passed for s in scores if not s.skipped)


def _failed(scores, fragment):
    return any((not s.passed) and fragment in s.name for s in scores)


def test_acronyms_match_as_words():
    print("matching:")
    check(not _term_found("see section 4 of the policy", "SEC"), "'SEC' does not match inside 'section'")
    check(_term_found("the SEC fined the firm", "SEC"), "but does match the word SEC")
    check(_term_found("Under the wwft the bank must", "Wwft"), "longer terms match case-insensitively")
    # Found by this suite on its first run: "AMLD6" did not count as AMLD, so a
    # correct lens answer would have been scored wrong in the baseline.
    check(_term_found("AMLD6 requires", "AMLD"), "a version number after an acronym still matches")


def test_lens():
    print("lens:")
    case = LENS_CASES[0]  # AML / CDD, NL + EU
    good = {"summary": "The Wwft and AMLD6 require customer due diligence at onboarding; "
                       "DNB supervises compliance.", "sources": [{"title": "Wwft"}]}
    check(_all_pass(grade_lens(case, good)), "a correct, in-scope summary passes")
    stray = {**good, "summary": good["summary"] + " The FCA expects the same in the UK."}
    check(_failed(grade_lens(case, stray), "stays inside"), "naming a UK regulator fails scope")
    missing = {"summary": "Customer onboarding must be risk-based.", "sources": [{"title": "x"}]}
    check(_failed(grade_lens(case, missing), "mentions"), "missing the core law fails")
    check(_failed(grade_lens(case, [{"title": "a bare list"}]), "an object"),
          "a bare list instead of an object fails the shape check")


def test_frameworks():
    print("frameworks:")
    case = FRAMEWORKS_CASES[0]
    good = [
        {"framework_name": "Wwft", "specific_provision": "Art. 3 Wwft", "jurisdiction": "NL"},
        {"framework_name": "AMLD (EU) 2015/849", "specific_provision": "Art. 13", "jurisdiction": "EU"},
    ]
    check(_all_pass(grade_frameworks(case, good)), "the expected frameworks with numbered provisions pass")
    uk = good + [{"framework_name": "MLR 2017", "specific_provision": "Reg. 28", "jurisdiction": "UK"}]
    scores = grade_frameworks(case, uk)
    check(_failed(scores, "outside the scope") and _failed(scores, "jurisdiction"),
          "a UK regulation fails both the content and the jurisdiction check")
    vague = [{"framework_name": "Wwft", "specific_provision": "the law", "jurisdiction": "NL"},
             {"framework_name": "AMLD", "specific_provision": "", "jurisdiction": "EU"}]
    check(_failed(grade_frameworks(case, vague), "specific"), "provisions without numbers fail")


def test_finding():
    print("finding:")
    case = FINDING_CASES[0]  # 14 of 60, since 2021
    good = {"title": "No periodic re-screening", "condition": "14 of 60 customers were not re-screened since 2021.",
            "criteria": "Sanctions law requires ongoing screening.", "cause": "No control designed.",
            "effect": "Sanctioned parties may go undetected.", "recommendation": "Introduce periodic re-screening.",
            "rating": "high", "rating_rationale": "x"}
    check(_all_pass(grade_finding(case, good)), "a complete finding using only the given numbers passes")
    invented = {**good, "condition": "23 of 60 customers were not re-screened since 2021."}
    check(_failed(grade_finding(case, invented), "numbers"), "a number the auditor did not give fails")
    derived = {**good, "condition": "14 of 60 customers (23.3%) were not re-screened since 2021."}
    check(not _failed(grade_finding(case, derived), "numbers"),
          "a correctly computed percentage is arithmetic, not invention")
    miscalculated = {**good, "condition": "14 of 60 customers (40%) were not re-screened since 2021."}
    check(_failed(grade_finding(case, miscalculated), "numbers"),
          "but a percentage that does not follow from the given numbers still fails")
    remainder = {**good, "condition": "14 of 60 customers were not re-screened since 2021; "
                                      "the other 46 were."}
    check(not _failed(grade_finding(case, remainder), "numbers"),
          "the remainder of two given counts is arithmetic, not invention")
    soft = {**good, "rating": "low"}
    check(_failed(grade_finding(case, soft), "rated"), "a rating outside the allowed set fails")
    hollow = {**good, "cause": ""}
    check(_failed(grade_finding(case, hollow), "five C"), "an empty C fails")


def test_qa():
    print("qa review:")
    case = QA_CASES[0]
    good = {"overall_quality": "needs_work", "summary": "Several conclusions are unsupported.", "comments": [
        {"severity": "must_fix", "comment": "Test 1: a sample of 5 days is too small for a daily control."},
        {"severity": "must_fix", "comment": "Test 2 reports 3 of 25 exceptions yet concludes effective — contradiction."},
        {"severity": "must_fix", "comment": "Test 3 was not yet performed but is concluded effective."},
        {"severity": "suggestion", "comment": "State the control objective for each test."},
    ]}
    check(_all_pass(grade_qa(case, good)), "a review that finds all four planted defects passes")
    partial = {**good, "comments": good["comments"][:1]}
    check(_failed(grade_qa(case, partial), "finds"), "a review that misses planted defects fails")
    flattering = {**good, "overall_quality": "good"}
    check(_failed(grade_qa(case, flattering), "does not call"), "calling a defective artifact good fails")

    clean = QA_CASES[1]
    alarmist = {"overall_quality": "needs_work", "summary": "", "comments": [
        {"severity": "must_fix", "comment": "a"}, {"severity": "must_fix", "comment": "b"}]}
    check(_failed(grade_qa(clean, alarmist), "false alarms"), "two must-fixes on a clean artifact fail")


def test_rcsa():
    print("rcsa mapping:")
    case = RCSA_CASES[0]
    columns = [{"column": n, "target": None} for n in case.names]
    for idx, allowed in case.expected.items():
        columns[idx]["target"] = allowed[0]
    check(_all_pass(grade_rcsa(case, {"columns": columns})), "the expected mapping passes")
    swapped = [dict(c) for c in columns]
    for idx in (9, 10, 11, 20):   # inherent likelihood/impact/exposure and a residual one, blanked
        swapped[idx]["target"] = None
    check(_failed(grade_rcsa(case, {"columns": swapped}), "right field"),
          "four wrong columns out of twenty drop it under the bar")
    check(_failed(grade_rcsa(case, {"columns": columns[:-1]}), "one proposal per column"),
          "a missing column fails")


def main():
    test_acronyms_match_as_words()
    test_lens()
    test_frameworks()
    test_finding()
    test_qa()
    test_rcsa()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
