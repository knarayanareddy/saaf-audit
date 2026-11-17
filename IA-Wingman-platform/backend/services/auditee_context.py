"""What an agent needs to know before writing to the auditee.

The notification letter and the kick-off agenda are two documents produced from
one body of facts: the engagement, the topic memo, the accepted scope and the
accepted frameworks. Both drafters loaded that themselves, with the same five
queries and the same two filters, differing only in variable names —
`items_in` here, `in_scope` there.

Duplicated context is worse than duplicated formatting, because the copies
diverge silently. Both currently filter scope items on `is_accepted`, which is
right: **only what the auditor accepted may reach the auditee.** Nothing in
either file said so, and nothing stopped one copy from dropping the filter.

Now it is stated once, and the test that asserts it has one place to look.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import select

from models.engagement import Engagement
from models.planning import ApplicableFramework, ScopeItem, ScopeObjectives, TopicIntelligence


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


@dataclass(frozen=True)
class AuditeeContext:
    """The engagement as it may be described to the auditee."""

    engagement: Engagement
    #: Accepted in-scope and out-of-scope descriptions. Never the proposals: a
    #: scope item an auditor has not accepted is not something to tell an
    #: auditee about.
    in_scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    #: Accepted frameworks only, same reason.
    frameworks: list[str] = field(default_factory=list)
    overall_objective: str = ""
    ti_summary: str = ""
    ti_conclusion: str = ""
    ti_key_risks: list = field(default_factory=list)
    ti_interview_agenda: dict = field(default_factory=dict)

    @property
    def ia_prework(self) -> list:
        """The preparation the memo suggested Internal Audit do beforehand."""
        return self.ti_interview_agenda.get("ia_prework", [])

    def _ticked(self, group: str) -> list[str]:
        return [q["question_text"].strip() for q in self.ti_interview_agenda.get(group, [])
                if isinstance(q, dict) and q.get("included", True) and (q.get("question_text") or "").strip()]

    @property
    def sponsor_questions(self) -> list[str]:
        """What the auditor ticked in the memo to ask the sponsor — for the kick-off."""
        return self._ticked("sponsor")

    @property
    def sme_questions(self) -> list[str]:
        """What the auditor ticked in the memo to ask experts — for the interviews."""
        return self._ticked("sme")


async def load(db, engagement_id: str) -> AuditeeContext:
    """Everything the auditee-facing drafters read, in one pass."""
    eng = await db.get(Engagement, engagement_id)

    ti = (await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )).scalar_one_or_none()

    scope = (await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )).scalar_one_or_none()

    in_scope: list[str] = []
    out_of_scope: list[str] = []
    if scope:
        items = (await db.execute(
            select(ScopeItem).where(ScopeItem.scope_id == scope.id)
        )).scalars().all()
        in_scope = [i.description for i in items if i.item_type == "in_scope" and i.is_accepted]
        out_of_scope = [i.description for i in items if i.item_type == "out_of_scope" and i.is_accepted]

    frameworks = [f.framework_name for f in (await db.execute(
        select(ApplicableFramework).where(
            ApplicableFramework.engagement_id == engagement_id,
            ApplicableFramework.is_accepted == True,  # noqa: E712
        )
    )).scalars().all()]

    return AuditeeContext(
        engagement=eng,
        in_scope=in_scope,
        out_of_scope=out_of_scope,
        frameworks=frameworks,
        overall_objective=(scope.overall_objective if scope else "") or "",
        ti_summary=(ti.regulatory_summary if ti else "") or "",
        ti_conclusion=(ti.conclusion if ti else "") or "",
        ti_key_risks=_loads(ti.key_risk_areas if ti else None, []),
        ti_interview_agenda=_loads(ti.interview_agenda if ti else None, {}),
    )
