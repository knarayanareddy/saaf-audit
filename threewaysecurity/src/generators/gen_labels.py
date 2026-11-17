"""Ground truth label generator for evaluation."""

from pathlib import Path

import pandas as pd


def generate_all(settings: dict) -> None:
    """Generate ground_truth.csv with expected audit outcomes."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]
    label_dir = root / settings["label_dir"]
    label_dir.mkdir(parents=True, exist_ok=True)

    df_index = pd.read_csv(output_dir / "invoices_index.csv")
    df_contracts = pd.read_csv(output_dir / "03_contracts.csv")
    df_grn = pd.read_csv(output_dir / "05_goods_receipts.csv")
    df_payments = pd.read_csv(output_dir / "06_payments.csv")

    # Build lookups
    contract_map = df_contracts.set_index("contract_id").to_dict("index")
    grn_map = df_grn.set_index("po_id").to_dict("index")
    payment_map = df_payments.set_index("po_id").to_dict("index")

    labels = []
    for _, row in df_index.iterrows():
        error_type = row["error_type"]
        contract_id = row["contract_id"]
        po_ref = row["po_ref"]

        # Payment info
        payment = payment_map.get(po_ref, {})
        days_late = int(payment.get("days_late", 0))
        payment_on_time = days_late == 0

        # Calculate delta_pct
        contract = contract_map.get(contract_id, {})
        agreed_price = contract.get("agreed_price", row["unit_price"])
        if agreed_price and agreed_price != 0:
            delta_pct = round(abs(row["unit_price"] - agreed_price) / agreed_price * 100, 2)
        else:
            delta_pct = 0.0

        # Calculate qty_delta
        grn = grn_map.get(po_ref, {})
        received_qty = int(grn.get("received_quantity", row["quantity"]))
        qty_delta = abs(int(row["quantity"]) - received_qty)

        # Determine error class and expected action
        if error_type == "correct":
            error_class = "NONE"
            should_block = False
            error_severity = "NONE"
            if days_late > 0:
                expected_action = "FLAG_FINANCE"
                error_class = "LATE_PAYMENT"
            else:
                expected_action = "APPROVE"
        elif error_type == "price_error":
            error_class = "PRICE_MISMATCH"
            should_block = True
            expected_action = "ESCALATE_PROCUREMENT"
            if delta_pct < 2:
                error_severity = "LOW"
            elif delta_pct <= 5:
                error_severity = "MEDIUM"
            else:
                error_severity = "HIGH"
        elif error_type == "quantity_error":
            error_class = "QTY_MISMATCH"
            should_block = True
            expected_action = "ESCALATE_LOGISTICS"
            if qty_delta <= 1:
                error_severity = "LOW"
            elif qty_delta == 2:
                error_severity = "MEDIUM"
            else:
                error_severity = "HIGH"
        elif error_type == "contract_expired":
            error_class = "CONTRACT_EXPIRED"
            should_block = True
            error_severity = "HIGH"
            expected_action = "ESCALATE_LEGAL"
        elif error_type == "combo_error":
            error_class = "COMBO"
            should_block = True
            error_severity = "HIGH"
            expected_action = "BLOCK_COMBO"
        else:
            error_class = "NONE"
            should_block = False
            error_severity = "NONE"
            expected_action = "APPROVE"

        labels.append({
            "invoice_id": row["invoice_id"],
            "should_block": should_block,
            "error_class": error_class,
            "error_severity": error_severity,
            "delta_pct": delta_pct if error_type in ("price_error", "combo_error") else 0.0,
            "qty_delta": qty_delta if error_type in ("quantity_error", "combo_error") else 0,
            "expected_action": expected_action,
            "contract_ref": contract_id,
            "payment_on_time": payment_on_time,
            "days_late": days_late,
        })

    df_labels = pd.DataFrame(labels)
    df_labels.to_csv(label_dir / "ground_truth.csv", index=False, encoding="utf-8")
    print(f"  ground_truth.csv: {len(df_labels)} records written")
