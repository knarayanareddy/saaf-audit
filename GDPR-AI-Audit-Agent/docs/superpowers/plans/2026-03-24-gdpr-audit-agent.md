# GDPR AI Audit Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based AI agent that detects, classifies, and masks PII in audit data while maintaining GDPR compliance and a verifiable audit trail.

**Architecture:** A 4-step pipeline (Request -> Detect PII -> Map Legal Basis -> Mask) orchestrated by a central agent. Each step is a standalone Python module with clear interfaces. The agent uses Claude API for NER-based PII detection and field classification, with regex fallback for structured patterns (emails, IBANs, SSNs). Role-based dynamic masking ensures auditors only see what their legal basis permits.

**Tech Stack:** Python 3.11+, pytest, Anthropic SDK (Claude API), pydantic (data models), python-dotenv, requests (Mattermost webhooks)

---

## File Structure

```
gdpr-audit-agent/
├── pyproject.toml                    # Project config, dependencies
├── .env.example                      # Template for API keys
├── .gitignore
├── src/
│   └── gdpr_agent/
│       ├── __init__.py
│       ├── models.py                 # Pydantic data models (PIIField, AuditRecord, MaskingResult)
│       ├── pii_detector.py           # NER + regex PII detection
│       ├── field_classifier.py       # Classify fields: Required / Optional / Excessive
│       ├── legal_basis_mapper.py     # Map fields to GDPR legal bases
│       ├── dynamic_masker.py         # Context-aware, role-based masking engine
│       ├── pseudonymizer.py          # Reversible tokenization for reproducibility
│       ├── audit_logger.py           # Immutable audit trail with chain-of-thought
│       ├── pipeline.py               # Orchestrates the 4-step pipeline
│       └── config.py                 # Configuration and role definitions
├── prompts/
│   ├── pii_detection_system.md       # System prompt for PII detection
│   ├── field_classification.md       # System prompt for field classification
│   ├── masking_decision.md           # System prompt for masking decisions
│   └── explainability_report.md      # System prompt for human-readable explanations
├── regulatory/
│   └── gdpr_legal_bases.json         # GDPR article -> legal basis mapping
├── tests/
│   ├── conftest.py                   # Shared fixtures (sample records, roles)
│   ├── test_models.py
│   ├── test_pii_detector.py
│   ├── test_field_classifier.py
│   ├── test_legal_basis_mapper.py
│   ├── test_dynamic_masker.py
│   ├── test_pseudonymizer.py
│   ├── test_audit_logger.py
│   ├── test_pipeline.py
│   └── test_e2e.py                   # End-to-end scenario test
└── data/
    └── sample_reimbursement.json     # Synthetic test data
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/gdpr_agent/__init__.py`
- Create: `tests/conftest.py`
- Create: `data/sample_reimbursement.json`

- [ ] **Step 1: Initialize git repository**

```bash
cd C:/Users/Rober/Documents/GDPR
git init
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "gdpr-audit-agent"
version = "0.1.0"
description = "GDPR-compliant AI Audit Agent for PII detection and masking"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40.0",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "requests>=2.31",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Create .env.example**

```
ANTHROPIC_API_KEY=your-key-here
MATTERMOST_WEBHOOK_URL=https://your-mattermost/hooks/xxx
```

- [ ] **Step 4: Create .gitignore**

```
__pycache__/
*.pyc
.env
.venv/
dist/
*.egg-info/
.pytest_cache/
outputs/
```

- [ ] **Step 5: Create src/gdpr_agent/__init__.py**

```python
"""GDPR AI Audit Agent - PII detection, classification, and masking."""
```

- [ ] **Step 6: Create synthetic test data**

Create `data/sample_reimbursement.json`:

```json
[
    {
        "id": "RMB-001",
        "employee_name": "Hans Mueller",
        "email": "hans.mueller@example.com",
        "iban": "DE89370400440532013000",
        "date": "2026-01-15",
        "amount": 245.50,
        "category": "Travel",
        "description": "Train ticket Berlin-Munich",
        "department": "Engineering",
        "ssn": "12 345678 A 123"
    },
    {
        "id": "RMB-002",
        "employee_name": "Maria Schmidt",
        "email": "maria.schmidt@example.com",
        "iban": "DE27100777770209299700",
        "date": "2026-02-03",
        "amount": 89.99,
        "category": "Office Supplies",
        "description": "Ergonomic keyboard",
        "department": "Marketing",
        "phone": "+49 170 1234567"
    }
]
```

- [ ] **Step 7: Install dependencies and verify**

```bash
cd C:/Users/Rober/Documents/GDPR
python -m venv .venv
source .venv/Scripts/activate
pip install -e ".[dev]"
```

Expected: `Successfully installed gdpr-audit-agent-0.1.0` (plus dependencies)

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .env.example .gitignore src/ data/
git commit -m "feat: scaffold GDPR audit agent project"
```

> **Note:** `tests/conftest.py` is created in Task 2 after `models.py` exists, since it imports from `gdpr_agent.models`.

---

### Task 2: Data Models

**Files:**
- Create: `src/gdpr_agent/models.py`
- Create: `tests/conftest.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
from gdpr_agent.models import (
    AuditContext,
    MaskingLevel,
    PIICategory,
    PIIField,
    Role,
)


def test_pii_field_creation():
    field = PIIField(
        field_name="email",
        value="hans@example.com",
        category=PIICategory.CONTACT,
        confidence=0.95,
    )
    assert field.field_name == "email"
    assert field.category == PIICategory.CONTACT
    assert field.confidence == 0.95


def test_audit_context_default_masking_level():
    ctx = AuditContext(
        role=Role.AUDITOR,
        purpose="review",
        legal_basis="legitimate_interest",
    )
    assert ctx.masking_level == MaskingLevel.FULL


def test_dpo_gets_partial_masking():
    ctx = AuditContext(
        role=Role.DPO,
        purpose="compliance",
        legal_basis="legal_obligation",
    )
    assert ctx.masking_level == MaskingLevel.PARTIAL


def test_admin_gets_no_masking():
    ctx = AuditContext(
        role=Role.ADMIN,
        purpose="system_admin",
        legal_basis="consent",
    )
    assert ctx.masking_level == MaskingLevel.NONE


def test_pii_category_values():
    assert PIICategory.IDENTIFIER.value == "identifier"
    assert PIICategory.FINANCIAL.value == "financial"
    assert PIICategory.CONTACT.value == "contact"
    assert PIICategory.SPECIAL.value == "special_category"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gdpr_agent.models'`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/models.py`:

```python
"""Core data models for the GDPR Audit Agent."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PIICategory(str, Enum):
    IDENTIFIER = "identifier"       # name, SSN, ID number
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
    NONE = "none"           # No masking (admin with justification)


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


ROLE_MASKING_MAP: dict[Role, MaskingLevel] = {
    Role.AUDITOR: MaskingLevel.FULL,
    Role.DPO: MaskingLevel.PARTIAL,
    Role.ADMIN: MaskingLevel.NONE,
}


class AuditContext(BaseModel):
    """Context for an audit request, determining masking behavior."""
    role: Role
    purpose: str
    legal_basis: str

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
    """A single audit log entry."""
    timestamp: str
    action: str
    role: Role
    purpose: str
    fields_detected: int
    fields_masked: int
    reasoning: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Create tests/conftest.py with shared fixtures**

Now that models.py exists, create the shared test fixtures.

```python
import json
from pathlib import Path

import pytest

from gdpr_agent.models import AuditContext, Role


@pytest.fixture
def sample_records():
    data_path = Path(__file__).parent.parent / "data" / "sample_reimbursement.json"
    with open(data_path) as f:
        return json.load(f)


@pytest.fixture
def auditor_context():
    return AuditContext(
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        legal_basis="legitimate_interest",
    )


@pytest.fixture
def dpo_context():
    return AuditContext(
        role=Role.DPO,
        purpose="compliance_check",
        legal_basis="legal_obligation",
    )
```

- [ ] **Step 6: Commit**

```bash
git add src/gdpr_agent/models.py tests/test_models.py tests/conftest.py
git commit -m "feat: add core data models (PIIField, AuditContext, Role, MaskingLevel)"
```

---

### Task 3: Configuration

**Files:**
- Create: `src/gdpr_agent/config.py`
- Create: `regulatory/gdpr_legal_bases.json`

- [ ] **Step 1: Create config module**

Create `src/gdpr_agent/config.py`:

```python
"""Configuration for the GDPR Audit Agent."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent
REGULATORY_DIR = PROJECT_ROOT / "regulatory"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "")

# PII detection patterns (regex)
PII_PATTERNS: dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "iban": r"[A-Z]{2}\d{2}[A-Z0-9]{4,30}",
    "phone": r"\+?\d[\d\s\-]{7,15}",
    "ssn": r"\d{2}\s?\d{6}\s?[A-Z]\s?\d{3}",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}

# Fields that are never PII
SAFE_FIELDS: set[str] = {
    "id", "date", "amount", "category", "department", "currency",
}


def load_legal_bases() -> dict:
    path = REGULATORY_DIR / "gdpr_legal_bases.json"
    with open(path) as f:
        return json.load(f)
```

- [ ] **Step 2: Create regulatory mapping**

Create `regulatory/gdpr_legal_bases.json`:

```json
{
    "articles": {
        "art_5_1_c": {
            "title": "Data Minimization",
            "description": "Personal data shall be adequate, relevant and limited to what is necessary.",
            "applies_to": ["all_processing"]
        },
        "art_6_1_f": {
            "title": "Legitimate Interest",
            "description": "Processing is necessary for legitimate interests pursued by the controller.",
            "applies_to": ["audit_review", "compliance_check"]
        },
        "art_15": {
            "title": "Right of Access",
            "description": "The data subject shall have the right to obtain confirmation of processing.",
            "applies_to": ["data_access_request"]
        },
        "art_17": {
            "title": "Right to Erasure",
            "description": "The data subject shall have the right to obtain erasure.",
            "applies_to": ["deletion_request"]
        },
        "art_22": {
            "title": "Automated Decision-Making",
            "description": "The data subject shall have the right not to be subject to automated decisions.",
            "applies_to": ["automated_processing"]
        },
        "art_28": {
            "title": "Processor Obligations",
            "description": "Processing by a processor shall be governed by a contract.",
            "applies_to": ["third_party_sharing"]
        },
        "art_32": {
            "title": "Security of Processing",
            "description": "Implement appropriate technical and organisational measures.",
            "applies_to": ["access_control", "encryption"]
        },
        "art_33": {
            "title": "Breach Notification to Authority",
            "description": "Notify the supervisory authority within 72 hours.",
            "applies_to": ["breach_investigation"]
        },
        "art_5_1_e": {
            "title": "Data Retention",
            "description": "Personal data shall be kept for no longer than is necessary for the purposes.",
            "applies_to": ["retention_review"]
        },
        "chapter_v": {
            "title": "Cross-Border Transfers",
            "description": "Transfers of personal data to third countries require appropriate safeguards.",
            "applies_to": ["cross_border_audit"]
        }
    },
    "purpose_to_legal_basis": {
        "reimbursement_review": "art_6_1_f",
        "compliance_check": "art_6_1_f",
        "breach_investigation": "art_33",
        "deletion_verification": "art_17",
        "data_access_request": "art_15",
        "third_party_audit": "art_28",
        "retention_review": "art_5_1_e",
        "cross_border_audit": "chapter_v"
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add src/gdpr_agent/config.py regulatory/
git commit -m "feat: add config module and GDPR legal basis mappings"
```

---

### Task 4: PII Detector

**Files:**
- Create: `src/gdpr_agent/pii_detector.py`
- Create: `tests/test_pii_detector.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pii_detector.py`:

```python
import pytest

from gdpr_agent.models import PIICategory
from gdpr_agent.pii_detector import detect_pii_in_record


def test_detects_email():
    record = {"email": "hans@example.com", "id": "RMB-001"}
    fields = detect_pii_in_record(record)
    emails = [f for f in fields if f.field_name == "email"]
    assert len(emails) == 1
    assert emails[0].category == PIICategory.CONTACT
    assert emails[0].confidence >= 0.9


def test_detects_iban():
    record = {"iban": "DE89370400440532013000"}
    fields = detect_pii_in_record(record)
    ibans = [f for f in fields if f.field_name == "iban"]
    assert len(ibans) == 1
    assert ibans[0].category == PIICategory.FINANCIAL


def test_detects_name():
    record = {"employee_name": "Hans Mueller"}
    fields = detect_pii_in_record(record)
    names = [f for f in fields if f.field_name == "employee_name"]
    assert len(names) == 1
    assert names[0].category == PIICategory.IDENTIFIER


def test_ignores_safe_fields():
    record = {"id": "RMB-001", "amount": 245.50, "category": "Travel"}
    fields = detect_pii_in_record(record)
    assert len(fields) == 0


def test_detects_phone():
    record = {"phone": "+49 170 1234567"}
    fields = detect_pii_in_record(record)
    phones = [f for f in fields if f.field_name == "phone"]
    assert len(phones) == 1
    assert phones[0].category == PIICategory.CONTACT


def test_detects_multiple_pii_fields(sample_records):
    fields = detect_pii_in_record(sample_records[0])
    field_names = {f.field_name for f in fields}
    assert "employee_name" in field_names
    assert "email" in field_names
    assert "iban" in field_names
    assert "id" not in field_names
    assert "amount" not in field_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pii_detector.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/pii_detector.py`:

```python
"""PII detection using regex pattern matching and heuristics."""

import re
from typing import Any

from gdpr_agent.config import PII_PATTERNS, SAFE_FIELDS
from gdpr_agent.models import PIICategory, PIIField

# Map pattern names to PII categories
PATTERN_CATEGORY_MAP: dict[str, PIICategory] = {
    "email": PIICategory.CONTACT,
    "iban": PIICategory.FINANCIAL,
    "phone": PIICategory.CONTACT,
    "ssn": PIICategory.IDENTIFIER,
    "ip_address": PIICategory.IDENTIFIER,
}

# Keywords in field names that suggest PII
NAME_KEYWORDS: set[str] = {"name", "first_name", "last_name", "employee_name", "full_name"}
ADDRESS_KEYWORDS: set[str] = {"address", "street", "city", "zip", "postal"}


def _classify_by_pattern(value: str) -> tuple[PIICategory, str, float] | None:
    """Try to match a value against known PII patterns."""
    str_value = str(value)
    for pattern_name, pattern in PII_PATTERNS.items():
        if re.search(pattern, str_value):
            category = PATTERN_CATEGORY_MAP[pattern_name]
            return category, pattern_name, 0.95
    return None


def _classify_by_field_name(field_name: str) -> tuple[PIICategory, float] | None:
    """Classify PII based on the field name itself."""
    lower = field_name.lower()
    if any(kw in lower for kw in NAME_KEYWORDS):
        return PIICategory.IDENTIFIER, 0.9
    if any(kw in lower for kw in ADDRESS_KEYWORDS):
        return PIICategory.CONTACT, 0.85
    return None


def detect_pii_in_record(record: dict[str, Any]) -> list[PIIField]:
    """Detect PII fields in a single data record.

    Uses a two-pass approach:
    1. Regex pattern matching on values (high confidence)
    2. Field name heuristics (medium confidence)
    """
    detected: list[PIIField] = []

    for field_name, value in record.items():
        if field_name.lower() in SAFE_FIELDS:
            continue

        str_value = str(value)

        # Pass 1: Pattern matching
        pattern_match = _classify_by_pattern(str_value)
        if pattern_match:
            category, _, confidence = pattern_match
            detected.append(PIIField(
                field_name=field_name,
                value=str_value,
                category=category,
                confidence=confidence,
            ))
            continue

        # Pass 2: Field name heuristics
        name_match = _classify_by_field_name(field_name)
        if name_match:
            category, confidence = name_match
            detected.append(PIIField(
                field_name=field_name,
                value=str_value,
                category=category,
                confidence=confidence,
            ))

    return detected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pii_detector.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/gdpr_agent/pii_detector.py tests/test_pii_detector.py
git commit -m "feat: add PII detector with regex and field-name heuristics"
```

---

### Task 5: Field Classifier

**Files:**
- Create: `src/gdpr_agent/field_classifier.py`
- Create: `tests/test_field_classifier.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_field_classifier.py`:

```python
from gdpr_agent.field_classifier import classify_fields
from gdpr_agent.models import FieldClassification, PIICategory, PIIField


def test_financial_field_required_for_reimbursement():
    fields = [
        PIIField(field_name="amount", value="245.50", category=PIICategory.FINANCIAL, confidence=0.9),
        PIIField(field_name="iban", value="DE89...", category=PIICategory.FINANCIAL, confidence=0.95),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    iban_field = next(f for f in result if f.field_name == "iban")
    assert iban_field.classification == FieldClassification.REQUIRED


def test_name_optional_for_reimbursement():
    fields = [
        PIIField(field_name="employee_name", value="Hans", category=PIICategory.IDENTIFIER, confidence=0.9),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    assert result[0].classification == FieldClassification.OPTIONAL


def test_ssn_excessive_for_reimbursement():
    fields = [
        PIIField(field_name="ssn", value="12 345678 A 123", category=PIICategory.IDENTIFIER, confidence=0.95),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    assert result[0].classification == FieldClassification.EXCESSIVE


def test_special_category_always_excessive_unless_justified():
    fields = [
        PIIField(field_name="health_condition", value="diabetes", category=PIICategory.SPECIAL, confidence=0.9),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    assert result[0].classification == FieldClassification.EXCESSIVE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_field_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/field_classifier.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_field_classifier.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/gdpr_agent/field_classifier.py tests/test_field_classifier.py
git commit -m "feat: add field classifier (Required/Optional/Excessive)"
```

---

### Task 6: Dynamic Masker

**Files:**
- Create: `src/gdpr_agent/dynamic_masker.py`
- Create: `tests/test_dynamic_masker.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dynamic_masker.py`:

```python
from gdpr_agent.dynamic_masker import mask_value
from gdpr_agent.models import MaskingLevel, MaskingResult, PIICategory


def test_full_mask_email():
    result = mask_value("hans.mueller@example.com", "email", PIICategory.CONTACT, MaskingLevel.FULL)
    assert result.masked_value == "h***@***.com"
    assert result.masking_method == "redacted"
    assert "hans" not in result.masked_value


def test_partial_mask_email():
    result = mask_value("hans.mueller@example.com", "email", PIICategory.CONTACT, MaskingLevel.PARTIAL)
    assert "@" in result.masked_value
    assert result.masked_value != "hans.mueller@example.com"
    assert result.masking_method == "partial"


def test_no_mask():
    result = mask_value("hans.mueller@example.com", "email", PIICategory.CONTACT, MaskingLevel.NONE)
    assert result.masked_value == "hans.mueller@example.com"
    assert result.masking_method == "none"


def test_full_mask_iban():
    result = mask_value("DE89370400440532013000", "iban", PIICategory.FINANCIAL, MaskingLevel.FULL)
    assert result.masked_value.startswith("DE")
    assert "****" in result.masked_value
    assert result.masking_method == "redacted"


def test_full_mask_name():
    result = mask_value("Hans Mueller", "employee_name", PIICategory.IDENTIFIER, MaskingLevel.FULL)
    assert result.masked_value == "[REDACTED]"
    assert result.masking_method == "redacted"


def test_partial_mask_name():
    result = mask_value("Hans Mueller", "employee_name", PIICategory.IDENTIFIER, MaskingLevel.PARTIAL)
    assert result.masked_value == "H*** M***"
    assert result.masking_method == "partial"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dynamic_masker.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/dynamic_masker.py`:

```python
"""Context-aware, role-based dynamic masking engine."""

import re

from gdpr_agent.models import MaskingLevel, MaskingResult, PIICategory


def _mask_email_full(value: str) -> str:
    """hans.mueller@example.com -> h***@***.com"""
    match = re.match(r"(.)[^@]*@[^.]*\.(.*)", value)
    if match:
        return f"{match.group(1)}***@***.{match.group(2)}"
    return "[REDACTED]"


def _mask_email_partial(value: str) -> str:
    """hans.mueller@example.com -> h***.m***@example.com"""
    parts = value.split("@")
    if len(parts) == 2:
        local = parts[0]
        return f"{local[0]}***@{parts[1]}"
    return value


def _mask_iban_full(value: str) -> str:
    """DE89370400440532013000 -> DE**************3000"""
    if len(value) >= 6:
        return value[:2] + "****" + "****" + "****" + value[-4:]
    return "[REDACTED]"


def _mask_iban_partial(value: str) -> str:
    """DE89370400440532013000 -> DE89**********3000"""
    if len(value) >= 8:
        return value[:4] + "****" + "****" + value[-4:]
    return value


def _mask_name_full(value: str) -> str:
    return "[REDACTED]"


def _mask_name_partial(value: str) -> str:
    """Hans Mueller -> H*** M***"""
    words = value.split()
    return " ".join(f"{w[0]}***" if len(w) > 1 else w for w in words)


def _mask_generic_full(value: str) -> str:
    return "[REDACTED]"


def _mask_generic_partial(value: str) -> str:
    if len(value) > 4:
        return value[:2] + "***" + value[-1:]
    return "***"


def mask_value(
    value: str,
    field_name: str,
    category: PIICategory,
    masking_level: MaskingLevel,
) -> MaskingResult:
    """Mask a single PII value based on its category and the required masking level."""
    if masking_level == MaskingLevel.NONE:
        return MaskingResult(
            field_name=field_name,
            original_category=category,
            masked_value=value,
            masking_method="none",
        )

    is_full = masking_level == MaskingLevel.FULL
    method = "redacted" if is_full else "partial"

    # Category-specific masking
    if category == PIICategory.CONTACT:
        if "@" in value:
            masked = _mask_email_full(value) if is_full else _mask_email_partial(value)
        else:
            masked = _mask_generic_full(value) if is_full else _mask_generic_partial(value)
    elif category == PIICategory.FINANCIAL:
        masked = _mask_iban_full(value) if is_full else _mask_iban_partial(value)
    elif category == PIICategory.IDENTIFIER:
        masked = _mask_name_full(value) if is_full else _mask_name_partial(value)
    elif category == PIICategory.SPECIAL:
        # Special category always fully redacted
        masked = "[REDACTED]"
        method = "redacted"
    else:
        masked = _mask_generic_full(value) if is_full else _mask_generic_partial(value)

    return MaskingResult(
        field_name=field_name,
        original_category=category,
        masked_value=masked,
        masking_method=method,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dynamic_masker.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/gdpr_agent/dynamic_masker.py tests/test_dynamic_masker.py
git commit -m "feat: add dynamic masker with role-based masking levels"
```

---

### Task 7: Pseudonymizer

**Files:**
- Create: `src/gdpr_agent/pseudonymizer.py`
- Create: `tests/test_pseudonymizer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pseudonymizer.py`:

```python
from gdpr_agent.pseudonymizer import Pseudonymizer


def test_pseudonymize_returns_token():
    ps = Pseudonymizer(secret_key="test-key-123")
    token = ps.pseudonymize("Hans Mueller")
    assert token != "Hans Mueller"
    assert token.startswith("PSE-")


def test_pseudonymize_is_deterministic():
    ps = Pseudonymizer(secret_key="test-key-123")
    token1 = ps.pseudonymize("Hans Mueller")
    token2 = ps.pseudonymize("Hans Mueller")
    assert token1 == token2


def test_pseudonymize_different_values_different_tokens():
    ps = Pseudonymizer(secret_key="test-key-123")
    token1 = ps.pseudonymize("Hans Mueller")
    token2 = ps.pseudonymize("Maria Schmidt")
    assert token1 != token2


def test_depseudonymize_reverses():
    ps = Pseudonymizer(secret_key="test-key-123")
    token = ps.pseudonymize("Hans Mueller")
    original = ps.depseudonymize(token)
    assert original == "Hans Mueller"


def test_depseudonymize_unknown_token_returns_none():
    ps = Pseudonymizer(secret_key="test-key-123")
    result = ps.depseudonymize("PSE-unknown")
    assert result is None


def test_different_keys_different_tokens():
    ps1 = Pseudonymizer(secret_key="key-1")
    ps2 = Pseudonymizer(secret_key="key-2")
    token1 = ps1.pseudonymize("Hans Mueller")
    token2 = ps2.pseudonymize("Hans Mueller")
    assert token1 != token2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pseudonymizer.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/pseudonymizer.py`:

```python
"""Reversible pseudonymization using HMAC-based tokenization."""

import hashlib
import hmac


class Pseudonymizer:
    """Reversible tokenization for reproducibility.

    Uses HMAC to generate deterministic pseudonyms.
    Maintains a reverse lookup table for depseudonymization.
    """

    def __init__(self, secret_key: str):
        self._key = secret_key.encode()
        self._reverse_map: dict[str, str] = {}

    def pseudonymize(self, value: str) -> str:
        """Replace a value with a deterministic pseudonym."""
        token_hash = hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()[:12]
        token = f"PSE-{token_hash}"
        self._reverse_map[token] = value
        return token

    def depseudonymize(self, token: str) -> str | None:
        """Reverse a pseudonym back to the original value.

        Only works if the pseudonym was created in this session.
        """
        return self._reverse_map.get(token)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pseudonymizer.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/gdpr_agent/pseudonymizer.py tests/test_pseudonymizer.py
git commit -m "feat: add reversible pseudonymizer with HMAC tokenization"
```

---

### Task 8: Audit Logger

**Files:**
- Create: `src/gdpr_agent/audit_logger.py`
- Create: `tests/test_audit_logger.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audit_logger.py`:

```python
import json

from gdpr_agent.audit_logger import AuditLogger
from gdpr_agent.models import Role


def test_log_creates_entry(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    logger.log(
        action="pii_detection",
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        fields_detected=5,
        fields_masked=4,
        reasoning="Detected 5 PII fields, masked 4 per auditor role policy.",
    )
    logs = logger.get_entries()
    assert len(logs) == 1
    assert logs[0].action == "pii_detection"
    assert logs[0].fields_detected == 5


def test_log_persists_to_file(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    logger.log(
        action="masking",
        role=Role.DPO,
        purpose="compliance_check",
        fields_detected=3,
        fields_masked=2,
        reasoning="DPO role: partial masking applied.",
    )
    log_files = list(tmp_path.glob("audit_*.jsonl"))
    assert len(log_files) == 1
    with open(log_files[0]) as f:
        line = f.readline()
        entry = json.loads(line)
        assert entry["action"] == "masking"
        assert entry["role"] == "dpo"


def test_multiple_entries(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    for i in range(3):
        logger.log(
            action=f"step_{i}",
            role=Role.AUDITOR,
            purpose="review",
            fields_detected=i,
            fields_masked=i,
            reasoning=f"Step {i}",
        )
    assert len(logger.get_entries()) == 3


def test_log_contains_no_pii(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    logger.log(
        action="detection",
        role=Role.AUDITOR,
        purpose="review",
        fields_detected=1,
        fields_masked=1,
        reasoning="Masked email field.",
    )
    log_files = list(tmp_path.glob("audit_*.jsonl"))
    content = log_files[0].read_text()
    assert "hans" not in content.lower()
    assert "@" not in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_audit_logger.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/audit_logger.py`:

```python
"""Immutable audit trail with chain-of-thought logging."""

import json
from datetime import datetime, timezone
from pathlib import Path

from gdpr_agent.models import AuditRecord, Role


class AuditLogger:
    """Append-only audit logger that persists to JSONL files."""

    def __init__(self, log_dir: Path):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._entries: list[AuditRecord] = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._log_file = self._log_dir / f"audit_{timestamp}.jsonl"

    def log(
        self,
        action: str,
        role: Role,
        purpose: str,
        fields_detected: int,
        fields_masked: int,
        reasoning: str,
    ) -> AuditRecord:
        """Create and persist an audit log entry."""
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            role=role,
            purpose=purpose,
            fields_detected=fields_detected,
            fields_masked=fields_masked,
            reasoning=reasoning,
        )
        self._entries.append(record)

        with open(self._log_file, "a") as f:
            f.write(record.model_dump_json() + "\n")

        return record

    def get_entries(self) -> list[AuditRecord]:
        """Return all entries from the current session."""
        return list(self._entries)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_audit_logger.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/gdpr_agent/audit_logger.py tests/test_audit_logger.py
git commit -m "feat: add append-only audit logger with JSONL persistence"
```

---

### Task 9: Prompt Templates

**Files:**
- Create: `prompts/pii_detection_system.md`
- Create: `prompts/field_classification.md`
- Create: `prompts/masking_decision.md`
- Create: `prompts/explainability_report.md`

- [ ] **Step 1: Create PII detection system prompt**

Create `prompts/pii_detection_system.md`:

```markdown
# PII Detection System Prompt

You are a GDPR-compliant PII detection agent. Your task is to analyze data records and identify all fields containing personal data.

## Categories

- **Identifier**: Names, SSN, ID numbers, passport numbers
- **Financial**: IBAN, credit card numbers, bank account details
- **Contact**: Email, phone, physical address, IP address
- **Special Category**: Health data, religious beliefs, political opinions, ethnic origin, biometric data

## Rules

1. Err on the side of caution — if uncertain, flag as PII
2. Consider indirect identifiers (e.g., "department" + "job title" could identify someone)
3. Return structured JSON with field name, category, and confidence score (0.0-1.0)
4. Never include the actual PII values in your reasoning output

## Output Format

```json
{
    "fields": [
        {"field_name": "...", "category": "identifier|financial|contact|special_category", "confidence": 0.95}
    ]
}
```
```

- [ ] **Step 2: Create field classification prompt**

Create `prompts/field_classification.md`:

```markdown
# Field Classification Prompt

Given a set of detected PII fields and an audit purpose, classify each field as:

- **Required**: Necessary for the stated audit purpose
- **Optional**: Useful but not essential — can be masked without impacting the audit
- **Excessive**: Not relevant to the purpose — must be masked or removed (Art. 5(1)(c) data minimization)

## Rules

1. Apply the principle of data minimization (Art. 5(1)(c))
2. Special category data (Art. 9) is always Excessive unless a specific exemption applies
3. Financial identifiers are Required only for financial audits
4. Names are typically Optional — use pseudonyms where possible

## Output Format

```json
{
    "classifications": [
        {"field_name": "...", "classification": "required|optional|excessive", "justification": "..."}
    ]
}
```
```

- [ ] **Step 3: Create masking decision prompt**

Create `prompts/masking_decision.md`:

```markdown
# Masking Decision Prompt

Determine the appropriate masking method for each PII field based on:

1. **Role** of the requester (Auditor, DPO, Admin)
2. **Legal basis** for processing
3. **Field classification** (Required, Optional, Excessive)

## Masking Rules

| Role | Required Fields | Optional Fields | Excessive Fields |
|------|----------------|-----------------|------------------|
| Auditor | Pseudonymize | Fully mask | Fully mask |
| DPO | Partially mask | Partially mask | Fully mask |
| Admin | Show (with justification) | Partially mask | Fully mask |

## Output Format

```json
{
    "decisions": [
        {"field_name": "...", "method": "redact|pseudonymize|partial|none", "justification": "..."}
    ]
}
```
```

- [ ] **Step 4: Create explainability report prompt**

Create `prompts/explainability_report.md`:

```markdown
# Explainability Report Prompt

Generate a human-readable report explaining the AI's masking decisions for auditor review.

## Report Structure

1. **Summary**: Number of fields detected, masked, and their categories
2. **Per-field decisions**: For each PII field, explain why it was masked and how
3. **Legal basis**: Which GDPR articles justify the processing
4. **Compliance status**: Whether the output meets data minimization requirements

## Rules

- Never include raw PII values in the report
- Reference GDPR articles by number
- Use clear, non-technical language where possible
- Flag any fields where the AI's confidence was below 0.8
```

- [ ] **Step 5: Commit**

```bash
git add prompts/
git commit -m "feat: add system prompt templates for PII detection, classification, masking, and explainability"
```

---

### Task 10: Legal Basis Mapper

**Files:**
- Create: `src/gdpr_agent/legal_basis_mapper.py`
- Create: `tests/test_legal_basis_mapper.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_legal_basis_mapper.py`:

```python
from gdpr_agent.legal_basis_mapper import map_legal_basis
from gdpr_agent.models import PIICategory, PIIField


def test_maps_reimbursement_to_legitimate_interest():
    field = PIIField(field_name="iban", value="DE89...", category=PIICategory.FINANCIAL, confidence=0.95)
    result = map_legal_basis(field, purpose="reimbursement_review")
    assert result.legal_basis == "art_6_1_f"


def test_maps_breach_investigation():
    field = PIIField(field_name="email", value="a@b.com", category=PIICategory.CONTACT, confidence=0.9)
    result = map_legal_basis(field, purpose="breach_investigation")
    assert result.legal_basis == "art_33"


def test_unknown_purpose_defaults_to_no_basis():
    field = PIIField(field_name="email", value="a@b.com", category=PIICategory.CONTACT, confidence=0.9)
    result = map_legal_basis(field, purpose="unknown_purpose")
    assert result.legal_basis is None


def test_special_category_requires_explicit_basis():
    field = PIIField(field_name="health", value="diabetes", category=PIICategory.SPECIAL, confidence=0.9)
    result = map_legal_basis(field, purpose="reimbursement_review")
    assert result.legal_basis is None  # No basis for special data in reimbursement
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_legal_basis_mapper.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/legal_basis_mapper.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_legal_basis_mapper.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/gdpr_agent/legal_basis_mapper.py tests/test_legal_basis_mapper.py
git commit -m "feat: add legal basis mapper with GDPR article resolution"
```

---

### Task 11: Pipeline Orchestrator

**Files:**
- Create: `src/gdpr_agent/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pipeline.py`:

```python
from pathlib import Path

from gdpr_agent.models import AuditContext, MaskingLevel, Role
from gdpr_agent.pipeline import AuditPipeline


def test_pipeline_masks_all_pii_for_auditor(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    assert len(results) == len(sample_records)
    for record in results:
        # No raw emails should survive
        for value in record.values():
            assert "@example.com" not in str(value)


def test_pipeline_preserves_safe_fields(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    assert results[0]["id"] == "RMB-001"
    assert results[0]["amount"] == 245.50
    assert results[0]["category"] == "Travel"


def test_pipeline_dpo_sees_partial_masking(sample_records, tmp_path):
    ctx = AuditContext(role=Role.DPO, purpose="compliance_check", legal_basis="legal_obligation")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    # DPO should see partial info (not fully redacted)
    email_val = str(results[0].get("email", ""))
    assert email_val != "hans.mueller@example.com"  # Not raw
    assert email_val != "[REDACTED]"  # Not fully masked


def test_pipeline_creates_audit_log(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    pipeline.process_records(sample_records)

    entries = pipeline.get_audit_log()
    assert len(entries) > 0


def test_pipeline_generates_summary(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    pipeline.process_records(sample_records)

    summary = pipeline.get_summary()
    assert "records_processed" in summary
    assert "total_pii_fields" in summary
    assert "total_masked" in summary
    assert summary["records_processed"] == 2


def test_pipeline_pseudonymizes_required_fields(sample_records, tmp_path):
    """Required PII fields should be pseudonymized (reversible) for auditors."""
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    # IBAN is Required for reimbursement_review — should be pseudonymized
    iban_val = results[0].get("iban", "")
    assert iban_val.startswith("PSE-"), "Required fields should be pseudonymized"
    assert iban_val != "DE89370400440532013000"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/gdpr_agent/pipeline.py`:

```python
"""Orchestrates the 4-step GDPR audit pipeline."""

from pathlib import Path
from typing import Any

from gdpr_agent.audit_logger import AuditLogger
from gdpr_agent.dynamic_masker import mask_value
from gdpr_agent.field_classifier import classify_fields
from gdpr_agent.legal_basis_mapper import map_legal_basis
from gdpr_agent.models import (
    AuditContext, AuditRecord, FieldClassification, MaskingLevel,
)
from gdpr_agent.pii_detector import detect_pii_in_record
from gdpr_agent.pseudonymizer import Pseudonymizer


class AuditPipeline:
    """4-step pipeline: Detect -> Classify -> Map Legal Basis -> Mask."""

    def __init__(self, audit_context: AuditContext, log_dir: Path, pseudonym_key: str = "default-key"):
        self._ctx = audit_context
        self._logger = AuditLogger(log_dir=log_dir)
        self._pseudonymizer = Pseudonymizer(secret_key=pseudonym_key)
        self._total_detected = 0
        self._total_masked = 0
        self._records_processed = 0

    def process_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Process a single record through the full pipeline."""
        # Step 1: Detect PII
        pii_fields = detect_pii_in_record(record)

        # Step 2: Classify fields
        classified = classify_fields(pii_fields, purpose=self._ctx.purpose)

        # Step 3: Map legal basis
        with_basis = [map_legal_basis(f, purpose=self._ctx.purpose) for f in classified]

        # Step 4: Apply masking (or pseudonymization for Required fields)
        masked_record = dict(record)  # Copy original
        fields_masked = 0

        for field in with_basis:
            # Excessive fields always fully masked regardless of role
            if field.classification == FieldClassification.EXCESSIVE:
                result = mask_value(
                    field.value, field.field_name, field.category, MaskingLevel.FULL
                )
            elif field.classification == FieldClassification.REQUIRED and self._ctx.masking_level != MaskingLevel.NONE:
                # Required fields get pseudonymized (reversible) instead of masked
                masked_record[field.field_name] = self._pseudonymizer.pseudonymize(field.value)
                fields_masked += 1
                continue
            else:
                result = mask_value(
                    field.value, field.field_name, field.category, self._ctx.masking_level
                )

            masked_record[field.field_name] = result.masked_value
            if result.masking_method != "none":
                fields_masked += 1

        # Log the action
        self._total_detected += len(pii_fields)
        self._total_masked += fields_masked
        self._records_processed += 1

        self._logger.log(
            action="process_record",
            role=self._ctx.role,
            purpose=self._ctx.purpose,
            fields_detected=len(pii_fields),
            fields_masked=fields_masked,
            reasoning=f"Detected {len(pii_fields)} PII fields, masked {fields_masked} "
                      f"per {self._ctx.role.value} role policy.",
        )

        return masked_record

    def process_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process multiple records through the pipeline."""
        return [self.process_record(r) for r in records]

    def get_audit_log(self) -> list[AuditRecord]:
        """Return all audit log entries."""
        return self._logger.get_entries()

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of the pipeline run."""
        return {
            "records_processed": self._records_processed,
            "total_pii_fields": self._total_detected,
            "total_masked": self._total_masked,
            "role": self._ctx.role.value,
            "purpose": self._ctx.purpose,
            "masking_level": self._ctx.masking_level.value,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/gdpr_agent/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator for 4-step GDPR audit flow"
```

---

### Task 12: End-to-End Test

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Write the end-to-end test**

Create `tests/test_e2e.py`:

```python
"""End-to-end test: auditor requests a customer reimbursement dataset."""

import json
from pathlib import Path

from gdpr_agent.models import AuditContext, Role
from gdpr_agent.pipeline import AuditPipeline


def test_e2e_reimbursement_audit(sample_records, tmp_path):
    """Scenario: Auditor requests a customer reimbursement dataset.

    Input: Full dataset with names, emails, IBANs
    Expected: No raw PII exposed, masking consistent, logs complete
    """
    ctx = AuditContext(
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        legal_basis="legitimate_interest",
    )
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)

    # Process
    masked_records = pipeline.process_records(sample_records)

    # Validation 1: No raw PII exposed
    raw_pii_values = {
        "Hans Mueller", "Maria Schmidt",
        "hans.mueller@example.com", "maria.schmidt@example.com",
        "DE89370400440532013000", "DE27100777770209299700",
        "+49 170 1234567", "12 345678 A 123",
    }
    for record in masked_records:
        for value in record.values():
            assert str(value) not in raw_pii_values, f"Raw PII leaked: {value}"

    # Validation 2: Safe fields preserved
    assert masked_records[0]["id"] == "RMB-001"
    assert masked_records[0]["amount"] == 245.50
    assert masked_records[0]["category"] == "Travel"
    assert masked_records[1]["department"] == "Marketing"

    # Validation 3: Masking consistent (same input -> same output)
    masked_again = pipeline.process_records(sample_records)
    for r1, r2 in zip(masked_records, masked_again):
        for key in r1:
            assert r1[key] == r2[key], f"Inconsistent masking for {key}"

    # Validation 4: Audit log complete
    entries = pipeline.get_audit_log()
    assert len(entries) >= len(sample_records) * 2  # 2 runs

    # Validation 5: Summary correct
    summary = pipeline.get_summary()
    assert summary["records_processed"] == len(sample_records) * 2
    assert summary["total_pii_fields"] > 0
    assert summary["total_masked"] > 0

    # Validation 6: Log files exist and contain no PII
    log_files = list(tmp_path.glob("audit_*.jsonl"))
    assert len(log_files) >= 1
    for log_file in log_files:
        content = log_file.read_text()
        for pii in raw_pii_values:
            assert pii not in content, f"PII in log: {pii}"


def test_e2e_role_comparison(sample_records, tmp_path):
    """Verify that different roles see different masking levels."""
    results_by_role = {}

    for role in [Role.AUDITOR, Role.DPO, Role.ADMIN]:
        ctx = AuditContext(role=role, purpose="reimbursement_review", legal_basis="legitimate_interest")
        log_subdir = tmp_path / role.value
        pipeline = AuditPipeline(audit_context=ctx, log_dir=log_subdir)
        results_by_role[role] = pipeline.process_records(sample_records)

    # Auditor should see more masking than DPO
    auditor_email = results_by_role[Role.AUDITOR][0].get("email", "")
    dpo_email = results_by_role[Role.DPO][0].get("email", "")
    admin_email = results_by_role[Role.ADMIN][0].get("email", "")

    assert auditor_email != dpo_email, "Auditor and DPO should have different masking"
    assert admin_email == "hans.mueller@example.com", "Admin should see raw data"
```

- [ ] **Step 2: Run the e2e test**

Run: `python -m pytest tests/test_e2e.py -v`
Expected: All 2 tests PASS

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS (models, detector, classifier, masker, pseudonymizer, logger, pipeline, e2e)

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "feat: add end-to-end test for reimbursement audit scenario"
```

---

### Task 13: Final Cleanup and Full Test Run

- [ ] **Step 1: Run full test suite with coverage**

```bash
python -m pytest tests/ -v --cov=gdpr_agent --cov-report=term-missing --cov-fail-under=80
```

Expected: All tests PASS, coverage >= 80% across all modules.

- [ ] **Step 2: Verify no real PII in codebase**

```bash
grep -r "real.*password\|actual.*key\|secret.*=" src/ tests/ --include="*.py" || echo "Clean"
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: complete GDPR audit agent v0.1.0 prototype"
```
