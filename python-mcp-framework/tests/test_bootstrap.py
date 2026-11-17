import json
import subprocess

import pytest
from test_starter import load_script


def fixture_repo(tmp_path, existing=False):
    (tmp_path / "reference.json").write_text(json.dumps({
        "url": "https://github.com/modelcontextprotocol/python-sdk",
        "tag": "v2.2.0", "commit": "expected", "examples": ["example.py"],
    }))
    target = tmp_path / ".references/python-sdk"
    if existing:
        (target / ".git").mkdir(parents=True)
        (target / "example.py").touch()
    return target


@pytest.mark.parametrize("existing", [False, True])
def test_clone_or_reuse_pinned_reference(tmp_path, monkeypatch, existing):
    bootstrap = load_script("bootstrap")
    target = fixture_repo(tmp_path, existing)
    calls = []

    def run(*args, **kwargs):
        calls.append(args)
        if args[1] == "clone":
            (target / ".git").mkdir(parents=True)
            (target / "example.py").touch()
        if args[1] == "remote":
            return "https://github.com/modelcontextprotocol/python-sdk.git"
        if args[1] == "rev-parse":
            return "expected"
        return ""

    monkeypatch.setattr(bootstrap, "run", run)
    assert bootstrap.ensure_reference(tmp_path) == "expected"
    assert any(call[1] == "clone" for call in calls) is not existing


@pytest.mark.parametrize("problem", ["origin", "dirty", "revision"])
def test_existing_clone_mismatch_is_not_overwritten(tmp_path, monkeypatch, problem):
    bootstrap = load_script("bootstrap")
    fixture_repo(tmp_path, True)

    def run(*args, **kwargs):
        assert args[1] not in ("clone", "reset", "checkout", "fetch")
        if args[1] == "remote":
            return "wrong" if problem == "origin" else (
                "https://github.com/modelcontextprotocol/python-sdk"
            )
        if args[1] == "status":
            return " M file" if problem == "dirty" else ""
        return "wrong" if problem == "revision" else "expected"

    monkeypatch.setattr(bootstrap, "run", run)
    with pytest.raises(RuntimeError):
        bootstrap.ensure_reference(tmp_path)


def test_missing_prerequisites_have_actionable_error(monkeypatch, capsys):
    bootstrap = load_script("bootstrap")
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _: None)
    assert bootstrap.main() == 1
    assert "Missing: git, uv" in capsys.readouterr().err


def test_clone_failure_blocks_preparation(monkeypatch, capsys):
    bootstrap = load_script("bootstrap")
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _: "/tool")

    def fail():
        raise subprocess.CalledProcessError(128, "git clone", stderr="Network unavailable")

    monkeypatch.setattr(bootstrap, "ensure_reference", fail)
    assert bootstrap.main() == 1
    assert "Network unavailable" in capsys.readouterr().err
