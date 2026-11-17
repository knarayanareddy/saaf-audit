"""Organization profile — the single source of truth for org identity.

IA Wingman is white-label: no organization name, entity, or brand is hardcoded
anywhere else in the codebase. Everything (frontend branding, entity metadata,
AI system-prompt context) derives from this profile. Swap the defaults below —
or override via env — to deploy IA Wingman for any internal-audit function.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class Entity:
    code: str
    label: str
    hex: str


@dataclass(frozen=True)
class OrganizationProfile:
    name: str
    short_name: str
    sector: str
    tagline: str
    brand_hex: str
    entities: list[Entity]
    audit_types: list[str] = field(default_factory=lambda: list(DEFAULT_AUDIT_TYPES))

    def entity_codes(self) -> list[str]:
        return [e.code for e in self.entities]

    def entity_label(self, code: str) -> str:
        for e in self.entities:
            if e.code == code:
                return e.label
        return code

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "short_name": self.short_name,
            "sector": self.sector,
            "tagline": self.tagline,
            "brand_hex": self.brand_hex,
            "entities": [asdict(e) for e in self.entities],
            "audit_types": self.audit_types,
        }


DEFAULT_AUDIT_TYPES = [
    "compliance", "operational", "it", "financial",
    "esg", "fraud", "conduct", "advisory", "validation",
]

# ── Default demo organization (fictional, privacy-safe) ────────────────────────
# Generic business units — not tied to any real institution. One-line configurable.
_DEFAULT = OrganizationProfile(
    name="Northwind Financial",
    short_name="Northwind",
    sector="financial services",
    tagline="Internal Audit",
    brand_hex="#1E6B4F",
    entities=[
        Entity("GRP", "Group", "#4F46E5"),
        Entity("RET", "Retail", "#0D9488"),
        Entity("BUS", "Business", "#D97706"),
        Entity("AM", "Asset Management", "#7C3AED"),
        Entity("INT", "International", "#DC2626"),
    ],
)


def _load() -> OrganizationProfile:
    """Optionally override the profile with a JSON blob in IA_ORG_PROFILE env var."""
    raw = os.environ.get("IA_ORG_PROFILE")
    if not raw:
        return _DEFAULT
    try:
        data = json.loads(raw)
        return OrganizationProfile(
            name=data["name"],
            short_name=data.get("short_name", data["name"]),
            sector=data.get("sector", "financial services"),
            tagline=data.get("tagline", "Internal Audit"),
            brand_hex=data.get("brand_hex", "#1E6B4F"),
            entities=[Entity(**e) for e in data["entities"]],
            audit_types=data.get("audit_types", list(DEFAULT_AUDIT_TYPES)),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return _DEFAULT


ORG = _load()


def org_system_context() -> str:
    """A compact org-context block injected into the AI system prompt.

    Keeps the assistant grounded in *this* organization without hardcoding it
    into every agent. Generic on purpose so IA Wingman works for any org.
    """
    ents = "\n".join(f"  {e.code} — {e.label}" for e in ORG.entities)
    return f"""ORGANISATION CONTEXT:
You support the Internal Audit (IA) function of {ORG.name}, an organisation in the
{ORG.sector} sector. Business units / auditable entities in scope:
{ents}
Treat this context as configurable — never assume facts about the organisation
that are not provided to you; ask or flag when entity-specific detail is missing."""
