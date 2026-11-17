"""One name per agent, and one place that knows it.

An agent's identity was spread across five layers, each with its own wording.
Data analysis was called `Data analysis` in the lifecycle graph, `data_analysis`
in its service, `Data Analysis` in the Agent Studio and `Data-Analysis / Anomaly
agent` in its own panel — and nothing at all in the activity log, which showed
the raw key to the auditor.

That log is where it stopped being cosmetic. It is the provenance trail: the
record of how an AI-assisted conclusion was reached. It knew five agent keys out
of the nine actually written to it, and four of its seven verbs were missing, so
"the finding drafter prepared a finding" was rendered as "finding_drafter ran".
The trail told the wrong story about what happened.

So: one registry, and every other layer reads from it.

**It is derived, not maintained in parallel.** The keys, labels, routes and gates
come from `orchestrator.STAGE_GRAPH` and `workflow_service.COMPANIONS`; this
module adds only what those cannot express — how an agent presents itself. A
stage added to the graph without an entry here fails `tests/test_agent_registry`
rather than quietly appearing as a blank row.

**Three kinds, because "agent" was doing three jobs.** The lifecycle called
Fieldwork's `Observations` an agent, and Resource Planning a `Resource planner`,
and the coverage check a `Consistency sweep` — one of those is a human typing,
one is a form, and one is a computed view with nothing to run. Mixing them under
one word is what made the roster feel arbitrary:

* `agent`     — an AI proposes something a human decides on.
* `engine`    — a deterministic computation. No model, no judgement, no cost.
* `your step` — you do it. The platform holds the result; it does not produce it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.orchestrator import STAGE_GRAPH
from services.workflow_service import COMPANIONS, PHASE_OF, STAGE_INFO

AGENT = "agent"
ENGINE = "engine"
HUMAN = "your step"


@dataclass(frozen=True)
class Agent:
    """How one agent presents itself, everywhere."""
    key: str
    name: str            # the one name, in every surface
    kind: str            # agent | engine | your step
    icon: str            # a lucide icon name; the frontend maps it explicitly
    reads: str           # what it takes in
    produces: str        # what it hands back
    you_decide: str      # what stays with the auditor
    tier: str = "draft"  # quick | draft | judge | none
    # The agent that serves this step. Defaults to the step's own key, so a step
    # with nobody else to share with is its own agent. Several steps naming the
    # same id are served by one prompt, one schema and one service — which is
    # what "fewer agents" means: fewer things to maintain, not fewer steps in an
    # audit.
    agent_id: str = ""
    # Every other string this agent has been known by: AGENT_TYPE constants,
    # activity-log keys, schema names. This is what lets the log stop printing
    # snake_case at people.
    aliases: tuple[str, ...] = ()
    # Filled in from the lifecycle graph — never typed twice.
    label: str = ""
    phase: str = ""
    route: str = ""
    base: str = ""
    description: str = ""
    companion: bool = False
    gates: tuple[str, ...] = field(default_factory=tuple)


# ── Which steps share an agent ───────────────────────────────────────────────
# Read it as: this step is served by that agent. A step absent from this map is
# its own agent.
#
# Each merge is here because two steps were doing one job with two prompts:
#
#   supervisory_guidance  guidance is a SOURCE TYPE on a requirement, and the
#                         scout's own decision line said so: "what you take into
#                         the framework list" — output that only matters as
#                         another agent's input.
#   interview_companion   the same job at two moments: the questions before the
#                         interview, the follow-ups and minutes during it.
#   kickoff               both write to the auditee out of the engagement record.
#                         The template is a parameter, not an agent.
#   vendor_guard          identical operation on a different corpus: assess
#                         documents against a framework set, propose the gaps as
#                         risks. Vendor is a preset — which also retires its own
#                         second, parallel framework list.
_SERVED_BY: dict[str, str] = {
    "supervisory_guidance": "frameworks",
    "interview_companion": "interviews",
    "interview_guide": "interviews",
    "kickoff": "auditee_comms",
    "anl": "auditee_comms",
    "racm_governance": "framework_assessment",
    "vendor_guard": "framework_assessment",

    # The work program and the matrix produced the same four columns into two
    # stores with nothing between them. Of nine engagements holding either, two
    # held both; four built a matrix and never signed, three signed with an
    # empty matrix. The work program is now a projection of the spine, so one
    # agent generates it.
    "work_program": "spine",
    "racm_scoping": "spine",
}

# What a merged agent is called where it is named as an agent rather than as a
# step. A step that is its own agent reuses its own name.
_AGENT_NAMES: dict[str, str] = {
    "interviews": "Interviews",
    "auditee_comms": "Auditee communications",
    "framework_assessment": "Framework assessment",
    "spine": "Spine",
}


# ── What the graph cannot say ────────────────────────────────────────────────
_PRESENTATION: dict[str, dict] = {
    "topic_intelligence": dict(
        name="Topic Intelligence", kind=AGENT, icon="Radar",
        reads="regulation, supervisory publications, public signals and your uploaded documents",
        produces="a memo on the topic and the key risk areas it suggests scoping",
        you_decide="whether you agree with the memo before anything is built on it",
    ),
    "frameworks": dict(
        name="Frameworks & Requirements", kind=AGENT, icon="Scale",
        reads="the topic memo and the jurisdictions in play",
        produces="the applicable laws and guidance, and the testable requirement behind each",
        you_decide="which frameworks actually apply to this audit",
    ),
    "process_understanding": dict(
        name="Process Understanding", kind=AGENT, icon="Network",
        reads="uploaded process documentation and the audit's own subject",
        produces="a walkthrough of the in-scope processes and preliminary observations",
        you_decide="which processes belong in scope",
    ),
    "scope": dict(
        name="Scope & Objectives", kind=AGENT, icon="Target",
        reads="the topic memo and the applicable requirements",
        produces="proposed in-scope and out-of-scope areas, and the key audit questions",
        you_decide="every scope item and every key audit question",
    ),
    "bra": dict(
        name="Background Risk Assessment", kind=AGENT, icon="AlertTriangle",
        reads="the scope, the frameworks, and what prior audits found on this topic",
        produces="the risk assessment sections and a proposed risk register",
        you_decide="which risks you accept into the assessment",
    ),
    "anl": dict(
        name="Audit Notification Letter", kind=AGENT, icon="Mail",
        reads="the scope, the objectives and the planned timing",
        produces="the letter to the auditee, with an AI review of it before sign-off",
        you_decide="the wording, and the Head of IA approves it",
    ),
    "kickoff": dict(
        name="Kick-off", kind=AGENT, icon="Users",
        reads="the scope and the engagement's context",
        produces="the kick-off agenda and the questions worth asking",
        you_decide="what is actually discussed in the meeting",
    ),
    "resource_plan": dict(
        name="Resource Planning", kind=HUMAN, icon="CalendarDays", tier="none",
        reads="nothing — this one is yours",
        produces="the confirmed dates, hours and team",
        you_decide="all of it",
    ),
    "interview_guide": dict(
        name="Interview Guide", kind=AGENT, icon="MessagesSquare",
        reads="the scope, the risks and the requirements",
        produces="persona-based interview guides, each question traceable to a risk",
        you_decide="which questions you actually ask",
    ),
    "work_program": dict(
        name="Work Program", kind=AGENT, icon="ListChecks",
        reads="the scope, the accepted risks, the requirements and prior audits",
        produces="the test program: process, risk, control objective and test steps",
        you_decide="you sign it off — and that is what unlocks fieldwork",
    ),
    "drl": dict(
        name="Document Request List", kind=AGENT, icon="FileText",
        reads="the evidence your tests say they need, plus the scope and the frameworks",
        produces="one request per document, saying which of those needs it settles",
        you_decide="what you actually ask for",
    ),
    "interview_companion": dict(
        name="Interview Companion", kind=AGENT, icon="Mic",
        reads="what you type during an interview",
        produces="follow-up questions, observations and the minutes",
        you_decide="what goes in the file",
        aliases=("interview_companion",),
    ),
    "quality_coverage": dict(
        name="Coverage check", kind=ENGINE, icon="LayoutGrid", tier="none",
        reads="the scope, the risk matrix and the tests, as they stand right now",
        produces="which in-scope areas have no risk, control or test behind them",
        you_decide="whether a gap is acceptable",
        aliases=("coverage",),
    ),
    "quality_review": dict(
        name="AI quality review", kind=AGENT, icon="ClipboardCheck",
        reads="each drafted artefact in the file",
        produces="what must be fixed, separated from what is only a suggestion",
        you_decide="which comments you accept",
        aliases=("qa_review", "grounding"),
    ),
    "quality_peer_review": dict(
        name="AI peer review (GIAS)", kind=AGENT, icon="Gavel", tier="judge",
        reads="the audit file itself — the letter, the risk assessment, the work program, "
              "the tests and their evidence, the findings and the report",
        produces="a rating per GIAS criterion, with the evidence behind each",
        you_decide="a human peer reviewer confirms every rating",
        aliases=("peer_review", "PeerReview"),
    ),
    "racm_scoping": dict(
        name="Matrix scoping", kind=AGENT, icon="LayoutList",
        reads="the scope and the accepted risks",
        produces="the objective → risk → control → test spine",
        you_decide="you accept or dismiss every proposal in the matrix",
        aliases=("scoping_engine",),
    ),
    "racm_governance": dict(
        name="Governance assessor", kind=AGENT, icon="ScanSearch",
        reads="the accepted frameworks and the relevant passages of your governance documents",
        produces="a coverage judgement per requirement, and the gaps as proposed risks",
        you_decide="whether each proposed gap becomes a risk",
        aliases=("governance_assessor", "GovernanceAssessment"),
    ),
    "racm_data_analysis": dict(
        name="Data analysis", kind=ENGINE, icon="BarChart3", tier="none",
        reads="the population you supply",
        produces="full-population checks — duplicates, gaps, outliers, segregation conflicts",
        you_decide="which exceptions become tests; AI explanations are opt-in",
        aliases=("data_analysis",),
    ),
    "racm_evidence_chase": dict(
        name="Evidence chase", kind=ENGINE, icon="FolderSearch", tier="none",
        reads="every document that arrives against the tests that need it",
        produces="what is matched, and what is still outstanding",
        you_decide="whether a document actually satisfies the request",
    ),
    "fieldwork": dict(
        name="Fieldwork", kind=HUMAN, icon="PenLine", tier="none",
        reads="nothing — you record what you found",
        produces="observations, good practices and improvements",
        you_decide="all of it",
    ),
    "findings": dict(
        name="Findings (5C)", kind=AGENT, icon="FileWarning",
        reads="the observation, the test behind it and how comparable findings were rated before",
        produces="a report-ready 5C finding and a rating — then a second agent challenges that rating",
        you_decide="you confirm every finding and its rating",
        aliases=("finding_drafter", "FindingDraft", "RatingChallenge"),
    ),
    "report_draft": dict(
        name="Audit report", kind=AGENT, icon="FileCheck2", tier="judge",
        reads="the confirmed findings and the engagement's conclusions",
        produces="the report and the overall opinion",
        you_decide="you approve the report before it goes anywhere",
        aliases=("report_drafter", "report_opinion"),
    ),
    # ── Companions ───────────────────────────────────────────────────────────
    "supervisory_guidance": dict(
        name="Guidance scout", kind=AGENT, icon="Compass",
        reads="supervisory publications for the topic and jurisdictions",
        produces="the guidance that bears on this audit",
        you_decide="what you take into the framework list",
    ),
    "rcsa_import": dict(
        name="RCSA import", kind=AGENT, icon="Table2",
        reads="the risk and control self-assessment the business exported, column by column",
        produces="a confirmed column mapping, and the rows read with it",
        you_decide="you confirm what each column holds, and whether to rely on the work at all",
        aliases=("rcsa_import", "RcsaMappingProposal"),
    ),
    "pbc_assistant": dict(
        name="PBC assistant", kind=AGENT, icon="Inbox",
        reads="the document request list and everything the auditee sends back",
        produces="the requests, the reminders, and a judgement on each document received",
        you_decide="whether a document satisfies the request",
        aliases=("pbc_assistant",),
    ),
    "privacy_guard": dict(
        name="Privacy Guard", kind=ENGINE, icon="Lock", tier="none",
        reads="the data you load",
        produces="detected personal data, classified and masked by role",
        you_decide="the purpose you are processing it for",
        aliases=("privacy_guard",),
    ),
    "vendor_guard": dict(
        name="Vendor Guard", kind=AGENT, icon="ShieldQuestion",
        reads="the vendor's documents, against eight curated EU/NL frameworks",
        produces="a scorecard per framework and the critical gaps as proposed risks",
        you_decide="whether each gap enters the matrix",
        aliases=("vendor_guard",),
    ),
}

#: Keys written to the activity log or used as schema names that belong to an
#: agent whose own key differs. Kept beside the presentation table rather than
#: inside it so the mapping can be read in one go.
_EXTRA_ALIASES = {
    "topic_intelligence": "topic_intelligence",

    # ── AgentRun.agent_type values ───────────────────────────────────────────
    # Written as inline literals in routers and services rather than as
    # AGENT_TYPE constants, which is why the coverage test never saw them and
    # why thirteen of the fourteen resolved to nothing. `display_name` then fell
    # back to title-casing the key, so the activity log showed an auditor "Bra
    # scope" and "Lens1" — raw keys, in the record of how a conclusion was
    # reached. `tests/test_agent_registry` now reads these literals out of the
    # source, so a new one cannot arrive unregistered.

    # The Topic Intelligence cascade: three agents behind one memo, plus three
    # lenses. `interview` is part of it — it drafts the early orientation
    # questions that land in the memo, and is NOT the Interview Guide step, which
    # is grounded in scope and risks and comes much later. Pointing it at the
    # guide sent the reader to the wrong screen.
    "regulatory": "topic_intelligence",
    "policy": "topic_intelligence",
    "interview": "topic_intelligence",
    "interview_agent": "topic_intelligence",
    "lens1": "topic_intelligence",
    "lens2": "topic_intelligence",
    "lens3": "topic_intelligence",

    "framework_requirements": "frameworks",
    "anl_drafter": "anl",
    "anl_reviewer": "anl",
    "bra_drafter": "bra",
    "bra_scope": "bra",
    "kickoff_drafter": "kickoff",
    "kickoff_scope": "kickoff",
}


def _build() -> dict[str, Agent]:
    agents: dict[str, Agent] = {}
    graph = {s["key"]: s for s in STAGE_GRAPH}
    companions = {c["key"]: c for c in COMPANIONS}

    for key, source in list(graph.items()) + list(companions.items()):
        p = _PRESENTATION.get(key)
        if p is None:
            continue  # the coverage test fails loudly; no silent blank row
        info = STAGE_INFO.get(key, {})
        agents[key] = Agent(
            key=key,
            label=source.get("label", key),
            phase=source.get("phase") or PHASE_OF.get(key, "planning"),
            route=source.get("route", ""),
            base=source.get("base", ""),
            description=(p.get("one_liner") or info.get("description")
                         or source.get("description", "")),
            companion=key in companions,
            gates=tuple(source.get("gates", ())),
            name=p["name"], kind=p["kind"], icon=p["icon"],
            reads=p["reads"], produces=p["produces"], you_decide=p["you_decide"],
            tier=p.get("tier", "draft"),
            aliases=tuple(p.get("aliases", ())),
            agent_id=_SERVED_BY.get(key, key),
        )
    return agents


AGENTS: dict[str, Agent] = _build()


def agent_name(agent_id: str) -> str:
    """What a merged agent is called when it is named as an agent.

    A step that is its own agent keeps its own name; only the merges need a new
    one, because "Frameworks & Requirements" reads oddly as the thing that also
    scouts supervisory guidance.
    """
    if agent_id in _AGENT_NAMES:
        return _AGENT_NAMES[agent_id]
    a = AGENTS.get(agent_id)
    return a.name if a else agent_id


def agents() -> list[dict]:
    """One row per AGENT, with the steps it serves.

    `catalog()` answers "what steps are there"; this answers "how many things do
    we maintain". While every step was its own agent those were the same
    question, and the answer to the second was wrong by seven.
    """
    order = [a.key for a in AGENTS.values()]
    rows: dict[str, dict] = {}
    for key in order:
        a = AGENTS[key]
        row = rows.setdefault(a.agent_id, {
            "agent_id": a.agent_id,
            "name": agent_name(a.agent_id),
            "kind": a.kind,
            "tier": a.tier,
            "icon": AGENTS[a.agent_id].icon if a.agent_id in AGENTS else a.icon,
            "phase": a.phase,
            "serves": [],
        })
        row["serves"].append(key)
    return list(rows.values())

#: Every string any layer has ever used for an agent → its key.
ALIAS_TO_KEY: dict[str, str] = {}
for _key, _a in AGENTS.items():
    ALIAS_TO_KEY[_key] = _key
    for _alias in _a.aliases:
        ALIAS_TO_KEY[_alias] = _key
ALIAS_TO_KEY.update(_EXTRA_ALIASES)


def resolve(key: str | None) -> Agent | None:
    """The agent behind any name it has ever been called."""
    if not key:
        return None
    return AGENTS.get(ALIAS_TO_KEY.get(key, key))


def display_name(key: str | None) -> str:
    """A name fit to show a person — never a raw key.

    Falls back to a readable form of the key rather than the key itself: an
    unregistered agent should read as "Some New Agent", not `some_new_agent`.
    """
    agent = resolve(key)
    if agent:
        return agent.name
    return (key or "Unknown agent").replace("_", " ").strip().capitalize()


def catalog() -> list[dict]:
    """The whole roster, ordered by phase then by lifecycle position."""
    order = {s["key"]: i for i, s in enumerate(STAGE_GRAPH)}
    # Derived from the phase list rather than repeated here: a band added to the
    # lifecycle without being named here used to fall silently to the end.
    from services.workflow_service import PHASES
    phases = [p["key"] for p in PHASES]

    def sort_key(a: Agent):
        return (phases.index(a.phase) if a.phase in phases else len(phases),
                order.get(a.key, 999))

    return [
        {
            "key": a.key, "name": a.name, "kind": a.kind, "icon": a.icon,
            "phase": a.phase, "label": a.label, "route": a.route, "base": a.base,
            "description": a.description, "companion": a.companion,
            "reads": a.reads, "produces": a.produces, "you_decide": a.you_decide,
            "tier": a.tier, "gates": list(a.gates), "aliases": list(a.aliases),
        }
        for a in sorted(AGENTS.values(), key=sort_key)
    ]
