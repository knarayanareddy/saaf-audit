"""Orchestrates the 4-step Privacy Guard pipeline for a fieldwork dataset.

Detect -> Classify -> Map legal basis -> Mask, per record, with a tamper-evident
audit trail. Produces a masked view + a per-field report + the trail. It writes
nothing to the RACM spine — the auditor keeps ownership of the data.
"""

import copy
from typing import Any, Optional

from .audit_logger import AuditLogger
from .config import get_pseudonym_key, load_legal_bases
from .dynamic_masker import mask_value
from .field_classifier import classify_fields
from .legal_basis_mapper import map_legal_basis
from .models import (
    AuditContext, FieldClassification, MaskingLevel, MaskingResult,
)
from .pii_detector import detect_pii_in_record
from .pseudonymizer import Pseudonymizer, PseudonymVault


def format_article(code: Optional[str]) -> Optional[str]:
    """art_6_1_c -> 'Art. 6(1)(c)'; art_33 -> 'Art. 33'; chapter_v -> 'Chapter V'."""
    if not code:
        return None
    if code.startswith("chapter_"):
        return "Chapter " + code.split("_", 1)[1].upper()
    parts = code.split("_")
    if parts and parts[0] == "art":
        rest = parts[1:]
        if not rest:
            return "Art."
        out = f"Art. {rest[0]}"
        for seg in rest[1:]:
            out += f"({seg})"
        return out
    return code


def _set_by_path(container: Any, path: list[str], value: Any) -> None:
    """Write a value back to its position in a nested record."""
    target = container
    for key in path[:-1]:
        target = target[int(key)] if isinstance(target, list) else target[key]
    last = path[-1]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value


class PrivacyGuardPipeline:
    """4-step pipeline: Detect -> Classify -> Map Legal Basis -> Mask."""

    def __init__(
        self,
        audit_context: AuditContext,
        pseudonym_key: Optional[str] = None,
        vault: Optional[PseudonymVault] = None,
    ):
        key = pseudonym_key if pseudonym_key is not None else get_pseudonym_key()
        if not key:
            raise ValueError(
                "no pseudonymisation key configured; set the GDPR_PSEUDONYM_KEY "
                "environment variable"
            )
        self._ctx = audit_context
        self._logger = AuditLogger(log_dir=None)  # in-memory; caller serialises
        self._pseudonymizer = Pseudonymizer(secret_key=key, vault=vault)
        self._articles = load_legal_bases().get("articles", {})
        self._total_detected = 0
        self._total_masked = 0
        self._records_processed = 0
        self._field_report: list[dict] = []

    def _legal_basis_display(self, code: Optional[str]) -> dict:
        title = self._articles.get(code, {}).get("title") if code else None
        return {"code": code, "article": format_article(code), "title": title}

    def process_record(self, record: dict[str, Any]) -> dict[str, Any]:
        pii_fields = detect_pii_in_record(record)
        classified = classify_fields(pii_fields, purpose=self._ctx.purpose)
        with_basis = [map_legal_basis(f, purpose=self._ctx.purpose) for f in classified]

        masked_record = copy.deepcopy(record)
        fields_masked = 0

        record_id = record.get("id") if isinstance(record, dict) else None
        if record_id is None and isinstance(record, dict):
            record_id = record.get("case_id") or record.get("customer_id")
        record_id = str(record_id) if record_id is not None else f"record-{self._records_processed}"

        for field in with_basis:
            path = field.path or [field.field_name]

            if field.classification == FieldClassification.EXCESSIVE:
                result = mask_value(
                    field.value, field.field_name, field.category, MaskingLevel.FULL
                )
            elif (
                field.classification == FieldClassification.REQUIRED
                and self._ctx.masking_level == MaskingLevel.FULL
            ):
                # Auditor: Required fields are pseudonymised (reversible with a
                # vault) rather than masked, so equal values stay equal.
                result = MaskingResult(
                    field_name=field.field_name,
                    original_category=field.category,
                    masked_value=self._pseudonymizer.pseudonymize(field.value),
                    masking_method="pseudonymized",
                    reversible=self._pseudonymizer.is_reversible,
                )
            else:
                result = mask_value(
                    field.value, field.field_name, field.category, self._ctx.masking_level
                )

            _set_by_path(masked_record, path, result.masked_value)
            if result.masking_method != "none":
                fields_masked += 1

            self._field_report.append({
                "record_id": record_id,
                "field_name": field.field_name,
                "category": field.category.value,
                "classification": field.classification.value if field.classification else None,
                "legal_basis": self._legal_basis_display(field.legal_basis),
                "masking_method": result.masking_method,
                "masked_value": result.masked_value,
                "reversible": result.reversible,
                # Original only surfaces in admin (unmasked) mode; then the
                # masked value is the original anyway.
                "original_value": field.value if self._ctx.masking_level == MaskingLevel.NONE else None,
            })

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
            record_id=record_id,
            field_names=[f.field_name for f in with_basis],
            justification=self._ctx.justification,
        )
        return masked_record

    def process_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        masked = [self.process_record(r) for r in records]
        entries = self._logger.get_entries()
        return {
            "masked_records": masked,
            "field_report": self._field_report,
            "summary": {
                "records_processed": self._records_processed,
                "total_pii_fields": self._total_detected,
                "total_masked": self._total_masked,
                "role": self._ctx.role.value,
                "purpose": self._ctx.purpose,
                "masking_level": self._ctx.masking_level.value,
            },
            "audit_trail": [e.model_dump(mode="json") for e in entries],
            "audit_trail_jsonl": self._logger.to_jsonl(),
            "chain_intact": AuditLogger.verify_chain(entries),
        }
