"""Classify PII fields as Required, Optional, or Excessive per purpose."""

from gdpr_agent.models import FieldClassification, PIICategory, PIIField

# Purpose -> set of required PII categories
PURPOSE_REQUIRED_CATEGORIES: dict[str, dict[PIICategory, set[str]]] = {
    "reimbursement_review": {
        PIICategory.FINANCIAL: {"iban", "account_number", "bank"},
    },
    "compliance_check": {
        PIICategory.IDENTIFIER: {"employee_name", "employee_id"},
    },
    "breach_investigation": {
        PIICategory.CONTACT: {"email"},
    },
}

# Fields that are always excessive regardless of purpose
ALWAYS_EXCESSIVE_FIELDS: set[str] = {"ssn", "social_security", "passport"}


def classify_fields(
    fields: list[PIIField],
    purpose: str,
) -> list[PIIField]:
    """Classify each PII field as Required, Optional, or Excessive.

    Rules:
    1. Special category data is always Excessive unless purpose explicitly requires it
    2. Fields in ALWAYS_EXCESSIVE_FIELDS are always Excessive
    3. Fields matching the purpose's required categories are Required
    4. Everything else is Optional
    """
    required_map = PURPOSE_REQUIRED_CATEGORIES.get(purpose, {})
    classified: list[PIIField] = []

    for field in fields:
        updated = field.model_copy()

        if field.field_name.lower() in ALWAYS_EXCESSIVE_FIELDS:
            updated.classification = FieldClassification.EXCESSIVE
        elif field.category == PIICategory.SPECIAL:
            updated.classification = FieldClassification.EXCESSIVE
        elif field.category in required_map:
            required_fields = required_map[field.category]
            if field.field_name.lower() in required_fields:
                updated.classification = FieldClassification.REQUIRED
            else:
                updated.classification = FieldClassification.OPTIONAL
        else:
            updated.classification = FieldClassification.OPTIONAL

        classified.append(updated)

    return classified
