"""Retrieval — agents read the passages that matter, and cite where they came from.

Before this, every agent that reasoned over uploaded documents was handed the
FIRST few thousand characters of each one. For a forty-page policy that is the
cover page and the table of contents, which is why the governance assessor could
declare a requirement a "gap" when its control was described on page thirty —
and then write that false gap into the risk matrix as a real risk.

The fix is not a bigger clip. It is choosing: split each document on its own
structure, rank the pieces against what this agent is actually looking for, and
spend the prompt budget on those.

Three decisions worth stating, because they are what make this trustworthy
rather than merely better:

**Lexical, not embeddings.** Scoring is Okapi BM25 over the chunks of this
engagement's own documents. No model call, no vector store, no network, no cost,
and the same input always returns the same passages — an audit tool that cannot
reproduce its own evidence selection is not an audit tool. Regulatory text is
also unusually literal: "beneficial owner", "Art. 13", "periodic review" appear
verbatim, which is the case lexical ranking handles best. Embeddings would add
recall on paraphrase; they can be layered on top of this interface later without
any caller changing, because `rank()` is the only thing that would move.

**Every document gets a hearing.** One long, wordy document would otherwise win
every slot and the agent would report on a file it never opened. Each document
with text contributes its best passage before the remaining budget is filled by
global rank, so "I did not see it" can never be an artefact of another file
being longer.

**Citations survive.** Each passage carries a stable id, its document, its
section heading and its character range, and it says so in the prompt. The agent
is told to cite that id, which turns "evidence: the policy covers this" into
something the auditor can click, and which `verify_citation` can check against
the passage the model claims to be quoting.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from services.doc_context import DocCoverage
from services.prompt_safety import safe_label

# ── Tokenising ───────────────────────────────────────────────────────────────
# A short, purely grammatical stoplist. Domain words ("control", "risk",
# "requirement") are deliberately NOT stripped: inside one audit's documents they
# carry real meaning, and BM25's IDF already discounts whatever turns out to be
# everywhere. That is the job IDF exists for, and it adapts per corpus where a
# hand-written list cannot.
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can", "could",
    "did", "do", "does", "for", "from", "had", "has", "have", "if", "in", "into", "is", "it",
    "its", "may", "must", "no", "nor", "not", "of", "on", "or", "our", "shall", "should",
    "such", "than", "that", "the", "their", "then", "there", "these", "this", "those", "to",
    "was", "were", "when", "where", "which", "will", "with", "would",
}

_WORD = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9'’\-]*|\d+(?:\.\d+)*")


def tokens(text: str) -> list[str]:
    """Words and article numbers. "Art. 13(1)" keeps its 13 and its 1, which is
    exactly how a requirement is referred to in the documents that answer it."""
    return [t for t in (m.group(0).lower() for m in _WORD.finditer(text or "")) if t not in _STOP]


# ── Chunking ─────────────────────────────────────────────────────────────────
# Documents are split on the boundaries their authors already wrote: a numbered
# clause, an article, a markdown heading, a short capitalised line. Cutting every
# 1,400 characters regardless would routinely slice a requirement in half and
# hand the model the second half.
_HEADING = re.compile(
    r"""^(?:
        \#{1,6}\s+\S.*                      # markdown heading
      | (?:article|art\.?|section|clause|chapter|annex|appendix)\s+\d+[A-Za-z]?\b.*
      | \d+(?:\.\d+){0,3}[.)]?\s+\S.{0,90}  # 3.2.1 Numbered clause title
      | [A-Z][A-Z0-9 ,'&/\-()]{3,70}        # SHORT CAPITALISED LINE
    )$""",
    re.VERBOSE | re.IGNORECASE,
)

TARGET_CHARS = 1400     # a passage long enough to carry an argument
MAX_CHARS = 2200        # hard ceiling before an oversized block is split
MIN_CHARS = 180         # below this a fragment is folded into its neighbour


@dataclass(frozen=True)
class Passage:
    """One retrievable piece of one document, and where it came from."""
    cid: str            # citation id the model quotes back, e.g. "P7"
    doc_id: str
    doc_label: str
    section: str
    char_start: int
    char_end: int
    text: str
    terms: list[str] = field(default_factory=list, repr=False)
    # Scored separately and weighted: a clause headed "Periodic re-screening"
    # is about re-screening in a way a paragraph merely mentioning it is not.
    head_terms: list[str] = field(default_factory=list, repr=False)

    def location(self) -> str:
        where = f'"{self.section}"' if self.section else "no heading"
        return f"{self.doc_label} · {where} · characters {self.char_start:,}–{self.char_end:,}"


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 100:
        return False
    if stripped.endswith((".", ";", ",")) and not re.match(r"^\d", stripped):
        return False
    return bool(_HEADING.match(stripped))


def split_document(text: str, doc_id: str, doc_label: str) -> list[Passage]:
    """Split one document into passages on its own structure.

    Character offsets are into the original text, so a citation can be resolved
    back to the source exactly — including for the part of a document that was
    never sent to the model.
    """
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not body.strip():
        return []

    # Walk the lines, starting a new block at each heading and whenever the
    # current block has grown past its target.
    blocks: list[tuple[int, int, str]] = []   # (start, end, heading)
    start = 0
    heading = ""
    pending_heading = ""
    cursor = 0
    for line in body.split("\n"):
        line_len = len(line) + 1
        here = cursor
        cursor += line_len
        if _is_heading(line):
            if here > start and (here - start) >= MIN_CHARS:
                blocks.append((start, here, heading))
                start = here
                heading = line.strip()
            else:
                # A heading immediately after another: keep the most specific one.
                heading = line.strip() or heading
                pending_heading = heading
            continue
        if cursor - start >= TARGET_CHARS:
            blocks.append((start, cursor, heading or pending_heading))
            start = cursor
    if cursor > start:
        blocks.append((start, cursor, heading or pending_heading))

    passages: list[Passage] = []
    for b_start, b_end, b_heading in blocks:
        chunk = body[b_start:b_end]
        if not chunk.strip():
            continue
        # An oversized block (a long unbroken section) is cut on sentence ends.
        for c_start, c_end in _cut(chunk, b_start):
            piece = body[c_start:c_end].strip()
            if len(piece) < MIN_CHARS and passages and passages[-1].doc_id == doc_id:
                # Fold a scrap into the passage before it rather than ranking it
                # on its own, where it would score noise.
                prev = passages.pop()
                merged = body[prev.char_start:c_end].strip()
                passages.append(Passage(
                    prev.cid, doc_id, doc_label, prev.section, prev.char_start, c_end,
                    merged, tokens(merged), tokens(prev.section),
                ))
                continue
            if not piece:
                continue
            passages.append(Passage(
                "", doc_id, doc_label, b_heading, c_start, c_end, piece,
                tokens(piece), tokens(b_heading),
            ))
    return passages


def _cut(chunk: str, offset: int) -> list[tuple[int, int]]:
    """Absolute (start, end) spans for one block, split on sentence ends when it
    exceeds MAX_CHARS."""
    if len(chunk) <= MAX_CHARS:
        return [(offset, offset + len(chunk))]
    spans, pos = [], 0
    while pos < len(chunk):
        end = min(pos + TARGET_CHARS, len(chunk))
        if end < len(chunk):
            window = chunk[pos:end]
            brk = max(window.rfind(". "), window.rfind(".\n"), window.rfind("\n\n"))
            if brk > MIN_CHARS:
                end = pos + brk + 1
        spans.append((offset + pos, offset + end))
        pos = end
    return spans


# ── Ranking ──────────────────────────────────────────────────────────────────
# k1 controls how fast a repeated term stops paying off. The textbook 1.2 suits
# prose where saying something six times really does mean more; it does not suit
# clause-structured documents, where the operative rule is usually stated ONCE,
# precisely, and the sections that merely discuss the topic are the ones that
# repeat its vocabulary. 0.9 saturates sooner, which is what that shape wants.
# Measured on the golden set: it is the difference between an operative clause
# ranking behind a "background and governance" section and ahead of it.
_K1 = 0.9
_B = 0.75
# How much a term in the section heading is worth against the same term in the
# body. The same idiom audit_memory.py uses for its title matches.
_HEAD_WEIGHT = 2.0


def rank(passages: list[Passage], query: str) -> list[tuple[float, Passage]]:
    """Okapi BM25, plus a bonus for query bigrams appearing verbatim.

    The bigram bonus is what keeps "beneficial ownership" from scoring the same
    as a passage that happens to use "beneficial" and "ownership" ten lines
    apart — in regulatory text the phrase is usually the whole point.
    """
    q = tokens(query)
    if not passages or not q:
        return [(0.0, p) for p in passages]

    n = len(passages)
    df: dict[str, int] = {}
    for p in passages:
        for t in set(p.terms) | set(p.head_terms):
            df[t] = df.get(t, 0) + 1
    avg_len = sum(len(p.terms) for p in passages) / n or 1.0

    q_bigrams = {f"{a} {b}" for a, b in zip(q, q[1:])}
    q_set = set(q)

    scored: list[tuple[float, Passage]] = []
    for p in passages:
        freq: dict[str, int] = {}
        for t in p.terms:
            if t in q_set:
                freq[t] = freq.get(t, 0) + 1
        length = len(p.terms) or 1
        score = 0.0
        for t, f in freq.items():
            idf = math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            score += idf * (f * (_K1 + 1)) / (f + _K1 * (1 - _B + _B * length / avg_len))
        # The heading, weighted. Not length-normalised: a heading is a handful of
        # words by definition, and normalising it would only punish a specific
        # one against a vague one.
        for t in set(p.head_terms) & q_set:
            score += _HEAD_WEIGHT * math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
        if q_bigrams:
            body = " ".join(p.head_terms + p.terms)
            hits = sum(1 for bg in q_bigrams if bg in body)
            score *= 1 + 0.15 * hits
        scored.append((score, p))
    scored.sort(key=lambda sp: (-sp[0], sp[1].doc_label, sp[1].char_start))
    return scored


# ── Selection and rendering ──────────────────────────────────────────────────
@dataclass
class Retrieved:
    """What one retrieval produced: the prompt block, the passages behind it,
    and an honest account of what was left unread."""
    block: str
    passages: list[Passage]
    coverage: DocCoverage
    by_cid: dict[str, Passage]


def retrieve(documents, query: str, budget_chars: int = 24_000,
             per_document_floor: int = 1) -> Retrieved:
    """Choose the passages this agent should read.

    `documents` is an iterable of (doc_id, label, full_text).
    """
    all_passages: list[Passage] = []
    chars_total = 0
    documents_seen = documents_empty = 0

    for doc_id, label, text in documents:
        documents_seen += 1
        body = (text or "").strip()
        if not body:
            documents_empty += 1
            continue
        chars_total += len(body)
        all_passages.extend(split_document(body, doc_id, safe_label(label)))

    if not all_passages:
        return Retrieved("", [], DocCoverage(documents_seen, documents_empty, 0, chars_total), {})

    scored = rank(all_passages, query)

    # Each document's best passages first, so no file goes unopened, then the
    # rest of the budget by global rank.
    chosen: list[Passage] = []
    used = 0
    seen: set[int] = set()

    def take(p: Passage) -> bool:
        nonlocal used
        if id(p) in seen or used + len(p.text) > budget_chars:
            return False
        seen.add(id(p))
        chosen.append(p)
        used += len(p.text)
        return True

    if per_document_floor > 0:
        per_doc: dict[str, int] = {}
        for _score, p in scored:
            if per_doc.get(p.doc_id, 0) >= per_document_floor:
                continue
            if take(p):
                per_doc[p.doc_id] = per_doc.get(p.doc_id, 0) + 1

    for _score, p in scored:
        if used >= budget_chars:
            break
        take(p)

    # Reading order, not score order: grouped by document and in the order the
    # author wrote them, so the model can follow an argument across passages.
    chosen.sort(key=lambda p: (p.doc_label, p.char_start))
    numbered = [
        Passage(f"P{i + 1}", p.doc_id, p.doc_label, p.section, p.char_start, p.char_end,
                p.text, p.terms, p.head_terms)
        for i, p in enumerate(chosen)
    ]

    coverage = DocCoverage(
        documents=documents_seen,
        documents_empty=documents_empty,
        chars_read=sum(len(p.text) for p in numbered),
        chars_total=chars_total,
        passages=len(numbered),
        documents_hit=len({p.doc_id for p in numbered}),
    )
    return Retrieved(render(numbered, coverage), numbered, coverage,
                     {p.cid: p for p in numbered})


def render(passages: list[Passage], coverage: DocCoverage) -> str:
    """The prompt block. Every passage is labelled with the id the model must
    cite and the place it came from, and the preamble states plainly that this
    is a selection — an agent that does not know it is reading extracts will
    read an absence as a gap."""
    if not passages:
        return ""
    head = (
        f"The passages below were selected from the uploaded documents by relevance to this task: "
        f"{coverage.sentence()}. Each one is labelled [P#] with the document, section and character "
        f"range it came from.\n"
        f"You are NOT seeing the whole of these documents. Anything not shown is unknown to you, not "
        f"absent — never conclude that something is missing because it does not appear below.\n"
        f"When you rely on a passage, cite it by its [P#] id.\n"
    )
    body = "\n\n".join(f"[{p.cid}] {p.location()}\n{p.text}" for p in passages)
    return f"{head}\n{body}"


# ── Citations coming back ────────────────────────────────────────────────────
_CITE = re.compile(r"\[?\b(P\d{1,3})\b\]?")


def verify_citation(claim: str, by_cid: dict[str, Passage]) -> dict:
    """Resolve the [P#] ids in a model's evidence string back to real passages.

    Same principle as grounded_validator's verbatim quote check: a citation the
    agent invented must not read as provenance. Returns which ids were real,
    which were not, and where the real ones point — so the UI can link to the
    passage and flag the rest.
    """
    ids = [m.group(1) for m in _CITE.finditer(claim or "")]
    resolved, unknown = [], []
    for cid in dict.fromkeys(ids):          # de-duplicated, order preserved
        p = by_cid.get(cid)
        if p:
            resolved.append({
                "cid": cid, "document_id": p.doc_id, "document": p.doc_label,
                "section": p.section, "char_start": p.char_start, "char_end": p.char_end,
            })
        else:
            unknown.append(cid)
    return {"cited": resolved, "unresolved": unknown, "has_citation": bool(resolved)}
