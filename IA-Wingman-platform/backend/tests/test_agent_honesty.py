"""Tests for the claims the agents make about their own work.

Run from the backend dir:
    venv/Scripts/python.exe -m tests.test_agent_honesty

Deterministic and read-only: no AI calls and no writes to the database.

Each of these guards a claim that was once made and was not true:

  * the AI peer review rated audit QUALITY from row counts, and eight of its
    twelve criteria had no evidence in the prompt at all;
  * a criterion this platform cannot record was scored as a failure of the
    audit rather than a limit of the tool;
  * "6 documents assessed" meant six files existed, not that they were read;
  * a drafted finding with a missing field erased what the auditor had typed;
  * autonomy kept spending on engagements that were already closed.

They are here so that none of them can quietly come back.
"""
import asyncio
import sys

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.reporting import Finding
from services import copilot_service
from services.doc_context import clip_documents
from services.review_service import (
    PEER_REVIEW_CRITERIA, criteria_for_phase, score_peer_review,
    _load_peer_review_context, _peer_review_blocks, _clip, _rows,
)

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


# ── The peer review reads the file ───────────────────────────────────────────

def test_every_criterion_has_evidence_or_is_declared_unrecordable():
    print("peer review — every criterion is backed by something:")
    no_record = [c["nr"] for c in PEER_REVIEW_CRITERIA if c.get("platform_evidence") is False]
    check(no_record == [9],
          f"exactly one criterion is declared unrecordable (the closing meeting); got {no_record}")

    async def run():
        async with AsyncSessionLocal() as db:
            eng = (await db.execute(select(Engagement))).scalars().first()
            blocks = await _peer_review_blocks(eng.id, db)
        return blocks

    blocks = asyncio.run(run())
    missing = [c["nr"] for c in PEER_REVIEW_CRITERIA
               if c.get("platform_evidence") is not False and c["nr"] not in blocks]
    check(not missing, f"every recordable criterion gets its own evidence block; missing {missing}")
    check(9 not in blocks, "the unrecordable criterion gets no block rather than an invented one")


def test_the_pack_carries_content_not_counts():
    print("peer review — the pack is the file, not a tally:")

    async def run():
        async with AsyncSessionLocal() as db:
            # The engagement with the most findings: where counting was most blind.
            best, best_n = None, -1
            for e in (await db.execute(select(Engagement))).scalars().all():
                n = len((await db.execute(
                    select(Finding).where(Finding.engagement_id == e.id)
                )).scalars().all())
                if n > best_n:
                    best, best_n = e, n
            findings = (await db.execute(
                select(Finding).where(Finding.engagement_id == best.id)
            )).scalars().all()
            ctx = await _load_peer_review_context(
                best.id, db, [c["nr"] for c in criteria_for_phase("fieldwork")],
            )
        return best, findings, ctx

    eng, findings, ctx = asyncio.run(run())
    check(len(ctx) > 3000, f"the fieldwork pack is substantial, not a handful of status lines ({len(ctx):,} chars)")

    # The actual words of a finding must reach the reviewer, not just its count.
    quoted = 0
    for f in findings:
        for field in (f.condition, f.criteria, f.effect, f.cause):
            head = " ".join((field or "").split())[:60]
            if head and head in ctx:
                quoted += 1
    check(quoted >= 2, f"the findings' own text reaches the reviewer ({quoted} field(s) found verbatim)")

    # And the supporting context must carry the audit's intent, not a row count.
    check("Overall objective:" in ctx, "the engagement's stated objective is in the pack")
    check("Key audit questions" in ctx, "the key audit questions are in the pack")


def test_a_phase_review_only_pays_for_its_own_phase():
    print("peer review — a phase review reads only its phase:")

    async def run():
        async with AsyncSessionLocal() as db:
            eng = (await db.execute(select(Engagement))).scalars().first()
            planning = await _load_peer_review_context(
                eng.id, db, [c["nr"] for c in criteria_for_phase("planning")])
            total = await _load_peer_review_context(
                eng.id, db, [c["nr"] for c in criteria_for_phase("total")])
        return planning, total

    planning, total = asyncio.run(run())
    check(len(planning) < len(total),
          f"a planning review is smaller than a full one ({len(planning):,} < {len(total):,})")
    check("EVIDENCE FOR CRITERION 12" not in planning,
          "a planning review does not carry the final report's evidence")


def test_every_cap_announces_itself():
    print("peer review — nothing is dropped in silence:")
    long_field = "word " * 400
    clipped = _clip(long_field, 100)
    check("truncated here" in clipped and "characters in full" in clipped,
          "a clipped field says it was clipped, and how much there was")
    check(_clip("") == "(empty)" and _clip(None) == "(empty)",
          "an empty field reads as empty rather than as missing data")

    many = _rows([f"- row {i}" for i in range(40)], cap=10)
    check("showing 10 of 40" in many and "30 further row" in many,
          "a capped list states what it left out")
    check(_rows([]) == "  (none recorded)",
          "an empty block reads as 'none recorded' — real evidence of absent work")


# ── Scoring: the tool's blind spots are not the audit's failures ─────────────

def test_unrecordable_criteria_leave_the_score():
    print("peer review — the score measures the audit, not the tool:")
    perfect = [{"title": c["title"], "rating": "na" if c.get("platform_evidence") is False else "gc"}
               for c in PEER_REVIEW_CRITERIA]
    r = score_peer_review(perfect)
    check(r["percentage"] == 100,
          f"a faultless file scores 100%, not a capped 92% ({r['total_score']}/{r['max_score']})")
    check(r["max_score"] == 2 * (len(PEER_REVIEW_CRITERIA) - 1),
          "the unrecordable criterion is out of the maximum, not scored as zero")
    check(r["not_assessable"] == 1, "the count of unrecordable criteria is reported")
    check(any(c["severity"] == "info" for c in r["comments"]),
          "it still produces a comment — 'we cannot see this' is what a reviewer needs told")

    empty = [{"title": c["title"], "rating": "na" if c.get("platform_evidence") is False else "nc"}
             for c in PEER_REVIEW_CRITERIA]
    r = score_peer_review(empty)
    check(r["percentage"] == 0 and r["overall_quality"] == "needs_work",
          "an unevidenced file still scores zero — the change does not soften real gaps")


# ── Documents: a file count is not coverage ─────────────────────────────────

def test_document_coverage_is_measured_not_counted():
    print("documents — what was read, not how many files there were:")
    parts, cov = clip_documents(
        [("Policy.pdf", "x" * 80_000), ("SOP.docx", "y" * 1_000), ("scan.pdf", "")], 4_000)
    check(cov.documents == 3 and cov.documents_empty == 1,
          "unreadable files are counted separately, not passed off as read")
    check(cov.chars_read == 5_000 and cov.chars_total == 81_000,
          f"the meter reports what went in ({cov.chars_read:,} of {cov.chars_total:,})")
    check(cov.percentage == 6 and not cov.complete,
          f"6% of the text, and it says so rather than claiming three documents ({cov.sentence()})")
    check("of 81,000 characters" in cov.sentence() and "no extractable text" in cov.sentence(),
          "the sentence the UI shows carries both numbers")
    check("EXTRACT" in parts[0] and "not absent" in parts[0],
          "the model is told it holds an extract, so an absence is not read as a gap")
    check("EXTRACT" not in parts[1],
          "a document that fitted whole carries no extract warning")

    _, whole = clip_documents([("Short.txt", "z" * 100)], 4_000)
    check(whole.complete and whole.sentence() == "read 1 document in full",
          "when nothing was left behind the wording stays simple")


# ── A draft never erases the auditor ────────────────────────────────────────

def test_the_drafter_cannot_blank_the_auditors_own_text():
    print("finding drafter — the auditor's text survives a partial draft:")
    src = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "services" / "finding_drafter.py").read_text(encoding="utf-8")
    for field in ("condition", "criteria", "cause", "effect", "recommendation"):
        check(f'f.{field} = draft.get("{field}")' not in src,
              f"'{field}' is no longer assigned straight from an absent key")
    check("if value and value.strip():" in src,
          "a field is written only when the model actually returned one")

    # Since the output contract landed, the guarantee is stronger than a guard at
    # the write step: the schema itself refuses a draft with a missing C, so the
    # case the guard defends against cannot reach the database at all.
    from pydantic import ValidationError
    from services.agent_schemas import FindingDraft
    complete = {"title": "No periodic re-screening", "condition": "c", "criteria": "cr",
                "cause": "ca", "effect": "e", "recommendation": "r", "rating": "high",
                "rating_rationale": "because"}
    check(FindingDraft.model_validate(complete).cause == "ca", "a complete draft validates")
    for field in ("condition", "criteria", "cause", "effect", "recommendation"):
        try:
            FindingDraft.model_validate({k: v for k, v in complete.items() if k != field})
            ok = False
        except ValidationError:
            ok = True
        check(ok, f"a draft with no '{field}' is rejected before it can overwrite anything")


# ── Autonomy stops at a closed audit ────────────────────────────────────────

def test_closed_engagements_are_left_alone():
    print("copilot — a closed audit is finished work:")
    check(hasattr(copilot_service, "is_closed"), "there is a single place that answers 'is it closed?'")

    async def run():
        async with AsyncSessionLocal() as db:
            engs = (await db.execute(select(Engagement))).scalars().all()
        closed = [e for e in engs if e.status == "closed"]
        open_ = [e for e in engs if e.status != "closed"]
        results = {}
        if closed:
            results["closed"] = await copilot_service.is_closed(closed[0].id)
        if open_:
            results["open"] = await copilot_service.is_closed(open_[0].id)
        return results

    r = asyncio.run(run())
    check(r.get("closed") is True, "a closed engagement reads as closed")
    check(r.get("open") is False, "an open engagement does not")

    src = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "services" / "copilot_orchestrator.py").read_text(encoding="utf-8")
    check(src.count("is_closed(engagement_id)") >= 4,
          "both scanners, the preflight and the report nudge all check it")


def main():
    test_every_criterion_has_evidence_or_is_declared_unrecordable()
    test_the_pack_carries_content_not_counts()
    test_a_phase_review_only_pays_for_its_own_phase()
    test_every_cap_announces_itself()
    test_unrecordable_criteria_leave_the_score()
    test_document_coverage_is_measured_not_counted()
    test_the_drafter_cannot_blank_the_auditors_own_text()
    test_closed_engagements_are_left_alone()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
