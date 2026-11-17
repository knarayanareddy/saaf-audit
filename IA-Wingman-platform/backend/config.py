import re

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Whitespace anywhere, and the invisible characters a web page or editor can
#: slip into a copied value. None of them is ever part of an API key.
_NOT_IN_A_KEY = re.compile(r"[\s​‌‍⁠﻿]")


def clean_api_key(raw: str) -> str:
    """The key as pasted into a host's secret field, without what came with it:
    surrounding quotes, the `NAME=` of the .env line it was copied from, and
    spaces, line breaks or invisible characters. On Render (2026-10-23) a key
    that began with `sk-ant-` on screen still failed the check — whatever was in
    front of it could not be seen in the field."""
    s = _NOT_IN_A_KEY.sub("", raw or "")
    s = s.strip("'\"")
    if s.startswith("ANTHROPIC_API_KEY="):
        s = s.split("=", 1)[1].strip("'\"")
    return s


def api_key_problem(key: str) -> str | None:
    """Why the key cannot be used, in words that never repeat the key."""
    if not key:
        return "missing"
    if "REPLACE" in key or "your-key" in key:
        return "placeholder"
    if not key.startswith("sk-ant-"):
        return "unexpected_prefix"
    return None


class Settings(BaseSettings):
    # utf-8-sig transparently strips a UTF-8 BOM if an editor (e.g. some Windows tools) adds one
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", extra="ignore")

    ANTHROPIC_API_KEY: str

    @field_validator("ANTHROPIC_API_KEY", mode="before")
    @classmethod
    def _clean_key(cls, v):
        return clean_api_key(v) if isinstance(v, str) else v

    TAVILY_API_KEY: str = ""
    # Privacy Guard (GDPR) — HMAC key for pseudonymisation. Fail-closed: empty
    # means the agent refuses to run rather than produce reversible-by-anyone
    # tokens. Must be >= 32 chars and unique per deployment; no default.
    GDPR_PSEUDONYM_KEY: str = ""
    APP_USERNAME: str = "iawingman"
    APP_PASSWORD: str = ""
    # Fail-closed by default: an empty APP_PASSWORD locks the app rather than
    # silently opening it. Set IA_WINGMAN_DEV_OPEN=1 to explicitly run without a
    # password (local dev only) — this is deliberately opt-in and loud.
    IA_WINGMAN_DEV_OPEN: bool = False
    # Show FastAPI's /docs + /openapi.json. NOTE: FastAPI mounts these itself, so
    # they are NOT covered by the global require_auth dependency — with this True
    # the full API surface (every route + schema) is readable without a password.
    # Fine for a local demo; set False for any exposed/hardened deployment. Known
    # residual risk, documented rather than silently relied upon as "auth-gated".
    EXPOSE_API_DOCS: bool = True


settings = Settings()
