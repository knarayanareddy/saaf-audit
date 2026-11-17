from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")


def load_dotenv(path: Path) -> None:
    """Load a simple .env file without overriding existing environment values."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _csv_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    environment: str
    report_language: str
    log_level: str
    high_risk_threshold: float
    critical_risk_threshold: float
    risk_score_max: float
    ineffective_statuses: set[str]
    require_human_approval: bool
    audit_hash_chain: bool
    default_output_dir: str
    llm_provider: str

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        if env_file is not None:
            load_dotenv(env_file)

        statuses = {
            _normalize_token(status)
            for status in _csv_env(
                "EXEC_SUMMARY_INEFFECTIVE_STATUSES",
                ["ineffective", "not effective", "onvoldoende", "partially effective"],
            )
        }

        return cls(
            environment=os.getenv("EXEC_SUMMARY_ENVIRONMENT", "development"),
            report_language=os.getenv("EXEC_SUMMARY_REPORT_LANGUAGE", "nl"),
            log_level=os.getenv("EXEC_SUMMARY_LOG_LEVEL", "INFO"),
            high_risk_threshold=_float_env("EXEC_SUMMARY_HIGH_RISK_THRESHOLD", 15.0),
            critical_risk_threshold=_float_env("EXEC_SUMMARY_CRITICAL_RISK_THRESHOLD", 20.0),
            risk_score_max=_float_env("EXEC_SUMMARY_RISK_SCORE_MAX", 25.0),
            ineffective_statuses=statuses,
            require_human_approval=_bool_env("EXEC_SUMMARY_REQUIRE_HUMAN_APPROVAL", True),
            audit_hash_chain=_bool_env("EXEC_SUMMARY_AUDIT_HASH_CHAIN", True),
            default_output_dir=os.getenv("EXEC_SUMMARY_DEFAULT_OUTPUT_DIR", "reports"),
            llm_provider=os.getenv("EXEC_SUMMARY_LLM_PROVIDER", "offline"),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "report_language": self.report_language,
            "log_level": self.log_level,
            "high_risk_threshold": self.high_risk_threshold,
            "critical_risk_threshold": self.critical_risk_threshold,
            "risk_score_max": self.risk_score_max,
            "ineffective_statuses": sorted(self.ineffective_statuses),
            "require_human_approval": self.require_human_approval,
            "audit_hash_chain": self.audit_hash_chain,
            "default_output_dir": self.default_output_dir,
            "llm_provider": self.llm_provider,
        }


def _normalize_token(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def redacted_env_snapshot() -> dict[str, str]:
    keys = [
        "EXEC_SUMMARY_ENVIRONMENT",
        "EXEC_SUMMARY_REPORT_LANGUAGE",
        "EXEC_SUMMARY_LOG_LEVEL",
        "EXEC_SUMMARY_HIGH_RISK_THRESHOLD",
        "EXEC_SUMMARY_CRITICAL_RISK_THRESHOLD",
        "EXEC_SUMMARY_RISK_SCORE_MAX",
        "EXEC_SUMMARY_INEFFECTIVE_STATUSES",
        "EXEC_SUMMARY_REQUIRE_HUMAN_APPROVAL",
        "EXEC_SUMMARY_AUDIT_HASH_CHAIN",
        "EXEC_SUMMARY_DEFAULT_OUTPUT_DIR",
        "EXEC_SUMMARY_LLM_PROVIDER",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    snapshot: dict[str, str] = {}
    for key in keys:
        value = os.getenv(key)
        if value is None:
            snapshot[key] = "<unset>"
        elif any(marker in key.upper() for marker in SECRET_MARKERS):
            snapshot[key] = "<set:redacted>" if value else "<empty>"
        else:
            snapshot[key] = value
    return snapshot


def load_reporting_profile(path: Path, profile_name: str = "default") -> dict[str, Any]:
    if not path.exists():
        return {"name": "Built-in default profile", "frameworks": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    profile = data.get(profile_name)
    if isinstance(profile, dict):
        return profile
    return {"name": f"Missing profile: {profile_name}", "frameworks": []}
