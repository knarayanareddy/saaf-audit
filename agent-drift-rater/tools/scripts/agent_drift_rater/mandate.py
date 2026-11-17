"""The approved-mandate profile for an agent unit, and stage-1 extraction.

Drift is defined against the *mandate*, so each unit gets a profile first. It is stored as
one editable JSON file per unit (local only, gitignored) so a human can review and confirm it
before rating. README text is a claim; the rater verifies claims against code, so the profile
records the source location of each hard rule for later code cross-check.
"""

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import config

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"

# Source documents in priority order (role, filename-regex).
SOURCE_ROLES = [
    ("mandate", re.compile(r"(^|/)AUDIT-CRITERIA\.md$")),
    ("instructions", re.compile(r"(^|/)CLAUDE\.md$|(^|/)AGENTS\.md$")),
    ("claim", re.compile(r"(^|/)README[^/]*$")),
    ("system_prompt", re.compile(r"prompts?/.+\.(md|txt)$|system_prompt|\.prompt$")),
]

# Sentences that read like a hard rule.
RULE_SENT = re.compile(r"\b(must|never|always|required|shall|only|do not|don't|no more than|"
                       r"at most|maximum|minimum|prohibited)\b", re.I)
RULE_CAT = [
    ("threshold", re.compile(r"\b(no more than|at most|maximum|minimum|limit|exceed|over|under|"
                             r"\d+\s*(?:%|percent|eur|usd|\$|€|days?|hours?))\b", re.I)),
    ("approval", re.compile(r"\b(approv|authori[sz]|sign[\s-]?off|human|supervisor|escalat)\b", re.I)),
    ("data", re.compile(r"\b(evidence|pii|personal data|confidential|anonymi[sz])\b", re.I)),
    ("prohibition", re.compile(r"\b(never|do not|don't|prohibited|forbidden)\b", re.I)),
]


@dataclass
class HardRule:
    id: str
    rule: str          # <= 25-word paraphrase
    category: str
    source: str        # path#Lnn


@dataclass
class Mandate:
    schema_version: str = SCHEMA_VERSION
    unit_id: str = ""
    repo: str = ""
    unit_path: str = ""
    commit_sha: Optional[str] = None
    status: str = "unconfirmed"       # unconfirmed | confirmed | stale | rejected
    reviewer: Optional[str] = None
    reviewed_on: Optional[str] = None
    review_notes: str = ""
    source_fingerprint: str = ""
    confirmed_fingerprint: Optional[str] = None
    extracted_by: Dict[str, str] = field(default_factory=dict)
    sources: List[Dict[str, str]] = field(default_factory=list)
    purpose: str = ""
    autonomy_level: str = "advisory"  # advisory | assisted | autonomous
    hard_rules: List[Dict[str, str]] = field(default_factory=list)
    human_approval_points: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    mandate_gaps: List[str] = field(default_factory=list)
    confidence: str = "Low"

    def path(self, mandates_dir: Path) -> Path:
        return mandates_dir / f"{self.unit_id}.json"


def fingerprint(files: Dict[str, str]) -> str:
    joined = "\n".join(f"{p}:{hashlib.sha256(t.encode('utf-8')).hexdigest()}"
                       for p, t in sorted(files.items()))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _paraphrase(sentence: str, limit: int = 25) -> str:
    words = re.sub(r"\s+", " ", sentence).strip().split(" ")
    return " ".join(words[:limit]) + (" …" if len(words) > limit else "")


def _categorize(sentence: str) -> str:
    for name, pattern in RULE_CAT:
        if pattern.search(sentence):
            return name
    return "scope"


def extract_deterministic(unit_id: str, repo: str, unit_path: str, commit_sha: Optional[str],
                          source_files: Dict[str, str]) -> Mandate:
    """Heuristic mandate from doc headings and modal sentences. No network."""
    mandate = Mandate(unit_id=unit_id, repo=repo, unit_path=unit_path, commit_sha=commit_sha)
    mandate.source_fingerprint = fingerprint(source_files)
    mandate.extracted_by = {"method": "deterministic"}

    chosen: Dict[str, str] = {}
    for role, pattern in SOURCE_ROLES:
        for path in source_files:
            if pattern.search(path) and role not in chosen:
                chosen[role] = path
                mandate.sources.append({"path": path, "role": role})

    rule_id = 1
    for role in ("mandate", "instructions", "claim", "system_prompt"):
        path = chosen.get(role)
        if not path:
            continue
        lines = source_files[path].splitlines()
        if role in ("claim", "instructions") and not mandate.purpose:
            for line in lines:
                clean = line.strip().lstrip("#").strip()
                if len(clean) > 30 and not clean.startswith(("|", "-", "*", "`", ">")):
                    mandate.purpose = _paraphrase(clean, 40)
                    break
        for i, line in enumerate(lines, 1):
            if RULE_SENT.search(line) and 15 < len(line.strip()) < 240 and rule_id <= 15:
                clean = line.strip().lstrip("-*0123456789. ").strip()
                mandate.hard_rules.append(asdict(HardRule(
                    id=f"R{rule_id}", rule=_paraphrase(clean), category=_categorize(line),
                    source=f"{path}#L{i}")))
                rule_id += 1
        if role in ("mandate", "claim"):
            for i, line in enumerate(lines, 1):
                if re.search(r"\b(approv|escalat|human review|sign[\s-]?off)\b", line, re.I):
                    mandate.human_approval_points.append(f"{path}#L{i}: {_paraphrase(line.strip(), 18)}")
                    break

    if not mandate.sources:
        mandate.mandate_gaps.append("No mandate/README/prompt document found")
    if not mandate.hard_rules:
        mandate.mandate_gaps.append("No hard rules documented")
    if not mandate.purpose:
        mandate.mandate_gaps.append("No stated purpose")
    mandate.confidence = "Low" if mandate.mandate_gaps else "Medium"
    return mandate


def load(path: Path) -> Optional[Mandate]:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Mandate(**data)


def save(mandate: Mandate, mandates_dir: Path) -> Path:
    mandates_dir.mkdir(parents=True, exist_ok=True)
    path = mandate.path(mandates_dir)
    path.write_text(json.dumps(asdict(mandate), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def reconcile(existing: Optional[Mandate], fresh: Mandate) -> Mandate:
    """Keep a confirmed mandate; mark it stale if its sources changed."""
    if existing is None:
        return fresh
    if existing.status == "confirmed":
        if existing.confirmed_fingerprint and existing.confirmed_fingerprint != fresh.source_fingerprint:
            existing.status = "stale"
            existing.source_fingerprint = fresh.source_fingerprint
        return existing
    fresh.reviewer = existing.reviewer
    return fresh


def confirm(mandate: Mandate, reviewer: str, notes: str, when: str) -> Mandate:
    mandate.status = "confirmed"
    mandate.reviewer = reviewer
    mandate.review_notes = notes
    mandate.reviewed_on = when
    mandate.confirmed_fingerprint = mandate.source_fingerprint
    return mandate
