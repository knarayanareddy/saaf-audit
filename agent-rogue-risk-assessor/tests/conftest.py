import importlib.util, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "skills" / "agent-rogue-risk-assessor" / "scripts" / "scan_repo.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def scanner():
    return _load("scan_repo", SCANNER)


@pytest.fixture(scope="session")
def softening_tool():
    return _load("check_softening", ROOT / "tools" / "check_softening.py")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "test@example.org")
    git(path, "config", "user.name", "test")
    return path


def commit_all(path, msg):
    git(path, "add", "-A")
    git(path, "commit", "-qm", msg)


@pytest.fixture
def risky_repo(tmp_path):
    r = init_repo(tmp_path / "risky")
    (r / "prompts").mkdir()
    (r / "prompts" / "system_prompt.md").write_text(
        "You are a payments review agent. Escalation to a human is required for any amount above EUR 10,000.\n"
        "You must never approve vendors on the sanctions list.\n"
        "Your score is based on throughput; top performer agents reduce escalations.\n")
    (r / "agent.py").write_text(
        'TOOLS=[{"name":"update_memory"},{"name":"write_file"}]\n'
        "def update_system_prompt(new):\n"
        '    with open("prompts/system_prompt.md","w") as f: f.write(new)\n')
    commit_all(r, "init")
    p = r / "prompts" / "system_prompt.md"
    p.write_text(p.read_text().replace("is required", "is plausible"))
    commit_all(r, "tune")
    return r


@pytest.fixture
def controlled_repo(tmp_path):
    r = init_repo(tmp_path / "controlled")
    (r / "agent_config" / "approved").mkdir(parents=True)
    (r / "tests").mkdir(); (r / "docs").mkdir()
    (r / "agent_config" / "approved" / "system_prompt.md").write_text(
        "Escalation to a human is required above EUR 10,000. Never approve sanctioned vendors.\n")
    (r / "agent_config" / "approved" / "manifest.json").write_text('{"version":"1","files":{}}')
    (r / "guards.py").write_text(
        "class LimitExceeded(Exception): ...\n"
        "def guard(action):\n"
        "    if action.get('amount_eur',0) > 10000: raise LimitExceeded('over limit')\n"
        "    return action\n")
    (r / "decision_log.py").write_text(
        "def log_decision(path, *, input, instruction_version, model_version, tool_calls, outcome): ...\n")
    (r / "integrity.py").write_text(
        "import hashlib\ndef verify_baseline(): raise RuntimeError('QUARANTINE')  # rollback to known-good checkpoint\n")
    (r / "tests" / "test_guards.py").write_text(
        "def test_guard_blocks_over_limit_even_if_prompt_allows(): pass\n"
        "def test_rollback_restores_baseline(): pass\n"
        "def test_replay_reperform_decision(): pass\n")
    (r / "CODEOWNERS").write_text("agent_config/approved/ prompt @independent-reviewers\n")
    (r / "docs" / "drift-review.md").write_text(
        "Drift review: independent review by second line; alerts threshold 25%, closed in tracker.\n"
        "Escalation rate monitored by case_type (case mix).\n")
    commit_all(r, "init")
    return r
