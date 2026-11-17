"""What a column means, and what this platform is allowed to do with it.

The mapping is the whole design. A bank's RCSA export has no standard shape —
the column names differ per template, per department and per year — so a parser
written against one file works against exactly that file. Instead: an agent
proposes what each column is, a person confirms it once, and the confirmation is
the template. The second import from the same template is one click.

Two rules, and both come from what a real export turned out to look like.

**An unmapped column is reported, never guessed.** It stays in the row, it stays
on screen, and it says it was not mapped. A wrong match is worse than a visible
gap, because a wrong match is invisible.

**"Residual" is not one column.** That export carries two residual bands — one
*during change implementation*, one *when going live* — each with its own
Likelihood, Impact and Exposure. Which of the two an auditor means is a judgement
about the audit, not a detail of parsing, so the mapping records the band beside
the field and the UI shows it. Reading "the residual rating" off a sheet with two
of them is the kind of quiet mistake nothing downstream could catch.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import select

from database import AsyncSessionLocal
from models.rcsa import RcsaImport, RcsaRow, RcsaTemplate, RelianceDecision

#: The label every view carries. An RCSA is the auditee's own assessment —
#: evidence about the control environment, never Internal Audit's conclusion.
#: `tests/test_rcsa_import` asserts it cannot be dropped.
AUDITEE_LABEL = "The auditee's own risk and control self-assessment"


@dataclass(frozen=True)
class Target:
    """One field this platform can use, and what it is for."""
    key: str
    label: str
    why: str
    #: True where the same field exists once per residual band, so the mapping
    #: has to say which band it was taken from.
    banded: bool = False


TARGETS: tuple[Target, ...] = (
    Target("risk_id", "Risk ID", "The business's own reference, so a row can be pointed at"),
    Target("process", "(Sub)process", "Which process the risk belongs to — what scoping works from"),
    Target("risk_title", "Risk title", "The risk in the auditee's own words"),
    Target("event", "Risk event", "What could happen; often a taxonomy value such as ORX level 2"),
    Target("cause", "Cause", "Why it could happen; often ORX cause level 1 and 2"),
    Target("impact_categories", "Impact categories",
           "Which kinds of damage: financial, reputational, regulatory, operational, customers"),
    Target("inherent_likelihood", "Inherent likelihood", "Before controls"),
    Target("inherent_impact", "Inherent impact", "Before controls"),
    Target("inherent_exposure", "Inherent exposure", "The combined rating before controls"),
    Target("inherent_rationale", "Inherent rating rationale", "Why that rating before controls"),
    Target("key_risk", "Key risk",
           "The business's own yes/no flag. The single most useful column for scoping: "
           "it says where the auditee itself thinks the risk sits"),
    Target("controls", "Controls in place", "What is said to mitigate it; may be a reference"),
    Target("control_effectiveness", "Control effectiveness", "How well the control environment works"),
    # Three fields the first draft of this list did not have. They were added
    # after reading a real template, which carries a rationale for the inherent
    # rating as well as the residual one, and a likelihood and impact under each
    # residual band rather than only a combined exposure. Guessing the shape of
    # the data would have quietly dropped all three.
    Target("residual_likelihood", "Residual likelihood", "Likelihood after controls", banded=True),
    Target("residual_impact", "Residual impact", "Impact after controls", banded=True),
    Target("residual_exposure", "Residual exposure", "The combined rating after controls", banded=True),
    Target("residual_rationale", "Residual rationale", "Why that residual rating", banded=True),
    Target("risk_response", "Risk response", "What the business decided to do about it"),
)

TARGET_KEYS = tuple(t.key for t in TARGETS)
BY_KEY = {t.key: t for t in TARGETS}


# ── Values ───────────────────────────────────────────────────────────────────
_RATING = re.compile(r"^\s*\(?(\d+)\)?\s*[-–—:.]?\s*(.*)$")


def parse_rating(text: str) -> dict:
    """`"(4) Likely"` → score 4, label "Likely", and the raw string beside them.

    The raw value is kept because the score only means something inside its own
    template: a 4 on a five-point scale and a 4 on a ten-point scale are not the
    same judgement, and nothing here invents an ordering between templates. A
    value with no number keeps its label alone.
    """
    raw = (text or "").strip()
    if not raw:
        return {}
    m = _RATING.match(raw)
    if m and m.group(1):
        label = m.group(2).strip()
        return {"score": int(m.group(1)), "label": label or raw, "raw": raw}
    return {"label": raw, "raw": raw}


_YES = {"yes", "y", "true", "ja", "1", "key", "key risk"}
_NO = {"no", "n", "false", "nee", "0", "not a key risk"}


def parse_flag(text: str) -> bool | None:
    """Yes/no, or None when the cell says something else — which is not a no."""
    value = (text or "").strip().lower()
    if value in _YES:
        return True
    if value in _NO:
        return False
    return None


_RATING_FIELDS = {"inherent_likelihood", "inherent_impact", "inherent_exposure",
                  "control_effectiveness", "residual_likelihood", "residual_impact",
                  "residual_exposure"}


def project(raw: dict, columns: list[dict], primary_band: str | None = None) -> dict:
    """Turn one source row into the fields the platform can use.

    `columns` is the template's mapping, in column order. Every mapped column
    contributes its field; every unmapped one is listed by name under
    `unmapped`, so the count of columns nobody claimed is visible rather than
    absent. `raw` is untouched — re-projecting under a corrected mapping never
    needs the file again.

    Banded fields are the reason this is not a flat copy. A real export carries
    two residual bands, each with its own likelihood, impact, exposure and
    rationale, and both are true about different moments. Every band is kept
    under `by_band`; a value is promoted to the top level only when one band
    supplies it, or when `primary_band` says which one the audit reads. Two
    bands and no choice leaves `needs_band_choice` on the row instead of
    silently promoting whichever column came last.
    """
    out: dict = {"unmapped": []}
    banded: dict[str, dict[str, object]] = {}

    def value_of(target: str, text: str):
        if target in _RATING_FIELDS:
            return parse_rating(text) or None
        if target == "key_risk":
            return parse_flag(text)
        return text or None

    for col in columns:
        name = col.get("column") or ""
        target = col.get("target")
        text = (raw.get(name) or "").strip()
        if not target:
            if name:
                out["unmapped"].append(name)
            continue
        if target not in BY_KEY:
            continue
        value = value_of(target, text)
        if value is None:
            continue
        band = (col.get("band") or "").strip()
        if BY_KEY[target].banded and band:
            banded.setdefault(band, {})[target] = value
        else:
            out[target] = value

    if banded:
        out["by_band"] = banded
        for target in {t for fields in banded.values() for t in fields}:
            bands_with = [b for b, fields in banded.items() if target in fields]
            if len(bands_with) == 1:
                out[target] = banded[bands_with[0]][target]
                out.setdefault("bands", {})[target] = bands_with[0]
            elif primary_band and primary_band in bands_with:
                out[target] = banded[primary_band][target]
                out.setdefault("bands", {})[target] = primary_band
            else:
                out.setdefault("needs_band_choice", []).append(target)
    return out


def mapped_targets(columns: list[dict]) -> list[str]:
    return [c["target"] for c in columns if c.get("target") in BY_KEY]


def coverage(columns: list[dict]) -> dict:
    """What this template does and does not claim to read.

    Reported as three numbers rather than a percentage: a template that maps ten
    of fifteen fields and leaves twelve columns unclaimed is a different thing
    from one that maps ten and claims everything.
    """
    targets = mapped_targets(columns)
    return {
        "columns": len(columns),
        "mapped": len(targets),
        "unmapped": sum(1 for c in columns if not c.get("target")),
        "targets_covered": sorted(set(targets)),
        "targets_missing": [k for k in TARGET_KEYS if k not in targets],
    }


# ── Reliance ─────────────────────────────────────────────────────────────────
async def may_rely_on(import_id: str) -> tuple[bool, str]:
    """Whether this import may be leaned on yet, and why not when it may not.

    The moment Internal Audit builds on second-line work, that is *reliance*,
    and the standards require assessing the quality of what you rely on before
    relying on it. This gate exists before the thing it gates: nothing flows into
    the matrix or into scope yet, and when it does, it comes through here.

    `extent = "none"` is a decision too — the auditor looked and chose not to
    lean on it — and it blocks the flow just as an absent decision does, but for
    a reason that is on the record.
    """
    async with AsyncSessionLocal() as db:
        decision = (await db.execute(
            select(RelianceDecision)
            .where(RelianceDecision.rcsa_import_id == import_id)
            .order_by(RelianceDecision.decided_at.desc())
        )).scalars().first()

    if decision is None:
        return False, ("No reliance decision has been recorded for this RCSA. "
                       "Assess the quality of the second-line work before relying on it.")
    if not decision.quality_assessed:
        return False, "The quality of this RCSA has not been assessed yet."
    if decision.extent == "none":
        return False, f"Reliance was declined: {decision.rationale or 'no rationale recorded'}"
    return True, f"Reliance: {decision.extent} — {decision.rationale}"


async def reproject(import_id: str) -> int:
    """Re-run the template over rows already stored. Returns rows rewritten.

    The correction path. An auditor who mapped the wrong residual band fixes the
    template and calls this; the source rows are untouched, because they were
    kept whole on the way in.
    """
    async with AsyncSessionLocal() as db:
        imp = await db.get(RcsaImport, import_id)
        if not imp or not imp.template_id:
            return 0
        template = await db.get(RcsaTemplate, imp.template_id)
        if not template:
            return 0
        columns = json.loads(template.columns or "[]")
        primary = template.primary_band
        rows = (await db.execute(
            select(RcsaRow).where(RcsaRow.import_id == import_id)
        )).scalars().all()

        for row in rows:
            raw = json.loads(row.raw or "{}")
            projected = project(raw, columns, primary)
            row.projected = json.dumps(projected)
            row.risk_title = (projected.get("risk_title") or "")[:500] or None
            row.process = (projected.get("process") or "")[:300] or None
            row.key_risk = projected.get("key_risk")
        await db.commit()
        return len(rows)


# ── The proposal ─────────────────────────────────────────────────────────────
PROPOSER_SYSTEM = (
    "You read a risk-and-control self-assessment exported from a bank's risk system and work out "
    "what each column holds. Export templates differ per department and per year, so you judge "
    "from the column name AND the sample values under it. You never force a match: a column that "
    "holds something the audit platform has no field for is left unmapped, and you say so."
)


def _targets_block() -> str:
    lines = []
    for t in TARGETS:
        banded = " [exists once per band — say which band]" if t.banded else ""
        lines.append(f"- {t.key}: {t.label} — {t.why}{banded}")
    return "\n".join(lines)


async def propose_mapping(names: list[str], samples: list[list[str]],
                          bands: list[str] | None = None) -> dict:
    """Ask what each column is. Returns {"columns": [...], "notes": str}.

    The header names and three sample rows go in; one proposal per column comes
    back. Nothing is stored from this: a person confirms it, and their
    confirmation is the template.
    """
    from services.agent_contract import run_agent
    from services.agent_schemas import RcsaMappingProposal

    sample_block = "\n".join(
        "| " + " | ".join((row[i] if i < len(row) else "")[:60] for i in range(len(names))) + " |"
        for row in samples[:3]
    )
    band_block = ""
    if bands and any(bands):
        band_block = "\nTHE BAND EACH COLUMN SITS UNDER:\n" + "\n".join(
            f"- {n}: {b}" for n, b in zip(names, bands) if b)

    prompt = f"""Work out what each column of this RCSA export holds.

COLUMNS, in order:
{chr(10).join(f'- {n}' for n in names)}
{band_block}

THE FIRST ROWS UNDER THEM:
{sample_block or '(no data rows were found under this header)'}

TARGET FIELDS the audit platform can use:
{_targets_block()}

Rules:
- One entry per column, in the same order, including columns that map to nothing.
- Judge from the values as much as the name. A column called "Likelihood" under
  an inherent band and one under a residual band are different fields.
- Where a target field exists once per band, the band decides which one it is.
  If you cannot tell which band a column belongs to, leave it unmapped and say
  why in `why` — an audit that reads the wrong residual rating has no way to
  notice.
- Leave `target` null for anything the list does not cover: internal reference
  numbers, comment columns, cross-references to another sheet, empty columns.
"""
    result = await run_agent(PROPOSER_SYSTEM, prompt, RcsaMappingProposal, max_tokens=6_000,
                             description="Return one proposal per column, in column order.")
    proposal = result.data.model_dump()
    # The model answers about the columns it was given; anything else it invents
    # is dropped here rather than offered to the person confirming.
    known = set(names)
    proposal["columns"] = [c for c in proposal["columns"] if c["column"] in known]
    proposal["meta"] = result.meta.as_dict()
    return proposal
