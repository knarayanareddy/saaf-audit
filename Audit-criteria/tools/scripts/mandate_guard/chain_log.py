"""Tamper-evident JSONL log: each line carries the hash of the line before it.

Editing, deleting or reordering any earlier line breaks the chain, and
``verify`` reports the first line where it breaks. This turns a run log from a
record someone could quietly edit into evidence an auditor can rely on
(IIA 2340 supervision trail, GIAS evidence integrity).

Pure standard library.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

GENESIS = "0" * 64


def sha256_json(obj: Any) -> str:
    """Fingerprint of any JSON value: SHA-256 of its canonical serialisation."""
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _digest(record: Dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seal(record: Dict[str, Any], prev_hash: str, seq: int) -> Dict[str, Any]:
    """Return a copy of ``record`` with seq, prev_hash and its own hash added."""
    sealed = dict(record, seq=seq, prev_hash=prev_hash)
    sealed["hash"] = _digest(sealed)
    return sealed


class ChainLog:
    """Append-only, hash-chained JSONL writer. Resumes an existing chain."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prev_hash, self.seq = GENESIS, 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.prev_hash, self.seq = rec["hash"], rec["seq"] + 1

    def append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        sealed = seal(record, self.prev_hash, self.seq)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sealed, ensure_ascii=False) + "\n")
        self.prev_hash, self.seq = sealed["hash"], self.seq + 1
        return sealed


def verify(path: Path) -> Tuple[bool, Optional[int], str]:
    """Check the whole chain. Returns (ok, first_bad_line_number, reason)."""
    prev = GENESIS
    lines = [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    for n, line in enumerate(lines, start=1):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            return False, n, "line is not valid JSON"
        if rec.get("seq") != n - 1:
            return False, n, f"sequence {rec.get('seq')} where {n - 1} expected (line removed or reordered)"
        if rec.get("prev_hash") != prev:
            return False, n, "prev_hash does not match the line before (line removed or reordered)"
        if _digest(rec) != rec.get("hash"):
            return False, n, "content does not match its hash (line edited)"
        prev = rec["hash"]
    return True, None, f"{len(lines)} line(s) intact"
