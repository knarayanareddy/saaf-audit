"""Transaction generator — purchase orders, goods receipts, and payments."""

import random
from datetime import timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


# Category-based quantity ranges
QUANTITY_RANGES: dict[str, tuple[int, int]] = {
    "Chemicals": (10, 100),
    "Materials": (10, 100),
    "Sensors": (2, 20),
    "CMP": (2, 20),
    "Optics": (1, 5),
    "Laser": (1, 5),
    "Source": (1, 5),
    "Robotics": (1, 5),
    "Optical coatings": (1, 5),
    "Power systems": (1, 5),
}


def generate_all(settings: dict) -> None:
    """Generate PO, GRN, and payment CSVs."""
    seed = settings["seed"]
    random.seed(seed)
    fake = Faker("nl_NL")
    Faker.seed(seed)

    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]

    # Load master data
    df_suppliers = pd.read_csv(output_dir / "01_suppliers.csv")
    df_parts = pd.read_csv(output_dir / "02_parts.csv")
    df_contracts = pd.read_csv(output_dir / "03_contracts.csv")

    supplier_map = df_suppliers.set_index("supplier_id").to_dict("index")
    parts_map = df_parts.set_index("part_id").to_dict("index")

    # --- Step 1: Purchase Orders ---
    active_contracts = df_contracts[df_contracts["status"] == "ACTIVE"].to_dict("records")
    n_pos = settings["n_purchase_orders"]

    purchase_orders = []
    for i in range(n_pos):
        contract = random.choice(active_contracts)
        category = parts_map[contract["part_id"]]["category"]
        q_min, q_max = QUANTITY_RANGES.get(category, (1, 5))
        quantity = random.randint(q_min, q_max)

        po_date = pd.Timestamp("2025-01-01") + timedelta(
            days=random.randint(0, 333)  # up to 2025-11-30
        )
        delivery_offset = random.randint(14, 60)
        expected_delivery = po_date + timedelta(days=delivery_offset)

        # PO status distribution: 80/15/5
        status_roll = random.random()
        if status_roll < 0.80:
            po_status = "DELIVERED"
        elif status_roll < 0.95:
            po_status = "OPEN"
        else:
            po_status = "PARTIAL"

        purchase_orders.append({
            "po_id": f"PO-2025-{i + 1:05d}",
            "supplier_id": contract["supplier_id"],
            "part_id": contract["part_id"],
            "contract_id": contract["contract_id"],
            "quantity": quantity,
            "unit_price": contract["agreed_price"],
            "po_date": po_date.strftime("%Y-%m-%d"),
            "expected_delivery_date": expected_delivery.strftime("%Y-%m-%d"),
            "po_status": po_status,
            "requestor": fake.name(),
        })

    df_po = pd.DataFrame(purchase_orders)
    df_po.to_csv(output_dir / "04_purchase_orders.csv", index=False, encoding="utf-8")
    print(f"  04_purchase_orders.csv: {len(df_po)} records written")

    # --- Step 2: Goods Receipts ---
    goods_receipts = []
    for i, po in enumerate(purchase_orders):
        expected = pd.Timestamp(po["expected_delivery_date"])
        receipt_date = expected + timedelta(days=random.randint(-3, 3))

        ordered_qty = po["quantity"]
        # Received quantity distribution: 85% exact, 10% short, 5% surplus
        qty_roll = random.random()
        if qty_roll < 0.85:
            received_qty = ordered_qty
            grn_status = "COMPLETE"
        elif qty_roll < 0.95:
            delta = random.randint(1, min(3, max(1, ordered_qty - 1)))
            received_qty = max(1, ordered_qty - delta)
            grn_status = "PARTIAL"
        else:
            delta = random.randint(1, 2)
            received_qty = ordered_qty + delta
            grn_status = "SURPLUS"

        warehouse = random.choice(["WH-A1", "WH-B2", "WH-C3", "WH-D4"])

        goods_receipts.append({
            "grn_id": f"GRN-2025-{i + 1:05d}",
            "po_id": po["po_id"],
            "supplier_id": po["supplier_id"],
            "part_id": po["part_id"],
            "ordered_quantity": ordered_qty,
            "received_quantity": received_qty,
            "receipt_date": receipt_date.strftime("%Y-%m-%d"),
            "warehouse_location": warehouse,
            "grn_status": grn_status,
        })

    df_grn = pd.DataFrame(goods_receipts)
    df_grn.to_csv(output_dir / "05_goods_receipts.csv", index=False, encoding="utf-8")
    print(f"  05_goods_receipts.csv: {len(df_grn)} records written")

    # --- Step 3: Payments ---
    # 180 payments (20 POs remain unpaid)
    paid_indices = sorted(random.sample(range(n_pos), 180))

    payments = []
    for idx, po_idx in enumerate(paid_indices):
        po = purchase_orders[po_idx]
        supplier = supplier_map.get(po["supplier_id"], {})
        terms_str = supplier.get("payment_terms", "Net-30")
        terms_days = int(terms_str.replace("Net-", ""))

        po_date = pd.Timestamp(po["po_date"])
        amount = round(po["quantity"] * po["unit_price"], 2)

        # 80% on time, 20% late
        if random.random() < 0.80:
            payment_date = po_date + timedelta(days=terms_days)
            days_late = 0
            payment_status = "PAID"
        else:
            late_days = random.randint(3, 45)
            payment_date = po_date + timedelta(days=terms_days + late_days)
            days_late = late_days
            payment_status = "OVERDUE"

        payments.append({
            "payment_id": f"PAY-2025-{idx + 1:05d}",
            "po_id": po["po_id"],
            "invoice_ref": "",
            "amount": amount,
            "payment_date": payment_date.strftime("%Y-%m-%d"),
            "iban_destination": supplier.get("iban", ""),
            "currency": "EUR",
            "payment_status": payment_status,
            "days_late": days_late,
        })

    # Mark remaining 20 as PENDING
    unpaid_indices = [i for i in range(n_pos) if i not in set(paid_indices)]
    for idx2, po_idx in enumerate(unpaid_indices):
        po = purchase_orders[po_idx]
        supplier = supplier_map.get(po["supplier_id"], {})
        amount = round(po["quantity"] * po["unit_price"], 2)

        payments.append({
            "payment_id": f"PAY-2025-{180 + idx2 + 1:05d}",
            "po_id": po["po_id"],
            "invoice_ref": "",
            "amount": amount,
            "payment_date": "",
            "iban_destination": supplier.get("iban", ""),
            "currency": "EUR",
            "payment_status": "PENDING",
            "days_late": 0,
        })

    # Only write the 180 paid/overdue records (spec says 180 records)
    df_payments = pd.DataFrame(payments[:180])
    df_payments.to_csv(output_dir / "06_payments.csv", index=False, encoding="utf-8")
    print(f"  06_payments.csv: {len(df_payments)} records written")
