"""What the Topic Intelligence scan actually starts with.

An auditor is about to let three agents reason about their audit, and until now
the only honest answer to "on what basis?" was to read the source. That is the
wrong way round: the inputs of a scan are part of its result, because a
conclusion drawn from a thin starting point is a different conclusion.

So this module reports the starting context, and it reports it **as it is**:

- It names the fields the lenses are actually given.
- It says, in the same breath, that the uploaded documents are **not** among
  them. The start screen invites uploads and the next phases use them, but the
  three lenses never read them — an auditor who assumes otherwise would credit
  the scan with knowledge it does not have. Listing them here as "context"
  would be exactly the kind of quiet claim this platform exists to remove.
- It leaves a place for what the auditor knows and the record does not say.

Both this report and the run read the same engagement row, so the two cannot
drift into telling different stories.
"""
from __future__ import annotations

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement, jurisdictions_or_default
from models.planning import TopicIntelligence, UploadedDocument
from services.query_generator import ENTITY_DOMAINS

#: Said once, here, so the API and the screen cannot disagree about it.
DOCUMENTS_NOT_READ = (
    "The four-lens scan does not read uploaded documents. They are stored for "
    "the later planning steps, which do. To put something from a document in "
    "front of the scan, add it below in your own words."
)


async def scan_context(engagement_id: str) -> dict | None:
    """The starting context, or None when there is no such engagement."""
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        if not eng:
            return None

        docs = (await db.execute(
            select(UploadedDocument).where(UploadedDocument.engagement_id == engagement_id)
        )).scalars().all()

        ti = (await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
        )).scalar_one_or_none()

    entity_info = ENTITY_DOMAINS.get(eng.entity, ENTITY_DOMAINS["GRP"])

    return {
        # Given to every lens, straight from the engagement record.
        "given": [
            {"label": "Audit", "value": eng.name, "source": "engagement record"},
            {"label": "Entity", "value": f"{eng.entity} ({entity_info['primary_regulator']})",
             "source": "engagement record"},
            {"label": "Audit type", "value": eng.audit_type or "—", "source": "engagement record"},
            {"label": "Jurisdictions", "value": ", ".join(jurisdictions_or_default(eng)),
             "source": "engagement record" if eng.jurisdictions else "default (none chosen)"},
        ],
        # Named so that what is absent is as visible as what is present.
        "not_given": [
            {"label": "Uploaded documents",
             "value": f"{len(docs)} uploaded" if docs else "none uploaded",
             "why": DOCUMENTS_NOT_READ},
        ],
        "documents": [d.original_filename for d in docs],
        # What a previous scan ran with, so a re-run starts from what was used
        # rather than from an empty box.
        "extra_context": (ti.extra_context if ti else None) or "",
    }
