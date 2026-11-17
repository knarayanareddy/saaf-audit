"""Grounded finding validator — a second opinion that re-reads the source.

Update #3's Explainability Annex answers "is this finding *traceable*?" (the
O→R→C→T→E lineage + a grounding-strength meter). This validator answers a
different, content-level question: "does the source actually *say* what the
finding claims?" It re-reads the real source behind a finding — the test
conclusion, the linked evidence, the fieldwork observation, the applicable
frameworks — and checks each 5C claim against it, returning found yes|partial|no
with a VERBATIM quote + location. The auditor then reviews only the flagged items.

DETERMINISTIC-FIRST: a free, always-on lexical pre-screen flags claims with no
support in the source. It is a *candidate list, not a verdict* — lexical overlap
is not semantic proof, so it is labelled "verify". The opt-in AI "judge" is the
authoritative layer; every quote it returns is verified as a verbatim substring of
the source, so the hallucination detector cannot itself hallucinate a citation
(honesty over green). A hand-typed finding with no attached source reads
"no source to verify against" (no_source) — never a false "unsupported".
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlalchemy import select

from services.explainability_annex import _fetch_lineage, _finding_signature
from services.prompt_safety import wrap_untrusted, safe_label
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT

# Generic words carry no claim signal — dropping them keeps overlap about the
# substance, not the grammar.
_STOP = {
    "the", "and", "for", "with", "not", "are", "was", "were", "that", "this", "from", "has", "have",
    "its", "their", "any", "all", "may", "can", "must", "should", "would", "could", "per", "via",
    "which", "when", "where", "there", "than", "then", "into", "over", "under", "also", "such", "been",
    "being", "does", "did", "had", "but", "our", "out", "who", "whom", "were", "will", "shall",
}

# Each 5C claim, its display label, and its epistemic kind. "factual"/"norm" claims
# are checked hard against the source; "judgement"/"forward" claims are the
# auditor's reasoning/action — low source coverage is expected, so they are shown
# neutrally rather than flagged red.
_CLAIM_META = [
    ("condition", "Condition — what was found", "factual"),
    ("criteria", "Criteria — the norm/expectation", "norm"),
    ("cause", "Cause — why it happened", "judgement"),
    ("effect", "Effect — consequence/risk", "factual"),
    ("recommendation", "Recommendation — corrective action", "forward"),
]

_FOUND_MAP = {"yes": "supported", "partial": "partial", "no": "unsupported"}
_MAX_CHUNK = 1600  # per source chunk, chars
_MAX_DOC = 3000    # linked uploaded-document text, chars


def _s(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _short(v, n=240) -> str:
    t = _s(v)
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _norm(t: str) -> str:
    """Collapse whitespace + lowercase — for verbatim-substring verification."""
    return re.sub(r"\s+", " ", (t or "").lower()).strip()


def _tokenize(text) -> set:
    out = set()
    for w in re.split(r"[^a-z0-9]+", str(text or "").lower()):
        if len(w) >= 3 and w not in _STOP:
            out.add(w)
    return out


def _sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) >= 12]


# ── source corpus (the ground truth the validator re-reads) ─────────────────────

async def _assemble_corpus(db, finding, parts) -> list[dict]:
    """Build the labelled source corpus from the finding's lineage + frameworks.
    Each chunk = {ref, label, kind, text}; the label lets a quote cite its origin."""
    from models.planning import UploadedDocument, FieldworkObservation, ApplicableFramework

    chunks: list[dict] = []

    test = parts.get("test")
    if test is not None:
        ref = _s(getattr(test, "ref", None)) or "Test"
        for attr, suffix in (("conclusion", "conclusion"), ("description", "description")):
            t = _s(getattr(test, attr, None))
            if t:
                chunks.append({"ref": ref, "label": f"Test {ref} {suffix}".strip(), "kind": "data", "text": t[:_MAX_CHUNK]})

    for e in parts.get("evidence") or []:
        ref = _s(getattr(e, "ref", None)) or "E"
        t = " ".join(x for x in (_s(getattr(e, "title", None)), _s(getattr(e, "description", None))) if x)
        doc_id = getattr(e, "source_document_id", None)
        if doc_id:
            doc = await db.get(UploadedDocument, doc_id)
            dt = _s(getattr(doc, "extracted_text", None)) if doc else ""
            if dt:
                t = (t + " " + dt).strip()
        if t:
            chunks.append({"ref": ref, "label": f"Evidence {ref}".strip(),
                           "kind": _s(getattr(e, "kind", None)) or "document", "text": t[:_MAX_DOC]})

    if getattr(finding, "source_observation_id", None):
        obs = await db.get(FieldworkObservation, finding.source_observation_id)
        if obs is not None:
            t = " ".join(x for x in (_s(obs.detailed_observation), _s(obs.criteria),
                                     _s(obs.root_cause), _s(obs.risk)) if x)
            if t:
                chunks.append({"ref": "OBS", "label": "Fieldwork observation", "kind": "observation", "text": t[:_MAX_CHUNK]})

    fws = (await db.execute(
        select(ApplicableFramework).where(
            ApplicableFramework.engagement_id == finding.engagement_id,
            ApplicableFramework.is_accepted == True,  # noqa: E712
        )
    )).scalars().all()
    for fw in fws:
        t = " ".join(x for x in (_s(fw.framework_name), _s(fw.specific_provision),
                                 _s(fw.applicability_rationale)) if x)
        if t:
            chunks.append({"ref": _s(fw.framework_code) or "FW",
                           "label": f"Framework {_short(fw.framework_name, 40)}".strip(),
                           "kind": "framework", "text": t[:_MAX_CHUNK]})

    return chunks


# ── deterministic pre-screen ────────────────────────────────────────────────────

def _determine(coverage: float, best_score: int, kind: str, has_source: bool) -> str:
    if not has_source:
        return "judgement" if kind in ("judgement", "forward") else "no_source"
    if kind in ("judgement", "forward"):
        # the auditor's reasoning/action — never a red "unsupported"; supported only
        # when it genuinely overlaps the source, else a neutral "judgement".
        return "supported" if coverage >= 0.5 else "judgement"
    if coverage >= 0.5 and best_score >= 2:
        return "supported"
    if coverage >= 0.2 or best_score >= 2:
        return "partial"
    return "unsupported"


def _best_sentence(claim_tokens: set, corpus_sentences: list):
    best, best_score = None, 0
    for chunk, sent, stoks in corpus_sentences:
        score = len(claim_tokens & stoks)
        if score > best_score:
            best, best_score = (chunk, sent), score
    return best, best_score


def compute_headline(claims: list[dict]) -> dict:
    eff = [effective_verdict(c) for c in claims]
    counts = {v: eff.count(v) for v in ("supported", "partial", "unsupported", "no_source", "judgement")}
    counts["total"] = len(claims)
    counts["needs_review"] = counts["unsupported"] + counts["partial"]
    return counts


def effective_verdict(claim: dict) -> str:
    """The AI judge is authoritative when present; else the deterministic verdict.
    Judgement/forward claims (cause/recommendation) are the auditor's reasoning, not
    source facts — "not in source" is expected there, so they are never flagged red."""
    ai = claim.get("ai")
    if ai and ai.get("found"):
        v = _FOUND_MAP.get(ai["found"], claim["verdict"])
        if claim.get("claim_kind") in ("judgement", "forward") and v in ("unsupported", "partial"):
            return "judgement"
        return v
    return claim["verdict"]


def validate_finding(finding, corpus: list[dict]) -> dict:
    """Deterministic lexical pre-screen: per-claim verdict + best-matching sentence.
    A candidate list, not a verdict — labelled for the auditor to verify."""
    has_source = bool(corpus)
    all_tokens = set()
    corpus_sentences = []
    for c in corpus:
        toks = _tokenize(c["text"])
        all_tokens |= toks
        for s in _sentences(c["text"]):
            corpus_sentences.append((c, s, _tokenize(s)))

    claims = []
    for key, label, kind in _CLAIM_META:
        text = _s(getattr(finding, key, None))
        if not text:
            continue
        ctoks = _tokenize(text)
        if not ctoks:
            continue
        coverage = len(ctoks & all_tokens) / len(ctoks) if ctoks else 0.0
        best, best_score = _best_sentence(ctoks, corpus_sentences)
        verdict = _determine(coverage, best_score, kind, has_source)
        best_match = None
        if best and best_score >= 2:
            chunk, sent = best
            best_match = {"quote": _short(sent), "source_label": chunk["label"],
                          "ref": chunk["ref"], "kind": chunk["kind"], "source": "lexical"}
        claims.append({
            "key": key, "label": label, "claim_kind": kind,
            "claim_text": _short(text, 400),
            "verdict": verdict, "coverage": round(coverage, 2),
            "best_match": best_match,
        })

    return {"claims": claims, "headline": compute_headline(claims), "has_source": has_source}


# ── opt-in AI judge (grounded; every quote verified verbatim) ───────────────────

_JUDGE_SYSTEM = BASE_SYSTEM_PROMPT + """

GROUNDED-VALIDATOR ROLE:
You are a second-opinion validator checking whether an audit finding's claims are
supported by the SOURCE material provided. STRICT RULES:
- Use ONLY the source text inside the untrusted block. NEVER use outside knowledge.
- If a claim is supported, copy a VERBATIM quote (an exact substring) from the source.
  If it is not supported, set found="no" and quote="".
- NEVER invent, paraphrase, translate or reconstruct a quote. A "yes" REQUIRES a verbatim quote.
- found is one of: "yes" (clearly supported), "partial" (partly/indirectly), "no" (not in the source).
- Be conservative: when in doubt, prefer "partial" or "no". The auditor decides.
"""


async def judge_finding(corpus: list[dict], claims: list[dict]) -> list[dict]:
    """One AI call. Returns verified per-claim verdicts. The source is fenced as
    untrusted data; every returned quote is checked as a verbatim substring."""
    source_block = "\n\n".join(f"[{c['label']}]\n{c['text']}" for c in corpus)
    fenced = wrap_untrusted(source_block, safe_label("finding source material"))
    claim_lines = [f'- {c["key"]}: "{c["claim_text"]}"' for c in claims]
    prompt = (
        "Validate each CLAIM against the SOURCE below.\n\n" + fenced +
        "\n\nCLAIMS:\n" + "\n".join(claim_lines) +
        "\n\nReturn ONLY a JSON object: "
        '{"claims":[{"key":"...","found":"yes|partial|no","quote":"verbatim substring or empty",'
        '"source_label":"which source","confidence":"high|medium|low","note":"one short sentence"}]}'
    )
    out = await run_agent_to_json(_JUDGE_SYSTEM, prompt, max_tokens=1600)
    verdicts = out.get("claims") if isinstance(out, dict) else out
    return _verify_quotes(corpus, verdicts if isinstance(verdicts, list) else [])


def _verify_quotes(corpus: list[dict], verdicts: list) -> list[dict]:
    """Anti-hallucination backstop: a quote must appear verbatim in the source, and
    a "yes"/"partial" must carry a verifiable quote — otherwise it is downgraded and
    flagged. The judge cannot fabricate a citation to certify support."""
    corpus_norm = _norm(" ".join(c["text"] for c in corpus))
    out = []
    for v in verdicts:
        if not isinstance(v, dict):
            continue
        found = _s(v.get("found")).lower()
        if found not in ("yes", "partial", "no"):
            found = "no"
        quote = _s(v.get("quote"))
        unverified = False
        if quote and _norm(quote) not in corpus_norm:
            unverified = True          # fabricated citation → strip it
            quote = ""
        if found in ("yes", "partial") and not quote:
            unverified = True          # claims support but no verifiable quote → cap at partial
            found = "partial"
        out.append({
            "key": _s(v.get("key")),
            "found": found,
            "quote": _short(quote),
            "source_label": _s(v.get("source_label")),
            "confidence": (_s(v.get("confidence")).lower() or "low"),
            "note": _short(v.get("note"), 200),
            "quote_unverified": unverified,
        })
    return out


# ── DB-aware assembly + persistence (mirrors the explainability annex) ──────────

def _persisted(finding):
    raw = getattr(finding, "validation", None)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


async def assemble(db, finding) -> dict:
    """Fresh deterministic pre-screen, with any persisted AI judge overlaid and
    flagged stale if the finding changed since it was judged."""
    parts = await _fetch_lineage(db, finding)
    corpus = await _assemble_corpus(db, finding, parts)
    result = validate_finding(finding, corpus)
    result["reference"] = ("Content check — does the source say this? Complements the "
                           "explainability annex (is it traceable?).")

    persisted = _persisted(finding)
    if persisted and persisted.get("claims"):
        by_key = {c.get("key"): c for c in persisted["claims"] if isinstance(c, dict)}
        for claim in result["claims"]:
            j = by_key.get(claim["key"])
            if j:
                claim["ai"] = j
        result["judged_at"] = persisted.get("judged_at")
        result["judge_stale"] = persisted.get("based_on_sig") != _finding_signature(finding)
        result["headline"] = compute_headline(result["claims"])
    return result


async def judge_finding_task(finding_id: str, engagement_id: str):
    """Opt-in background task: build the corpus, run one AI judge call, verify the
    quotes, and persist ONLY the AI verdicts. Best-effort."""
    from database import AsyncSessionLocal
    from models.reporting import Finding

    async with AsyncSessionLocal() as db:
        f = await db.get(Finding, finding_id)
        if not f or f.engagement_id != engagement_id:
            return
        parts = await _fetch_lineage(db, f)
        corpus = await _assemble_corpus(db, f, parts)
        result = validate_finding(f, corpus)
        claims = result["claims"]
        sig = _finding_signature(f)

    # Only the checkable claims go to the judge: factual (condition/effect) + norm
    # (criteria). Cause/recommendation are the auditor's reasoning, not source claims.
    judgeable = [c for c in claims if c["claim_kind"] in ("factual", "norm")]
    if not corpus or not judgeable:
        return  # nothing to judge against
    try:
        verdicts = await judge_finding(corpus, judgeable)
    except Exception:  # noqa: BLE001
        return  # keep the deterministic pre-screen on failure

    async with AsyncSessionLocal() as db:
        f = await db.get(Finding, finding_id)
        if not f:
            return
        f.validation = json.dumps({
            "claims": verdicts,
            "judged_at": datetime.now(timezone.utc).isoformat(),
            "based_on_sig": sig,
        })
        await db.commit()
