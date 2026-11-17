"""Reading an RCSA the platform has never seen before.

    venv/Scripts/python.exe -m tests.test_rcsa_import

Two exports, shaped on purpose to share almost nothing: `tests/rcsa_fixtures`.
One follows a real template — a title block, a banded multi-row header with
merged group cells, two residual bands and ratings written as "(4) Likely". The
other is the same audit content under a different template. A parser that only
reads the first is a hardcoded parser with extra steps.

No API calls: the column proposal is the one part that asks a model, and it is
measured separately (see the commit that introduced this). Everything here is
the machinery around it, which has to hold without one.
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.rcsa import RcsaImport, RcsaRow, RcsaTemplate, RelianceDecision
from services import rcsa_mapping as mapping
from services.rcsa_source import (
    column_names, data_rows, expand_merges, header_candidates, source_for,
)
from tests.rcsa_fixtures import other_shape, photo_shape

failures: list[str] = []
TMP = Path(tempfile.mkdtemp())
IMPORT_ID = "test-rcsa-" + uuid4().hex[:8]


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _ensure():
    import models  # noqa: F401
    from database import create_tables
    await create_tables()


async def _clean():
    async with AsyncSessionLocal() as db:
        for row in (await db.execute(
            select(RcsaRow).where(RcsaRow.import_id == IMPORT_ID))).scalars().all():
            await db.delete(row)
        for dec in (await db.execute(
            select(RelianceDecision).where(
                RelianceDecision.rcsa_import_id == IMPORT_ID))).scalars().all():
            await db.delete(dec)
        imp = await db.get(RcsaImport, IMPORT_ID)
        if imp:
            if imp.template_id:
                tpl = await db.get(RcsaTemplate, imp.template_id)
                if tpl:
                    await db.delete(tpl)
            await db.delete(imp)
        await db.commit()


# ── The sheet ────────────────────────────────────────────────────────────────
def test_the_header_is_found_under_a_title_block():
    print("finding the header:")
    ref = photo_shape(TMP / "photo.xlsx")
    grid = source_for(ref).preview(ref)

    best = header_candidates(grid)[0]
    check(best.row == 7, f"the column names are on row 7, not row 1 ({best.row})")
    check(grid[0][0] == "Risk Assessment", "row 1 is the title block, as in the real export")

    other = other_shape(TMP / "other.xlsx")
    check(header_candidates(source_for(other).preview(other))[0].row == 6,
          "and on row 6 in a template with a deeper title block")


def test_a_merged_band_covers_its_own_range_and_no_more():
    print("the banded header:")
    rows = [["A", "", "", "B", ""], ["1", "2", "3", "4", "5"]]
    filled = expand_merges(rows, [(1, 1, 1, 3), (1, 4, 1, 5)])
    check(filled[0] == ["A", "A", "A", "B", "B"], f"each band fills its range ({filled[0]})")

    # Carrying the last band rightwards until "the next one" would run it off
    # the end of the row and stamp it on every column after it.
    one = expand_merges([["A", "", "", "", ""]], [(1, 1, 1, 2)])
    check(one[0] == ["A", "A", "", "", ""], f"and stops where the merge stops ({one[0]})")


def test_the_two_residual_bands_stay_apart():
    print("two residual ratings, one export:")
    ref = photo_shape(TMP / "photo.xlsx")
    grid = source_for(ref).preview(ref)
    names = column_names(grid, [5, 6, 7])

    likelihoods = [n for n in names if n.endswith("Likelihood")]
    check(len(set(likelihoods)) == len(likelihoods) and likelihoods,
          f"no two columns share a name ({likelihoods})")
    check(any("during Change implementation" in n and "Exposure (residual)" in n for n in names)
          and any("going live" in n and "Exposure (Mitigated)" in n for n in names),
          "each residual exposure carries the band it belongs to")

    rows = data_rows(grid, [5, 6, 7])
    check([r for r, _ in rows] == [8, 9, 10], f"the data starts under the header ({[r for r, _ in rows]})")


# ── The mapping ──────────────────────────────────────────────────────────────
def test_a_value_keeps_what_it_said():
    print("values:")
    check(mapping.parse_rating("(4) Likely") == {"score": 4, "label": "Likely", "raw": "(4) Likely"},
          "a coded rating gives up its number and its word")
    check(mapping.parse_rating("Medium") == {"label": "Medium", "raw": "Medium"},
          "and a rating with no number keeps only the word — no score is invented")
    check(mapping.parse_rating("") == {}, "an empty cell is nothing, not a zero")
    check(mapping.parse_flag("Yes") is True and mapping.parse_flag("No") is False,
          "a yes/no column reads as a flag")
    check(mapping.parse_flag("Not applicable") is None,
          "and anything else is unknown, which is not a no")


def test_an_unmapped_column_is_reported_and_kept():
    print("a column nobody claimed:")
    columns = [{"column": "Risk title", "target": "risk_title"},
               {"column": "Owner", "target": None},
               {"column": "Last reviewed", "target": None}]
    raw = {"Risk title": "Incorrect information", "Owner": "A. Jansen",
           "Last reviewed": "2026-03-01"}
    projected = mapping.project(raw, columns)
    check(projected["unmapped"] == ["Owner", "Last reviewed"],
          f"it is named ({projected['unmapped']})")
    check(mapping.coverage(columns)["unmapped"] == 2, "and counted")
    check("Owner" in raw and raw["Owner"] == "A. Jansen",
          "and the source row still holds it — reported, never dropped")


def test_which_residual_band_is_read_is_a_decision():
    print("one row, two residual ratings:")
    columns = [
        {"column": "Exposure (residual)", "target": "residual_exposure",
         "band": "Residual Risk Rating during Change implementation"},
        {"column": "Exposure (Mitigated)", "target": "residual_exposure",
         "band": "Residual Risk rating when going live"},
    ]
    raw = {"Exposure (residual)": "(2) Moderate", "Exposure (Mitigated)": "(1) Low"}

    undecided = mapping.project(raw, columns)
    check("residual_exposure" not in undecided,
          "with no choice made, nothing is promoted to 'the' residual rating")
    check(undecided["needs_band_choice"] == ["residual_exposure"],
          "the row says a choice is owed")
    check(len(undecided["by_band"]) == 2, "and both bands are kept, in full")

    chosen = mapping.project(raw, columns, "Residual Risk rating when going live")
    check(chosen["residual_exposure"]["score"] == 1,
          f"once chosen, that band's value is the one read ({chosen['residual_exposure']})")
    check(chosen["bands"]["residual_exposure"] == "Residual Risk rating when going live",
          "and the row says which band it came from")


# ── Storage, re-projection, reliance ─────────────────────────────────────────
def test_a_correction_is_a_reprojection_not_a_reupload():
    print("correcting the mapping:")

    async def run():
        await _ensure()
        await _clean()
        columns = [
            {"column": "Risk title", "target": "risk_title"},
            {"column": "Exposure (residual)", "target": "residual_exposure", "band": "during change"},
            {"column": "Exposure (Mitigated)", "target": "residual_exposure", "band": "go-live"},
        ]
        raw = {"Risk title": "Incorrect information",
               "Exposure (residual)": "(2) Moderate", "Exposure (Mitigated)": "(1) Low"}

        async with AsyncSessionLocal() as db:
            tpl = RcsaTemplate(id="tpl-" + IMPORT_ID, name="test", columns=json.dumps(columns),
                               header_rows="[7]", primary_band="during change")
            db.add(tpl)
            db.add(RcsaImport(id=IMPORT_ID, engagement_id="test-rcsa-eng",
                              original_filename="x.xlsx", file_path="x.xlsx",
                              template_id=tpl.id, status="imported", row_count=1))
            db.add(RcsaRow(id="row-" + IMPORT_ID, import_id=IMPORT_ID, sheet_row=8,
                           raw=json.dumps(raw),
                           projected=json.dumps(mapping.project(raw, columns, "during change"))))
            await db.commit()

        first = await _row_projection()
        async with AsyncSessionLocal() as db:
            tpl = await db.get(RcsaTemplate, "tpl-" + IMPORT_ID)
            tpl.primary_band = "go-live"          # the auditor meant the other band
            await db.commit()
        count = await mapping.reproject(IMPORT_ID)
        second = await _row_projection()
        return first, second, count

    first, second, count = asyncio.run(run())
    check(first["residual_exposure"]["score"] == 2, "the first reading takes the band it was told")
    check(count == 1 and second["residual_exposure"]["score"] == 1,
          f"after the correction it takes the other ({second['residual_exposure']})")
    check(first["risk_title"] == second["risk_title"] == "Incorrect information",
          "the source row never changed — no file was read again")


async def _row_projection() -> dict:
    async with AsyncSessionLocal() as db:
        row = await db.get(RcsaRow, "row-" + IMPORT_ID)
        return json.loads(row.projected)


def test_nothing_may_be_relied_on_until_someone_decided():
    print("reliance:")

    async def run():
        allowed_before, why_before = await mapping.may_rely_on(IMPORT_ID)

        async def decide(assessed, extent, rationale):
            async with AsyncSessionLocal() as db:
                db.add(RelianceDecision(id=str(uuid4()), rcsa_import_id=IMPORT_ID,
                                        quality_assessed=assessed, extent=extent,
                                        rationale=rationale))
                await db.commit()
            return await mapping.may_rely_on(IMPORT_ID)

        declined = await decide(True, "none", "Sample testing showed the ratings were stale")
        allowed = await decide(True, "partial", "Design assessed; we re-test the key controls")
        return (allowed_before, why_before), declined, allowed

    (before, why), declined, allowed = asyncio.run(run())
    check(before is False and "No reliance decision" in why,
          f"an import nobody decided about cannot be leaned on ({why[:48]})")
    check(declined[0] is False and "declined" in declined[1],
          "a decision NOT to rely is a decision, and it is on the record")
    check(allowed[0] is True and "partial" in allowed[1],
          f"and a recorded, assessed decision opens it ({allowed[1][:56]})")
    asyncio.run(_clean())


def test_nothing_reaches_the_matrix_before_the_decision():
    print("into the matrix:")
    from models.racm import RacmRisk
    from services import rcsa_to_spine

    ENG = "test-rcsa-eng"

    async def run():
        await _ensure()
        await _clean()
        columns = [{"column": "Risk title", "target": "risk_title"},
                   {"column": "Key risk", "target": "key_risk"},
                   {"column": "Exposure (residual)", "target": "residual_exposure",
                    "band": "at go-live"},
                   {"column": "Controls", "target": "controls"}]
        rows = [
            ({"Risk title": "Incorrect information", "Key risk": "Yes",
              "Exposure (residual)": "(4) High", "Controls": "See R48"}, 8),
            ({"Risk title": "Wrong methodology", "Key risk": "No",
              "Exposure (residual)": "(1) Low", "Controls": "Quarterly review"}, 9),
        ]
        async with AsyncSessionLocal() as db:
            tpl = RcsaTemplate(id="tpl-" + IMPORT_ID, name="t", columns=json.dumps(columns),
                               header_rows="[1]", primary_band="at go-live")
            db.add(tpl)
            db.add(RcsaImport(id=IMPORT_ID, engagement_id=ENG, original_filename="AM RCSA.xlsx",
                              file_path="x.xlsx", template_id=tpl.id, status="imported",
                              row_count=len(rows)))
            for raw, sheet_row in rows:
                projected = mapping.project(raw, columns, "at go-live")
                db.add(RcsaRow(id=f"row-{sheet_row}-{IMPORT_ID}", import_id=IMPORT_ID,
                               sheet_row=sheet_row, raw=json.dumps(raw),
                               projected=json.dumps(projected),
                               risk_title=projected.get("risk_title"),
                               key_risk=projected.get("key_risk")))
            await db.commit()

        refused = await rcsa_to_spine.propose_rows(ENG, IMPORT_ID)

        async with AsyncSessionLocal() as db:
            db.add(RelianceDecision(id=str(uuid4()), rcsa_import_id=IMPORT_ID,
                                    quality_assessed=True, extent="partial",
                                    rationale="Design assessed"))
            await db.commit()
        pushed = await rcsa_to_spine.propose_rows(ENG, IMPORT_ID)

        async with AsyncSessionLocal() as db:
            written = (await db.execute(
                select(RacmRisk).where(RacmRisk.engagement_id == ENG))).scalars().all()
            provenance = [json.loads(r.provenance or "{}") for r in written]
            titles = [r.title for r in written]
            ratings = [r.inherent_rating for r in written]
            for r in written:
                await db.delete(r)
            await db.commit()
        return refused, pushed, titles, provenance, ratings

    refused, pushed, titles, provenance, ratings = asyncio.run(run())
    check(refused["written"] == 0 and refused["refused"],
          f"before a reliance decision nothing is written ({refused['reason'][:40]})")
    check(pushed["written"] == 1 and titles == ["Incorrect information"],
          f"the default selection is the business's own key risks ({titles})")
    check(provenance[0]["source_id"] == "row-8-" + IMPORT_ID,
          "the proposal names the row it came from")
    check("sheet row 8" in provenance[0]["source_ref"] and "AM RCSA.xlsx" in provenance[0]["source_ref"],
          f"and says it in words the auditor can follow ({provenance[0]['source_ref']})")
    check(provenance[0]["rationale"].startswith(mapping.AUDITEE_LABEL),
          "the rationale opens by saying whose assessment this is")
    check(ratings == ["high"], f"'High' is carried across as high — the same word ({ratings})")
    asyncio.run(_clean())


def test_a_rating_on_someone_elses_scale_is_not_converted():
    print("their scale is not ours:")
    from services.rcsa_to_spine import _rating_of

    rating, note = _rating_of({"residual_exposure": {"label": "Likely", "raw": "(4) Likely",
                                                     "score": 4}})
    check(rating == "medium" and "(4) Likely" in note,
          f"a position on their scale is quoted, not translated ({rating}, {note})")
    plain, plain_note = _rating_of({"residual_exposure": {"label": "High", "raw": "High"}})
    check(plain == "high" and not plain_note, "a word both sides use is simply the same word")
    none, none_note = _rating_of({})
    check(none == "medium" and "no rating" in none_note, "and no rating says so")


def test_the_auditee_label_cannot_be_dropped():
    print("whose assessment it is:")
    check("auditee" in mapping.AUDITEE_LABEL.lower(), f"the label says so ({mapping.AUDITEE_LABEL})")

    router = (Path(__file__).resolve().parent.parent / "routers" / "rcsa.py").read_text(encoding="utf-8")
    payloads = router.count("_label({")
    check(payloads >= 4, f"every payload carrying rows goes through _label ({payloads})")
    check("return {**payload, \"auditee_label\": mapping.AUDITEE_LABEL}" in router,
          "and _label is what attaches it")
    for endpoint in ("async def rows", "async def list_imports", "async def confirm"):
        body = router.split(endpoint, 1)[1].split("@router", 1)[0]
        check("_label(" in body, f"{endpoint.split()[-1]} carries it")

    page = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "pages"
            / "planning" / "RcsaPage.jsx")
    if page.exists():
        check("auditee_label" in page.read_text(encoding="utf-8"),
              "and the page shows it rather than printing its own heading")


def main():
    test_the_header_is_found_under_a_title_block()
    test_a_merged_band_covers_its_own_range_and_no_more()
    test_the_two_residual_bands_stay_apart()
    test_a_value_keeps_what_it_said()
    test_an_unmapped_column_is_reported_and_kept()
    test_which_residual_band_is_read_is_a_decision()
    test_a_correction_is_a_reprojection_not_a_reupload()
    test_nothing_may_be_relied_on_until_someone_decided()
    test_nothing_reaches_the_matrix_before_the_decision()
    test_a_rating_on_someone_elses_scale_is_not_converted()
    test_the_auditee_label_cannot_be_dropped()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
