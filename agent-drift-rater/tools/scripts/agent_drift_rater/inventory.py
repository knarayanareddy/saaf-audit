"""Classify repos, split monorepos into agent units, and select the files to review.

Classification uses imports and manifests, not README wording, to avoid the substring
false positives of keyword matching. A repo is split into units only for the SAAF template
convention (``tools/scripts/<agent>``) or when overrides.json says so; multi-agent systems
inside one repo stay one unit.
"""

import fnmatch
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from . import config
from .sources import RepoInfo

logger = logging.getLogger(__name__)

CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}
WEB_EXT = {".html", ".htm"}
TEXT_EXT = {".md", ".txt", ".prompt", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini"}

EXCLUDED_DIRS = {
    "data", "samples", "sample_data", "fixtures", "outputs", "reports", "cache", "public",
    "static", "demo", "dist", "build", "node_modules", "__pycache__", ".venv", "venv", "runs",
    "images", "img", "assets",
}
LOCKFILES = {"package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml", "Pipfile.lock", "uv.lock"}

P0_PATTERNS = [
    r"(^|/)README[^/]*$", r"(^|/)AUDIT-CRITERIA\.md$", r"(^|/)CLAUDE\.md$", r"(^|/)AGENTS\.md$",
    r"^\.claude/agents/[^/]+\.md$", r"(^|/)SKILL\.md$", r"^\.claude/settings[^/]*\.json$",
    r"(^|/)\.?mcp[^/]*\.json$", r"(^|/)prompts?/.+\.(md|txt|prompt)$", r"system-instructions/",
    r"[^/]*prompt[^/]*\.(md|txt)$", r"\.prompt$", r"(^|/)docs/adr[^/]*/.+\.md$",
    r"(^|/)memory/.+\.(md|txt|json)$", r"(^|/)lessons[^/]*\.(md|txt|json)$",
]
P1_PATTERNS = [
    r"(^|/)requirements[^/]*\.txt$", r"(^|/)pyproject\.toml$", r"(^|/)setup\.py$",
    r"(^|/)package\.json$", r"(^|/)Dockerfile$", r"^\.github/workflows/[^/]+\.ya?ml$",
    r"(^|/)CODEOWNERS$", r"allowlist[^/]*\.json$",
]
TEST_PATTERNS = [
    r"(^|/)tests?/", r"(^|/)test_[^/]+\.py$", r"_test\.py$", r"\.test\.[jt]sx?$",
    r"\.spec\.[jt]sx?$", r"(^|/)evals?/",
]
RANK_HINTS = (
    "prompt", "system", "agent", "tool", "guard", "polic", "validat", "log", "audit_trail",
    "memory", "lesson", "mcp", "server", "cli", "main", "app", "orchestr", "config", "run",
    "approv", "rule",
)
SHARED_ROOT_PATTERNS = [
    r"^README[^/]*$", r"^AUDIT-CRITERIA\.md$", r"^CLAUDE\.md$", r"^AGENTS\.md$", r"^CODEOWNERS$",
    r"^\.github/", r"^requirements[^/]*\.txt$", r"^pyproject\.toml$", r"^package\.json$",
    r"^\.claude/settings[^/]*\.json$", r"^\.mcp\.json$",
]

LLM_IMPORT_PY = re.compile(
    r"^\s*(?:from|import)\s+(anthropic|openai|langchain[\w.]*|langgraph[\w.]*|claude_agent_sdk|"
    r"google\.generativeai|google\.genai|ollama|litellm|mistralai|cohere|transformers)\b",
    re.M,
)
LLM_IMPORT_JS = re.compile(
    r"""(?:from\s+|require\(\s*|import\(\s*)['"](@anthropic-ai/[\w-]+|openai|@langchain/[\w-]+|"""
    r"""langchain|ai|@ai-sdk/[\w-]+|ollama)['"]"""
)
LLM_ENDPOINT = re.compile(r"api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com")
LLM_DEPS = re.compile(
    r"^\s*['\"]?(anthropic|openai|langchain[\w-]*|langgraph|claude-agent-sdk|google-generativeai|"
    r"google-genai|ollama|litellm|mistralai|cohere|@anthropic-ai/[\w-]+|@langchain/[\w-]+)\b",
    re.M | re.I,
)
AGENTIC = re.compile(
    r"\btools\s*=\s*[\[A-Za-z_]|\btools\s*:\s*\[|\binput_schema\b|\btool_use\b|\btool_calls\b|"
    r"@tool\b|\bbind_tools\(|\bStateGraph\b|ClaudeSDKClient|\ballowed_tools\b|FastMCP|@mcp\.tool|"
    r"\bfunction_call\b|\btool\(\{|create_react_agent|AgentExecutor|tool_runner"
)
WEB_FRAMEWORKS = re.compile(r'"(next|react|vite|astro|svelte|nuxt|vue|@angular/core)"\s*:')

REPO_READ_CAP_FILES = 300
REPO_READ_CAP_BYTES = 3_000_000


@dataclass
class Unit:
    unit_id: str
    repo: RepoInfo
    root: str  # "" for the whole repo, else e.g. "tools/scripts/agent_a"
    classification: str = "tool"  # agent | llm-app | tool
    files: Dict[str, str] = field(default_factory=dict)  # selected path -> text
    skipped: List[Tuple[str, str]] = field(default_factory=list)
    coverage: float = 1.0

    @property
    def display_name(self) -> str:
        return f"{self.repo.name}/{self.root}" if self.root else self.repo.name


@dataclass
class RepoInventory:
    repo: RepoInfo
    classification: str  # agent | llm-app | tool | website | docs | empty | unavailable | excluded
    reasons: List[str] = field(default_factory=list)
    units: List[Unit] = field(default_factory=list)


def load_overrides(path=config.OVERRIDES_FILE) -> Dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _matches(path: str, patterns: List[str]) -> bool:
    return any(re.search(p, path) for p in patterns)


def is_test(path: str) -> bool:
    return _matches(path, TEST_PATTERNS)


def tier(path: str) -> Optional[int]:
    """Return 0-3 for reviewable files, None for files to skip."""
    parts = PurePosixPath(path).parts
    name = parts[-1]
    if any(part.lower() in EXCLUDED_DIRS for part in parts[:-1]) or "transcript" in path.lower():
        return None
    if name in LOCKFILES or name.endswith(".min.js"):
        return None
    suffix = PurePosixPath(name).suffix.lower()
    if _matches(path, P0_PATTERNS):
        return 0
    if _matches(path, P1_PATTERNS):
        return 1
    if suffix in CODE_EXT or suffix in WEB_EXT:
        return 3 if is_test(path) else 2
    return None


def _rank(path: str) -> Tuple[int, int]:
    lowered = path.lower()
    hits = sum(1 for hint in RANK_HINTS if hint in lowered)
    web_penalty = 1 if PurePosixPath(path).suffix.lower() in WEB_EXT else 0
    return (web_penalty, -hits)


def _ordered(candidates: List[str]) -> List[str]:
    by_tier: Dict[int, List[str]] = {0: [], 1: [], 2: [], 3: []}
    for path in candidates:
        by_tier[tier(path)].append(path)  # type: ignore[index]
    by_tier[2].sort(key=_rank)
    return by_tier[0] + by_tier[1] + by_tier[2] + by_tier[3]


def uses_llm(path: str, text: str) -> bool:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".py" and LLM_IMPORT_PY.search(text):
        return True
    if suffix in CODE_EXT and suffix != ".py" and LLM_IMPORT_JS.search(text):
        return True
    if suffix in CODE_EXT or suffix in WEB_EXT:
        return bool(LLM_ENDPOINT.search(text))
    if PurePosixPath(path).name.startswith("requirements") or path.endswith(
        ("pyproject.toml", "setup.py", "package.json")
    ):
        return bool(LLM_DEPS.search(text))
    return False


def _unit_root(path: str) -> Optional[str]:
    match = re.match(r"^(tools/scripts/[^/]+?)(?:/|\.py$)", path)
    if match:
        return match.group(1)
    return None


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")


def build_inventory(source, repo: RepoInfo, overrides: Dict[str, Any]) -> RepoInventory:
    """Fetch, classify and split one repo. Reads files through ``source``."""
    repo_cfg = overrides.get("repos", {}).get(repo.name, {})
    if repo.name in overrides.get("exclude_repos", []):
        return RepoInventory(repo, "excluded", ["listed in overrides.exclude_repos"])

    source.load_tree(repo)
    if repo.error:
        cls = "empty" if "empty" in repo.error else "unavailable"
        return RepoInventory(repo, cls, [repo.error])

    include = repo_cfg.get("include")
    eligible = []
    for path, size in repo.files.items():
        if include and not any(fnmatch.fnmatch(path, pattern) for pattern in include):
            continue
        if tier(path) is None or size > config.MAX_FILE_BYTES:
            continue
        eligible.append(path)

    code_paths = [p for p in eligible if PurePosixPath(p).suffix.lower() in CODE_EXT | WEB_EXT]
    if not code_paths:
        return RepoInventory(repo, "docs", ["no code files"])

    # Read in priority order up to a per-repo budget.
    texts: Dict[str, str] = {}
    budget = 0
    for path in _ordered(eligible):
        if len(texts) >= REPO_READ_CAP_FILES or budget > REPO_READ_CAP_BYTES:
            break
        text = source.read(repo, path)
        if text is None:
            continue
        texts[path] = text
        budget += len(text)

    llm_files = {p for p, t in texts.items() if uses_llm(p, t)}
    reasons = [f"LLM usage in {len(llm_files)} file(s)"] if llm_files else ["no LLM SDK or endpoint found"]

    if not llm_files:
        manifest = texts.get("package.json", "")
        web_bytes = sum(repo.files[p] for p in repo.files if PurePosixPath(p).suffix.lower() in WEB_EXT | {".css"})
        code_bytes = sum(repo.files[p] for p in code_paths if PurePosixPath(p).suffix.lower() in CODE_EXT)
        if WEB_FRAMEWORKS.search(manifest) or web_bytes > code_bytes:
            return RepoInventory(repo, "website", reasons + ["web framework or HTML-dominant"])
        return RepoInventory(repo, "tool", reasons)

    # Unit roots: split only for tools/scripts/<x> layouts (or when forced by overrides).
    llm_roots = sorted({r for r in (_unit_root(p) for p in llm_files) if r})
    monorepo = bool(repo_cfg.get("monorepo")) or len(llm_roots) >= 2
    roots = llm_roots if monorepo and llm_roots else [""]

    inventory = RepoInventory(repo, "llm-app", reasons)
    for root in roots:
        unit_id = repo.name if not root else f"{repo.name}__{_slug(root.replace('tools/scripts/', ''))}"
        unit = Unit(unit_id=unit_id, repo=repo, root=root)
        if root:
            in_scope = [p for p in eligible if p == root + ".py" or p.startswith(root + "/")]
            unit_code = "\n".join(texts.get(p, "") for p in in_scope)
            shared = [p for p in eligible if _matches(p, SHARED_ROOT_PATTERNS)]
            referenced = [
                p for p in eligible
                if tier(p) == 0 and p not in in_scope and PurePosixPath(p).stem in unit_code
                and len(PurePosixPath(p).stem) >= 6
            ]
            scope = in_scope + [p for p in shared + referenced if p not in in_scope]
        else:
            scope = list(eligible)
        _select(unit, scope, texts, repo)
        unit_text = "\n".join(unit.files.values())
        if any(uses_llm(p, unit.files[p]) for p in unit.files):
            unit.classification = "agent" if (
                AGENTIC.search(unit_text) or any(p.startswith(".claude/agents/") for p in unit.files)
            ) else "llm-app"
        inventory.units.append(unit)

    classes = {u.classification for u in inventory.units}
    inventory.classification = "agent" if "agent" in classes else "llm-app"
    inventory.units = [u for u in inventory.units if u.classification in ("agent", "llm-app")]
    if monorepo:
        inventory.reasons.append(f"monorepo: {len(inventory.units)} agent unit(s)")
    return inventory


def _select(unit: Unit, scope: List[str], texts: Dict[str, str], repo: RepoInfo) -> None:
    """Apply tier ordering and per-unit caps; compute byte coverage."""
    ordered = _ordered(scope)
    tests = [p for p in ordered if tier(p) == 3]
    non_tests = [p for p in ordered if tier(p) != 3]
    reserve_for_tests = min(10, len(tests))
    picked: List[str] = []
    total = 0
    for path in non_tests + tests:
        size = repo.files.get(path, 0)
        limit = config.MAX_UNIT_FILES - (reserve_for_tests if tier(path) != 3 else 0)
        if path not in texts:
            unit.skipped.append((path, "not read (repo budget)"))
            continue
        if len(picked) >= limit or total + size > config.MAX_UNIT_BYTES:
            unit.skipped.append((path, "unit cap"))
            continue
        picked.append(path)
        total += size
    unit.files = {p: texts[p] for p in picked}
    candidate_bytes = sum(repo.files.get(p, 0) for p in scope) or 1
    unit.coverage = round(min(1.0, total / candidate_bytes), 3)
