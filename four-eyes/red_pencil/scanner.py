"""Walk a folder, run the rules on each file, collect findings.

Only reads files. Never imports, executes or sends anything.
"""

from __future__ import annotations

import fnmatch
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from .rules import RULES, SEVERITY_ORDER, Finding, check_python, check_template, suppressed

SKIP_DIRS = {
    ".git",
    ".hg",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "site-packages",
    "dist",
    "build",
    ".next",
}
PYTHON_EXT = {".py"}
TEMPLATE_EXT = {".html", ".htm", ".jinja", ".jinja2", ".j2"}
MAX_BYTES = 1_000_000  # skip very large files (generated or vendored code)


@dataclass
class ScanResult:
    root: str
    repo: str
    files_scanned: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (path, reason)
    findings: list[Finding] = field(default_factory=list)


def _iter_files(root: Path, exclude: list[str]):
    if root.is_file():
        yield root, root.name
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            rel = path.relative_to(root).as_posix()
            if any(fnmatch.fnmatch(rel, pattern) for pattern in exclude):
                continue
            yield path, rel


def scan(root: Path, exclude: list[str] | None = None, repo: str | None = None) -> ScanResult:
    root = Path(root)
    result = ScanResult(root=str(root), repo=repo or root.resolve().name)
    for path, rel in _iter_files(root, exclude or []):
        suffix = path.suffix.lower()
        if suffix not in PYTHON_EXT and suffix not in TEMPLATE_EXT:
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                result.skipped.append((rel, "larger than 1 MB"))
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            result.skipped.append((rel, f"unreadable: {exc.strerror or exc}"))
            continue

        if suffix in PYTHON_EXT:
            try:
                # Scanned code may contain odd escape sequences; keep the output clean.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    hits = check_python(source)
            except (SyntaxError, ValueError) as exc:
                result.skipped.append((rel, f"not parseable as Python: {exc.__class__.__name__}"))
                continue
        else:
            hits = check_template(source)

        result.files_scanned += 1
        lines = source.splitlines()
        for rule_id, line, detail in hits:
            line_text = lines[line - 1] if 0 < line <= len(lines) else ""
            if suppressed(line_text, rule_id):
                continue
            result.findings.append(Finding(RULES[rule_id], rel, line, detail))

    result.findings.sort(key=lambda f: (-SEVERITY_ORDER[f.rule.severity], f.path, f.line))
    return result
