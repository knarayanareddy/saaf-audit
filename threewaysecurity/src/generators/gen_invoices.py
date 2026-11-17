"""Invoice generator — JSON data + PDF documents with error injection."""

import json
import random
from datetime import timedelta
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def _build_pdf(invoice: dict, output_path: Path) -> None:
    """Generate a professional A4 invoice PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle", parent=styles["Title"], fontSize=24, alignment=2
    )
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, textColor=colors.grey)

    elements = []

    # Header: supplier name (left) | FACTUUR (right)
    header_data = [
        [
            Paragraph(f"<b>{invoice['supplier_name']}</b><br/>{invoice.get('supplier_city', '')}", normal),
            Paragraph("INVOICE", title_style),
        ]
    ]
    header_table = Table(header_data, colWidths=[10 * cm, 7 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Invoice details
    details_data = [
        ["Invoice No:", invoice["invoice_id"]],
        ["Date:", invoice["invoice_date"]],
        ["Due Date:", invoice["due_date"]],
        ["PO Reference:", invoice["po_ref"]],
    ]
    details_table = Table(details_data, colWidths=[4 * cm, 13 * cm])
    details_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.3 * cm))

    # Supplier info
    supplier_info = [
        ["IBAN:", invoice["iban"]],
        ["VAT Number:", invoice["vat_number"]],
    ]
    si_table = Table(supplier_info, colWidths=[4 * cm, 13 * cm])
    si_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(si_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Line items table
    line_data = [
        ["Part-ID", "Description", "Qty", "Unit Price (EUR)", "Total (EUR)"],
        [
            invoice["part_id"],
            invoice["part_description"],
            str(invoice["quantity"]),
            f"{invoice['unit_price']:,.2f}",
            f"{invoice['total_amount']:,.2f}",
        ],
    ]
    line_table = Table(line_data, colWidths=[2.5 * cm, 6.5 * cm, 2 * cm, 3.5 * cm, 3.5 * cm])
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.3 * cm))

    # Totals
    totals_data = [
        ["", "", "Subtotal:", f"{invoice['total_amount']:,.2f} EUR"],
        ["", "", "VAT (21%):", f"{invoice['vat_amount']:,.2f} EUR"],
        ["", "", "Total incl. VAT:", f"{invoice['total_incl_vat']:,.2f} EUR"],
    ]
    totals_table = Table(totals_data, colWidths=[2.5 * cm, 6.5 * cm, 5 * cm, 4 * cm])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (2, 2), (2, 2), "Helvetica-Bold"),
        ("FONTNAME", (3, 2), (3, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (2, 2), (-1, 2), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 1 * cm))

    # Payment instruction
    elements.append(Paragraph(
        f"<b>Please transfer before {invoice['due_date']}</b>",
        normal,
    ))
    elements.append(Spacer(1, 2 * cm))

    # Footer disclaimer
    elements.append(Paragraph(
        "This is a synthetic test invoice — no fiscal value",
        small,
    ))

    doc.build(elements)


def generate_all(settings: dict) -> None:
    """Generate 200 invoices (JSON + PDF) with error injection per settings."""
    seed = settings["seed"]
    random.seed(seed)

    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]
    invoice_dir = root / settings["invoice_dir"]
    invoice_dir.mkdir(parents=True, exist_ok=True)

    # Load source data
    df_po = pd.read_csv(output_dir / "04_purchase_orders.csv")
    df_grn = pd.read_csv(output_dir / "05_goods_receipts.csv")
    df_contracts = pd.read_csv(output_dir / "03_contracts.csv")
    df_suppliers = pd.read_csv(output_dir / "01_suppliers.csv")
    df_parts = pd.read_csv(output_dir / "02_parts.csv")

    supplier_map = df_suppliers.set_index("supplier_id").to_dict("index")
    parts_map = df_parts.set_index("part_id").to_dict("index")
    po_list = df_po.to_dict("records")
    grn_map = df_grn.set_index("po_id").to_dict("index")
    contracts_map = {}
    for _, row in df_contracts.iterrows():
        key = (row["supplier_id"], row["part_id"])
        contracts_map.setdefault(key, []).append(row.to_dict())

    # Determine error distribution
    n_invoices = settings["n_invoices"]
    split = settings["invoice_split"]
    n_correct = int(n_invoices * split["correct"])
    n_price = int(n_invoices * split["price_error"])
    n_qty = int(n_invoices * split["quantity_error"])
    n_expired = int(n_invoices * split["contract_expired"])
    n_combo = n_invoices - n_correct - n_price - n_qty - n_expired

    error_types = (
        ["correct"] * n_correct
        + ["price_error"] * n_price
        + ["quantity_error"] * n_qty
        + ["contract_expired"] * n_expired
        + ["combo_error"] * n_combo
    )
    random.shuffle(error_types)

    # Find expired contracts for contract_expired errors
    expired_contracts = df_contracts[df_contracts["status"] == "EXPIRED"].to_dict("records")

    mag = settings["error_magnitude"]
    index_records = []
    counts = {"correct": 0, "price_error": 0, "quantity_error": 0, "contract_expired": 0, "combo_error": 0}

    for i in range(n_invoices):
        error_type = error_types[i]
        counts[error_type] += 1
        invoice_id = f"INV-2025-{i + 1:05d}"

        # For contract_expired, use an expired contract and its corresponding PO
        if error_type == "contract_expired" and expired_contracts:
            exp_contract = random.choice(expired_contracts)
            # Find a PO for this supplier/part or use any PO
            matching_pos = [p for p in po_list if p["supplier_id"] == exp_contract["supplier_id"]]
            if not matching_pos:
                matching_pos = po_list
            po = random.choice(matching_pos)
        else:
            po = po_list[i % len(po_list)]

        grn = grn_map.get(po["po_id"], {})
        supplier = supplier_map.get(po["supplier_id"], {})
        part = parts_map.get(po["part_id"], {})

        # Find contract for this PO
        contract_key = (po["supplier_id"], po["part_id"])
        contract_list = contracts_map.get(contract_key, [])
        if error_type == "contract_expired" and expired_contracts:
            contract = exp_contract
        elif contract_list:
            # Prefer active contracts
            active = [c for c in contract_list if c["status"] == "ACTIVE"]
            contract = active[0] if active else contract_list[0]
        else:
            contract = {"contract_id": "UNKNOWN", "agreed_price": po["unit_price"],
                        "payment_terms_days": 30, "valid_from": "2024-01-01",
                        "valid_to": "2026-12-31"}

        agreed_price = float(contract["agreed_price"])
        received_qty = int(grn.get("received_quantity", po["quantity"]))
        receipt_date = pd.Timestamp(grn.get("receipt_date", po["expected_delivery_date"]))
        payment_terms_days = int(contract.get("payment_terms_days", 30))

        # Apply error injection
        if error_type == "correct":
            quantity = received_qty
            unit_price = agreed_price
        elif error_type == "price_error":
            quantity = received_qty
            deviation_pct = random.uniform(mag["price_min_pct"], mag["price_max_pct"])
            if mag["price_direction"] == "both":
                direction = random.choice([1, -1])
            elif mag["price_direction"] == "over":
                direction = 1
            else:
                direction = -1
            unit_price = round(agreed_price * (1 + direction * deviation_pct / 100), 2)
        elif error_type == "quantity_error":
            delta = random.randint(mag["quantity_delta_min"], mag["quantity_delta_max"])
            direction = random.choice([1, -1])
            quantity = max(1, received_qty + direction * delta)
            unit_price = agreed_price
        elif error_type == "contract_expired":
            quantity = received_qty
            unit_price = agreed_price
        elif error_type == "combo_error":
            # Both price and quantity error
            deviation_pct = random.uniform(mag["price_min_pct"], mag["price_max_pct"])
            direction_p = random.choice([1, -1])
            unit_price = round(agreed_price * (1 + direction_p * deviation_pct / 100), 2)
            delta = random.randint(mag["quantity_delta_min"], mag["quantity_delta_max"])
            direction_q = random.choice([1, -1])
            quantity = max(1, received_qty + direction_q * delta)
        else:
            quantity = received_qty
            unit_price = agreed_price

        total_amount = round(quantity * unit_price, 2)
        invoice_date = receipt_date + timedelta(days=random.randint(1, 5))

        # For expired contracts, ensure invoice_date falls outside valid_to
        if error_type == "contract_expired":
            valid_to = pd.Timestamp(contract["valid_to"])
            if invoice_date <= valid_to:
                invoice_date = valid_to + timedelta(days=random.randint(10, 60))

        due_date = invoice_date + timedelta(days=payment_terms_days)
        vat_amount = round(total_amount * 0.21, 2)
        total_incl_vat = round(total_amount + vat_amount, 2)

        invoice = {
            "invoice_id": invoice_id,
            "supplier_id": po["supplier_id"],
            "supplier_name": supplier.get("name", ""),
            "supplier_city": supplier.get("city", ""),
            "part_id": po["part_id"],
            "part_description": part.get("description", ""),
            "po_ref": po["po_id"],
            "grn_ref": grn.get("grn_id", f"GRN-2025-{i + 1:05d}") if isinstance(grn.get("grn_id"), str) else f"GRN-2025-{i + 1:05d}",
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "iban": supplier.get("iban", ""),
            "vat_number": supplier.get("vat_number", ""),
            "vat_amount": vat_amount,
            "total_incl_vat": total_incl_vat,
            "currency": "EUR",
            "invoice_status": "PENDING",
            "error_injected": error_type,
        }

        # Write JSON
        json_path = invoice_dir / f"{invoice_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(invoice, f, indent=2, ensure_ascii=False)

        # Write PDF
        pdf_path = invoice_dir / f"{invoice_id}.pdf"
        _build_pdf(invoice, pdf_path)

        # Index record
        contract_id = contract.get("contract_id", contract.get("contract_id", "UNKNOWN"))
        index_records.append({
            "invoice_id": invoice_id,
            "supplier_id": po["supplier_id"],
            "part_id": po["part_id"],
            "po_ref": po["po_id"],
            "grn_ref": invoice["grn_ref"],
            "error_type": error_type,
            "invoice_date": invoice["invoice_date"],
            "unit_price": unit_price,
            "quantity": quantity,
            "total_amount": total_amount,
            "contract_id": contract_id,
        })

    # Write index CSV
    df_index = pd.DataFrame(index_records)
    df_index.to_csv(output_dir / "invoices_index.csv", index=False, encoding="utf-8")

    print(f"  invoices_index.csv: {len(df_index)} records written")
    print(f"  Invoices generated: {n_invoices} total — "
          f"{counts['correct']} correct, {counts['price_error']} price, "
          f"{counts['quantity_error']} qty, {counts['contract_expired']} expired, "
          f"{counts['combo_error']} combo")
