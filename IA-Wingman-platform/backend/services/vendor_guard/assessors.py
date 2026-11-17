"""Specialist framework assessors for Vendor Guard.

Each specialist embeds one or more curated framework texts in its system prompt
and makes a single AI call (via ai_service.run_agent_to_json) that judges the
vendor documents against those frameworks, returning gap-register findings.
Applicability is deterministic: security + resilience always run; ai_trust only
for AI vendors; gov_baseline only for Dutch-government vendors.
"""

from pathlib import Path

from services.ai_service import run_agent_to_json
from .models import Finding

FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"

# specialist key -> (label, framework files, applicability)
SPECIALISTS: dict[str, dict] = {
    "security": {
        "label": "Security (ISO 27001 / NIS2 / CBW)",
        "frameworks": ["iso27001_controls", "nis2_measures", "cbw_requirements"],
        "applies": "always",
    },
    "resilience": {
        "label": "Operational resilience (DORA)",
        "frameworks": ["dora_requirements"],
        "applies": "always",
    },
    "ai_trust": {
        "label": "AI trustworthiness (EU AI Act / ALTAI / EC Ethics)",
        "frameworks": ["ai_act_requirements", "altai_requirements", "ec_ethics_guidelines"],
        "applies": "ai",
    },
    "gov_baseline": {
        "label": "Government baseline (BIO2)",
        "frameworks": ["bio2_controls"],
        "applies": "gov",
    },
}


def _load_framework(name: str) -> str:
    path = FRAMEWORKS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def applicable_specialists(is_ai: bool, is_gov: bool) -> list[str]:
    """Deterministically choose which specialists apply to this vendor."""
    keys = []
    for key, spec in SPECIALISTS.items():
        applies = spec["applies"]
        if applies == "always" or (applies == "ai" and is_ai) or (applies == "gov" and is_gov):
            keys.append(key)
    return keys


def _system_prompt(specialist_key: str) -> str:
    spec = SPECIALISTS[specialist_key]
    framework_texts = "\n\n---\n\n".join(_load_framework(f) for f in spec["frameworks"])
    return (
        "You are a third-party (vendor) risk audit specialist. Assess the vendor documentation against "
        "the following regulatory frameworks.\n\n"
        f"{framework_texts}\n\n"
        "---\n\n"
        "## Instructions\n"
        "- Review the provided vendor documents carefully.\n"
        "- For each relevant control area, decide status: Compliant, Gap, Partial, or Not Applicable.\n"
        "- Only cite evidence explicitly present in the documents. Never invent or assume information.\n"
        "- If evidence is absent, mark it as a Gap and note 'No evidence provided.'\n"
        '- Return ONLY a JSON array of objects with this exact schema:\n'
        '  [{"framework": "ISO 27001", "control_id": "A.9.1", "control_name": "Access control policy", '
        '"status": "Gap", "severity": "High", "evidence": "...", "recommendation": "..."}]\n'
        "- No preamble, no explanation, no markdown fences."
    )


async def assess_specialist(specialist_key: str, vendor_docs_fenced: str) -> list[Finding]:
    """Run one specialist assessment. Returns normalised Findings (best-effort)."""
    result = await run_agent_to_json(
        system_prompt=_system_prompt(specialist_key),
        user_prompt=f"Please assess the following vendor documents:\n\n{vendor_docs_fenced}",
        max_tokens=8000,
    )
    if not isinstance(result, list):
        return []
    findings: list[Finding] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        try:
            findings.append(Finding(**item))
        except Exception:  # noqa: BLE001 — skip malformed rows rather than fail the run
            continue
    return findings
