"""Deterministic reporting helper — no LLM. Formats findings as a Markdown table."""

from typing import Dict, List


def to_table(rows: List[Dict[str, str]]) -> str:
    out = ["| id | risk | title |", "|---|---|---|"]
    for row in rows:
        out.append(f"| {row['id']} | {row['risk']} | {row['title']} |")
    return "\n".join(out)
