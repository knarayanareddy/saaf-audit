"""Contract matching agent — links invoices to valid contracts."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def run(settings: dict) -> dict:
    """Match parsed invoices to contracts and produce matched_contracts.json."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]

    # Load inputs
    with open(output_dir / "parsed_records.json", encoding="utf-8") as f:
        parsed_records = json.load(f)

    df_contracts = pd.read_csv(output_dir / "03_contracts.csv")

    # Build contract lookup: (supplier_id, part_id) -> list of contracts
    contract_lookup: dict[tuple[str, str], list[dict]] = {}
    for _, row in df_contracts.iterrows():
        key = (row["supplier_id"], row["part_id"])
        contract_lookup.setdefault(key, []).append(row.to_dict())

    matched_records = []
    counts = {"MATCHED": 0, "CONTRACT_EXPIRED": 0, "CONTRACT_NOT_FOUND": 0, "SKIPPED": 0}

    for record in parsed_records:
        # Skip INTAKE_FAILED records
        if record.get("intake_status") != "PARSED":
            record["contract_status"] = "SKIPPED"
            matched_records.append(record)
            counts["SKIPPED"] += 1
            continue

        key = (record["supplier_id"], record["part_id"])
        contracts = contract_lookup.get(key, [])

        if not contracts:
            record["contract_status"] = "CONTRACT_NOT_FOUND"
            record["matched_contract_id"] = None
            record["agreed_price"] = None
            record["contract_payment_terms_days"] = None
            record["incoterm"] = None
            record["penalty_pct"] = None
            record["contract_valid_from"] = None
            record["contract_valid_to"] = None
            matched_records.append(record)
            counts["CONTRACT_NOT_FOUND"] += 1
            continue

        invoice_date = pd.Timestamp(record["invoice_date"])

        # Try to find an active contract where invoice_date is within validity
        matched = False
        for contract in contracts:
            valid_from = pd.Timestamp(contract["valid_from"])
            valid_to = pd.Timestamp(contract["valid_to"])

            if valid_from <= invoice_date <= valid_to:
                record["contract_status"] = "MATCHED"
                record["matched_contract_id"] = contract["contract_id"]
                record["agreed_price"] = contract["agreed_price"]
                record["contract_payment_terms_days"] = contract["payment_terms_days"]
                record["incoterm"] = contract["incoterm"]
                record["penalty_pct"] = contract["penalty_pct"]
                record["contract_valid_from"] = contract["valid_from"]
                record["contract_valid_to"] = contract["valid_to"]
                matched_records.append(record)
                counts["MATCHED"] += 1
                matched = True
                break

        if not matched:
            # Contract exists but is expired
            # Use the most recent contract
            most_recent = max(contracts, key=lambda c: c["valid_to"])
            record["contract_status"] = "CONTRACT_EXPIRED"
            record["matched_contract_id"] = most_recent["contract_id"]
            record["agreed_price"] = most_recent["agreed_price"]
            record["contract_payment_terms_days"] = most_recent["payment_terms_days"]
            record["incoterm"] = most_recent["incoterm"]
            record["penalty_pct"] = most_recent["penalty_pct"]
            record["contract_valid_from"] = most_recent["valid_from"]
            record["contract_valid_to"] = most_recent["valid_to"]
            matched_records.append(record)
            counts["CONTRACT_EXPIRED"] += 1

    # Write output
    output_path = output_dir / "matched_contracts.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(matched_records, f, indent=2, ensure_ascii=False)

    print(f"  matched_contracts.json: {len(matched_records)} records written")
    print(f"  Contract match: {counts['MATCHED']} matched, "
          f"{counts['CONTRACT_EXPIRED']} expired, "
          f"{counts['CONTRACT_NOT_FOUND']} not found, "
          f"{counts['SKIPPED']} skipped")

    return counts
