"""Decision agent — applies business rules and generates audit decisions."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def run(settings: dict) -> dict:
    """Apply decision logic and produce decisions.json."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]

    # Load inputs
    with open(output_dir / "check_results.json", encoding="utf-8") as f:
        check_results = json.load(f)

    df_payments = pd.read_csv(output_dir / "06_payments.csv")
    payment_map = df_payments.set_index("po_id").to_dict("index")

    decisions = []
    counts = {"APPROVE": 0, "BLOCK": 0, "FLAG": 0}

    for record in check_results:
        inv_id = record.get("invoice_id", "")
        contract_id = record.get("matched_contract_id", "")
        contract_status = record.get("contract_status", "")
        overall_check = record.get("overall_check", "")
        delta_pct = record.get("delta_pct", 0.0)
        qty_delta_grn = record.get("qty_delta_grn", 0)
        grn_ref = record.get("grn_ref", "")
        invoice_qty = record.get("quantity", 0)
        valid_to = record.get("contract_valid_to", "")
        inv_date = record.get("invoice_date", "")

        # Payment info
        po_ref = record.get("po_ref", "")
        payment = payment_map.get(po_ref, {})
        days_late = int(payment.get("days_late", 0))

        # Decision logic (priority order)
        if contract_status in ("CONTRACT_EXPIRED", "CONTRACT_NOT_FOUND"):
            decision = "BLOCK"
            action = "ESCALATE_LEGAL"
            blocked = True
            motivation = (
                f"Invoice {inv_id} blocked: contract {contract_id} "
                f"expired on {valid_to}. Invoice date {inv_date} "
                f"falls outside validity period."
            )
        elif overall_check == "COMBO_FAIL":
            decision = "BLOCK"
            action = "BLOCK_COMBO"
            blocked = True
            motivation = (
                f"Invoice {inv_id} blocked due to multiple deviations: "
                f"price deviation {delta_pct:.2f}% and quantity deviation "
                f"{qty_delta_grn} units."
            )
        elif overall_check == "PRICE_FAIL":
            decision = "BLOCK"
            action = "ESCALATE_PROCUREMENT"
            blocked = True
            motivation = (
                f"Invoice {inv_id} blocked due to price deviation of "
                f"{delta_pct:.2f}% vs. contract price (contract "
                f"{contract_id}). Allowed tolerance: 0.5%."
            )
        elif overall_check == "QTY_FAIL":
            decision = "BLOCK"
            action = "ESCALATE_LOGISTICS"
            blocked = True
            grn_qty = int(record.get("quantity", 0)) - int(qty_delta_grn)
            motivation = (
                f"Invoice {inv_id} blocked: invoiced quantity "
                f"({invoice_qty}) deviates from received quantity per GRN "
                f"({grn_ref}). Difference: {qty_delta_grn} units."
            )
        elif days_late > 0:
            decision = "FLAG"
            action = "FLAG_FINANCE"
            blocked = False
            motivation = (
                f"Invoice {inv_id} approved but flagged: payment is "
                f"{days_late} days overdue."
            )
        else:
            decision = "APPROVE"
            action = "APPROVE"
            blocked = False
            motivation = (
                f"Invoice {inv_id} approved. Price conforms to contract "
                f"({contract_id}), quantity confirmed by GRN "
                f"({grn_ref}). Payment released."
            )

        record["decision"] = decision
        record["action"] = action
        record["blocked"] = blocked
        record["motivation"] = motivation
        record["decision_timestamp"] = datetime.now(timezone.utc).isoformat()

        decisions.append(record)
        counts[decision] += 1

    # Write output
    output_path = output_dir / "decisions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)

    print(f"  decisions.json: {len(decisions)} records written")
    print(f"  Decisions: {counts['APPROVE']} approved, "
          f"{counts['BLOCK']} blocked, {counts['FLAG']} flagged")

    return counts
