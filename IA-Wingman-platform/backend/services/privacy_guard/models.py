"""Core data models for the Privacy Guard engine."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# Length of the SHA-256 hex digests used in the audit chain.
HASH_HEX_LENGTH = 64
GENESIS_HASH = "0" * HASH_HEX_LENGTH

# An admin runs with masking disabled, so the justification is the only
# remaining control. Require enough text to be meaningful in a review.
MIN_JUSTIFICATION_LENGTH = 10


class PIICategory(str, Enum):
    IDENTIFIER = "identifier"       # name, SSN, BSN, ID number
    FINANCIAL = "financial"         # IBAN, credit card
    CONTACT = "contact"             # email, phone, address
    SPECIAL = "special_category"    # health, religion, ethnicity


class Role(str, Enum):
    AUDITOR = "auditor"
    DPO = "dpo"
    ADMIN = "admin"


class MaskingLevel(str, Enum):
    FULL = "full"           # All PII masked
    PARTIAL = "partial"     # Some PII visible (e.g., last 4 digits)
    NONE = "none"           # No masking (admin, with recorded justification)


class FieldClassification(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    EXCESSIVE = "excessive"


class PIIField(BaseModel):
    """A detected PII field with classification metadata."""
    field_name: str
    value: str
    category: PIICategory
    confidence: float = Field(ge=0.0, le=1.0)
    classification: Optional[FieldClassification] = None
    legal_basis: Optional[str] = None
    # Every pattern that fired, not just the winning one. A value can be both
    # an identifier and contact data, and the audit trail should say so.
    matched_patterns: list[str] = Field(default_factory=list)
    # Location of the value inside the record. Flat records leave this empty
    # and fall back to field_name; nested ones carry the full key path.
    path: list[str] = Field(default_factory=list)


ROLE_MASKING_MAP: dict[Role, MaskingLevel] = {
    Role.AUDITOR: MaskingLevel.FULL,
    Role.DPO: MaskingLevel.PARTIAL,
    Role.ADMIN: MaskingLevel.NONE,
}

# Roles permitted to reverse a pseudonym back to the original value.
DEPSEUDONYMISATION_ROLES: frozenset[Role] = frozenset({Role.DPO, Role.ADMIN})


class AuditContext(BaseModel):
    """Context for a privacy request, determining masking behaviour."""
    role: Role
    purpose: str
    legal_basis: str
    justification: Optional[str] = None

    @model_validator(mode="after")
    def _require_justification_for_unmasked_access(self) -> "AuditContext":
        """Admins read raw PII, so the reason has to be stated and logged.

        Selecting the admin role disables masking entirely, so without a
        justification nothing would be recorded about why.
        """
        if ROLE_MASKING_MAP[self.role] == MaskingLevel.NONE:
            text = (self.justification or "").strip()
            if len(text) < MIN_JUSTIFICATION_LENGTH:
                raise ValueError(
                    f"role '{self.role.value}' receives unmasked data and requires a "
                    f"justification of at least {MIN_JUSTIFICATION_LENGTH} characters"
                )
        return self

    @property
    def masking_level(self) -> MaskingLevel:
        return ROLE_MASKING_MAP[self.role]


class MaskingResult(BaseModel):
    """Result of masking a single field."""
    field_name: str
    original_category: PIICategory
    masked_value: str
    masking_method: str  # "redacted", "pseudonymized", "partial", "none"
    reversible: bool = False


class AuditRecord(BaseModel):
    """A single audit log entry, linked to its predecessor by hash.

    `prev_hash` and `entry_hash` form an append-only chain: altering or
    removing any earlier entry invalidates every hash after it, which is what
    makes the trail tamper-evident rather than merely append-mode.
    """
    timestamp: str
    action: str
    role: Role
    purpose: str
    fields_detected: int
    fields_masked: int
    reasoning: str
    sequence: int = 0
    record_id: Optional[str] = None
    field_names: list[str] = Field(default_factory=list)
    justification: Optional[str] = None
    prev_hash: str = GENESIS_HASH
    entry_hash: str = ""
