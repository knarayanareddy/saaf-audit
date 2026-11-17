"""What prior audits found, put in front of the agent that needs it.

`audit_memory.py` has been able to recall precedents from other engagements since
it was written. Nothing used it. It had a router and a panel, and not one agent
ever asked it a question — so every drafter started each engagement as though the
organisation had never audited anything before.

The Background Risk Assessment makes the gap plain. Its own prompt asks the model
for "what we know from prior audits" and for "audit findings from related
reviews", and hands it nothing to answer with. Whatever came back was invented.

This module turns a recall into a context block, and the framing is the whole
point. A precedent is **not evidence about this audit**. It is a conclusion
somebody reached about a different engagement, and the only honest thing it can
do is tell an agent what has been worth looking at before.

Two distinctions the block makes, because the data supports them:

* **Settled or in progress.** A finding on a closed engagement is a conclusion
  somebody signed. A finding still marked draft, on an audit still running, is
  an opinion in mid-argument. Presenting the two as equivalent would be the same
  error as counting rows and calling it a peer review.
* **What it matched on.** Every precedent carries the terms it shares with this
  engagement, so an auditor reading the output can see why it surfaced — and
  dismiss it when the overlap is coincidence.

One thing this deliberately does NOT say: whether a prior recommendation was ever
implemented. Nothing in this platform tracks remediation or follow-up, so an
agent claiming "three recommendations are still open" would be making it up.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from models.engagement import Engagement
from models.reporting import Finding
from services.audit_memory import recall

#: A finding is a conclusion only once the engagement that produced it has closed
#: AND the finding itself is past draft. Anything else is work in progress.
_SETTLED_ENGAGEMENT_STATUS = "closed"
_SETTLED_FINDING_STATUS = {"ready", "confirmed", "accepted"}

_PREAMBLE = """PRIOR AUDITS ON ADJACENT TOPICS
These are conclusions from OTHER engagements, matched to this one by shared terms.
They are context, never evidence: they say what has been found before and what has
been worth examining, and nothing at all about whether it is true here.

- Never state a prior finding as a fact about this audit. Use it to decide what to
  look at, and let this audit's own work decide what is true.
- [settled] means the source engagement is closed and the conclusion was signed off.
  [in progress] means it is a draft on an audit still running — it may yet change.
- Where a precedent shapes what you propose, say so in the text, naming the audit it
  came from, so the auditor can go and check it.
- A precedent that is not relevant here should simply be ignored. The match is keyword
  overlap, not judgement."""


@dataclass
class Memory:
    """The recall, ready to go into a prompt and onto a receipt."""
    items: list[dict] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    block: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.items

    @property
    def settled(self) -> int:
        return sum(1 for i in self.items if i.get("settled"))

    def sentence(self) -> str:
        """One line for a run summary — what the agent was told, in short."""
        if self.is_empty:
            return "no prior-audit precedents matched"
        sources = sorted({i["source_engagement_name"] for i in self.items if i.get("source_engagement_name")})
        noun = "precedent" if len(self.items) == 1 else "precedents"
        base = f"recalled {len(self.items)} {noun} from {len(sources)} prior audit(s)"
        if self.settled:
            base += f", {self.settled} from closed engagements"
        return base

    def as_dict(self) -> dict:
        return {
            "count": len(self.items), "settled": self.settled,
            "terms": self.terms, "sentence": self.sentence(),
            "items": [
                {k: i.get(k) for k in
                 ("kind", "title", "rating", "settled", "source_engagement_name",
                  "source_status", "shared")}
                for i in self.items
            ],
        }


async def recall_for(db, engagement_id: str, limit: int = 8,
                     kinds: tuple[str, ...] | None = None) -> Memory:
    """Recall precedents for this engagement and render them for a prompt.

    `kinds` narrows what is worth recalling for a given agent: a work-program
    generator wants prior findings and controls, a risk assessment wants risks
    and findings. Passing everything to everyone would spend prompt budget on
    material the agent has no use for.
    """
    result = await recall(db, engagement_id, limit=limit * 2 if kinds else limit)
    items = result.get("items", [])
    if kinds:
        items = [i for i in items if i.get("kind") in kinds][:limit]

    # Which of these are settled conclusions rather than drafts in flight.
    finding_status: dict[str, str] = {}
    engagement_status: dict[str, str] = {}
    if items:
        from sqlalchemy import select
        for e in (await db.execute(select(Engagement))).scalars().all():
            engagement_status[e.id] = e.status or ""
        for f in (await db.execute(select(Finding))).scalars().all():
            finding_status[f"{f.engagement_id}:{f.title}"] = f.status or "draft"

    for i in items:
        src = i.get("source_engagement_id")
        closed = engagement_status.get(src, "") == _SETTLED_ENGAGEMENT_STATUS
        if i.get("kind") == "finding":
            status = finding_status.get(f"{src}:{i.get('title')}", "draft")
            i["settled"] = closed and status in _SETTLED_FINDING_STATUS
        else:
            i["settled"] = closed

    memory = Memory(items=items, terms=result.get("terms", []))
    memory.block = _render(items)
    return memory


def _render(items: list[dict]) -> str:
    if not items:
        return ""
    lines = []
    for i in items:
        marks = [i.get("kind", "item"), "settled" if i.get("settled") else "in progress"]
        if i.get("rating"):
            marks.append(str(i["rating"]))
        if i.get("decision_type"):
            marks.append(str(i["decision_type"]))
        shared = ", ".join(i.get("shared") or []) or "topic overlap"
        summary = " ".join((i.get("summary") or "").split())[:220]
        lines.append(
            f"- [{' · '.join(marks)}] {i.get('title', '(untitled)')}\n"
            f"    from \"{i.get('source_engagement_name') or 'an earlier audit'}\""
            f" ({i.get('source_status') or 'status unknown'}) · matched on: {shared}"
            + (f"\n    {summary}" if summary else "")
        )
    return f"{_PREAMBLE}\n\n" + "\n".join(lines)
