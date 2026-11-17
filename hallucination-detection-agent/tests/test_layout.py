"""The repository layout after the move out of SAAF-Project (October 2026).

The code used to resolve the repo root four folders up; in its own repo that
pointed at /Users. These tests fail loudly if the prompts or the root move again.
CO-5 of AUDIT-CRITERIA.md: key from the environment only, none in tracked files.
"""
import importlib
import re
from pathlib import Path

import pytest

from hallucination import claude_client

ROOT = Path(__file__).resolve().parents[1]

# A real Anthropic key is the prefix followed by a long token. The bare prefix
# and the documented placeholder appear in prose and must not trip the scan.
KEY_PATTERN = re.compile(r"sk-ant-(?!PLACEHOLDER)[A-Za-z0-9_-]{40,}")


def test_repo_root_is_this_repository():
    assert claude_client.REPO_ROOT == ROOT


def test_repo_root_can_be_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("HALLUCINATION_REPO_ROOT", str(tmp_path))
    importlib.reload(claude_client)
    try:
        assert claude_client.REPO_ROOT == tmp_path
    finally:
        monkeypatch.delenv("HALLUCINATION_REPO_ROOT")
        importlib.reload(claude_client)


def test_both_prompts_load_from_this_repository():
    extractor = claude_client.load_prompt("prompts/audit-use-cases/hallucination-claim-extractor.md")
    verifier = claude_client.load_prompt("prompts/audit-use-cases/hallucination-claim-verifier.md")
    assert "factual claim" in extractor.lower()
    assert "SUPPORTED" in verifier and "UNVERIFIED" in verifier and "LIKELY_HALLUCINATED" in verifier


def test_api_key_missing_fails_fast(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        claude_client.get_api_key()


def test_placeholder_key_is_rejected(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-PLACEHOLDER-replace-me")
    with pytest.raises(EnvironmentError):
        claude_client.get_api_key()


def test_key_pattern_matches_a_real_shaped_key_only():
    assert KEY_PATTERN.search("sk-ant-" + "a" * 60)
    assert not KEY_PATTERN.search("the key starts with sk-ant- and is long")
    assert not KEY_PATTERN.search("sk-ant-PLACEHOLDER-replace-me")


def test_no_key_committed_in_tracked_files():
    hits = []
    for p in ROOT.rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        if p.suffix in {".py", ".md", ".txt", ".json", ".example", ".toml", ".cfg", ".ini", ".local"}:
            if KEY_PATTERN.search(p.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(p.relative_to(ROOT)))
    assert hits == [], f"possible API key in tracked files: {hits}"
