"""The golden set — frozen cases with a known right answer.

Everything before this layer was argued for. Retrieval "reads the passages that
matter"; the contract "stops a cut-off answer looking finished"; the peer review
"reads the file". Those are claims, and a claim about agent quality that nobody
measures decays the moment someone edits a prompt.

So each case here states, in advance, what a competent agent must conclude — and
the graders in graders.py check it without a model being asked for an opinion.

**Two things make these cases worth trusting.**

*The distractors.* Every case buries its answer in a document that also contains
sections about the same subject which do NOT answer the question. A retrieval
layer that scores well only because the filler was about something else has
proved nothing; the question is whether the needle beats its near-misses. Each
case names them, and the grader checks the needle outranks all of them.

*The depth.* The needle sits at a stated position — early, middle or late. The
cases with a late needle are the ones the old head-of-document clip could not
reach at all, and they are kept separate in the scorecard so that improvement is
attributable rather than averaged away.

The prose is synthetic, written for this suite, and says so. It is modelled on
the shape of real policy and framework documents — numbered clauses, a heading
per section, administrative filler between the substance — because that shape is
what the chunker has to cope with. It is not real client material and no claim
about real-world recall is made from it.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Section:
    heading: str
    body: str


@dataclass(frozen=True)
class Case:
    """One frozen retrieval question with a known answer."""
    id: str
    topic: str
    question: str
    #: The sentence that answers it. Must appear verbatim in the built document.
    needle: str
    #: Headings that talk about the same subject without answering the question.
    #: The needle has to outrank all of them or the case fails.
    distractors: tuple[str, ...]
    #: Where the needle sits: "early" (< 4k chars), "mid", "late" (> 20k).
    depth: str
    sections: tuple[Section, ...] = field(default_factory=tuple)
    #: Extra documents in the corpus for this case, to test that the right file
    #: is chosen and not merely the right paragraph.
    extra_documents: tuple[tuple[str, str], ...] = field(default_factory=tuple)


# ── Filler that is plausible, not lorem ipsum ────────────────────────────────
# Retrieval that only works because the filler was obviously irrelevant would
# flatter itself. This reads like the administrative half of a real policy.
_FILLER = [
    ("Document control and version history",
     "This document is maintained by the second line of defence and reviewed annually. "
     "Version changes are recorded in the register held by the policy office. Material "
     "amendments require the approval of the responsible committee before publication. "),
    ("Scope of application",
     "This policy applies to all business units, branches and subsidiaries within the "
     "consolidated group, including staff engaged through third parties where they act on "
     "behalf of the organisation. Local addenda may impose stricter requirements. "),
    ("Roles and responsibilities",
     "The first line owns and operates the controls described in this document. The second "
     "line sets the standard and monitors adherence. Internal Audit provides independent "
     "assurance over the design and operating effectiveness of the framework. "),
    ("Training and awareness",
     "All staff in scope complete annual training. Completion is tracked centrally and "
     "reported quarterly. Staff in specialist roles complete additional modules appropriate "
     "to their responsibilities. "),
    ("Records and retention",
     "Records supporting the operation of controls are retained for the statutory period "
     "and stored in the designated repository. Retention schedules are reviewed annually "
     "against applicable legal requirements. "),
    ("Escalation and exceptions",
     "Departures from this policy require a documented exception, approved at the level "
     "set out in the delegated authority matrix, with an expiry date and a remediation plan. "),
    ("Reporting lines",
     "Periodic reporting is provided to the responsible committee. Reporting includes key "
     "indicators, breaches, open exceptions and the status of remediation activity. "),
    ("Glossary",
     "Terms used in this document carry the meaning given in the group glossary unless "
     "defined otherwise here. Where a term is defined in law, the legal definition prevails. "),
]


def _filler_section(i: int, pad: int = 3) -> Section:
    heading, body = _FILLER[i % len(_FILLER)]
    return Section(f"{heading}", body * pad)


def build_document(case: Case, stuffing: int = 1) -> str:
    """Assemble the case's document, with the needle at its stated depth.

    The section that carries the needle is numbered like any other, so nothing
    about its formatting marks it as the answer.

    `stuffing` controls how hard the near-miss sections try to look like the
    answer — how many times they echo the question's own vocabulary. 1 is what a
    real "background and governance" section does. 4 is keyword stuffing, kept
    as a separate adversarial tier: see ADVERSARIAL_STUFFING.
    """
    before = {"early": 1, "mid": 6, "late": 16}[case.depth]
    after = 6

    parts = [f"{case.topic.upper()}\nInternal policy document — synthetic, written for the "
             f"IA Wingman evaluation suite.\n"]
    n = 1

    # Distractors are spread through the filler, not clustered next to the needle.
    distractor_at = {max(1, before // 2): 0}
    if len(case.distractors) > 1:
        distractor_at[max(2, before - 1)] = 1
    if len(case.distractors) > 2:
        distractor_at[before + 2] = 2

    for i in range(before):
        if i in distractor_at and distractor_at[i] < len(case.distractors):
            d = case.distractors[distractor_at[i]]
            parts.append(f"\n{n}. {d}\n" + _distractor_body(case, d, stuffing))
        else:
            sec = _filler_section(i)
            parts.append(f"\n{n}. {sec.heading}\n{sec.body}")
        n += 1

    for sec in case.sections:
        parts.append(f"\n{n}. {sec.heading}\n{sec.body}")
        n += 1

    for i in range(after):
        idx = before + i
        if idx in distractor_at and distractor_at[idx] < len(case.distractors):
            d = case.distractors[distractor_at[idx]]
            parts.append(f"\n{n}. {d}\n" + _distractor_body(case, d, stuffing))
        else:
            sec = _filler_section(idx)
            parts.append(f"\n{n}. {sec.heading}\n{sec.body}")
        n += 1

    return "".join(parts)


#: How many times the adversarial tier echoes the question's vocabulary. At this
#: level the near-miss contains the query's rare terms four or five times over
#: while the operative clause states each once — and no purely lexical ranker
#: survives that, by construction. The tier is kept and reported rather than
#: deleted, because it is the honest statement of where BM25 ends and where an
#: embedding layer would have to begin.
ADVERSARIAL_STUFFING = 4


def _distractor_body(case: Case, heading: str, stuffing: int = 1) -> str:
    """A near-miss: the right subject, no operative answer.

    It shares the question's vocabulary — a distractor that shares no terms with
    the query is not a distractor at all — but at stuffing=1 it mentions the
    topic the way a real background section does: once, in passing, before
    sending the reader elsewhere.
    """
    words = [w for w in case.question.replace("?", "").split() if len(w) > 4][:4]
    echo = " ".join(words).lower()
    opener = (
        f"This section provides background on {echo} and explains which committee owns the "
        f"topic. It does not state the operative requirement; for that, see the relevant "
        f"clause of this document. "
    )
    filler = (
        "The subject has been part of the framework since the last major revision, and the "
        "owning committee reviews the surrounding arrangements annually as part of the "
        "standard governance cycle. Historical context, prior decisions and the rationale "
        "for the current allocation of responsibilities are recorded in the committee "
        "minutes rather than reproduced here. "
    )
    return opener * stuffing + filler * 3


# ── The cases ────────────────────────────────────────────────────────────────
CASES: tuple[Case, ...] = (
    Case(
        id="cdd-ubo-late",
        topic="Customer Acceptance Policy",
        question="Must beneficial ownership be verified before onboarding a legal entity?",
        needle=("Beneficial ownership must be identified and verified before the business "
                "relationship is established, and the UBO register extract retained on file."),
        distractors=("Beneficial ownership — background and governance",
                     "Customer onboarding — historical context"),
        depth="late",
        sections=(Section(
            "Beneficial ownership verification",
            "Beneficial ownership must be identified and verified before the business "
            "relationship is established, and the UBO register extract retained on file. "
            "Where the ownership structure is opaque, enhanced due diligence applies and the "
            "file is escalated to the compliance officer. "),),
    ),
    Case(
        id="cdd-edd-trigger-mid",
        topic="Customer Due Diligence Standard",
        question="What triggers enhanced due diligence on a customer?",
        needle=("Enhanced due diligence is triggered where the customer is a politically "
                "exposed person, is established in a high-risk third country, or where the "
                "risk score exceeds the defined threshold."),
        distractors=("Enhanced due diligence — scope and ownership",),
        depth="mid",
        sections=(Section(
            "Triggers for enhanced due diligence",
            "Enhanced due diligence is triggered where the customer is a politically "
            "exposed person, is established in a high-risk third country, or where the "
            "risk score exceeds the defined threshold. The outcome is documented in the "
            "customer file and reviewed by a second reviewer. "),),
    ),
    Case(
        id="cdd-rescreen-late",
        topic="Ongoing Monitoring Policy",
        question="How often are existing customers re-screened after onboarding?",
        needle=("Existing customers are re-screened against sanctions and PEP lists at least "
                "every twelve months, and immediately on a material change of circumstances."),
        distractors=("Ongoing monitoring — principles", "Screening — systems and tooling"),
        depth="late",
        sections=(Section(
            "Periodic re-screening",
            "Existing customers are re-screened against sanctions and PEP lists at least "
            "every twelve months, and immediately on a material change of circumstances. "
            "High-risk relationships are re-screened every six months. "),),
    ),
    Case(
        id="dora-exit-late",
        topic="Outsourcing and Third-Party Risk Policy",
        question="What must an outsourcing contract contain about exit and termination?",
        needle=("Every outsourcing contract covering a critical or important function must "
                "include a documented exit strategy, transition assistance obligations and "
                "the provider's duty to return or delete data on termination."),
        distractors=("Outsourcing contracts — governance and approval",
                     "Termination — commercial considerations"),
        depth="late",
        sections=(Section(
            "Exit strategies and termination rights",
            "Every outsourcing contract covering a critical or important function must "
            "include a documented exit strategy, transition assistance obligations and "
            "the provider's duty to return or delete data on termination. Exit plans are "
            "tested at least once every three years. "),),
    ),
    Case(
        id="dora-incident-mid",
        topic="ICT Incident Management Standard",
        question="Within what time must a major ICT incident be reported to the supervisor?",
        needle=("A major ICT-related incident must be reported to the competent authority "
                "using the initial notification within four hours of classification, and in "
                "any event within twenty-four hours of detection."),
        distractors=("Incident management — roles and committees",),
        depth="mid",
        sections=(Section(
            "Regulatory notification timelines",
            "A major ICT-related incident must be reported to the competent authority "
            "using the initial notification within four hours of classification, and in "
            "any event within twenty-four hours of detection. Intermediate and final "
            "reports follow the prescribed schedule. "),),
    ),
    Case(
        id="esg-scenario-late",
        topic="ESG Risk Framework",
        question="Are climate scenarios translated into financial impact in the ICAAP?",
        needle=("Climate scenarios are translated into quantified financial impact and "
                "integrated into the ICAAP, covering at minimum a disorderly transition and "
                "a hot-house world pathway."),
        distractors=("Climate risk — strategy and ambition", "Scenario analysis — methodology owners"),
        depth="late",
        sections=(Section(
            "Integration into ICAAP and stress testing",
            "Climate scenarios are translated into quantified financial impact and "
            "integrated into the ICAAP, covering at minimum a disorderly transition and "
            "a hot-house world pathway. Results inform the capital planning cycle. "),),
    ),
    Case(
        id="esg-appetite-mid",
        topic="Risk Appetite Statement",
        question="Is ESG risk anchored in the risk appetite statement with indicators?",
        needle=("ESG risk is anchored in the Risk Appetite Statement through quantified "
                "indicators with defined thresholds, monitored quarterly and reported to the "
                "Board Risk Committee."),
        distractors=("Risk appetite — purpose and scope",),
        depth="mid",
        sections=(Section(
            "ESG risk appetite indicators",
            "ESG risk is anchored in the Risk Appetite Statement through quantified "
            "indicators with defined thresholds, monitored quarterly and reported to the "
            "Board Risk Committee. Breaches follow the standard escalation route. "),),
    ),
    Case(
        id="model-validation-late",
        topic="Model Risk Management Policy",
        question="Who performs independent validation of a high-materiality model?",
        needle=("Independent validation of high-materiality models is performed by the Model "
                "Validation function, which reports to the CRO and is organisationally "
                "separate from model development and ownership."),
        distractors=("Model governance — committee structure", "Model development — standards"),
        depth="late",
        sections=(Section(
            "Independent validation",
            "Independent validation of high-materiality models is performed by the Model "
            "Validation function, which reports to the CRO and is organisationally "
            "separate from model development and ownership. Validation precedes "
            "production use and is repeated annually. "),),
    ),
    Case(
        id="itsec-access-mid",
        topic="Access Control Standard",
        question="How often are privileged access rights recertified?",
        needle=("Privileged access rights are recertified by the system owner at least "
                "quarterly, and revoked within one business day of a leaver being notified."),
        distractors=("Access control — principles and ownership",),
        depth="mid",
        sections=(Section(
            "Recertification of privileged access",
            "Privileged access rights are recertified by the system owner at least "
            "quarterly, and revoked within one business day of a leaver being notified. "
            "Evidence of each recertification is retained. "),),
    ),
    Case(
        id="itsec-segregation-early",
        topic="Payments Control Standard",
        question="Is segregation of duties required between payment initiation and approval?",
        needle=("No individual may both initiate and approve a payment; the system enforces "
                "segregation of duties and blocks any attempt to do so."),
        distractors=("Segregation of duties — general principles",),
        depth="early",
        sections=(Section(
            "Segregation of duties in the payment process",
            "No individual may both initiate and approve a payment; the system enforces "
            "segregation of duties and blocks any attempt to do so. Exceptions require "
            "dual approval by the finance director and the CRO. "),),
    ),
    Case(
        id="cass-reconciliation-late",
        topic="Client Asset Protection Policy",
        question="How frequently are client money reconciliations performed?",
        needle=("Internal client money reconciliations are performed on each business day, "
                "and external reconciliations against the bank statement at least weekly, "
                "with any shortfall funded the same day."),
        distractors=("Client assets — governance and oversight", "Reconciliations — tooling"),
        depth="late",
        sections=(Section(
            "Reconciliation frequency and shortfalls",
            "Internal client money reconciliations are performed on each business day, "
            "and external reconciliations against the bank statement at least weekly, "
            "with any shortfall funded the same day. "),),
    ),
    Case(
        id="gdpr-lawfulbasis-mid",
        topic="Data Protection Standard",
        question="What is the lawful basis for processing personal data for CDD purposes?",
        needle=("Personal data processed for customer due diligence is processed on the basis "
                "of compliance with a legal obligation, and is not reused for marketing."),
        distractors=("Data protection — principles", "Lawful bases — overview"),
        depth="mid",
        sections=(Section(
            "Lawful basis for due-diligence processing",
            "Personal data processed for customer due diligence is processed on the basis "
            "of compliance with a legal obligation, and is not reused for marketing. "
            "Retention follows the statutory period. "),),
        # A second document on an adjacent topic, so the case also tests whether
        # the right FILE is chosen and not merely the right paragraph.
        extra_documents=(
            ("Marketing Consent Procedure.docx",
             "MARKETING CONSENT PROCEDURE\n1. Purpose\nThis procedure governs consent for "
             "marketing communications, the lawful basis for which is consent freely given "
             "by the data subject and withdrawable at any time. Personal data processed for "
             "marketing may not be combined with due-diligence records. " * 12),
        ),
    ),
)


def corpus_for(case: Case, stuffing: int = 1) -> list[tuple[str, str, str]]:
    """The (doc_id, label, text) triples one case is retrieved over."""
    docs = [(f"{case.id}-main", f"{case.topic}.pdf", build_document(case, stuffing))]
    docs += [(f"{case.id}-extra-{i}", label, text)
             for i, (label, text) in enumerate(case.extra_documents)]
    return docs
