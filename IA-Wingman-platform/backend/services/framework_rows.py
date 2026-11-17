"""Where a framework row is written. One place, two kinds.

Laws and supervisory guidance already share a table: `ApplicableFramework`,
tagged `category='law'` or `category='guidance'`. What they did not share was the
code that writes it. Two services held the same thirteen-field insert and the
same delete-only-my-own-rows discipline, differing in three key names and two
constants — which is how the two copies came to disagree.

They disagreed in a way worth naming. The law side deleted by `source` alone:

    delete(ApplicableFramework).where(
        engagement_id == ...,
        source == "auto_analysed",       # and nothing about category
    )

Any future writer reusing that source string would have had its rows removed by
a re-run of the laws agent. The guidance side filtered on both. One store, one
rule: **a kind deletes only rows carrying its own category AND its own source.**

The two prompts stay apart on purpose. One is steered towards binding statute
with article references; the other deliberately away from statute, towards
policy rules, guidance, good-practice papers and Dear CEO letters. A single
prompt doing both blurs the distinction, and the distinction is what the reader
is buying. Same agent, two modes — not one prompt.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import delete

from models.planning import ApplicableFramework


def _as_bool(value, default: bool = False) -> bool:
    """Models answer this question in prose as often as in JSON."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


@dataclass(frozen=True)
class Kind:
    """One category of framework row, and how its agent names its fields.

    `fields` maps our column to the key the agent's schema uses. The two agents
    describe the same thing in their own vocabulary — a law "requires", guidance
    "says" — and that is worth keeping in the prompts rather than flattening.
    """

    category: str
    source: str
    fields: dict[str, str]


LAW = Kind(
    category="law",
    source="auto_analysed",
    fields={
        "code": "framework_code",
        "name": "framework_name",
        "rationale": "what_it_requires",
        "provision": "specific_provision",
    },
)

GUIDANCE = Kind(
    category="guidance",
    source="guidance_analysed",
    fields={
        "code": "guidance_code",
        "name": "guidance_name",
        "rationale": "what_it_says",
        "provision": "guidance_type",
    },
)


async def replace_rows(db, engagement_id: str, kind: Kind, items: list[dict]) -> int:
    """Replace this kind's own rows for one engagement. Returns rows written.

    Does not commit: the caller owns the transaction, because both agents write
    more than this in the same unit of work.

    A row with no name is skipped rather than stored blank — an unnamed framework
    is something the model failed to find, not something that exists without a
    name.
    """
    f = kind.fields
    await db.execute(
        delete(ApplicableFramework).where(
            ApplicableFramework.engagement_id == engagement_id,
            ApplicableFramework.category == kind.category,
            ApplicableFramework.source == kind.source,
        )
    )

    written = 0
    for item in items or []:
        name = item.get(f["name"])
        if not name:
            continue
        fallback_code = item.get("issuer") or kind.category.upper()
        db.add(ApplicableFramework(
            id=str(uuid4()),
            engagement_id=engagement_id,
            framework_code=(item.get(f["code"]) or fallback_code)[:50],
            framework_name=str(name)[:255],
            applicability_rationale=item.get(f["rationale"]) or "",
            specific_provision=item.get(f["provision"]),
            source_url=item.get("source_url"),
            confidence=item.get("confidence") or "medium",
            jurisdiction=item.get("jurisdiction") or "",
            category=kind.category,
            is_primary=_as_bool(item.get("is_primary")),
            is_accepted=True,
            source=kind.source,
        ))
        written += 1
    return written
