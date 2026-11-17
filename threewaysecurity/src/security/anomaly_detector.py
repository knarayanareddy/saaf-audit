"""Anomaly detector — OWASP A07: Identification and Authentication Failures.

Statistical anomaly detection on invoice patterns.
Detects IBAN fraud, price spikes, volume anomalies, and timing irregularities.
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class Alert:
    """Security alert from anomaly detection."""
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    invoice_id: str
    details: str


class AnomalyDetector:
    """Statistical anomaly detection on invoice patterns."""

    def detect_iban_mismatch(
        self, invoice: dict, suppliers_df: pd.DataFrame
    ) -> Alert | None:
        """CRITICAL: Check if invoice IBAN matches registered IBAN."""
        supplier_id = invoice.get("supplier_id", "")
        invoice_iban = invoice.get("iban", "")

        row = suppliers_df[suppliers_df["supplier_id"] == supplier_id]
        if row.empty:
            return Alert(
                alert_type="UNKNOWN_SUPPLIER",
                severity="CRITICAL",
                invoice_id=invoice.get("invoice_id", ""),
                details=f"Supplier {supplier_id} not in register",
            )

        registered_iban = row.iloc[0]["iban"]
        if invoice_iban != registered_iban:
            return Alert(
                alert_type="IBAN_MISMATCH",
                severity="CRITICAL",
                invoice_id=invoice.get("invoice_id", ""),
                details=(
                    f"Invoice IBAN {invoice_iban} does not match "
                    f"registered IBAN {registered_iban} for {supplier_id}"
                ),
            )
        return None

    def detect_price_anomaly(
        self, invoice: dict, contracts_df: pd.DataFrame
    ) -> Alert | None:
        """Flag prices deviating >20% from contract price."""
        part_id = invoice.get("part_id", "")
        supplier_id = invoice.get("supplier_id", "")
        invoice_price = invoice.get("unit_price", 0)

        matching = contracts_df[
            (contracts_df["supplier_id"] == supplier_id)
            & (contracts_df["part_id"] == part_id)
        ]
        if matching.empty or invoice_price == 0:
            return None

        agreed = matching.iloc[0]["agreed_price"]
        if agreed == 0:
            return None

        deviation_pct = abs(invoice_price - agreed) / agreed * 100
        if deviation_pct > 20:
            return Alert(
                alert_type="PRICE_ANOMALY",
                severity="HIGH",
                invoice_id=invoice.get("invoice_id", ""),
                details=(
                    f"Price {invoice_price} deviates {deviation_pct:.1f}% "
                    f"from contract price {agreed}"
                ),
            )
        return None

    def detect_volume_anomaly(
        self, invoice: dict, po_df: pd.DataFrame
    ) -> Alert | None:
        """Flag quantity >3x the average for this part."""
        part_id = invoice.get("part_id", "")
        invoice_qty = invoice.get("quantity", 0)

        matching = po_df[po_df["part_id"] == part_id]
        if matching.empty or len(matching) < 3:
            return None

        avg_qty = matching["quantity"].mean()
        if avg_qty > 0 and invoice_qty > 3 * avg_qty:
            return Alert(
                alert_type="VOLUME_ANOMALY",
                severity="MEDIUM",
                invoice_id=invoice.get("invoice_id", ""),
                details=(
                    f"Quantity {invoice_qty} exceeds 3x average "
                    f"({avg_qty:.0f}) for part {part_id}"
                ),
            )
        return None

    def detect_timing_anomaly(self, invoice: dict) -> Alert | None:
        """Flag invoices with rush payment terms (<7 days)."""
        try:
            inv_date = date.fromisoformat(invoice.get("invoice_date", ""))
            due = date.fromisoformat(invoice.get("due_date", ""))
            days = (due - inv_date).days
            if days < 7:
                return Alert(
                    alert_type="RUSH_PAYMENT",
                    severity="MEDIUM",
                    invoice_id=invoice.get("invoice_id", ""),
                    details=f"Due date only {days} days after invoice date (pressure to pay fast)",
                )
        except (ValueError, TypeError):
            pass
        return None

    def detect_duplicate(self, invoice_id: str, processed: set) -> Alert | None:
        """Detect replay attack: same invoice_id processed twice."""
        if invoice_id in processed:
            return Alert(
                alert_type="DUPLICATE_INVOICE",
                severity="HIGH",
                invoice_id=invoice_id,
                details=f"Invoice {invoice_id} already processed (replay attack?)",
            )
        return None

    def run_all_checks(
        self,
        invoice: dict,
        suppliers_df: pd.DataFrame,
        contracts_df: pd.DataFrame,
        po_df: pd.DataFrame,
        processed_ids: set,
    ) -> list[Alert]:
        """Run all anomaly checks on a single invoice."""
        alerts: list[Alert] = []

        for check in [
            lambda: self.detect_iban_mismatch(invoice, suppliers_df),
            lambda: self.detect_price_anomaly(invoice, contracts_df),
            lambda: self.detect_volume_anomaly(invoice, po_df),
            lambda: self.detect_timing_anomaly(invoice),
            lambda: self.detect_duplicate(invoice.get("invoice_id", ""), processed_ids),
        ]:
            result = check()
            if result is not None:
                alerts.append(result)

        return alerts
