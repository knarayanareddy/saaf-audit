"""Compliance Q&A portal — backend.

Pipeline: one PDF + one question → one structured ComplianceVerdict.

Usage (from the repo root):

    export ANTHROPIC_API_KEY=sk-...
    python tools/scripts/compliance_qa.py path/to/policy.pdf \
      "Wordt MFA afgedwongen voor alle gebruikers?"

The Streamlit UI (`compliance_qa_app.py`) wraps the same functions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

# --- Constants ---------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-5"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "compliance-qa-schema.json"
SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system-prompt.md"

Status = Literal["Voldaan", "Niet voldaan", "Niet van toepassing", "Geen antwoord"]


# --- Pydantic models ---------------------------------------------------------


class EvidenceQuote(BaseModel):
    exact_quote: str
    # page=0 is reserved for auditor-provided context (see SYSTEM_PROMPT)
    page: int = Field(ge=0)
    section: str | None = None
    verified: bool = True  # False when quote did not match source even after normalisation


class GIASReasoning(BaseModel):
    """The 8-step GIAS v2024 reasoning trail produced by the agent.

    See https://www.theiia.org/en/standards/2024-standards/ — the numbered
    GIAS references (13.3, 14.5) ensure findings trace back to the standard.
    """

    objective_scope: str         # Step 1 (GIAS 13.3) — what, scope, audit objective
    risk_context: str            # Step 2 — risks addressed, likelihood, impact, why
    evidence_gathering: str      # Step 3 — relevant / reliable / sufficient per GIAS
    professional_skepticism: str # Step 4 — logic check, inconsistencies, bias
    analysis: str                # Step 5 — what the evidence says, design vs operating
    evidence_sufficiency: str    # Step 6 — enough? reliable enough? counter-evidence?
    conclusion: str              # Step 7 (GIAS 14.5) — effective/partial/ineffective
    audit_trail: str             # Step 8 — Conclusion -> Finding -> Evidence chain


LogStage = Literal[
    "initial_ai",        # first AI verdict on a question
    "reevaluated_ai",    # re-run with auditor-provided additional context
    "auditor_accepted",  # auditor accepted the AI verdict as-is
    "auditor_override",  # auditor overrode the AI status
]


class ComplianceVerdict(BaseModel):
    question: str
    documents: list[str] = Field(default_factory=list)  # one or more uploaded doc names
    document: str | None = None  # kept for backwards compatibility
    status: Status
    confidence: int = Field(ge=0, le=100)
    confidence_reasoning: str = ""
    information_needed: list[str] = Field(default_factory=list)
    evidence: list[EvidenceQuote] = Field(default_factory=list)
    reasoning_trail: GIASReasoning | None = None
    ai_reasoning: str
    auditor_judgement: str | None = None
    auditor_additional_info: str | None = None
    auditor_override_status: Status | None = None
    reevaluated: bool = False
    log_stage: LogStage = "initial_ai"
    timestamp: str | None = None
    model: str | None = None
    session_id: str | None = None


# --- System prompt (kept inline so `ask()` can run without filesystem) -------


SYSTEM_PROMPT = """You are a compliance audit assistant. You apply a structured
audit methodology aligned with the Global Internal Audit Standards (GIAS v2024,
effective January 2025), including risk-based assessment, professional
skepticism, and evidence-based conclusions supported by traceable documentation.

An auditor will give you:
1. The full text of a policy document (with [Page N] markers)
2. ONE compliance question about that document

Your job: answer the question using ONLY evidence from the document. Never
use outside knowledge. Never paraphrase — always quote source text exactly.
Never extract or output any PII (GDPR).

=============================================================================
GIAS 8-STEP REASONING (apply internally, return in reasoning_trail)
=============================================================================

Step 1 — Define Objective & Scope (GIAS 13.3)
  What is being assessed? Scope (process, control, period)? Audit objective?

Step 2 — Identify Risk Context
  What risks does this control address? Likelihood and impact? Why is the
  control relevant?

Step 3 — Gather Evidence
  For every evidence item implicitly note: source, type (document / interview /
  system data), date, direct vs indirect, reliability (high / medium / low),
  corroboration (yes / no). GIAS requires evidence to be
  RELEVANT · RELIABLE · SUFFICIENT.

Step 4 — Apply Professional Skepticism (CRUCIAL)
  For each piece of evidence: is it logical? Any inconsistencies? Does it
  need additional verification? Could it contain bias? Step 4 concerns
  LOWER the confidence score.

Step 5 — Perform Analysis
  What does the evidence say? Does it support the control? Are there
  deviations? Always link back to: risk · control design · control operating
  effectiveness.

Step 6 — Evaluate Evidence Sufficiency
  Is there enough evidence? Reliable enough? Is there counter-evidence?

Step 7 — Form Conclusion (GIAS 14.5)
  Effective / Partially effective / Ineffective, underpinned by evidence,
  analysis, and risk impact. This conclusion drives the `status` field:
    - Effective        -> "Voldaan"
    - Partially effect.-> "Niet voldaan" (with clear gap description)
    - Ineffective      -> "Niet voldaan"
    - Out of scope     -> "Niet van toepassing"
    - Insufficient evid-> "Geen antwoord"

Step 8 — Create Audit Trail (Workpaper logic)
  Conclusion -> Finding(s) -> Evidence -> Analysis -> Risk linkage. Describe
  the chain in a way another auditor could reproduce.

=============================================================================
OUTPUT JSON SHAPE
=============================================================================

Return strictly valid JSON with these fields:

{
  "status": "Voldaan" | "Niet voldaan" | "Niet van toepassing" | "Geen antwoord",
  "confidence": integer 0-100,
  "confidence_reasoning": "Short paragraph: factors from Steps 3, 4, 6.",
  "information_needed": [
    "Concrete item 1 that would raise the confidence",
    "Concrete item 2 ..."
  ],
  "evidence": [
    {"exact_quote": "...", "page": 3, "section": "4.2 Access Management"}
  ],
  "reasoning_trail": {
    "objective_scope":         "Step 1 output — 2-4 sentences.",
    "risk_context":            "Step 2 output — 2-4 sentences.",
    "evidence_gathering":      "Step 3 output — relevance/reliability/sufficiency summary.",
    "professional_skepticism": "Step 4 output — logic checks, inconsistencies, bias flags.",
    "analysis":                "Step 5 output — what the evidence says vs the control.",
    "evidence_sufficiency":    "Step 6 output — enough/reliable/counter-evidence?",
    "conclusion":              "Step 7 output — effective/partial/ineffective + why.",
    "audit_trail":             "Step 8 output — Conclusion -> Finding -> Evidence chain."
  },
  "ai_reasoning": "One short paragraph (3-5 sentences) summarising the verdict for the dashboard."
}

Status decision rules:
- "Voldaan"             — document explicitly states the control/requirement is met
- "Niet voldaan"        — document explicitly states it is NOT met, or the absence
                          of the control is explicitly acknowledged
- "Niet van toepassing" — the question does not apply to the scope of this document
- "Geen antwoord"       — the document does not contain enough information to decide

Confidence rules:
- 90-100 = multiple explicit, unambiguous quotes
- 70-89  = one explicit quote, or several implicit statements pointing the same way
- 40-69  = indirect evidence requiring interpretation
- 0-39   = weak or conflicting evidence; prefer "Geen antwoord" below ~40

confidence_reasoning: name the factors that set the score (how many quotes,
  how explicit, whether they conflict, whether operational evidence is missing).
information_needed: a short list of 2-5 specific, concrete artefacts or facts
  that — if supplied — would most raise the confidence. Examples: "the access
  review procedure document", "a sample access-review export from Q1 2026",
  "confirmation from the CISO that policy X supersedes the 2023 version".
  If confidence is already 95+, return an empty list.

If the auditor supplies <additional_context>, treat it as authoritative
extra evidence alongside the document. Quote from it too (use page: 0 and
section: "Auditor-provided context"). If the additional context resolves
prior gaps, raise confidence and update information_needed accordingly.

Every exact_quote MUST be a verbatim substring of the supplied document
OR of the <additional_context> block (if provided).
Do not shorten, paraphrase, or translate quotes.
"""


# --- PDF handling ------------------------------------------------------------


def extract_pdf_text(pdf_path: Path) -> str:
    """Return full document text with [Page N] markers. Digital PDFs only.

    Scanned PDFs are handled by the Vision fallback in a later iteration.
    """
    try:
        import pdfplumber  # local import so tests can run without the dep
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "pdfplumber is required for PDF ingestion — install it with "
            "`pip install pdfplumber`"
        ) from e

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            parts.append(f"[Page {i}]\n{text}")
    return "\n\n".join(parts)


# --- Core ask() --------------------------------------------------------------


def ask(
    document_text: str,
    question: str,
    *,
    client=None,
    model: str = DEFAULT_MODEL,
    document_name: str | None = None,
    additional_context: str | None = None,
    language: str = "nl",
) -> ComplianceVerdict:
    """Send the document + question to Claude and return a ComplianceVerdict.

    `client` is injected for testability. In production: `Anthropic()`.

    `additional_context` is optional extra evidence supplied by the auditor
    (e.g. "I also have a procedure document that says X"). When provided, the
    model treats it as authoritative alongside the PDF text.
    """
    if client is None:
        from anthropic import Anthropic  # local import

        client = Anthropic()

    extra_block = ""
    if additional_context and additional_context.strip():
        extra_block = (
            f"\n\n<additional_context>\n{additional_context.strip()}\n</additional_context>"
        )

    lang_label = {"nl": "Dutch (Nederlands)", "en": "English"}.get(language, "Dutch (Nederlands)")
    user_message = (
        f"<document>\n{document_text}\n</document>"
        f"{extra_block}\n\n"
        f"Question: {question}\n\n"
        f"Write ai_reasoning, confidence_reasoning and information_needed in {lang_label}. "
        "Status values MUST remain in their Dutch enum form "
        "(Voldaan / Niet voldaan / Niet van toepassing / Geen antwoord). "
        "Evidence quotes MUST stay in the original document language.\n\n"
        "Return JSON matching the compliance-qa schema. "
        "Only the JSON object — no preamble, no markdown fences."
    )

    response = client.messages.create(
        model=model,
        max_tokens=4096,  # GIAS reasoning_trail adds ~1500 tokens
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    # Tolerate markdown fencing even though the prompt forbids it
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.endswith("```"):
            raw = raw[:-3]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned non-JSON output:\n{raw[:500]}") from e

    data.setdefault("question", question)
    data["document"] = document_name or data.get("document")
    data["model"] = model
    data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if additional_context:
        data["auditor_additional_info"] = additional_context.strip()
        data["reevaluated"] = True

    try:
        verdict = ComplianceVerdict.model_validate(data)
    except ValidationError as e:  # surface schema drift clearly
        raise ValueError(f"Verdict did not match schema:\n{e}\n\nRaw:\n{raw}") from e

    # Hallucination guard: every evidence quote MUST be a substring of the source
    # (document OR additional_context when supplied)
    allowed_sources = document_text + "\n" + (additional_context or "")
    _validate_evidence(verdict, allowed_sources)

    return verdict


def _normalise(s: str) -> str:
    """Normalise a string for fuzzy-but-faithful substring matching.

    Handles the common gap between 'what Claude quotes' and 'what pdfplumber
    extracts': whitespace runs, smart quotes, dash variants, NBSPs, NFC.
    """
    import re
    import unicodedata

    s = unicodedata.normalize("NFKC", s)
    # Unify quote-likes
    for a, b in [
        ("“", '"'), ("”", '"'), ("„", '"'), ("‟", '"'),
        ("‘", "'"), ("’", "'"), ("‚", "'"), ("‛", "'"),
        ("–", "-"), ("—", "-"), ("−", "-"),
        ("\u00a0", " "),  # non-breaking space
    ]:
        s = s.replace(a, b)
    # Collapse whitespace (including newlines) to a single space
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _validate_evidence(verdict: ComplianceVerdict, document_text: str) -> None:
    """Soft-flag any evidence quote that is not a substring of the source.

    Two-pass check:
      1. exact substring match → `verified = True`
      2. normalised substring match (whitespace/Unicode collapsed) → still True
      3. otherwise → `verified = False` (NOT raised — the auditor sees a warning)

    Nothing raises. Auditors get to see all returned quotes and judge for
    themselves which ones look reliable. The UI highlights unverified items.
    """
    doc_norm = _normalise(document_text)
    for q in verdict.evidence:
        if q.exact_quote in document_text:
            q.verified = True
            continue
        if _normalise(q.exact_quote) in doc_norm:
            q.verified = True
            continue
        q.verified = False


# --- Audit log ---------------------------------------------------------------

# External, outside any git repo. File is chmod 444 (read-only) after every
# append; we briefly flip to 600 to append, then back to 444.
DEFAULT_LOG_PATH = Path.home() / "saaf-audit-log" / "audit-log.jsonl"


def append_to_log(verdict: ComplianceVerdict, log_path: Path | None = None) -> Path:
    """Append verdict to an external read-only JSONL audit log.

    Returns the absolute log path used.
    """
    log_path = Path(log_path) if log_path else DEFAULT_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Briefly make writable so we can append (no-op if file doesn't exist yet)
    if log_path.exists():
        os.chmod(log_path, 0o600)

    with log_path.open("a", encoding="utf-8") as f:
        f.write(verdict.model_dump_json() + "\n")

    # Lock back to read-only after the append
    os.chmod(log_path, 0o444)
    return log_path


# --- CLI ---------------------------------------------------------------------


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask a compliance question about a PDF.")
    parser.add_argument("pdf", type=Path, help="Path to the policy PDF")
    parser.add_argument("question", type=str, help="The compliance question to ask")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="JSONL audit log path",
    )
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2

    document_text = extract_pdf_text(args.pdf)
    verdict = ask(document_text, args.question, model=args.model, document_name=args.pdf.name)
    append_to_log(verdict, args.log)

    print(verdict.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_cli())
