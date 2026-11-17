"""Shared helpers for SAAF scanner checks. Checks import: from _lib import Hit, functions, snippet, redact"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Hit:
    path: str            # repo-relative path
    line: int            # 1-based
    evidence: str        # short excerpt; secrets MUST be passed through redact()
    detail: str = ""     # why this location matches


def snippet(line: str, n: int = 160) -> str:
    return re.sub(r"\s+", " ", line.strip())[:n]


def redact(s: str) -> str:
    """Keep the first 4 characters of anything secret-looking."""
    return re.sub(r"([A-Za-z0-9_\-]{4})[A-Za-z0-9_\-+/=]{8,}", r"\1***", s)


_DEF = re.compile(r"^(\s*)(async\s+def|def)\s+\w+")


def functions(lines: list[str]):
    """Yield (start_idx, end_idx, header) for each Python function, using indentation (no import/exec of code)."""
    defs = [(i, len(m.group(1))) for i, l in enumerate(lines) if (m := _DEF.match(l))]
    for k, (i, ind) in enumerate(defs):
        j = i + 1
        while j < len(lines):
            l = lines[j]
            if l.strip() and (len(l) - len(l.lstrip())) <= ind and not l.lstrip().startswith(("#", ")", "]", "}")):
                break
            j += 1
        yield i, j, lines[i].strip()
