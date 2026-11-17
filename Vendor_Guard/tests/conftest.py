"""
Suite-wide guards: tests must never reach the network or the real Anthropic API.

- ANTHROPIC_API_KEY is removed, so a missed mock cannot spend credits or leak data.
- anthropic.Anthropic raises unless a test patches it with a mock.
- Outbound IPv4/IPv6 socket connections raise.
- The default "api" backend is used, and `claude_agent_sdk` is replaced by a fake
  module whose query() refuses, so no test can start a real Claude Code process.
  Tests that exercise the claude-code backend swap in their own fake query().
"""
import socket
import sys
import types
from dataclasses import dataclass, field
from typing import Any

import anthropic
import pytest


class NetworkAccessInTests(RuntimeError):
    pass


@dataclass
class FakeTextBlock:
    text: str


@dataclass
class FakeAssistantMessage:
    content: list
    model: str = "fake"
    error: str | None = None


@dataclass
class FakeResultMessage:
    subtype: str = "success"
    is_error: bool = False
    result: str | None = None
    errors: list | None = None
    api_error_status: int | None = None


@dataclass
class FakeClaudeAgentOptions:
    system_prompt: Any = None
    model: str | None = None
    tools: Any = None
    setting_sources: Any = None
    strict_mcp_config: bool = False
    max_turns: int | None = None
    extra: dict = field(default_factory=dict)


def make_fake_sdk(query):
    module = types.ModuleType("claude_agent_sdk")
    module.AssistantMessage = FakeAssistantMessage
    module.ResultMessage = FakeResultMessage
    module.TextBlock = FakeTextBlock
    module.ClaudeAgentOptions = FakeClaudeAgentOptions
    module.query = query
    return module


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("VENDORGUARD_BACKEND", raising=False)


@pytest.fixture(autouse=True)
def _no_real_claude_code(monkeypatch):
    async def _refuse(*args, **kwargs):
        raise NetworkAccessInTests("claude_agent_sdk.query() called without a fake")
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setitem(sys.modules, "claude_agent_sdk", make_fake_sdk(_refuse))


@pytest.fixture(autouse=True)
def _no_unmocked_client(monkeypatch):
    def _refuse(*args, **kwargs):
        raise NetworkAccessInTests("anthropic.Anthropic() called without a mock")

    monkeypatch.setattr(anthropic, "Anthropic", _refuse)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _is_inet(sock):
        return sock.family in (socket.AF_INET, socket.AF_INET6)

    def _is_outbound(sock, address):
        # Loopback is allowed so the local web UI server can be tested in-process.
        return _is_inet(sock) and address[0] not in ("127.0.0.1", "::1", "localhost")

    def connect(self, address, *args, **kwargs):
        if _is_outbound(self, address):
            raise NetworkAccessInTests(f"Outbound connection attempted in tests: {address!r}")
        return real_connect(self, address, *args, **kwargs)

    def connect_ex(self, address, *args, **kwargs):
        if _is_outbound(self, address):
            raise NetworkAccessInTests(f"Outbound connection attempted in tests: {address!r}")
        return real_connect_ex(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
