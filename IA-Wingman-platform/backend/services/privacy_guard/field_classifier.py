"""Classify PII fields as Required, Optional, or Excessive per purpose."""

from .models import FieldClassification, PIICategory, PIIField

# Purpose -> required PII categories -> the field names that are Required for it.
# A field whose category is listed but whose name is not falls to Optional; a
# field whose category is not listed at all is Optional. Names are matched on
# the leaf (last path segment), lower-cased.
PURPOSE_REQUIRED_CATEGORIES: dict[str, dict[PIICategory, set[str]]] = {
    # IA Wingman CDD/AML onboarding audit: the auditor must be able to verify
    # that identity was established, so the customer name is Required; contact
    # details and the full IBAN are useful but not necessary for the audit
    # (Optional); national identifiers are Excessive (see ALWAYS_EXCESSIVE).
    "customer_due_diligence": {
        PIICategory.IDENTIFIER: {"customer_name", "employee_name", "name"},
    },
    "reimbursement_review": {
        PIICategory.FINANCIAL: {"iban", "account_number", "bank"},
    },
    "compliance_check": {
        PIICategory.IDENTIFIER: {"employee_name", "employee_id", "customer_name"},
    },
    "breach_investigation": {
        PIICategory.CONTACT: {"email"},
    },
    "data_access_request": {
        PIICategory.IDENTIFIER: {"customer_name", "employee_name", "name"},
        PIICategory.CONTACT: {"email", "phone"},
    },
}

# Fields that are always excessive regardless of purpose. National identifiers
# are collected at onboarding but are not needed to *audit* the control, so
# surfacing them here demonstrates the data-minimisation judgement.
ALWAYS_EXCESSIVE_FIELDS: set[str] = {
    "ssn", "social_security", "passport", "bsn", "national_id",
}


def _leaf(field_name: str) -> str:
    """Last segment of a dotted field path, lower-cased."""
    return field_name.split(".")[-1].lower()


def classify_fields(fields: list[PIIField], purpose: str) -> list[PIIField]:
    """Classify each PII field as Required, Optional, or Excessive.

    Rules:
    1. Fields in ALWAYS_EXCESSIVE_FIELDS are always Excessive
    2. Special category data is always Excessive
    3. Fields matching the purpose's required categories + names are Required
    4. Everything else is Optional
    """
    required_map = PURPOSE_REQUIRED_CATEGORIES.get(purpose, {})
    classified: list[PIIField] = []

    for field in fields:
        updated = field.model_copy()
        leaf = _leaf(field.field_name)

        if leaf in ALWAYS_EXCESSIVE_FIELDS:
            updated.classification = FieldClassification.EXCESSIVE
        elif field.category == PIICategory.SPECIAL:
            updated.classification = FieldClassification.EXCESSIVE
        elif field.category in required_map and leaf in required_map[field.category]:
            updated.classification = FieldClassification.REQUIRED
        else:
            updated.classification = FieldClassification.OPTIONAL

        classified.append(updated)

    return classified
