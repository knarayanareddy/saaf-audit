from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    file: str
    row: str

    @property
    def label(self) -> str:
        return f"{self.file}:{self.row}"


@dataclass
class Control:
    control_id: str
    name: str
    effectiveness: str
    owner: str = ""
    department: str = ""
    process: str = ""
    framework: str = ""
    risk_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    source: SourceRef = field(default_factory=lambda: SourceRef("", ""))
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Risk:
    risk_id: str
    name: str
    residual_score: float | None = None
    inherent_score: float | None = None
    impact: float | None = None
    likelihood: float | None = None
    rating: str = ""
    owner: str = ""
    department: str = ""
    process: str = ""
    framework: str = ""
    control_ids: list[str] = field(default_factory=list)
    trend: str = ""
    rationale: str = ""
    source: SourceRef = field(default_factory=lambda: SourceRef("", ""))
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dataset:
    controls: list[Control]
    risks: list[Risk]
    skipped_records: list[dict[str, Any]] = field(default_factory=list)
    source_files: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Finding:
    finding_id: str
    title: str
    severity: str
    confidence: str
    theme: str
    risk_id: str = ""
    control_ids: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class AnalysisResult:
    posture: str
    metrics: dict[str, Any]
    findings: list[Finding]
    themes: list[dict[str, Any]]
    data_quality: list[str]
    traceability: list[dict[str, Any]]
    assumptions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
