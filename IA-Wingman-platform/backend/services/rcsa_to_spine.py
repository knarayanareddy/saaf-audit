"""Putting the auditee's own risks in front of the auditor, as proposals.

This is where the RCSA stops being a spreadsheet and starts being something an
audit can act on — and it is deliberately the thinnest possible step.

**Nothing here judges.** The platform does not rank the auditee's risks, does not
decide which are serious, and does not translate their rating scale into its
own. It cannot: `parse_rating` reads "(4) Likely" as a score and a word, and a 4
on one department's five-point scale is not a 4 on another's ten-point scale.
Inventing an order across templates would be exactly the kind of quiet claim the
rest of this platform exists to remove. So the auditor selects the rows, the
default selection is the ones **the business itself flagged as key risks**, and
every proposal carries the auditee's own wording and their own rating verbatim.

**Nothing passes without a reliance decision.** `may_rely_on` is checked here,
not in the UI, because the moment IA builds on second-line work is the moment the
standards require having assessed it.

**Every proposal can name its row.** `source_id` is the RcsaRow, `source_ref` is
what the auditor reads — the file and the sheet row. Reference, not resemblance:
an auditor asking "where did this come from" gets the line in the export, not a
similar-looking sentence.
"""
from __future__ import annotations

import json

from sqlalchemy import select

from database import AsyncSessionLocal
from models.rcsa import RcsaImport, RcsaRow
from services.rcsa_mapping import AUDITEE_LABEL, may_rely_on
from services.risk_proposals import ProposedRisk
from services.risk_proposals import write as write_proposals

#: The provenance these proposals carry, and the family a re-push replaces. A
#: re-push clears only this source's UNACCEPTED proposals — anything the auditor
#: has accepted is theirs.
PROVENANCE_SOURCE = "rcsa_import"

#: The three words that mean the same thing in any scale. Anything else is left
#: alone rather than mapped onto them.
_PLAIN_RATINGS = {"high", "medium", "low"}


def _rating_of(projected: dict) -> tuple[str, str]:
    """(rating, note). The auditee's word when it is one this platform shares.

    A label reading "High" is not a translation, it is the same word. A label
    reading "(4) Likely" is a position on a scale this platform knows nothing
    about, so the proposal keeps the default and says the real value in its
    rationale instead of pretending to have converted it.
    """
    residual = projected.get("residual_exposure") or projected.get("inherent_exposure") or {}
    label = str(residual.get("label") or "").strip().lower()
    raw = str(residual.get("raw") or residual.get("label") or "").strip()
    if label in _PLAIN_RATINGS:
        return label, ""
    if raw:
        return "medium", f"The auditee rated this {raw}, on their own scale."
    return "medium", "The auditee recorded no rating for this row."


def default_selection(rows: list[RcsaRow]) -> list[str]:
    """The rows the business itself flagged as key risks.

    A default, not a decision: it is the auditee's own answer to "where does the
    risk sit", which is the most defensible starting point available and still
    only a starting point. Where no row carries the flag, nothing is selected —
    better an empty list the auditor fills than a selection nobody chose.
    """
    return [r.id for r in rows if r.key_risk is True]


def describe(projected: dict) -> str:
    """What the auditee said, in their words, labelled as theirs."""
    parts = []
    for key, prefix in (("cause", "Cause"), ("event", "Event"),
                        ("impact_categories", "Impact")):
        value = projected.get(key)
        if value:
            parts.append(f"{prefix}: {value}")
    controls = projected.get("controls")
    if controls:
        parts.append(f"Controls the business names: {controls}")
    effectiveness = projected.get("control_effectiveness") or {}
    if effectiveness:
        parts.append(f"Control effectiveness (their assessment): "
                     f"{effectiveness.get('raw') or effectiveness.get('label')}")
    return " · ".join(parts)


async def propose_rows(engagement_id: str, import_id: str,
                       row_ids: list[str] | None = None) -> dict:
    """Push the selected rows into the matrix as proposals awaiting acceptance.

    Returns what happened, including a refusal with its reason: an import nobody
    has decided about produces no proposals and says why, rather than failing
    silently or — worse — succeeding.
    """
    allowed, why = await may_rely_on(import_id)
    if not allowed:
        return {"written": 0, "refused": True, "reason": why}

    async with AsyncSessionLocal() as db:
        imp = await db.get(RcsaImport, import_id)
        if not imp or imp.engagement_id != engagement_id:
            return {"written": 0, "refused": True, "reason": "That RCSA is not on this engagement"}
        rows = (await db.execute(
            select(RcsaRow).where(RcsaRow.import_id == import_id).order_by(RcsaRow.sheet_row)
        )).scalars().all()

    chosen = [r for r in rows if r.id in set(row_ids)] if row_ids is not None else \
        [r for r in rows if r.id in set(default_selection(rows))]

    proposals = []
    for row in chosen:
        try:
            projected = json.loads(row.projected or "{}")
        except (json.JSONDecodeError, TypeError):
            projected = {}
        title = (projected.get("risk_title") or row.risk_title or "").strip()
        if not title:
            continue  # a row with no risk named is not a risk
        rating, note = _rating_of(projected)
        band = (projected.get("bands") or {}).get("residual_exposure")
        rationale = " ".join(x for x in (
            f"{AUDITEE_LABEL}.",
            note,
            f"Residual rating taken from the band '{band}'." if band else "",
            "Flagged by the business as a key risk." if projected.get("key_risk") else "",
        ) if x)

        proposals.append(ProposedRisk(
            title=title,
            description=describe(projected) or None,
            category=(projected.get("process") or row.process or None),
            inherent_rating=rating,
            # Not the platform's confidence in the risk — this is a faithful copy
            # of someone else's assessment, and how much it is worth is what the
            # reliance decision says.
            confidence=None,
            source_ref=f"{imp.original_filename}, sheet row {row.sheet_row}",
            source_id=row.id,
            rationale=rationale,
        ))

    written = await write_proposals(engagement_id, import_id, PROVENANCE_SOURCE, proposals)
    return {"written": written, "refused": False, "reason": why,
            "selected": len(chosen), "skipped": len(chosen) - len(proposals)}
