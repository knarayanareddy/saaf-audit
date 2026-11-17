"""
AC-11: model backends (see AUDIT-CRITERIA.md).

The claude-code backend is exercised against a fake `claude_agent_sdk` module
(tests/conftest.py); no test starts a real Claude Code process.
"""
import importlib
import json
import sys
from datetime import date

import pytest

from agents.llm import NEUTRAL_SYSTEM_PROMPT, ModelCallError, complete, get_backend
from tests.conftest import FakeAssistantMessage, FakeResultMessage, FakeTextBlock, make_fake_sdk


def install_fake_query(monkeypatch, messages):
    """Replace claude_agent_sdk.query with one that yields `messages` and records its calls."""
    calls = []

    async def fake_query(*, prompt, options):
        calls.append({"prompt": prompt, "options": options})
        for message in messages:
            yield message

    monkeypatch.setitem(sys.modules, "claude_agent_sdk", make_fake_sdk(fake_query))
    return calls


def answer(text):
    return [FakeAssistantMessage(content=[FakeTextBlock(text)]), FakeResultMessage(result=text)]


@pytest.fixture
def claude_code(monkeypatch):
    monkeypatch.setenv("VENDORGUARD_BACKEND", "claude-code")


# --- backend selection ---------------------------------------------------------------

def test_ac11_default_backend_is_api():
    assert get_backend() == "api"


@pytest.mark.parametrize("value", ["claude-code", " Claude-Code ", "api"])
def test_ac11_backend_from_environment(monkeypatch, value):
    monkeypatch.setenv("VENDORGUARD_BACKEND", value)
    assert get_backend() == value.strip().lower()


def test_ac11_unknown_backend_is_rejected(monkeypatch):
    monkeypatch.setenv("VENDORGUARD_BACKEND", "openai")
    with pytest.raises(ValueError, match="not one of"):
        complete(model="m", system="s", user="u", max_tokens=10)


# --- claude-code backend is locked down ---------------------------------------------

def test_ac11_claude_code_runs_without_tools_settings_or_mcp(monkeypatch, claude_code):
    calls = install_fake_query(monkeypatch, answer("[]"))
    complete(model="claude-sonnet-4-6", system="SYSTEM", user="USER", max_tokens=10)
    options = calls[0]["options"]
    assert options.tools == []
    assert options.setting_sources == []
    assert options.strict_mcp_config is True
    assert options.max_turns == 1
    assert options.model == "claude-sonnet-4-6"


def test_ac11_claude_code_keeps_vendor_text_out_of_system_prompt(monkeypatch, claude_code):
    calls = install_fake_query(monkeypatch, answer("[]"))
    complete(model="m", system="SYSTEM", user="VENDOR-TEXT-4411", max_tokens=10)
    assert calls[0]["options"].system_prompt == "SYSTEM"
    assert calls[0]["prompt"] == "VENDOR-TEXT-4411"


def test_ac11_claude_code_never_falls_back_to_its_coding_prompt(monkeypatch, claude_code):
    calls = install_fake_query(monkeypatch, answer("memo"))
    complete(model="m", system=None, user="u", max_tokens=10)
    assert calls[0]["options"].system_prompt == NEUTRAL_SYSTEM_PROMPT


# --- claude-code backend responses ---------------------------------------------------

def test_ac11_claude_code_returns_result_text(monkeypatch, claude_code):
    install_fake_query(monkeypatch, answer('[{"a": 1}]'))
    assert complete(model="m", system="s", user="u", max_tokens=10) == '[{"a": 1}]'


def test_ac11_claude_code_joins_text_blocks_when_result_missing(monkeypatch, claude_code):
    install_fake_query(monkeypatch, [
        FakeAssistantMessage(content=[FakeTextBlock("[{"), FakeTextBlock('"a": 1}]')]),
        FakeResultMessage(result=None),
    ])
    assert complete(model="m", system="s", user="u", max_tokens=10) == '[{"a": 1}]'


def test_ac11_claude_code_not_logged_in_explains_how_to_log_in(monkeypatch, claude_code):
    install_fake_query(monkeypatch, [FakeAssistantMessage(content=[], error="authentication_failed")])
    with pytest.raises(ModelCallError, match="sign in with your own account"):
        complete(model="m", system="s", user="u", max_tokens=10)


@pytest.mark.parametrize("messages,match", [
    ([FakeResultMessage(is_error=True, subtype="error_during_execution", errors=["boom"])], "boom"),
    ([FakeResultMessage(is_error=True, subtype="success", api_error_status=529)], "HTTP 529"),
    ([FakeAssistantMessage(content=[FakeTextBlock("partial")])], "without a result"),
    ([FakeResultMessage(result="   ")], "empty response"),
    ([FakeAssistantMessage(content=[], error="rate_limit")], "rate limit"),
])
def test_ac11_claude_code_errors_fail_loudly(monkeypatch, claude_code, messages, match):
    install_fake_query(monkeypatch, messages)
    with pytest.raises(ModelCallError, match=match):
        complete(model="m", system="s", user="u", max_tokens=10)


def test_ac11_missing_sdk_gives_install_hint(monkeypatch, claude_code):
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", None)
    with pytest.raises(ModelCallError, match="requirements-claude-code.txt"):
        complete(model="m", system="s", user="u", max_tokens=10)


def test_ac11_api_backend_ignores_claude_code(monkeypatch, mocker):
    """With the default backend, the Agent SDK is never touched (the conftest fake would raise)."""
    client = mocker.MagicMock()
    client.messages.create.return_value.content = [mocker.MagicMock(text="ok")]
    mocker.patch("anthropic.Anthropic", return_value=client)
    assert complete(model="m", system="s", user="u", max_tokens=10) == "ok"


# --- every agent works through the claude-code backend ------------------------------

FINDING = {"framework": "X", "control_id": "1", "control_name": "n", "status": "Gap",
           "severity": "High", "evidence": "e", "recommendation": "r"}

AGENTS = [
    ("agents.security_agent", "run_security_agent"),
    ("agents.resilience_agent", "run_resilience_agent"),
    ("agents.gov_baseline_agent", "run_gov_baseline_agent"),
    ("agents.ai_trust_agent", "run_ai_trust_agent"),
]


@pytest.mark.parametrize("module_name,func_name", AGENTS)
def test_ac11_finding_agents_on_claude_code(monkeypatch, claude_code, module_name, func_name):
    calls = install_fake_query(monkeypatch, answer(json.dumps([FINDING])))
    run = getattr(importlib.import_module(module_name), func_name)
    findings = run("VENDOR-TEXT-9921")
    assert len(findings) == 1 and findings[0].status == "Gap"
    assert "VENDOR-TEXT-9921" not in calls[0]["options"].system_prompt
    assert "VENDOR-TEXT-9921" in calls[0]["prompt"]


def test_ac11_orchestrator_on_claude_code(monkeypatch, claude_code):
    from agents.orchestrator import build_vendor_profile
    profile = {"name": "Acme", "sector": "Finance", "services": [], "processes_personal_data": False,
               "is_ai_system": False, "is_dutch_government_vendor": False, "applicable_frameworks": []}
    install_fake_query(monkeypatch, answer(json.dumps(profile)))
    assert build_vendor_profile("docs").name == "Acme"


def test_ac11_document_validity_on_claude_code(monkeypatch, claude_code):
    from agents.document_validity_agent import run_document_validity_agent
    record = {"doc_type": "SOC2_TYPE_II", "title": "SOC 2", "audit_period_end": "2026-01-01"}
    install_fake_query(monkeypatch, answer(json.dumps([record])))
    [f] = run_document_validity_agent("docs", date(2026, 4, 21))
    assert f.status == "Compliant"


def test_ac11_memo_on_claude_code(monkeypatch, claude_code):
    from models.finding import Finding, VendorProfile
    from synthesizer.memo import draft_memo_text
    install_fake_query(monkeypatch, answer("1. Executive Summary"))
    profile = VendorProfile(name="Acme", sector="Finance", services=[], processes_personal_data=False,
                            is_ai_system=False, is_dutch_government_vendor=False, applicable_frameworks=[])
    finding = Finding(**FINDING)
    assert draft_memo_text(profile, [finding], {"X": {"rag": "Red"}}) == "1. Executive Summary"


def test_ac11_unfaked_claude_code_is_refused(claude_code):
    """Guard check: without a fake query, the conftest stub refuses to run Claude Code."""
    with pytest.raises(RuntimeError, match="without a fake"):
        complete(model="m", system="s", user="u", max_tokens=10)
