"""
Finding I/O
===========

Load and save audit findings conforming to
``outputs/schemas/finding-schema.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("id", "title", "risk_rating", "observation", "recommendation")


def load_finding(path: Path) -> dict[str, Any]:
    """Load a finding JSON file and validate required fields.

    Args:
        path: Path to a JSON file conforming to finding-schema.json.

    Returns:
        The finding as a dict.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If JSON is malformed or required fields are missing.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Finding file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {path}: {e}") from e

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Finding {path} missing required fields: {missing}")

    return data


def save_finding(finding: dict[str, Any], path: Path) -> None:
    """Write a finding JSON back to disk with stable formatting.

    Args:
        finding: Finding dict (may include hallucination_check extension).
        path: Destination path. Parent directory created if missing.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(finding, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def finding_text(finding: dict[str, Any]) -> str:
    """Concatenate title + observation + recommendation into one string.

    This is the input to the claim extractor.

    Args:
        finding: Finding dict.

    Returns:
        Single string, the three fields separated by blank lines.
    """
    parts = [
        str(finding.get("title", "")).strip(),
        str(finding.get("observation", "")).strip(),
        str(finding.get("recommendation", "")).strip(),
    ]
    return "\n\n".join(p for p in parts if p)
