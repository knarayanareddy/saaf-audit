"""Which step produced a scope item.

Six planning steps write into Scope & Objectives — topic intelligence, process
understanding, frameworks, the kick-off, the background risk assessment, and the
auditor typing one in. They converge on a single list, and until now that list
told the auditor almost nothing about where its contents came from.

Two things were wrong with the old `source` column.

**One string meant three different producers.** `cascaded` was written by the
topic-intelligence accept route, by the golden-path seed and by the ESG demo
seed. An auditor reading `cascaded` learned that something upstream put it
there, which they could already see.

**The screen showed it for one case only.** `ScopeObjectivesPage` tagged a row
"AI" when `source === 'cascaded'`, so the fourteen items carrying an accurate
`from_frameworks` or `from_process_understanding` displayed no origin at all.
The better data was the data nobody saw.

So: the producing step names itself, the label comes from the registry rather
than from a second list that can drift from it, and `ref` records *which row*
upstream — because "from Process Understanding" identifies a step, and an
auditor checking a scope item wants the paragraph.

**An item with no known source is not offered.** `stamp()` is how a writer
declares its origin, and it refuses a source this module does not know. A
proposal that cannot say where it came from is not a proposal; it is a rumour
with a checkbox next to it.

Sources are added here when a step starts writing, not before. The scoping
meeting and the RCSA import both belong in this list eventually; neither writes
yet, and an entry for a producer that does not exist is a promise, not a record.
"""
from __future__ import annotations

from dataclasses import dataclass

#: What the UI shows when a row predates this module and cannot be resolved.
UNKNOWN_LABEL = "Origin not recorded"


@dataclass(frozen=True)
class Source:
    """One producing step, and the names it has been stored under."""

    key: str
    #: The registry step id, so the map and the item agree on what a step is.
    #: Empty for `manual`: the auditor is not a step in the registry.
    step: str
    #: Only for sources with no registry step; otherwise the registry answers.
    own_label: str = ""
    #: Strings earlier writers used for this same origin.
    legacy: tuple[str, ...] = ()


SOURCES: tuple[Source, ...] = (
    Source("from_topic_intelligence", "topic_intelligence"),
    Source("from_process_understanding", "process_understanding"),
    # Supervisory guidance is a step of the same merged agent, and it publishes
    # through the frameworks route. One origin, because the auditor opens one
    # screen to check it.
    Source("from_frameworks", "frameworks"),
    Source("from_kickoff", "kickoff"),
    Source("from_bra", "bra"),
    Source("manual", "", own_label="Entered by the auditor"),
)

BY_KEY: dict[str, Source] = {s.key: s for s in SOURCES}
_BY_LEGACY: dict[str, Source] = {old: s for s in SOURCES for old in s.legacy}

TOPIC_INTELLIGENCE = "from_topic_intelligence"
PROCESS_UNDERSTANDING = "from_process_understanding"
FRAMEWORKS = "from_frameworks"
KICKOFF = "from_kickoff"
BRA = "from_bra"
MANUAL = "manual"


def normalise(value: str | None) -> str:
    """The canonical key for a stored source, or "" when it is not one of ours.

    Empty rather than a guess: a caller that cannot tell should say so, and the
    two places that care — the screen and `stamp()` — both handle "" already.
    """
    key = (value or "").strip()
    if key in BY_KEY:
        return key
    if key in _BY_LEGACY:
        return _BY_LEGACY[key].key
    return ""


def is_known(value: str | None) -> bool:
    return bool(normalise(value))


def label(value: str | None) -> str:
    """What to print next to the item."""
    key = normalise(value)
    if not key:
        return UNKNOWN_LABEL
    source = BY_KEY[key]
    if source.own_label:
        return source.own_label
    from services.agent_registry import AGENTS

    agent = AGENTS.get(source.step)
    return agent.label if agent else source.step


def step_of(value: str | None) -> str:
    """The registry step id, for linking the item to the map."""
    key = normalise(value)
    return BY_KEY[key].step if key else ""


def stamp(source: str, ref: str | None = None) -> dict:
    """The provenance fields for a new scope item or key audit question.

        db.add(ScopeItem(..., **stamp(TOPIC_INTELLIGENCE, ref=area.get("id"))))

    Raises on an unknown source. The alternative — writing it anyway — is how
    `cascaded` came to mean three things: nothing refused the vague answer at
    the moment the writer chose it.
    """
    key = normalise(source)
    if not key:
        raise ValueError(
            f"{source!r} is not a scope source. Add it to SOURCES, or use "
            f"{MANUAL!r} if a person typed this in."
        )
    return {"source": key, "source_ref": (ref or "") or None}


def describe(value: str | None, ref: str | None = None) -> dict:
    """The provenance as the API hands it to the screen."""
    return {
        "source": normalise(value) or (value or ""),
        "source_label": label(value),
        "source_step": step_of(value),
        "source_ref": ref or "",
    }


async def backfill(db) -> dict:
    """Give the pre-existing `cascaded` rows the name of their real producer.

    Three writers used that one string, and they can still be told apart,
    because two of them only ever wrote accepted rows:

    - the **seeds** (`golden_path_service`, `seed_demo_esg`) write demo scope
      that is already accepted, so no auditor decision is being overwritten;
    - the **topic-intelligence accept route** writes proposals, `is_accepted`
      False, waiting for that decision.

    So an unaccepted `cascaded` row can only have come from topic intelligence.
    An accepted one cannot be resolved — both seeds are hand-written content
    with no upstream row to point at — and becomes `manual`, which is what a
    hand-written item is.

    Idempotent: rows already carrying a known source are left alone.
    """
    from sqlalchemy import select

    from models.planning import KeyAuditQuestion, ScopeItem

    moved = {TOPIC_INTELLIGENCE: 0, MANUAL: 0, "left_alone": 0}
    for model in (ScopeItem, KeyAuditQuestion):
        for row in (await db.execute(select(model))).scalars().all():
            if is_known(row.source):
                moved["left_alone"] += 1
                continue
            key = MANUAL if row.is_accepted else TOPIC_INTELLIGENCE
            row.source = key
            moved[key] += 1
    await db.commit()
    return moved


async def run_ref(db, engagement_id: str, agent_type: str) -> str:
    """The id of the run whose accepted output a publish route is writing out.

    Three publish routes hand the auditor a list an agent produced and write the
    selected rows into scope. The rows themselves carry no id — the agents return
    plain text — so the run is the finest thing there is to point at, and it is
    worth pointing at: it is the record that holds the prompt, the sources and
    the auditor's acceptance.
    """
    from sqlalchemy import select

    from models.agent_run import AgentRun

    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == agent_type,
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    return run.id if run else ""
