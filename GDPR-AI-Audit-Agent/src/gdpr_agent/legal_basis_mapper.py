"""Map PII fields to GDPR legal bases based on processing purpose."""

from gdpr_agent.config import load_legal_bases
from gdpr_agent.models import PIICategory, PIIField

# Purposes that allow special category data processing (Art. 9(2) exemptions)
SPECIAL_CATEGORY_EXEMPTIONS: dict[str, str] = {
    "health_audit": "art_9_2_h",  # Health-related processing
}


def map_legal_basis(field: PIIField, purpose: str) -> PIIField:
    """Assign a legal basis to a PII field based on processing purpose.

    Special category data (Art. 9) gets no legal basis unless an explicit
    exemption exists for the purpose.
    """
    updated = field.model_copy()

    # Special category data requires explicit exemption
    if field.category == PIICategory.SPECIAL:
        updated.legal_basis = SPECIAL_CATEGORY_EXEMPTIONS.get(purpose)
        return updated

    # Load purpose-to-article mapping
    legal_bases = load_legal_bases()
    purpose_map = legal_bases.get("purpose_to_legal_basis", {})
    updated.legal_basis = purpose_map.get(purpose)

    return updated
