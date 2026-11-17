"""Tests for the retrieval layer (services/retrieval.py).

Run from the backend dir:
    venv/Scripts/python.exe -m tests.test_retrieval

Deterministic and read-only: no AI calls, no network, no writes.

The behaviour being defended is the one that made the old head-of-document clip
wrong rather than merely small: the answer to an audit question is very rarely in
the first four thousand characters of a policy, and an agent that cannot reach it
reports a gap that does not exist.
"""
import sys

from sqlalchemy import select

from database import AsyncSessionLocal
from models.planning import UploadedDocument
from services.doc_context import clip_documents
from services.retrieval import (
    retrieve, split_document, rank, tokens, verify_citation, TARGET_CHARS, MAX_CHARS,
)

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


# A policy of roughly forty pages whose one relevant clause sits near the end —
# the shape of document the old clip could not reach.
NEEDLE = (
    "Beneficial ownership must be identified and verified before onboarding a legal-entity "
    "customer, and the supporting extract from the UBO register must be retained on file."
)


def _long_policy() -> str:
    parts = ["CUSTOMER ACCEPTANCE POLICY\nVersion 4.1 — approved by the Board.\n"]
    for i in range(1, 31):
        parts.append(
            f"\n{i}. Section {i} — general administrative provisions\n"
            + ("This section sets out administrative arrangements, reporting lines, document "
               "retention periods and the annual review cycle applicable to this policy. " * 12)
        )
    parts.append(
        "\n31. Beneficial ownership\n" + NEEDLE + " "
        + "Enhanced due diligence applies where the ownership structure is opaque. " * 6
    )
    for i in range(32, 40):
        parts.append(
            f"\n{i}. Section {i} — further administrative provisions\n"
            + ("Further administrative arrangements, escalation routes and glossary entries "
               "are recorded here for completeness. " * 12)
        )
    return "".join(parts)


def test_documents_split_on_their_own_structure():
    print("chunking — a document is cut where its author cut it:")
    passages = split_document(_long_policy(), "d1", "Customer Acceptance Policy.pdf")
    check(len(passages) > 10, f"a long policy yields many passages ({len(passages)})")
    check(all(len(p.text) <= MAX_CHARS for p in passages),
          "no passage exceeds the hard ceiling")
    headed = [p for p in passages if p.section]
    check(len(headed) > len(passages) * 0.8,
          f"most passages carry the heading they sit under ({len(headed)}/{len(passages)})")
    check(any("Beneficial ownership" in p.section for p in passages),
          "the numbered clause heading is recognised as a heading")

    # Offsets must point back into the original text exactly, or a citation lies.
    body = _long_policy()
    check(all(body[p.char_start:p.char_end].strip().startswith(p.text[:40].strip()[:20])
              for p in passages[:8]),
          "character offsets resolve back to the source text")


def test_the_needle_is_found_where_a_clip_would_miss_it():
    print("ranking — the clause on page thirty is reachable:")
    body = _long_policy()
    query = "beneficial ownership UBO register verification legal entity customer"

    # What the old approach saw.
    old_parts, old_cov = clip_documents([("Customer Acceptance Policy.pdf", body)], 4_000)
    check(NEEDLE not in old_parts[0],
          "the old 4,000-character clip does not contain the relevant clause")
    check(old_cov.percentage < 15,
          f"...because it was {old_cov.percentage}% of the document")

    found = retrieve([("d1", "Customer Acceptance Policy.pdf", body)], query, budget_chars=8_000)
    check(NEEDLE in found.block, "retrieval puts the relevant clause in front of the model")
    check(found.coverage.passages > 0 and found.coverage.percentage < 100,
          f"and still only spends part of the budget ({found.coverage.sentence()})")

    scored = rank(split_document(body, "d1", "policy"), query)
    check(NEEDLE in scored[0][1].text,
          "the relevant passage ranks first, not merely somewhere in the selection")
    check(scored[0][0] > scored[-1][0] * 2,
          "relevance genuinely separates it from the administrative filler")


def test_no_document_goes_unopened():
    print("fairness — one long file cannot crowd out the others:")
    loud = "governance control policy requirement evidence " * 2000     # long and on-topic
    quiet = ("SUPPLIER CODE\n1. Scope\nThis short code covers third-party conduct and the "
             "beneficial ownership disclosures expected of suppliers.\n")
    found = retrieve(
        [("big", "Big Manual.pdf", loud), ("small", "Supplier Code.docx", quiet)],
        "beneficial ownership disclosure", budget_chars=6_000,
    )
    docs = {p.doc_id for p in found.passages}
    check(docs == {"big", "small"}, f"both documents contribute a passage ({sorted(docs)})")
    check(found.coverage.documents_hit == 2, "the coverage meter reports both were opened")

    none_floor = retrieve(
        [("big", "Big Manual.pdf", loud), ("small", "Supplier Code.docx", quiet)],
        "beneficial ownership disclosure", budget_chars=6_000, per_document_floor=0,
    )
    check(len({p.doc_id for p in none_floor.passages}) >= 1,
          "without the floor the selection is purely by rank (the control case)")


def test_the_prompt_block_is_honest_and_citable():
    print("the block — what the model is told about what it holds:")
    found = retrieve([("d1", "Policy.pdf", _long_policy())],
                     "beneficial ownership", budget_chars=6_000)
    check("You are NOT seeing the whole of these documents" in found.block,
          "the model is told it holds a selection")
    check("not absent" in found.block,
          "...and that an absence in the selection is not evidence of a gap")
    check("cite it by its [P#] id" in found.block, "the model is told how to cite")
    check(all(f"[{p.cid}]" in found.block for p in found.passages),
          "every passage carries its citation id")
    check(all("characters" in p.location() and p.doc_label in p.location() for p in found.passages),
          "every passage states its document and character range")

    ordered = [(p.doc_label, p.char_start) for p in found.passages]
    check(ordered == sorted(ordered),
          "passages are presented in reading order, not score order")


def test_invented_citations_do_not_pass_as_provenance():
    print("citations — an id the model made up is not evidence:")
    found = retrieve([("d1", "Policy.pdf", _long_policy())], "beneficial ownership", budget_chars=6_000)
    real = found.passages[0].cid

    ok = verify_citation(f"Covered — see [{real}].", found.by_cid)
    check(ok["has_citation"] and ok["cited"][0]["cid"] == real, "a real id resolves to its passage")
    check(ok["cited"][0]["char_start"] >= 0 and ok["cited"][0]["document"] == "Policy.pdf",
          "and carries the document and offset the auditor can open")

    bad = verify_citation("Covered per [P999].", found.by_cid)
    check(not bad["has_citation"] and bad["unresolved"] == ["P999"],
          "an invented id is reported as unresolved, not silently accepted")

    none = verify_citation("The policy covers this.", found.by_cid)
    check(not none["has_citation"] and not none["unresolved"],
          "a claim with no citation at all is distinguishable from a false one")


def test_tokenising_keeps_what_regulation_is_made_of():
    print("tokens — article numbers survive:")
    t = tokens("Article 13(1) requires the identification of the beneficial owner.")
    check("13" in t and "1" in t, "article numbers are tokens, not punctuation")
    check("the" not in t and "of" not in t, "grammatical words are dropped")
    check("beneficial" in t and "owner" in t, "domain words are kept — IDF decides their weight")
    check("control" in tokens("control environment"),
          "'control' is NOT stripped: inside one audit's documents it carries meaning")


def test_it_runs_on_the_real_documents():
    print("the real corpus — it works on what is actually uploaded:")
    import asyncio

    async def run():
        async with AsyncSessionLocal() as db:
            return (await db.execute(
                select(UploadedDocument).where(UploadedDocument.upload_status == "ready")
            )).scalars().all()

    docs = asyncio.run(run())
    if not docs:
        print("  SKIP  no ready documents in the database")
        return
    found = retrieve(
        ((d.id, d.original_filename, d.extracted_text) for d in docs),
        "governance control requirement risk evidence", budget_chars=24_000,
    )
    check(found.coverage.documents == len(docs),
          f"every ready document is accounted for ({found.coverage.documents})")
    check(found.passages and all(p.cid.startswith("P") for p in found.passages),
          f"passages come back numbered ({len(found.passages)})")
    check(found.coverage.chars_read <= 24_000, "the budget is respected")
    print(f"        {found.coverage.sentence()}")


def main():
    test_documents_split_on_their_own_structure()
    test_the_needle_is_found_where_a_clip_would_miss_it()
    test_no_document_goes_unopened()
    test_the_prompt_block_is_honest_and_citable()
    test_invented_citations_do_not_pass_as_provenance()
    test_tokenising_keeps_what_regulation_is_made_of()
    test_it_runs_on_the_real_documents()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
