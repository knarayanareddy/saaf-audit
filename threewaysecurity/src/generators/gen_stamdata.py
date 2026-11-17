"""Master data generator — suppliers, parts, and contracts."""

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


def generate_all(settings: dict) -> None:
    """Generate supplier, parts, and contract CSVs from config JSON files."""
    seed = settings["seed"]
    random.seed(seed)

    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1 — Load config
    with open(root / "config" / "suppliers.json", encoding="utf-8") as f:
        suppliers = json.load(f)
    with open(root / "config" / "parts.json", encoding="utf-8") as f:
        parts = json.load(f)

    # Step 2 — Write 01_suppliers.csv
    df_suppliers = pd.DataFrame(suppliers)[
        ["supplier_id", "name", "country", "iban", "kvk", "city", "payment_terms", "vat_number"]
    ]
    df_suppliers.to_csv(output_dir / "01_suppliers.csv", index=False, encoding="utf-8")
    print(f"  01_suppliers.csv: {len(df_suppliers)} records written")

    # Step 3 — Write 02_parts.csv
    df_parts = pd.DataFrame(parts)[
        ["part_id", "description", "category", "unit_price", "unit", "preferred_supplier_id"]
    ]
    df_parts.to_csv(output_dir / "02_parts.csv", index=False, encoding="utf-8")
    print(f"  02_parts.csv: {len(df_parts)} records written")

    # Step 4 — Generate 03_contracts.csv
    # Build supplier lookup for payment terms
    supplier_map = {s["supplier_id"]: s for s in suppliers}
    terms_map = {"Net-30": 30, "Net-45": 45, "Net-60": 60}

    # Group parts by supplier, pick 4 per supplier
    parts_by_supplier: dict[str, list[dict]] = {}
    for p in parts:
        sid = p["preferred_supplier_id"]
        parts_by_supplier.setdefault(sid, []).append(p)

    today = date.today()
    contracts = []
    contract_idx = 1

    for supplier_id in sorted(parts_by_supplier.keys()):
        supplier_parts = parts_by_supplier[supplier_id]
        # Pick 4 parts per supplier
        selected = supplier_parts[:4] if len(supplier_parts) >= 4 else supplier_parts

        for part in selected:
            # agreed_price: unit_price ± 0-3% variation
            variation = random.uniform(-0.03, 0.03)
            agreed_price = round(part["unit_price"] * (1 + variation), 2)

            # payment_terms_days consistent with supplier
            payment_terms = supplier_map[supplier_id]["payment_terms"]
            payment_terms_days = terms_map[payment_terms]

            # valid_from: random between 2024-01-01 and 2025-06-01
            start_range = date(2024, 1, 1)
            end_range = date(2025, 6, 1)
            days_range = (end_range - start_range).days
            valid_from = start_range + timedelta(days=random.randint(0, days_range))

            # valid_to calculation based on distribution
            roll = random.random()
            if roll < 0.70:
                # 70% — 24 months (active)
                valid_to = valid_from + timedelta(days=730)
            elif roll < 0.85:
                # 15% — 12 months (recently expired)
                valid_to = valid_from + timedelta(days=365)
            else:
                # 15% — 36 months (long active)
                valid_to = valid_from + timedelta(days=1095)

            incoterm = random.choice(["DDP", "DAP", "EXW"])
            penalty_pct = random.choice([1.0, 1.5, 2.0])
            status = "ACTIVE" if valid_to >= today else "EXPIRED"

            contracts.append({
                "contract_id": f"CON-{contract_idx:04d}",
                "supplier_id": supplier_id,
                "part_id": part["part_id"],
                "agreed_price": agreed_price,
                "payment_terms_days": payment_terms_days,
                "valid_from": valid_from.isoformat(),
                "valid_to": valid_to.isoformat(),
                "incoterm": incoterm,
                "penalty_pct": penalty_pct,
                "status": status,
            })
            contract_idx += 1

    df_contracts = pd.DataFrame(contracts)
    df_contracts.to_csv(output_dir / "03_contracts.csv", index=False, encoding="utf-8")

    n_active = sum(1 for c in contracts if c["status"] == "ACTIVE")
    n_expired = sum(1 for c in contracts if c["status"] == "EXPIRED")
    print(f"  03_contracts.csv: {len(contracts)} records written")
    print(f"  Contracts created: {n_active} active, {n_expired} expired")
