"""The shapes agents have to return.

One module rather than a model next to each agent, because the point of a
contract is that it can be read in one place — and because these schemas are
what the JSON-in-prose prompts were describing all along, only now they are
enforced instead of hoped for.

Each field carries a description. Those descriptions reach the model as part of
the tool schema, which means the instruction and the validation are the same
text: they cannot drift apart the way a prompt and a `.get()` call always did.
"""
from typing import Literal

from pydantic import BaseModel, Field

Rating = Literal["high", "medium", "low"]
Confidence = Literal["high", "medium", "low"]


# ── Governance assessor ──────────────────────────────────────────────────────
class ProposedRisk(BaseModel):
    """A gap, phrased as the risk it creates. These become rows in the risk
    matrix, so the shape has to hold: a proposal with no title was previously
    dropped in silence at the write step."""
    title: str = Field(..., min_length=3, description="Short risk title")
    description: str | None = Field(None, description="What is not adequately governed, and the consequence")
    category: str | None = Field(None, description="e.g. AML, Governance, Conduct")
    inherent_rating: Rating = Field("medium", description="Inherent risk of the gap")


class CoverageItem(BaseModel):
    requirement: str = Field(..., description="The specific requirement in plain language")
    coverage: Literal["covered", "partial", "gap"]
    evidence: str = Field(
        ...,
        description=(
            "What covers it, citing the passage id [P#] you relied on or naming the control. "
            "If it is not visible in the passages you were given, say that rather than calling it absent."
        ),
    )
    confidence: Confidence = "medium"
    framework_ref: str | None = Field(None, description="e.g. AMLD-Art.13")
    framework_name: str | None = None
    proposed_risk: ProposedRisk | None = Field(
        None, description="Required when coverage is partial or gap; omit when covered"
    )


class GovernanceAssessment(BaseModel):
    """The coverage items for the requirements put to one call.

    It used to carry a `summary` as well, and the model left it out on every run:
    asked for "one item per applicable requirement", it returned exactly that, and
    each run paid for a correction round over a field it had not been asked for in
    the prose. The panel does show a summary, so it is composed from these items
    instead — which is also the only honest place for it now that the assessment
    is made one framework at a time. No single call sees the whole picture any
    more, and a summary written by one that only saw a tenth of it would read like
    an overall judgement without being one.
    """
    #: Capped at eight as a backstop, not as the instruction: the prompt asks for
    #: the requirements that carry the risk, usually two to five. Given one
    #: framework and nothing else to weigh it against, the model enumerated every
    #: expectation in the document — ten frameworks came back as 101 requirements
    #: and 98 proposed risks, which is not a matrix an auditor can work through. A
    #: run that exceeds the cap fails loudly rather than filling the spine.
    items: list[CoverageItem] = Field(
        ..., min_length=1, max_length=6,
        description="One item per requirement of the framework given that bears on this audit")


# ── Finding drafter ──────────────────────────────────────────────────────────
class FindingDraft(BaseModel):
    """The 5 C's. Every field is required: a finding missing its criteria is not
    a finding, and returning one with a None in it was how the auditor's own
    typed text used to get overwritten with nothing."""
    title: str = Field(..., min_length=3, description="Concise finding title")
    condition: str = Field(..., description="What was actually found")
    criteria: str = Field(..., description="The norm, standard or regulation it should meet")
    cause: str = Field(..., description="The root cause, not a symptom")
    effect: str = Field(..., description="The consequence or risk if unaddressed")
    recommendation: str = Field(..., description="A concrete, feasible corrective action")
    rating: Rating
    rating_rationale: str = Field(..., description="One line justifying the rating")


class RatingChallenge(BaseModel):
    """The second opinion. `agrees` is a boolean and not a sentence, so the
    platform can count disagreements instead of parsing prose for them."""
    agrees: bool = Field(..., description="Whether you agree with the proposed rating")
    suggested_rating: Rating = Field(..., description="Your own rating — repeat the proposed one if you agree")
    rationale: str = Field(..., description="One line: your second opinion and why")


# ── AI peer review (GIAS) ────────────────────────────────────────────────────
class PeerCriterion(BaseModel):
    nr: int = Field(..., ge=1, description="The criterion number being rated")
    rating: Literal["gc", "pc", "nc", "na"] = Field(
        ...,
        description=(
            "gc = generally compliant, pc = partially, nc = not compliant or not evidenced, "
            "na = not assessable from this platform (only where the criterion is marked as such)"
        ),
    )
    comment: str = Field(..., description="Specific and actionable")
    evidence: str = Field(
        ...,
        description="The specific thing in that criterion's evidence block that drove the rating, or 'not evidenced'",
    )


class PeerReview(BaseModel):
    summary: str = Field(
        ...,
        description="3-4 sentences: strengths, learnings and improvement areas, grounded in what you read",
    )
    criteria: list[PeerCriterion] = Field(..., description="One entry per criterion number given")


# ── Work program ─────────────────────────────────────────────────────────────
class EvidenceNeed(BaseModel):
    """What one work program row needs from the auditee.

    `kind` decides whether it can become a document request at all: an
    interview is arranged and an observation is scheduled, so neither belongs
    on a document request list. That distinction used to live only in a prompt
    rule, where a model could quietly drop it.
    """
    title: str = Field(..., min_length=3,
                       description="The document, extract or file, named as the auditee would recognise it")
    kind: Literal["document", "data", "interview", "observation"] = Field(
        "document", description="document/data can be requested; interview/observation are arranged")
    requested_from: str | None = Field(
        None, description="The department that holds it — one that exists, not an invented function")
    period: str | None = Field(None, description="The population or period needed, if any")


class WorkProgramRow(BaseModel):
    """One row: an objective, the risk under it, the control, and how it is tested."""
    process: str = Field(..., min_length=2, description="Name of the process")
    activity: str = Field("", description="Specific activity or sub-process")
    risk_description: str = Field(..., min_length=3,
                                  description="What could go wrong — a specific risk statement, not 'there is a risk'")
    control_objective: str = Field(..., min_length=3,
                                   description="Verify that [subject] [action] [standard]")
    test_steps: list[str] = Field(
        ..., min_length=1,
        description="3-4 short imperative steps: obtain population, sample, inspect, conclude")
    priority: Rating = Field("medium", description="Reflects the residual risk")
    responsibility: str = Field("IA team", description="Always 'IA team'; auditors fill in names themselves")
    answers: list[str] = Field(
        default_factory=list,
        description=("The refs from KEY AUDIT QUESTIONS this row helps answer, usually one and "
                     "sometimes none. Do not stretch a row to cover a question it does not test"))
    evidence: list[EvidenceNeed] = Field(
        default_factory=list,
        description="1-2 items for the row as a whole, not per step — its steps share their documents")


class WorkProgram(BaseModel):
    """The rows. Nothing else: the surrounding prose was never read by anything."""
    rows: list[WorkProgramRow] = Field(..., min_length=1,
                                       description="8-14 rows, one per significant control point")


# ── Regulatory query generator ───────────────────────────────────────────────
class SearchQuery(BaseModel):
    """One search string, and the angle it covers."""
    query_text: str = Field(..., min_length=3, max_length=200,
                            description="At most 12 words. Use the exact regulatory name, "
                                        "e.g. 'WWFT Art 3' rather than 'Dutch AML law'")
    angle: Literal["legislation", "supervisory", "developments", "enforcement",
                   "guidance", "keyword"] = Field(
        ..., description="Which angle this query covers; one query per angle")
    primary_domain: str = Field(..., description="One of the available domains listed in the prompt")
    description: str = Field("", max_length=300,
                             description="Why this query matters for this audit")


class SearchQueries(BaseModel):
    """The queries. Asked for as a bare JSON array before, which is the form the
    model was most likely to wrap in a markdown fence — it did so on 4 of 4
    measured calls, against a prompt that forbade markdown in those words."""
    queries: list[SearchQuery] = Field(..., min_length=1, max_length=7)


# ── Document Request List ────────────────────────────────────────────────────
class DRLItem(BaseModel):
    """One request: a document to ask the auditee for, and what it settles."""
    document: str = Field(..., min_length=3, description="Name of the document or data extract")
    description: str = Field("", description="What it contains and why this audit needs it")
    regulatory_basis: str | None = Field(
        None, description="Article, provision or internal policy reason, if there is one")
    requested_from: str = Field(
        ..., min_length=2,
        description="Who owns it — a department that exists, not 'auditee'")
    category: Literal["Policy", "Procedure", "Report", "Data", "Evidence", "Contract"] = Field(
        ..., description="Ordered later as Policies, Procedures, Reports/Data, Evidence")
    covers: list[str] = Field(
        default_factory=list,
        description=("The refs from EVIDENCE THE TESTS NEED that this request settles. Merge "
                     "freely — one request may cover several needs, and that merging is the "
                     "point of the list. Every listed ref belongs in exactly one request"))


class DocumentRequestList(BaseModel):
    """The requests. `id` and `status` are set after the call: the first is
    positional and the second has one allowed value, so neither is worth asking
    a model for."""
    items: list[DRLItem] = Field(..., min_length=1, max_length=20,
                                 description="10-20 requests")


# ── Frameworks, requirements and what they contribute to scope ───────────────
#: Where an obligation applies. `International` covers the standard-setters that
#: are neither national nor EU law — FATF, Basel — which the frameworks prompt
#: has always allowed and the guidance prompt listed without.
Jurisdiction = Literal["NL", "UK", "BE", "ES", "EU", "International"]


class FrameworkItem(BaseModel):
    """One law or regulation, at the level of a specific provision."""
    framework_code: str = Field(..., min_length=2, max_length=50, description="Short code")
    framework_name: str = Field(..., min_length=3,
                                description="Full regulation name plus article where specific, "
                                            "e.g. 'Wft Art. 4:17'")
    specific_provision: str | None = Field(
        None, description="Art. X — one line on what this provision requires. "
                          "A specific provision, not just the name of the law")
    what_it_requires: str = Field("", description="2-3 sentences in plain audit language")
    jurisdiction: Jurisdiction = Field(..., description="The country or bloc it applies to")
    source_url: str | None = Field(None, description="Official URL, if there is one")
    confidence: Confidence = Field("medium",
                                   description="high = core legal obligation directly applicable; "
                                               "medium = likely applicable; low = worth considering")
    is_primary: bool = Field(False, description="True for the 1-2 central laws framing this audit")


class Frameworks(BaseModel):
    """The applicable laws. 4-8, the most relevant for this specific audit."""
    frameworks: list[FrameworkItem] = Field(..., min_length=1, max_length=8)


class RequirementItem(BaseModel):
    """One testable control requirement, tied back to the framework it comes from."""
    framework_ref: str = Field(
        ..., min_length=2, max_length=8,
        description=("Exactly one of the F1, F2 … tags listed in the prompt, copied verbatim. "
                     "A ref that does not match one is dropped, because a requirement whose "
                     "framework cannot be identified cannot be shown under it"))
    provision: str = Field(..., min_length=2, description="e.g. 'Art. 3 WWFT'")
    what_it_requires: str = Field("", description="2 sentences: what the regulation obliges")
    control_objective: str = Field(..., min_length=5,
                                   description="Verify that [subject] [action] [standard per provision] — "
                                               "testable and specific")
    test_approach: str = Field(
        ..., min_length=3,
        description="Walkthrough, Document inspection, Sample testing (n=X), Inquiry, "
                    "Re-performance, Observation, or a combination")
    is_included: bool = Field(True, description="False for lower-priority or out-of-scope items")


class Requirements(BaseModel):
    """5-12 requirements — one per significant provision, not one per framework."""
    requirements: list[RequirementItem] = Field(..., min_length=1, max_length=12)


class ScopeItemProposal(BaseModel):
    item_type: Literal["in_scope", "out_of_scope"]
    description: str = Field(..., min_length=3, description="Concise scope item")
    rationale: str = Field("", description="Regulatory basis, e.g. 'Art. 3 WWFT — identification obligation'")


class KeyQuestionProposal(BaseModel):
    question_text: str = Field(..., min_length=5,
                               description="Derived from a framework obligation, audit-ready")
    regulatory_basis: str = Field("", description="The specific provision it rests on")


class ScopeContribution(BaseModel):
    """What the frameworks contribute to Scope & Objectives."""
    scope_items: list[ScopeItemProposal] = Field(
        ..., min_length=1, description="3-5 in_scope items and 1-2 clearly excluded ones")
    key_questions: list[KeyQuestionProposal] = Field(
        ..., min_length=1, description="4-6 questions, each referencing a provision")


# ── Supervisory guidance ─────────────────────────────────────────────────────
class GuidanceItem(BaseModel):
    """One named supervisory publication — soft law, never statute."""
    guidance_code: str = Field(..., min_length=2, max_length=50, description="Short code")
    guidance_name: str = Field(..., min_length=3,
                               description="Exact publication title, e.g. 'EBA Guidelines on "
                                           "ML/TF risk factors (EBA/GL/2021/02)'")
    issuer: str = Field(..., min_length=2, description="DNB / AFM / EBA / FCA / ECB / …")
    guidance_type: Literal["Guideline", "Policy rule", "Good practice", "Thematic review",
                           "Q&A", "Supervisory letter", "Circular"]
    what_it_says: str = Field("", description="2-3 sentences on what it expects, in plain audit language")
    jurisdiction: Jurisdiction
    source_url: str | None = Field(None, description="Official URL of the publication, if there is one")
    confidence: Confidence = Field("medium",
                                   description="high = directly on point and current; "
                                               "medium = likely relevant; low = worth considering")
    is_primary: bool = Field(False, description="True for the 1-2 most central to this audit")


class SupervisoryGuidance(BaseModel):
    """3-8 publications. Primary legislation belongs to Frameworks, not here."""
    guidance: list[GuidanceItem] = Field(..., min_length=1, max_length=8)


# ── RCSA column mapping ──────────────────────────────────────────────────────
class ColumnProposal(BaseModel):
    """What one column of an RCSA export appears to be."""
    column: str = Field(..., min_length=1,
                        description="The column's name exactly as it appears in the header")
    target: str | None = Field(
        None,
        description=("The field this column holds, from the list of target fields given in the "
                     "prompt — or null when none of them fits. Null is a real answer: a column "
                     "matched to the wrong field is worse than one left unmapped, because the "
                     "mistake becomes invisible once the rows are stored"))
    band: str | None = Field(
        None,
        description=("The header band this column sits under, when there is one — e.g. "
                     "'Inherent Risk Rating (before controls)' or 'Residual Risk rating when "
                     "going live'. Required whenever a target field exists once per band, "
                     "because an export can carry two residual ratings and they are not "
                     "interchangeable"))
    confidence: Confidence = Field("medium", description="How sure you are of this column's field")
    why: str = Field("", max_length=200,
                     description="One short line: what in the name or the sample values decided it")


class RcsaMappingProposal(BaseModel):
    """One proposal per column, in the order the columns appear.

    Every column is answered for, including the ones that map to nothing — the
    person confirming the template has to see the whole sheet, not the part the
    model recognised.
    """
    columns: list[ColumnProposal] = Field(..., min_length=1, max_length=120)
    notes: str = Field("", max_length=400,
                       description="Anything about the sheet the person confirming should know, "
                                   "such as two bands of the same ratings or a column that looks "
                                   "like a cross-reference to another sheet")


# ── Topic Intelligence lenses ────────────────────────────────────────────────
# These were the last answers on the platform still asked for as "JSON in prose".
# Measured in the phase-0 baseline: three of twelve lens runs came back with the
# summary's bullet lines turned into keys of the object, or as a bare list of
# sources, and the summary was lost — the failure behind lens summaries going
# missing in real scans. A schema makes that shape impossible to return.
class LensSource(BaseModel):
    title: str = Field(..., description="Full name of the regulation, document, action or article")
    url: str | None = Field(None, description="Official URL, or null — never an invented one")
    date: str | None = Field(None, description="Year or date, or null")
    confidence: Confidence | None = Field(None, description="How directly this source applies")
    type: Literal["built_in_knowledge", "search_result"] | None = Field(
        None, description="Whether this came from a live search or from built-in knowledge")


_LENS_SUMMARY = ("ONE string: a short lead sentence, then 4-6 lines that each start with '- ', "
                 "separated by newlines. Every bullet belongs inside this one string.")


class LensSynthesis(BaseModel):
    """Lens 1 (normative & regulatory) and lens 2 (supervisory & enforcement)."""
    summary: str = Field(..., min_length=200, description=_LENS_SUMMARY)
    sources: list[LensSource] = Field(
        default_factory=list,
        description="The sources the summary rests on: search results when you searched, and "
                    "otherwise the laws, guidance and publications you drew on from your own "
                    "knowledge, typed 'built_in_knowledge'. Empty only if the summary cites nothing.")


class SocietyLensSynthesis(LensSynthesis):
    """Lens 3 (society, trends & incidents) — the same, plus what it means for this audit."""
    materiality_signal: str = Field(
        "", description="Exactly one sentence: what the external landscape means for the urgency "
                        "or scope of THIS audit")


# ── Topic Intelligence: the verification round ──────────────────────────────
class VerificationCheck(BaseModel):
    claim: str = Field(..., min_length=10, description="The statement checked, in one sentence, as the summaries make it")
    verdict: Literal["confirmed", "corrected", "not_found"] = Field(
        ..., description="confirmed: an official source says the same. corrected: an official source says "
                         "something different. not_found: the searches did not settle it")
    finding: str = Field(..., min_length=10, description="What the official source says, one or two sentences; for "
                                                         "not_found, what was looked for and not found")
    source_url: str | None = Field(None, description="The official page the finding rests on, or null")


class VerificationResult(BaseModel):
    checks: list[VerificationCheck] = Field(default_factory=list, max_length=5,
                                            description="At most 5; empty when nothing needs checking")


# ── Topic Intelligence: the plain-language primer ────────────────────────────
# Free text with a 500-token ceiling cut the primer off mid-sentence ("It also
# requires A") and nothing noticed. Typed, the reply is either complete or an
# error: a truncated answer raises instead of being stored.
class TopicPrimer(BaseModel):
    lead: str = Field(..., min_length=20, description="One short sentence defining the topic, at most 280 characters")
    in_practice: str = Field(..., description="What the topic means in practice and what an auditor typically looks at, "
                                              "two sentences at most")
    why_it_matters: str = Field(..., description="Why it matters for a financial organisation, two sentences at most")
    rules: str = Field(..., description="Which rules and regulators govern it in the jurisdictions in scope, with the "
                                        "date from which each applies only if the research gives one; say where the "
                                        "research calls something unconfirmed. Three sentences at most")
    what_surfaces: str = Field(..., description="What commonly surfaces when this topic is researched in those "
                                                "jurisdictions, two sentences at most")


# ── QA review ────────────────────────────────────────────────────────────────
# Moved off "JSON in prose" after the phase-0 evals: every QA review came back in
# a markdown fence the platform had to cut away before it could read it.
class QaComment(BaseModel):
    section: str = Field(..., description="Which part of the artifact the comment is about")
    severity: Literal["must_fix", "suggestion"] = Field(
        ..., description="must_fix only where the conclusion could be wrong or indefensible unless "
                         "this is addressed; suggestion for everything that would improve a sound artifact")
    comment: str = Field(..., min_length=10, description="Specific and actionable")


class QaReview(BaseModel):
    overall_quality: Literal["good", "adequate", "needs_work"] = Field(
        ..., description="'good' when there is no must_fix")
    summary: str = Field(..., description="Two or three sentences for the auditor")
    comments: list[QaComment] = Field(default_factory=list, max_length=10,
                                      description="Empty when there is nothing worth saying")
