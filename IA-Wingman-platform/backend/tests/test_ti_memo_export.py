"""Topic Intelligence memo as a Word file.

    venv/Scripts/python.exe -m tests.test_ti_memo_export

The memo lived on one page only. The file has to say what the page says, mark what the
auditor selected and what was left out, and print an unsettled point as unsettled.
No API calls.
"""
import asyncio
import io
import json
import sys
from uuid import uuid4

from docx import Document
from sqlalchemy import select

import main  # noqa: F401  (registers every model)
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import TopicIntelligence
from routers.planning import export_topic_memo_word
from services.topic_memo_export import generate_topic_memo_docx

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def memo(accepted=False):
    return {
        "memo_accepted": accepted,
        "topic_primer": "AI in a bank means systems that decide or advise.\n- **In practice:** auditors look at the inventory.\n- **Why it matters:** biased outcomes harm customers.",
        "conclusion": "Scope AI governance for credit and fraud use cases.",
        "verification": {"checks": [
            {"claim": "High-risk duties apply from 2 December 2027", "verdict": "confirmed",
             "finding": "Regulation (EU) 2026/1744 says so.", "source_url": "https://eur-lex.europa.eu/a"},
            {"claim": "DNB published AI priorities", "verdict": "not_found", "finding": "No official DNB page found.", "source_url": None}],
            "searches_used": 3, "searches_allowed": 4},
        "key_risk_areas": [{"title": "Model inventory gaps", "rationale": "No complete register.", "basis": "AI Act Art. 26", "included": True},
                           {"title": "Left-out risk", "rationale": "Not now.", "included": False}],
        "excluded_areas": [{"title": "Marketing AI", "rationale": "Low impact.", "included": True}],
        "interview_agenda": {
            "key_audit_questions": [{"question_text": "Does the bank know every AI system?", "included": True}],
            "sponsor": [{"question_text": "What does success look like?", "included": True}],
            "sme": [{"question_text": "How is a system inventoried?", "included": True},
                    {"question_text": "Unticked expert question", "included": False}],
            "ia_prework": ["Read the AI policy"]},
        "proposed_frameworks": [
            {"framework_code": "EU-AI-ACT", "framework_name": "EU AI Act", "tier": "core", "jurisdiction": "EU",
             "applicability_rationale": "Directly applicable.", "included": True},
            {"framework_code": "CCD2", "framework_name": "Consumer Credit Directive 2", "tier": "optional",
             "jurisdiction": "EU", "included": False}],
        "lens1_summary": "Formal law applies.\n- The AI Act is the core instrument.",
        "lens1_sources": [{"title": "AI Act", "url": "https://eur-lex.europa.eu/a", "date": "2024"}],
        "lens1_search": {"web_search": True, "used": 3, "allowed": 8, "errors": [], "queries": ["AI Act amendments 2026"]},
        "lens2_summary": "Supervisors focus on governance.", "lens2_sources": [],
        "lens2_search": {"web_search": True, "used": 0, "allowed": 8, "errors": []},
        "lens3_summary": None, "lens4_notes": "Prior audit found no AI register.",
    }


def read(docx_bytes):
    doc = Document(io.BytesIO(docx_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def test_the_file_says_what_the_page_says():
    print("the document:")
    text = read(generate_topic_memo_docx(memo(), {"name": "Artificial Intelligence", "audit_code": "26-047", "entity": "GRP"}))
    check("Topic Intelligence memo: Artificial Intelligence" in text and "26-047" in text, "title and audit code")
    check("Draft: not yet accepted by the auditor" in text and "AI-assisted research" in text,
          "it says it is a draft and AI-assisted")
    check("In practice: auditors look at the inventory." in text and "**" not in text, "the primer is readable, without markdown marks")
    check("Confirmed: High-risk duties apply from 2 December 2027" in text and "https://eur-lex.europa.eu/a" in text,
          "a confirmed point carries its source")
    check("Not settled: DNB published AI priorities" in text, "an unsettled point is printed as unsettled")
    check("Model inventory gaps" in text and "Left-out risk" not in text and "1 further proposed item not selected" in text,
          "selected items are listed and the count of those left out is stated")
    check("Unticked expert question" not in text and "Does the bank know every AI system?" in text and "What does success look like?" in text,
          "questions appear under their own place, only the ticked ones")
    check("1 of 2 proposed frameworks selected" in text and "Consumer Credit Directive 2 (Optional, EU, Not selected)" in text,
          "frameworks show their tier and whether they were selected")
    check("3 of 8 searches used." in text and "Searched for: AI Act amendments 2026" in text, "each lens shows its searches")
    check("No searches ran: treat this summary as written from memory" in text, "a lens that did not search says so")
    check("Prior audit found no AI register." in text, "the auditor's own context is included")
    accepted = read(generate_topic_memo_docx(memo(accepted=True), {"name": "AI", "audit_code": None, "entity": "GRP"}))
    check("Accepted by the auditor" in accepted and "TBD" in accepted, "an accepted memo says so; a missing audit code reads TBD")
    bare = read(generate_topic_memo_docx({"status": "review"}, {"name": "AI", "entity": "GRP"}))
    check("Topic Intelligence memo: AI" in bare, "a memo with almost nothing in it still produces a file")


async def test_the_endpoint_serves_a_word_file():
    print("the endpoint:")
    eid = f"tmp-export-{uuid4()}"
    async with AsyncSessionLocal() as db:
        db.add(Engagement(id=eid, audit_code="TMP-EX", name="AI", entity="GRP", audit_type="it", team_members="[]"))
        db.add(TopicIntelligence(id=str(uuid4()), engagement_id=eid, status="review", topic_primer="Lead sentence here.",
                                 key_risk_areas=json.dumps([{"title": "A risk", "included": True}])))
        await db.commit()
    try:
        async with AsyncSessionLocal() as db:
            response = await export_topic_memo_word(eid, db)
        check(response.media_type.endswith("wordprocessingml.document") and "TMP-EX" in response.headers["content-disposition"],
              "a Word file named after the audit")
        check("A risk" in read(response.body), "built from the stored memo")
        async with AsyncSessionLocal() as db:
            try:
                await export_topic_memo_word("does-not-exist", db)
                missing = False
            except Exception as exc:  # noqa: BLE001
                missing = getattr(exc, "status_code", None) == 404
        check(missing, "an audit that does not exist is a 404")
    finally:
        async with AsyncSessionLocal() as db:
            for row in (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == eid))).scalars().all():
                await db.delete(row)
            e = await db.get(Engagement, eid)
            if e:
                await db.delete(e)
            await db.commit()


def main_():
    test_the_file_says_what_the_page_says()
    asyncio.run(test_the_endpoint_serves_a_word_file())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
