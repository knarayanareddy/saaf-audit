"""Invoice intake agent — validates and parses incoming invoices."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def run(settings: dict) -> dict:
    """Validate all invoice JSONs and produce parsed_records.json."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]
    invoice_dir = root / settings["invoice_dir"]

    # Load PO register for po_ref validation
    df_po = pd.read_csv(output_dir / "04_purchase_orders.csv")
    valid_po_refs = set(df_po["po_id"].tolist())

    # VAT regex patterns
    vat_nl = re.compile(r"^NL\d{9}B\d{2}$")
    vat_de = re.compile(r"^DE\d{9}$")

    # Process all invoice JSONs
    json_files = sorted(invoice_dir.glob("INV-*.json"))
    parsed_records = []
    n_parsed = 0
    n_failed = 0

    for json_file in json_files:
        with open(json_file, encoding="utf-8") as f:
            invoice = json.load(f)

        errors: list[str] = []

        # 1. Check required fields
        required_fields = [
            "invoice_id", "supplier_id", "part_id", "po_ref",
            "quantity", "unit_price", "total_amount", "invoice_date",
            "due_date", "iban", "vat_number",
        ]
        for field in required_fields:
            if field not in invoice or invoice[field] is None or invoice[field] == "":
                errors.append(f"Missing required field: {field}")

        # 2. Validate VAT format
        vat = invoice.get("vat_number", "")
        if vat and not vat_nl.match(vat) and not vat_de.match(vat):
            errors.append(f"Invalid VAT format: {vat}")

        # 3. Validate PO reference exists
        po_ref = invoice.get("po_ref", "")
        if po_ref not in valid_po_refs:
            errors.append(f"PO reference not found: {po_ref}")

        # 4. Validate IBAN format
        iban = invoice.get("iban", "")
        if iban:
            if iban.startswith("NL") and len(iban) != 18:
                errors.append(f"Invalid NL IBAN length: {len(iban)} (expected 18)")
            elif iban.startswith("DE") and len(iban) != 22:
                errors.append(f"Invalid DE IBAN length: {len(iban)} (expected 22)")

        # 5. Determine status
        intake_status = "INTAKE_FAILED" if errors else "PARSED"

        if intake_status == "PARSED":
            n_parsed += 1
        else:
            n_failed += 1

        # 6. Build output record
        record = {**invoice}
        record["intake_status"] = intake_status
        record["intake_timestamp"] = datetime.now(timezone.utc).isoformat()
        record["validation_errors"] = errors

        parsed_records.append(record)

    # Write output
    output_path = output_dir / "parsed_records.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_records, f, indent=2, ensure_ascii=False)

    print(f"  parsed_records.json: {len(parsed_records)} records written")
    print(f"  Intake results: {n_parsed} PARSED, {n_failed} INTAKE_FAILED")

    return {"parsed": n_parsed, "failed": n_failed, "total": len(parsed_records)}
