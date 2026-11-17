"""Non-secret settings; add integration-specific settings after intake."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    name: str = "MCP Starter"

    @classmethod
    def from_environment(cls) -> "Settings":
        name = os.environ.get("MCP_SERVER_NAME", "MCP Starter").strip()
        if not name:
            raise ValueError("MCP_SERVER_NAME must not be empty")
        return cls(name=name)
