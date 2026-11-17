"""Orchestrates the 4-step GDPR audit pipeline."""

import copy
from pathlib import Path
from typing import Any

from gdpr_agent.audit_logger import AuditLogger
from gdpr_agent.config import PSEUDONYM_KEY_ENV_VAR, get_pseudonym_key
from gdpr_agent.dynamic_masker import mask_value
from gdpr_agent.field_classifier import classify_fields
from gdpr_agent.legal_basis_mapper import map_legal_basis
from gdpr_agent.models import (
    AuditContext, AuditRecord, FieldClassification, MaskingLevel, MaskingResult,
)
from gdpr_agent.pii_detector import detect_pii_in_record
from gdpr_agent.pseudonymizer import Pseudonymizer, PseudonymVault


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


class AuditPipeline:
    """4-step pipeline: Detect -> Classify -> Map Legal Basis -> Mask."""

    def __init__(
        self,
        audit_context: AuditContext,
        log_dir: Path,
        pseudonym_key: str | None = None,
        vault: PseudonymVault | None = None,
    ):
        """Build a pipeline.

        `pseudonym_key` falls back to the environment. There is deliberately no
        default value: a hardcoded key would make every token in every
        deployment reproducible by anyone with the source, and pseudonyms that
        anyone can reverse are not pseudonyms (GDPR Art. 4(5)).

        Pass a `vault` only when re-identification is genuinely required; the
        pipeline is one-way without one.
        """
        key = pseudonym_key if pseudonym_key is not None else get_pseudonym_key()
        if not key:
            raise ValueError(
                "no pseudonymisation key configured; set the "
                f"{PSEUDONYM_KEY_ENV_VAR} environment variable or pass "
                "pseudonym_key explicitly"
            )

        self._ctx = audit_context
        self._logger = AuditLogger(log_dir=log_dir)
        self._pseudonymizer = Pseudonymizer(secret_key=key, vault=vault)
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
        masked_record = copy.deepcopy(record)  # Deep copy: records may nest
        fields_masked = 0

        for field in with_basis:
            path = field.path or [field.field_name]

            # Excessive fields always fully masked regardless of role
            if field.classification == FieldClassification.EXCESSIVE:
                result = mask_value(
                    field.value, field.field_name, field.category, MaskingLevel.FULL
                )
            elif (
                field.classification == FieldClassification.REQUIRED
                and self._ctx.masking_level == MaskingLevel.FULL
            ):
                # Auditor: Required fields get pseudonymized (reversible) rather
                # than masked. Routed through MaskingResult like every other
                # branch so the trail records that this field was pseudonymised
                # and whether it can be reversed — the distinction a DPO needs.
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

        # Log the action
        self._total_detected += len(pii_fields)
        self._total_masked += fields_masked

        record_id = record.get("id") if isinstance(record, dict) else None
        record_id = str(record_id) if record_id is not None else f"record-{self._records_processed}"
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

    def process_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process multiple records through the pipeline."""
        return [self.process_record(r) for r in records]

    def get_audit_log(self) -> list[AuditRecord]:
        """Return all audit log entries."""
        return self._logger.get_entries()

    def verify_audit_log(self) -> bool:
        """True if the audit chain for this session is intact."""
        return AuditLogger.verify_chain(self._logger.get_entries())

    @property
    def audit_log_file(self) -> Path:
        return self._logger.log_file

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
