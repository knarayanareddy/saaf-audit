"""Offline tests for compliance_qa.ask() — Claude client is mocked.

Run from the repo root:

    pip install pydantic pytest
    pytest tools/scripts/tests/test_compliance_qa.py -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Make tools/scripts importable when running pytest from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compliance_qa import ComplianceVerdict, append_to_log, ask  # noqa: E402


# --- Fake Claude client ------------------------------------------------------


class FakeClient:
    """Minimal stand-in for anthropic.Anthropic().messages.create(...)."""

    def __init__(self, response_json: dict):
        self._payload = json.dumps(response_json)
        self.messages = SimpleNamespace(create=self._create)
        self.last_kwargs: dict | None = None

    def _create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(text=self._payload)])


# --- Shared fixtures ---------------------------------------------------------


SAMPLE_DOC = (
    "[Page 1]\n"
    "Information Security Policy v2.3\n"
    "Effective 2026-01-01\n"
    "\n"
    "[Page 5]\n"
    "4.3 Authentication\n"
    "All users must authenticate via MFA when accessing systems classified as Critical.\n"
    "\n"
    "[Page 6]\n"
    "4.3.1 Technical implementation\n"
    "MFA is enforced via Azure AD Conditional Access Policy 'MFA-All-Critical'.\n"
)


# --- Tests -------------------------------------------------------------------


def test_ask_returns_voldaan_with_valid_evidence():
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 85,
        "evidence": [
            {
                "exact_quote": "All users must authenticate via MFA when accessing systems classified as Critical.",
                "page": 5,
                "section": "4.3 Authentication",
            }
        ],
        "ai_reasoning": "The policy explicitly requires MFA on p.5.",
        "confidence_reasoning": "One explicit quote naming the control.",
        "information_needed": ["Azure AD Conditional Access export"],
    })

    verdict = ask(
        SAMPLE_DOC,
        "Wordt MFA afgedwongen voor alle gebruikers?",
        client=fake,
        document_name="infosec.pdf",
    )

    assert isinstance(verdict, ComplianceVerdict)
    assert verdict.status == "Voldaan"
    assert verdict.confidence == 85
    assert verdict.document == "infosec.pdf"
    assert len(verdict.evidence) == 1
    assert verdict.evidence[0].page == 5
    assert verdict.timestamp is not None
    assert verdict.question.startswith("Wordt MFA")
    assert verdict.confidence_reasoning != ""
    assert verdict.information_needed == ["Azure AD Conditional Access export"]
    assert verdict.reevaluated is False
    assert verdict.auditor_additional_info is None


def test_ask_reevaluates_with_additional_context():
    """Quote from additional_context must pass the hallucination check."""
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 95,
        "confidence_reasoning": "Original quote + procedure confirmation from auditor.",
        "information_needed": [],
        "evidence": [
            {
                "exact_quote": "All users must authenticate via MFA when accessing systems classified as Critical.",
                "page": 5,
                "section": "4.3 Authentication",
            },
            {
                "exact_quote": "Quarterly MFA coverage reports are reviewed by the CISO.",
                "page": 0,
                "section": "Auditor-provided context",
            },
        ],
        "ai_reasoning": "Confirmed by auditor-supplied procedure.",
    })

    extra = "Quarterly MFA coverage reports are reviewed by the CISO."
    verdict = ask(
        SAMPLE_DOC,
        "MFA?",
        client=fake,
        additional_context=extra,
    )

    assert verdict.confidence == 95
    assert verdict.reevaluated is True
    assert verdict.auditor_additional_info == extra
    assert len(verdict.evidence) == 2
    # Verify additional_context block was included in the user message
    msg = fake.last_kwargs["messages"][0]["content"]
    assert "<additional_context>" in msg
    assert extra in msg


def test_ask_accepts_geen_antwoord_with_empty_evidence():
    fake = FakeClient({
        "status": "Geen antwoord",
        "confidence": 20,
        "evidence": [],
        "ai_reasoning": "The document does not discuss business continuity.",
    })

    verdict = ask(SAMPLE_DOC, "Hoe vaak wordt het BCP getest?", client=fake)

    assert verdict.status == "Geen antwoord"
    assert verdict.evidence == []


def test_ask_soft_flags_hallucinated_quote():
    """Unverifiable quotes are flagged, not raised — auditor sees warning in UI."""
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 95,
        "evidence": [
            {
                "exact_quote": "MFA is mandatory for every employee without exception.",
                "page": 5,
            }
        ],
        "ai_reasoning": "Hallucinated.",
    })
    verdict = ask(SAMPLE_DOC, "MFA?", client=fake)
    assert verdict.evidence[0].verified is False


def test_ask_verifies_quote_despite_whitespace_variation():
    """Normalize whitespace/unicode — near-matches still count as verified."""
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 85,
        "evidence": [
            {
                "exact_quote": "All   users must\nauthenticate via MFA when   accessing systems classified as Critical.",
                "page": 5,
            }
        ],
        "ai_reasoning": "ok",
    })
    verdict = ask(SAMPLE_DOC, "q?", client=fake)
    assert verdict.evidence[0].verified is True


def test_ask_rejects_invalid_status():
    fake = FakeClient({
        "status": "Maybe",  # not in the enum
        "confidence": 50,
        "evidence": [],
        "ai_reasoning": "...",
    })

    with pytest.raises(ValueError):
        ask(SAMPLE_DOC, "q?", client=fake)


def test_ask_rejects_out_of_range_confidence():
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 150,
        "evidence": [],
        "ai_reasoning": "...",
    })

    with pytest.raises(ValueError):
        ask(SAMPLE_DOC, "q?", client=fake)


def test_ask_strips_markdown_fences():
    # Simulate a model that wraps JSON in ```json ... ``` despite instructions
    fenced = "```json\n" + json.dumps({
        "status": "Niet van toepassing",
        "confidence": 50,
        "evidence": [],
        "ai_reasoning": "Out of scope.",
    }) + "\n```"
    fake = FakeClient({})
    fake._payload = fenced  # type: ignore[attr-defined]

    verdict = ask(SAMPLE_DOC, "q?", client=fake)
    assert verdict.status == "Niet van toepassing"


def test_ask_uses_prompt_cache_on_system_prompt():
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 90,
        "evidence": [],
        "ai_reasoning": "...",
    })
    ask(SAMPLE_DOC, "q?", client=fake)
    assert fake.last_kwargs is not None
    system = fake.last_kwargs["system"]
    assert isinstance(system, list) and system[0]["cache_control"] == {"type": "ephemeral"}


def test_append_to_log_writes_read_only_file(tmp_path):
    """Log file is 0o444 after writing, and can still be appended to."""
    log_path = tmp_path / "audit.jsonl"

    v1 = ComplianceVerdict(
        question="q1",
        status="Voldaan",
        confidence=80,
        ai_reasoning="reason",
        log_stage="initial_ai",
    )
    v2 = ComplianceVerdict(
        question="q1",
        status="Niet voldaan",
        confidence=80,
        ai_reasoning="reason",
        log_stage="auditor_override",
        auditor_override_status="Niet voldaan",
    )

    append_to_log(v1, log_path)
    mode1 = os.stat(log_path).st_mode & 0o777
    assert mode1 == 0o444, f"expected 0o444 after first write, got {oct(mode1)}"

    append_to_log(v2, log_path)  # must still work despite read-only
    mode2 = os.stat(log_path).st_mode & 0o777
    assert mode2 == 0o444

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    entry2 = json.loads(lines[1])
    assert entry2["log_stage"] == "auditor_override"
    assert entry2["auditor_override_status"] == "Niet voldaan"


def test_verdict_carries_documents_list():
    v = ComplianceVerdict(
        question="q",
        status="Voldaan",
        confidence=90,
        ai_reasoning="r",
        documents=["a.pdf", "b.pdf"],
    )
    assert v.documents == ["a.pdf", "b.pdf"]


def test_ask_parses_gias_reasoning_trail():
    """When the model returns a reasoning_trail, it's parsed into the Pydantic model."""
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 80,
        "evidence": [],
        "ai_reasoning": "Summary.",
        "confidence_reasoning": "One explicit quote.",
        "information_needed": [],
        "reasoning_trail": {
            "objective_scope": "Assess MFA control on critical systems.",
            "risk_context": "Unauthorised access risk.",
            "evidence_gathering": "One direct policy statement, reliability high.",
            "professional_skepticism": "No inconsistencies found.",
            "analysis": "Policy design supports the control.",
            "evidence_sufficiency": "Sufficient at design level; operating effectiveness unverified.",
            "conclusion": "Design effective.",
            "audit_trail": "Conclusion -> Finding F-001 -> Evidence p.5.",
        },
    })
    verdict = ask(SAMPLE_DOC, "MFA?", client=fake)
    assert verdict.reasoning_trail is not None
    assert verdict.reasoning_trail.conclusion == "Design effective."
    assert "MFA" in verdict.reasoning_trail.objective_scope


def test_ask_without_reasoning_trail_still_works():
    """Backward compat: old-shape responses (no reasoning_trail) still parse."""
    fake = FakeClient({
        "status": "Voldaan",
        "confidence": 70,
        "evidence": [],
        "ai_reasoning": "Ok.",
    })
    verdict = ask(SAMPLE_DOC, "q?", client=fake)
    assert verdict.reasoning_trail is None
