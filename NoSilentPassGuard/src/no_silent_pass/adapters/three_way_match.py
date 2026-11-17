"""Three-way match with fail-closed input handling.

Pattern fixed: first-alias-wins column selection ("decoy columns"), unlocalised number
parsing, NaN passing ``abs(a-b) > tol`` comparisons, and a missing goods receipt being
only a warning.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from ..guard import Guard

QTY_ALIASES = ("quantity", "qty", "quantity_received", "quantity_billed")
PRICE_ALIASES = ("unit_price", "price", "unitprice")


def assess_invoice(
    po: Mapping[str, Mapping[str, Any]],
    grn: Mapping[str, Any],
    invoice_rows: List[Mapping[str, Any]],
    tol_qty: Any = 0,
    tol_price: Any = "0.01",
    decimal: Optional[str] = None,
) -> Guard:
    """``po`` maps sku -> {"qty", "price"}; ``grn`` maps sku -> received quantity."""
    g = Guard("three-way-match", decimal=decimal)
    for i, row in enumerate(invoice_rows, start=1):
        item = f"row {i}"
        sku = g.require_present(row, "sku", item)
        qty = g.require_unique(row, QTY_ALIASES, "quantity", item)
        price = g.require_unique(row, PRICE_ALIASES, "unit_price", item)
        if sku is None or qty is None or price is None:
            continue  # reasons already recorded; the row is counted as skipped
        if not g.check("sku_on_po", sku in po, item, f"sku {sku}"):
            g.mark_assessed(item)
            continue
        g.within("qty_vs_po", qty, po[sku]["qty"], tol_qty, item)
        g.within("price_vs_po", price, po[sku]["price"], tol_price, item)
        if g.check("goods_received", sku in grn, item, f"sku {sku} on goods receipt"):
            g.within("qty_vs_grn", qty, grn[sku], tol_qty, item)
        g.mark_assessed(item)
    return g


def naive_match(po, grn, invoice_rows, tol_qty=0.0, tol_price=0.01) -> str:
    """The fail-open pattern for comparison: first alias wins, NaN compares as 'no problem'."""

    def first(row, keys):
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return row[k]
        return None

    for row in invoice_rows:
        sku = row["sku"]
        qty, price = float(first(row, QTY_ALIASES)), float(first(row, PRICE_ALIASES))
        if abs(qty - float(po[sku]["qty"])) > tol_qty:
            return "MISMATCH"
        if abs(price - float(po[sku]["price"])) > tol_price:
            return "MISMATCH"
    return "MATCH"
