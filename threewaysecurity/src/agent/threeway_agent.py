"""Three-way match agent — price, PO quantity, and GRN quantity checks."""

import json
from pathlib import Path

import pandas as pd


def run(settings: dict) -> dict:
    """Run 3-way match checks and produce check_results.json."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]
    tolerance = settings["price_tolerance_pct"]

    # Load inputs
    with open(output_dir / "matched_contracts.json", encoding="utf-8") as f:
        matched_records = json.load(f)

    df_po = pd.read_csv(output_dir / "04_purchase_orders.csv")
    df_grn = pd.read_csv(output_dir / "05_goods_receipts.csv")

    po_map = df_po.set_index("po_id").to_dict("index")
    grn_map = df_grn.set_index("po_id").to_dict("index")

    check_results = []
    counts = {"ALL_PASS": 0, "PRICE_FAIL": 0, "QTY_FAIL": 0, "COMBO_FAIL": 0, "SKIPPED": 0}

    for record in matched_records:
        # Skip non-MATCHED records (but still include them)
        if record.get("contract_status") not in ("MATCHED", "CONTRACT_EXPIRED"):
            record["price_check"] = "SKIP"
            record["qty_po_check"] = "SKIP"
            record["qty_grn_check"] = "SKIP"
            record["overall_check"] = "SKIP"
            record["delta_pct"] = 0.0
            record["qty_delta_po"] = 0
            record["qty_delta_grn"] = 0
            check_results.append(record)
            counts["SKIPPED"] += 1
            continue

        po_ref = record.get("po_ref", "")
        po = po_map.get(po_ref, {})
        grn = grn_map.get(po_ref, {})

        agreed_price = record.get("agreed_price", 0)
        invoice_price = record.get("unit_price", 0)
        invoice_qty = int(record.get("quantity", 0))
        po_qty = int(po.get("quantity", 0))
        grn_qty = int(grn.get("received_quantity", 0))

        # Check A — Price
        if agreed_price and agreed_price != 0:
            delta_pct = round(abs(invoice_price - agreed_price) / agreed_price * 100, 4)
        else:
            delta_pct = 0.0
        price_check = "PASS" if delta_pct <= tolerance else "FAIL"

        # Check B — Quantity vs PO
        qty_delta_po = invoice_qty - po_qty
        qty_po_check = "PASS" if qty_delta_po == 0 else "FAIL"

        # Check C — Quantity vs GRN
        qty_delta_grn = invoice_qty - grn_qty
        qty_grn_check = "PASS" if qty_delta_grn == 0 else "FAIL"

        # Overall check
        fails = []
        if price_check == "FAIL":
            fails.append("PRICE")
        if qty_po_check == "FAIL" or qty_grn_check == "FAIL":
            fails.append("QTY")

        if not fails:
            overall_check = "ALL_PASS"
        elif len(fails) > 1:
            overall_check = "COMBO_FAIL"
        elif "PRICE" in fails:
            overall_check = "PRICE_FAIL"
        else:
            overall_check = "QTY_FAIL"

        record["price_check"] = price_check
        record["qty_po_check"] = qty_po_check
        record["qty_grn_check"] = qty_grn_check
        record["overall_check"] = overall_check
        record["delta_pct"] = delta_pct
        record["qty_delta_po"] = qty_delta_po
        record["qty_delta_grn"] = qty_delta_grn

        check_results.append(record)
        counts[overall_check] += 1

    # Write output
    output_path = output_dir / "check_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(check_results, f, indent=2, ensure_ascii=False)

    print(f"  check_results.json: {len(check_results)} records written")
    print(f"  3-way match: {counts['ALL_PASS']} pass, {counts['PRICE_FAIL']} price fail, "
          f"{counts['QTY_FAIL']} qty fail, {counts['COMBO_FAIL']} combo fail, "
          f"{counts['SKIPPED']} skipped")

    return counts
