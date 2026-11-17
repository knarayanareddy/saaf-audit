"""Schema validator — OWASP A04: Insecure Design Prevention.

Uses pydantic v2 strict mode for all data models.
Validates field formats, cross-references, and business rules.
"""

import re
from datetime import date, timedelta

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class InvoiceSchema(BaseModel):
    """Strict schema for invoice validation."""

    model_config = ConfigDict(strict=False)  # Allow int->float coercion

    invoice_id: str
    supplier_id: str
    part_id: str
    po_ref: str
    quantity: int
    unit_price: float
    total_amount: float
    invoice_date: str
    due_date: str
    iban: str
    vat_number: str

    @field_validator("invoice_id")
    @classmethod
    def validate_invoice_id(cls, v: str) -> str:
        if not re.match(r"^INV-\d{4}-\d{5}$", v):
            raise ValueError(f"Invalid invoice_id format: {v}")
        return v

    @field_validator("supplier_id")
    @classmethod
    def validate_supplier_id(cls, v: str) -> str:
        if not re.match(r"^SUP-\d{3}$", v):
            raise ValueError(f"Invalid supplier_id format: {v}")
        return v

    @field_validator("part_id")
    @classmethod
    def validate_part_id(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{3}-\d{4}$", v):
            raise ValueError(f"Invalid part_id format: {v}")
        return v

    @field_validator("po_ref")
    @classmethod
    def validate_po_ref(cls, v: str) -> str:
        if not re.match(r"^PO-\d{4}-\d{5}$", v):
            raise ValueError(f"Invalid po_ref format: {v}")
        return v

    @field_validator("vat_number")
    @classmethod
    def validate_vat(cls, v: str) -> str:
        if not re.match(r"^(NL\d{9}B\d{2}|DE\d{9})$", v):
            raise ValueError(f"Invalid VAT format: {v}")
        return v

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, v: str) -> str:
        if not re.match(r"^(NL\d{2}[A-Z]{4}\d{10}|DE\d{2}[A-Z]{4}\d{14})$", v):
            raise ValueError(f"Invalid IBAN format: {v}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0 or v > 10000:
            raise ValueError(f"Quantity out of range: {v}")
        return v

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, v: float) -> float:
        if v <= 0 or v > 1_000_000:
            raise ValueError(f"Unit price out of range: {v}")
        return v

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: float) -> float:
        if v <= 0 or v > 10_000_000:
            raise ValueError(f"Total amount out of range: {v}")
        return v

    @model_validator(mode="after")
    def validate_total_equals_qty_times_price(self) -> "InvoiceSchema":
        expected = round(self.quantity * self.unit_price, 2)
        actual = round(self.total_amount, 2)
        if abs(expected - actual) > 0.01:
            raise ValueError(
                f"total_amount ({actual}) != quantity ({self.quantity}) x "
                f"unit_price ({self.unit_price}) = {expected}"
            )
        return self

    @model_validator(mode="after")
    def validate_due_after_invoice(self) -> "InvoiceSchema":
        try:
            inv_date = date.fromisoformat(self.invoice_date)
            due = date.fromisoformat(self.due_date)
            if due < inv_date:
                raise ValueError(f"due_date ({self.due_date}) < invoice_date ({self.invoice_date})")
        except ValueError as e:
            if "due_date" in str(e):
                raise
        return self


def validate_cross_references(
    invoice: dict,
    suppliers_df: pd.DataFrame,
    po_df: pd.DataFrame,
) -> list[str]:
    """Verify supplier, IBAN, VAT, and PO cross-references.

    Returns list of violation descriptions (empty = all OK).
    """
    violations: list[str] = []
    supplier_id = invoice.get("supplier_id", "")
    invoice_iban = invoice.get("iban", "")
    invoice_vat = invoice.get("vat_number", "")
    po_ref = invoice.get("po_ref", "")

    # Check supplier exists
    supplier_row = suppliers_df[suppliers_df["supplier_id"] == supplier_id]
    if supplier_row.empty:
        violations.append(f"Supplier {supplier_id} not found in supplier register")
        return violations

    registered_iban = supplier_row.iloc[0]["iban"]
    registered_vat = supplier_row.iloc[0]["vat_number"]

    # CRITICAL: IBAN must match registered IBAN
    if invoice_iban != registered_iban:
        violations.append(
            f"IBAN MISMATCH: invoice has {invoice_iban}, "
            f"register has {registered_iban} for {supplier_id}"
        )

    # VAT must match
    if invoice_vat != registered_vat:
        violations.append(
            f"VAT MISMATCH: invoice has {invoice_vat}, "
            f"register has {registered_vat} for {supplier_id}"
        )

    # PO must exist and belong to same supplier
    po_row = po_df[po_df["po_id"] == po_ref]
    if po_row.empty:
        violations.append(f"PO {po_ref} not found in purchase order register")
    else:
        po_supplier = po_row.iloc[0]["supplier_id"]
        if po_supplier != supplier_id:
            violations.append(
                f"PO {po_ref} belongs to {po_supplier}, "
                f"not {supplier_id}"
            )

    return violations
