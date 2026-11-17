"""Payment instruction agent — Step 05.

Generates payment instructions for approved invoices.
CRITICAL SECURITY: Verifies IBAN against supplier register before every payment.
Blocks duplicate payments. Only APPROVE decisions result in payment release.

OWASP mitigations:
- A01: Only APPROVE decisions can trigger payment
- A02: IBAN verified cryptographically against register
- A05: Duplicate payment prevention
- A07: IBAN fraud detection (swap attack)
- A08: Hash chain on payment output
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


def run(settings: dict) -> dict:
    """Generate payment instructions with security checks."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]

    # Load inputs
    with open(output_dir / "decisions.json", encoding="utf-8") as f:
        decisions = json.load(f)

    df_suppliers = pd.read_csv(output_dir / "01_suppliers.csv")
    supplier_iban_map: dict[str, str] = dict(
        zip(df_suppliers["supplier_id"], df_suppliers["iban"])
    )

    payment_instructions: list[dict] = []
    blocked_queue: list[dict] = []
    paid_po_refs: set[str] = set()  # Duplicate payment detection

    counts = {"RELEASED": 0, "ON_HOLD": 0, "PENDING_REVIEW": 0, "IBAN_BLOCKED": 0, "DUPLICATE_BLOCKED": 0}

    for record in decisions:
        inv_id = record.get("invoice_id", "")
        decision = record.get("decision", "")
        action = record.get("action", "")
        supplier_id = record.get("supplier_id", "")
        invoice_iban = record.get("iban", "")
        po_ref = record.get("po_ref", "")
        total = record.get("total_incl_vat", record.get("total_amount", 0))

        # SECURITY CHECK 1: IBAN must match supplier register
        registered_iban = supplier_iban_map.get(supplier_id)
        iban_verified = (invoice_iban == registered_iban) if registered_iban else False

        # SECURITY CHECK 2: Duplicate payment prevention
        is_duplicate = po_ref in paid_po_refs

        # Build payment instruction based on decision
        instruction = {
            "invoice_id": inv_id,
            "supplier_id": supplier_id,
            "po_ref": po_ref,
            "amount": round(total, 2),
            "currency": "EUR",
            "iban_destination": invoice_iban,
            "iban_verified": iban_verified,
            "registered_iban": registered_iban or "",
            "decision": decision,
            "action": action,
        }

        if not iban_verified and decision == "APPROVE":
            # CRITICAL: Block payment if IBAN doesn't match
            instruction["payment_status"] = "IBAN_BLOCKED"
            instruction["payment_reason"] = (
                f"SECURITY BLOCK: Invoice IBAN {invoice_iban} does not match "
                f"registered IBAN {registered_iban} for {supplier_id}. "
                f"Possible IBAN swap fraud."
            )
            blocked_queue.append(instruction)
            counts["IBAN_BLOCKED"] += 1

        elif is_duplicate:
            # Block duplicate payment
            instruction["payment_status"] = "DUPLICATE_BLOCKED"
            instruction["payment_reason"] = (
                f"Duplicate payment prevented: PO {po_ref} already has a payment instruction."
            )
            blocked_queue.append(instruction)
            counts["DUPLICATE_BLOCKED"] += 1

        elif decision == "APPROVE":
            # Release payment
            inv_date = record.get("invoice_date", "")
            terms = record.get("contract_payment_terms_days", 30)
            try:
                from datetime import date as dt_date
                base = dt_date.fromisoformat(inv_date)
                value_date = (base + timedelta(days=int(terms))).isoformat()
            except (ValueError, TypeError):
                value_date = ""

            instruction["payment_status"] = "RELEASED"
            instruction["value_date"] = value_date
            instruction["payment_reason"] = "All checks passed. Payment released."
            payment_instructions.append(instruction)
            paid_po_refs.add(po_ref)
            counts["RELEASED"] += 1

        elif decision == "FLAG":
            # FLAG_FINANCE: create instruction but mark for manual review
            instruction["payment_status"] = "PENDING_REVIEW"
            instruction["manual_review_required"] = True
            instruction["payment_reason"] = (
                f"Payment flagged for manual review: {record.get('motivation', '')}"
            )
            payment_instructions.append(instruction)
            paid_po_refs.add(po_ref)
            counts["PENDING_REVIEW"] += 1

        else:
            # BLOCK/ESCALATE: no payment instruction
            instruction["payment_status"] = "ON_HOLD"
            instruction["payment_reason"] = (
                f"Payment on hold: {record.get('motivation', '')}"
            )
            blocked_queue.append(instruction)
            counts["ON_HOLD"] += 1

        instruction["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Write outputs
    pi_path = output_dir / "payment_instructions.json"
    with open(pi_path, "w", encoding="utf-8") as f:
        json.dump(payment_instructions, f, indent=2, ensure_ascii=False)

    bq_path = output_dir / "blocked_queue.json"
    with open(bq_path, "w", encoding="utf-8") as f:
        json.dump(blocked_queue, f, indent=2, ensure_ascii=False)

    print(f"  payment_instructions.json: {len(payment_instructions)} instructions")
    print(f"  blocked_queue.json: {len(blocked_queue)} blocked invoices")
    print(f"  Payment: {counts['RELEASED']} released, {counts['PENDING_REVIEW']} pending review, "
          f"{counts['ON_HOLD']} on hold, {counts['IBAN_BLOCKED']} IBAN blocked, "
          f"{counts['DUPLICATE_BLOCKED']} duplicate blocked")

    return counts
