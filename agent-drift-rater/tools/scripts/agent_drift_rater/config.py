"""Paths, limits and constants for the Agent Drift Rater."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[2]

ORG = "SAAF-Project"

# Local working state — all gitignored (see .gitignore in this package).
CACHE_DIR = PACKAGE_DIR / "cache"
RUNS_DIR = PACKAGE_DIR / "runs"
MANDATES_DIR = PACKAGE_DIR / "mandates"
OVERRIDES_FILE = PACKAGE_DIR / "overrides.json"

# Synthetic fixtures for --simulate / selftest.
SAMPLE_DIR = PACKAGE_DIR / "sample_data"
FIXTURE_REPOS_DIR = SAMPLE_DIR / "repos"
FIXTURE_ORG_FILE = SAMPLE_DIR / "fixture_org.json"
FIXTURE_MANDATES_DIR = SAMPLE_DIR / "mandates"
FIXTURE_EXPECTED_FILE = SAMPLE_DIR / "expected.json"

# Committed destinations — only written by `publish`, after the leak check.
PUBLISH_DIR = REPO_ROOT / "agent-drift-review" / "reports"
EXAMPLES_DIR = REPO_ROOT / "outputs" / "examples"
FINDING_SCHEMA_FILE = REPO_ROOT / "outputs" / "schemas" / "finding-schema.json"
PROMPT_FILE = REPO_ROOT / "prompts" / "audit-use-cases" / "agent-drift-rater.md"
PLANS_DIR = REPO_ROOT / "plans"

# Claude pass. Default per the Claude API guidance; override with --model.
DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "high"
MAX_OUTPUT_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"
DEFAULT_MAX_LLM_CALLS = 100

# File selection limits.
MAX_FILE_BYTES = 100_000
MAX_UNIT_FILES = 60
MAX_UNIT_BYTES = 600_000
LOW_COVERAGE = 0.60

# Excerpt limits for the Claude pass.
EXCERPT_CONTEXT_LINES = 3
MAX_EXCERPT_LINES_PER_UNIT = 400
MAX_PROMPT_CHARS = 8000

# Leak check: committed text may not share this many consecutive tokens with fetched code.
LEAK_SHINGLE_TOKENS = 6

FINDINGS_CAP_PER_UNIT = 6

DISCLAIMER = (
    "Static design review: ratings describe design susceptibility to drift based on code and "
    "documentation at a pinned commit. They are design evidence, not certification, and do not "
    "show how an agent behaved at runtime. EU AI Act articles are used as a good-practice "
    "benchmark; most hackathon agents are unlikely to be high-risk systems under Annex III."
)
