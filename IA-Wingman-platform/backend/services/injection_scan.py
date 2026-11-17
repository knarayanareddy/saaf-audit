"""Deterministic prompt-injection heuristics for uploaded/fetched content.

This is a *signal*, not a verdict. It flags text that looks like it is trying to
steer an LLM (instruction overrides, role hijacks, system-prompt disclosure,
exfiltration, delimiter breaks, invisible characters). It never calls an LLM and
never blocks a document — a flagged document stays fully usable; the UI shows
"possibly suspicious — verify".

Tuned for low false positives: patterns anchor on instruction-shaped objects
("ignore previous *instructions*"), not bare words, so ordinary audit prose that
merely mentions "ignore" or "system" does not trip them.
"""
import re

# Invisible / bidi-control characters commonly used to hide injected text.
_INVISIBLE = {
    "​": "zero-width space",
    "‌": "zero-width non-joiner",
    "‍": "zero-width joiner",
    "⁠": "word joiner",
    "﻿": "zero-width no-break space",
    "‎": "left-to-right mark",
    "‏": "right-to-left mark",
    "‪": "bidi embedding",
    "‫": "bidi embedding",
    "‭": "bidi override",
    "‮": "bidi override",
}

# (name, severity, regex). Severity: high = classic override/disclosure/exfil,
# medium = role/persuasion/delimiter tricks.
_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("instruction_override", "high", re.compile(
        r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}\b"
        r"(previous|above|prior|preceding|earlier|all)\b[^.\n]{0,30}\b"
        r"(instruction|instructions|prompt|prompts|context|rules|guidance)\b", re.I)),
    ("system_prompt_disclosure", "high", re.compile(
        r"\b(reveal|show|print|repeat|output|display|tell me|what (?:is|are))\b[^.\n]{0,30}\b"
        r"(your\s+)?(system\s+)?(prompt|instructions|guidelines|rules)\b", re.I)),
    ("exfiltration", "high", re.compile(
        r"\b(send|post|email|upload|exfiltrate|leak|transmit|forward)\b[^.\n]{0,50}\b"
        r"(http|https|url|webhook|endpoint|api\b|external|address)\b", re.I)),
    ("role_hijack", "medium", re.compile(
        r"\b(you are now|from now on(?:,)? you|act as|pretend to be|behave as|"
        r"you must now|new instructions?:)\b", re.I)),
    ("delimiter_break", "medium", re.compile(
        r"(?m)^(?:\s*(?:===+\s*end|<<end[:>]|-{3,}\s*end|```+\s*$|\[/?system\]|\[/?inst\]))", re.I)),
    ("model_address", "medium", re.compile(
        r"\b(as an ai|language model|assistant[:,]|dear (?:ai|assistant|claude|model)|"
        r"important instruction for the (?:ai|assistant|model))\b", re.I)),
]

_SNIPPET = 80


def scan_text(content: str | None) -> list[dict]:
    """Return a list of heuristic injection flags (may be empty)."""
    if not content:
        return []
    flags: list[dict] = []

    seen_invisible: set[str] = set()
    for ch, name in _INVISIBLE.items():
        if ch in content and ch not in seen_invisible:
            seen_invisible.add(ch)
            flags.append({
                "pattern": "invisible_characters",
                "severity": "medium",
                "detail": name,
                "offset": content.index(ch),
                "snippet": "",
            })

    for name, severity, rx in _PATTERNS:
        for m in rx.finditer(content):
            start = max(0, m.start() - 12)
            snippet = content[start:m.end() + 24].replace("\n", " ").strip()
            flags.append({
                "pattern": name,
                "severity": severity,
                "detail": "",
                "offset": m.start(),
                "snippet": snippet[:_SNIPPET],
            })

    flags.sort(key=lambda f: f["offset"])
    return flags


def scan_summary(flags: list[dict]) -> dict:
    """Compact roll-up for the UI: count + highest severity."""
    order = {"high": 3, "medium": 2, "low": 1}
    max_sev = max((f["severity"] for f in flags), key=lambda s: order.get(s, 0), default=None)
    return {"count": len(flags), "max_severity": max_sev}
