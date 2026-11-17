"""Agent cases — what a competent agent must conclude, stated before it runs.

The golden set measures retrieval: does the answer reach the prompt. These
measure the agents: given that input, is what comes back right. Six agents, the
ones whose output an auditor leans on most:

    Topic Intelligence (three lenses) · Frameworks · Governance assessment ·
    Finding drafter (5C) · QA review · RCSA column mapping

**Every grader is deterministic.** No model is asked whether another model did
well; a check either finds the regulation, the planted defect, the right column
— or it does not. That limits what can be graded to what can be stated in
advance, and that limit is the point: a score whose grader can drift is not a
baseline anything can be compared against.

**Every case is synthetic and says so.** The facts are invented for this suite.
The expectations are mine, written from general audit and regulatory knowledge,
and each case carries `needs_review=True` until a person who audits for a living
has confirmed that what it expects is what a competent agent should produce.
Until then a failure means "disagrees with the suite", not "is wrong".
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: Regulators and laws of jurisdictions that are never in scope in these cases.
#: A lens that names them has stepped outside the scope it was given.
FOREIGN_TO_NL_EU = ("BaFin", "Bundesbank", "FCA", "PRA", "SEC", "FINRA", "OCC",
                    "Federal Reserve", "CNMV", "Banco de España", "SEPBLAC", "MLR 2017")


@dataclass(frozen=True)
class LensCase:
    id: str
    lens: int                      # 1 regulatory · 2 supervisory · 3 society
    audit: str
    entity: str
    audit_type: str
    jurisdictions: tuple[str, ...]
    #: Each group is satisfied when ANY of its terms appears (case-insensitive).
    must_mention: tuple[tuple[str, ...], ...]
    must_not_mention: tuple[str, ...] = FOREIGN_TO_NL_EU
    #: Cyber and IT-security topics are where the current models' `cyber`
    #: classifier may decline; these cases exist to find out whether it does.
    may_be_refused: bool = False
    needs_review: bool = True


@dataclass(frozen=True)
class FrameworksCase:
    id: str
    audit: str
    entity: str
    audit_type: str
    jurisdictions: tuple[str, ...]
    must_include: tuple[tuple[str, ...], ...]
    must_not_include: tuple[str, ...] = ()
    needs_review: bool = True


@dataclass(frozen=True)
class GovernanceCase:
    id: str
    framework: dict
    #: (doc_id, label, text) — what the auditee "uploaded".
    documents: tuple[tuple[str, str, str], ...]
    question: str
    #: Requirement keyword -> coverage values a competent assessment may give it.
    expected_coverage: dict = field(default_factory=dict)
    may_be_refused: bool = False
    needs_review: bool = True


@dataclass(frozen=True)
class FindingCase:
    id: str
    audit: str
    entity: str
    audit_type: str
    seed: dict
    allowed_ratings: tuple[str, ...]
    needs_review: bool = True


@dataclass(frozen=True)
class QaCase:
    id: str
    audit: str
    entity: str
    audit_type: str
    label: str
    content: str
    #: Each planted defect: (name, terms any of which a comment must mention).
    planted: tuple[tuple[str, tuple[str, ...]], ...]
    #: For a clean artifact: the most must-fix comments that are tolerable.
    max_must_fix: int | None = None
    needs_review: bool = True


@dataclass(frozen=True)
class RcsaCase:
    id: str
    names: tuple[str, ...]
    bands: tuple[str, ...]
    samples: tuple[tuple[str, ...], ...]
    #: Column index -> targets a correct proposal may choose. Columns left out
    #: are genuinely ambiguous and not graded.
    expected: dict
    needs_review: bool = True


# ── Topic Intelligence ───────────────────────────────────────────────────────
LENS_CASES = (
    LensCase(
        "lens1-aml-cdd", 1, "Customer Due Diligence Onboarding Review", "GRP", "compliance",
        ("NL", "EU"),
        must_mention=(("Wwft", "WWFT"), ("AMLD", "Anti-Money Laundering Directive", "AMLR",
                                         "Anti-Money Laundering Regulation")),
    ),
    LensCase(
        "lens1-ict-dora", 1, "IT Security Management Review", "GRP", "it", ("NL", "EU"),
        must_mention=(("DORA", "Digital Operational Resilience"),),
        may_be_refused=True,
    ),
    # GRP, not RET: in this platform RET is supervised by NBB/FSMA (Belgium), so
    # an NL-only scope on a RET audit is a contradiction the model rightly flags.
    # The first baseline had exactly that mistake in it; it was the case's, not
    # the agent's.
    LensCase(
        "lens2-ict-supervisor", 2, "Cybersecurity Controls Review", "GRP", "it", ("NL", "EU"),
        must_mention=(("DNB", "De Nederlandsche Bank"),),
        may_be_refused=True,
    ),
    # Lens 3 is about peer incidents and its prompt allows a foreign case "when it
    # is directly relevant" — and the defining greenwashing case (DWS) was fined
    # by BaFin and the SEC. The first version of this case forbade those names
    # and scored a correct answer as out of scope three times out of three; what
    # is graded instead is that the answer stays anchored in the EU/NL scope.
    LensCase(
        "lens3-sustainable-finance", 3, "Sustainable Finance Disclosure Review", "AM", "esg",
        ("NL", "EU"),
        must_mention=(("greenwashing", "green-washing", "greenwash"), ("SFDR", "ESMA", "AFM")),
        must_not_mention=(),
    ),
)

# ── Frameworks ───────────────────────────────────────────────────────────────
FRAMEWORKS_CASES = (
    FrameworksCase(
        "fw-aml-cdd", "Customer Due Diligence Onboarding Review", "GRP", "compliance",
        ("NL", "EU"),
        must_include=(("Wwft", "WWFT"), ("AMLD", "Anti-Money Laundering", "AMLR", "2015/849")),
        must_not_include=("MLR 2017", "Ley 10/2010"),
    ),
    FrameworksCase(
        "fw-ict", "IT Security Management Review", "GRP", "it", ("NL", "EU"),
        must_include=(("DORA", "2022/2554", "Digital Operational Resilience"),),
        must_not_include=("FCA",),
    ),
    FrameworksCase(
        "fw-sfdr", "Sustainable Finance Disclosure Review", "AM", "esg", ("NL", "EU"),
        must_include=(("SFDR", "2019/2088", "Sustainable Finance Disclosure"),),
    ),
)

# ── Governance assessment ────────────────────────────────────────────────────
_ICT_POLICY = """ICT Risk and Incident Policy (synthetic — written for the IA Wingman eval suite)

1. Document control
This policy is owned by the CISO office and reviewed annually by the Risk Committee.

2. ICT incident classification and reporting
All ICT-related incidents are classified using the criteria of the incident register.
Major ICT-related incidents are reported to De Nederlandsche Bank within 4 hours of
classification, followed by an intermediate report within 72 hours and a final report
within one month.

3. Access management
Privileged access to production systems requires multi-factor authentication and is
reviewed quarterly by the system owner.

4. Business continuity
Each critical business service has a documented recovery time objective. Recovery plans
are tested once a year and test results are reported to the Operational Risk Committee.
"""

GOVERNANCE_CASES = (
    GovernanceCase(
        "gov-dora-ict",
        framework={"category": "law", "ref": "F1",
                   "name": "Digital Operational Resilience Act (Regulation (EU) 2022/2554)",
                   "provision": "Art. 19 incident reporting; Art. 28 register of information on ICT third-party providers",
                   "rationale": "The bank is a financial entity in scope of DORA."},
        documents=(("ict-policy", "ICT Risk and Incident Policy.pdf", _ICT_POLICY),),
        question="ICT incident reporting and the register of ICT third-party service providers",
        # The policy covers incident reporting and says nothing about a
        # third-party register: that is the planted gap.
        expected_coverage={
            "incident": ("covered", "partial"),
            "register": ("partial", "gap"),
            "third": ("partial", "gap"),
        },
        may_be_refused=True,
    ),
)

# ── Finding drafter ──────────────────────────────────────────────────────────
FINDING_CASES = (
    FindingCase(
        "finding-rescreening", "Sanctions Screening Process", "INT", "compliance",
        seed={"title": "Customers not re-screened after onboarding",
              "condition": "14 of 60 sampled customers had not been re-screened against the "
                           "sanctions list since onboarding in 2021.",
              "criteria": "", "cause": "", "effect": ""},
        allowed_ratings=("high",),
    ),
    FindingCase(
        "finding-expense-signature", "Fraud Risk Management", "GRP", "operational",
        seed={"title": "Second signature missing on expense claims",
              "condition": "2 of 25 sampled expense claims lacked the second approval "
                           "signature; both were below EUR 200.",
              "criteria": "The expense policy requires a second approval on every claim.",
              "cause": "", "effect": ""},
        allowed_ratings=("low", "medium"),
    ),
    FindingCase(
        "finding-sod", "Client Asset Segregation", "AM", "compliance",
        seed={"title": "Maker and checker are the same person",
              "condition": "On 9 of 40 client money reconciliations the preparer also "
                           "approved the reconciliation.",
              "criteria": "", "cause": "", "effect": ""},
        allowed_ratings=("medium", "high"),
    ),
)

# ── QA review ────────────────────────────────────────────────────────────────
_WORK_PROGRAM_WITH_DEFECTS = """Work program — Payment processing controls (synthetic)

Test 1 — Daily payment batch approval
Control: Payment batches above EUR 50,000 are approved by a second officer before release.
Control frequency: daily.
Test approach: inspect approval evidence for a sample of 5 days out of the year.
Result: no exceptions.
Conclusion: effective.

Test 2 — Beneficiary master-data changes
Test approach: re-perform the review of beneficiary changes for 25 changes.
Result: 3 of 25 changes had no evidence of independent review.
Conclusion: control is operating effectively.

Test 3 — Payment limit configuration
Control: The payment system blocks single payments above the user's authorised limit.
Test approach: inspect the system configuration.
Result: not yet performed.
Conclusion: effective.
"""

# The first version of this "clean" artifact was a thin demo, and the reviewer
# rightly sent back five must-fixes every time: no check that the recertified
# list was complete, no reverse test from HR leavers, no sampling method, no
# evidence references, no look at whether reviewers actually reviewed. It was the
# case that was wrong, not the reviewer. This version answers each of those.
_CLEAN_WORK_PROGRAM = """Work program — User access reviews, core banking system (synthetic)

Period: 1 January – 31 December 2025 (Q1–Q4). Control owner: Head of IT Access Management.
Framework: DORA Art. 9(4)(c) (access to ICT assets); internal Access Management Policy v4.2, §5.

Test 1 — Quarterly access recertification (operating effectiveness)
Control objective: only authorised users retain access to the core banking system.
Control: every quarter each system owner recertifies all user accounts and entitlements, including
privileged, service and generic accounts; accounts marked for removal are disabled within 5 working
days of the recertification sign-off.
Control frequency: quarterly (4 occurrences in the period).

Test approach:
a) Completeness of the population (IPE): for each quarter, reconciled the recertified user list to an
   independent extract of all active accounts taken by IA directly from the identity management system
   on the quarter-end date (extracts WP-UAR-01 to -04). Differences: none.
b) Review quality: for each quarter, inspected the sign-off by every system owner (12 owners), the date
   against the policy deadline, and the share of accounts revoked or changed; inquired with 3 owners and
   re-performed their review for 15 accounts each (WP-UAR-05). No rubber-stamping indicators.
c) Removals: population of 212 removals in the period; all 212 traced to the access log (full population,
   no sampling) for the 5-working-day criterion, measured from recertification sign-off (WP-UAR-06).
d) Reverse test: obtained all 87 leavers and 41 movers from the HR system for the period and verified
   for all 128 that access was removed or changed within the policy timeframe (WP-UAR-07).

Result: (a) complete in all 4 quarters; (b) all 48 sign-offs on time, re-performance agreed;
(c) 212 of 212 removals within 5 working days; (d) 128 of 128 leavers/movers processed in time.
Exceptions: none.
Conclusion (proposed, for review): the control operated effectively throughout the period.
Performed by: J. de Vries, 14 March 2026. Reviewed by: A. Bakker, 18 March 2026.
"""

QA_CASES = (
    QaCase(
        "qa-planted-defects", "Payment Processing Review", "RET", "operational",
        "Work program", _WORK_PROGRAM_WITH_DEFECTS,
        planted=(
            ("Test 1 sample too small for a daily control", ("sample", "5 days", "five days")),
            ("Test 2 concludes 'effective' despite 3 exceptions",
             ("exception", "3 of 25", "contradict", "inconsistent")),
            ("Test 3 concludes before testing", ("not yet performed", "not performed",
                                                 "before", "premature", "no evidence")),
            ("Tests 2 and 3 lack / Test 2 lacks a stated control", ("control objective",
                                                                    "objective", "no control")),
        ),
    ),
    QaCase(
        "qa-clean", "User Access Review", "GRP", "it", "Work program", _CLEAN_WORK_PROGRAM,
        planted=(),
        max_must_fix=1,
    ),
)

# ── RCSA mapping ─────────────────────────────────────────────────────────────
# The shape of the export in tests/rcsa_fixtures.photo_shape, with its bands.
_INH = "Inherent Risk Rating (before controls)"
_RES_CHANGE = "Residual Risk Rating during Change implementation"
_RES_LIVE = "Residual Risk rating when going live (Change to Run)"

RCSA_CASES = (
    RcsaCase(
        "rcsa-photo-shape",
        names=("Risk ID", "(Sub)process", "Risk title", "ORX Risk event level 2",
               "Undesirable event", "ORX Cause level 1 and 2", "Impact categories",
               "Probability for one time events", "Frequency for repeating events",
               "Resulting in", "Impact", "Exposure (inherent)", "Key risk",
               "Inherent Risk Rating Rationale", "Controls in place (existing) Descriptive",
               "Effectiveness Control environment", "Exposure (residual)",
               "Residual Risk Rating Rationale", "Risk Response",
               "Exposure (Mitigated)", "Likelihood", "Impact", "Residual Risk Rating Rationale"),
        bands=("", "", "", "", "", "", "",
               f"{_INH} · Likelihood", f"{_INH} · Likelihood", f"{_INH} · Likelihood",
               _INH, _INH, _INH, _INH, _INH,
               _RES_CHANGE, _RES_CHANGE, _RES_CHANGE, _RES_CHANGE,
               _RES_LIVE, _RES_LIVE, _RES_LIVE, _RES_LIVE),
        samples=(
            ("1", "Analyse Financial Information", "Incorrect information", "Poor data quality",
             "Financial loss and/or reputation damage",
             "Due to having incorrect or not detailed enough investee information",
             "Financial loss, Reputational", "Not applicable", "Monthly", "(4) Likely",
             "(2) Moderate", "High", "Yes", "Lack of data, wrong data could be imported daily",
             "See R48", "(3) Partially effective", "(2) Moderate",
             "Controls reduce the frequency but not the impact", "Mitigate",
             "(1) Minor", "(2) Unlikely", "(1) Minor", "After go-live the daily reconciliation applies"),
            ("3", "Report to investors", "Late reporting", "Process failure", "Regulatory breach",
             "Due to manual consolidation steps", "Regulatory, Reputational", "Yearly",
             "Not applicable", "(2) Unlikely", "(3) Significant", "Medium", "Yes",
             "Deadlines are externally set", "See R12", "(3) Partially effective", "(2) Moderate",
             "Manual steps remain", "Mitigate", "(2) Moderate", "(2) Unlikely", "(3) Significant",
             "Automation planned"),
        ),
        expected={
            0: ("risk_id",), 1: ("process",), 2: ("risk_title",), 4: ("event",),
            5: ("cause",), 6: ("impact_categories",), 9: ("inherent_likelihood",),
            10: ("inherent_impact",), 11: ("inherent_exposure",), 12: ("key_risk",),
            13: ("inherent_rationale",), 14: ("controls",), 15: ("control_effectiveness",),
            16: ("residual_exposure",), 17: ("residual_rationale",), 18: ("risk_response",),
            19: ("residual_exposure",), 20: ("residual_likelihood",), 21: ("residual_impact",),
            22: ("residual_rationale",),
        },
    ),
)


# ── Rating challenge (judge tier) ────────────────────────────────────────────
# The one judge-tier agent with an answer that can be stated in advance: a
# second opinion on a severity rating. Added so the judge tier's move to a new
# model is measured like the draft tier's was, not only smoke-tested.
@dataclass(frozen=True)
class ChallengeCase:
    id: str
    draft: dict
    expect_agrees: bool
    allowed_suggestions: tuple[str, ...]
    needs_review: bool = True


CHALLENGE_CASES = (
    ChallengeCase(
        "challenge-overrated",
        draft={"title": "Second signature missing on expense claims",
               "condition": "2 of 25 sampled expense claims lacked the second approval signature; "
                            "both were below EUR 200.",
               "criteria": "The expense policy requires a second approval on every claim.",
               "effect": "Small unapproved expenses could be reimbursed.",
               "rating": "high",
               "rating_rationale": "Any policy breach is serious."},
        expect_agrees=False,
        allowed_suggestions=("low", "medium"),
    ),
    ChallengeCase(
        "challenge-justified",
        draft={"title": "Sanctions re-screening not performed",
               "condition": "14 of 60 sampled customers had not been re-screened against the "
                            "sanctions list since onboarding in 2021.",
               "criteria": "Sanctions regulation requires ongoing screening of the customer base.",
               "effect": "Customers who became sanctioned after onboarding could keep transacting.",
               "rating": "high",
               "rating_rationale": "Regulatory breach with possible sanctions exposure; 23% of the sample."},
        expect_agrees=True,
        allowed_suggestions=("high",),
    ),
)
