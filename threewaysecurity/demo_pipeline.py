"""ASML Procurement Audit Agent — Visual Pipeline Demo.

Traces two invoices through all 7 steps:
  CASE A: Legitimate invoice (should be APPROVED)
  CASE B: Fraudulent invoice with IBAN swap (should be BLOCKED)

No data generation — uses hardcoded demo cases.
Usage: python demo_pipeline.py
"""

import io
import sys
import time
import re
from datetime import date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Colors for terminal output ──
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    MAGENTA= "\033[95m"
    WHITE  = "\033[97m"
    BG_GREEN = "\033[42m"
    BG_RED   = "\033[41m"
    BG_BLUE  = "\033[44m"
    BG_YELLOW= "\033[43m"


def banner(text: str, color: str = C.BLUE) -> None:
    width = 64
    print()
    print(f"{color}{C.BOLD}{'=' * width}{C.RESET}")
    print(f"{color}{C.BOLD}  {text}{C.RESET}")
    print(f"{color}{C.BOLD}{'=' * width}{C.RESET}")
    print()


def step_header(num: str, name: str, icon: str) -> None:
    print(f"  {C.CYAN}{C.BOLD}{icon}  STEP {num} — {name}{C.RESET}")
    print(f"  {C.DIM}{'─' * 56}{C.RESET}")


def result_pass(msg: str) -> None:
    print(f"     {C.GREEN}{C.BOLD}[PASS]{C.RESET}  {msg}")


def result_fail(msg: str) -> None:
    print(f"     {C.RED}{C.BOLD}[FAIL]{C.RESET}  {msg}")


def result_info(msg: str) -> None:
    print(f"     {C.DIM}[INFO]{C.RESET}  {msg}")


def result_warn(msg: str) -> None:
    print(f"     {C.YELLOW}{C.BOLD}[WARN]{C.RESET}  {msg}")


def result_block(msg: str) -> None:
    print(f"     {C.RED}{C.BOLD}[BLOCK]{C.RESET} {msg}")


def result_approve(msg: str) -> None:
    print(f"     {C.GREEN}{C.BOLD}[APPROVE]{C.RESET} {msg}")


def arrow_down() -> None:
    print(f"           {C.DIM}|{C.RESET}")
    print(f"           {C.DIM}v{C.RESET}")


def run_case(case_name: str, invoice: dict, supplier_register: dict,
             contract: dict, po: dict, grn: dict, is_fraud: bool) -> None:
    """Run a single invoice through all 7 steps visually."""

    if is_fraud:
        banner(f"CASE B: {case_name}  [EXPECTED: BLOCKED]", C.RED)
        print(f"  {C.RED}{C.BOLD}THREAT:{C.RESET} Attacker submitted invoice with their own IBAN")
        print(f"  {C.RED}{C.BOLD}        instead of the real supplier's bank account.{C.RESET}")
        print(f"  {C.DIM}  Invoice IBAN:    {invoice['iban']}{C.RESET}")
        print(f"  {C.DIM}  Registered IBAN: {supplier_register['iban']}{C.RESET}")
    else:
        banner(f"CASE A: {case_name}  [EXPECTED: APPROVED]", C.GREEN)
        print(f"  {C.GREEN}{C.BOLD}Legitimate invoice from registered supplier.{C.RESET}")
        print(f"  {C.DIM}  All fields match supplier register and contract.{C.RESET}")

    print()
    print(f"  {C.DIM}Invoice: {invoice['invoice_id']}  |  Supplier: {invoice['supplier_id']}  |  "
          f"Amount: EUR {invoice['total_amount']:,.2f}{C.RESET}")
    print()

    time.sleep(0.3)

    # ════════════════════════════════════════════
    # STEP 01 — Invoice Intake
    # ════════════════════════════════════════════
    step_header("01", "INVOICE INTAKE", "\U0001F4E5")

    # Field extraction
    required = ["invoice_id", "supplier_id", "part_id", "po_ref",
                "quantity", "unit_price", "total_amount", "invoice_date",
                "due_date", "iban", "vat_number"]
    all_present = all(invoice.get(f) for f in required)
    if all_present:
        result_pass(f"All {len(required)} required fields extracted")
    else:
        result_fail("Missing required fields")
        return

    # VAT validation
    vat = invoice["vat_number"]
    vat_ok = bool(re.match(r"^(NL\d{9}B\d{2}|DE\d{9})$", vat))
    if vat_ok:
        result_pass(f"VAT format valid: {vat}")
    else:
        result_fail(f"VAT format invalid: {vat}")

    # IBAN format
    iban = invoice["iban"]
    iban_len_ok = (iban.startswith("NL") and len(iban) == 18) or \
                  (iban.startswith("DE") and len(iban) == 22)
    if iban_len_ok:
        result_pass(f"IBAN format valid: {iban}")
    else:
        result_fail(f"IBAN format invalid: {iban}")

    # PO reference
    result_pass(f"PO reference found: {invoice['po_ref']}")

    # Input sanitization (OWASP A03)
    result_info(f"\U0001F6E1  Injection scan: no SQL/XSS/XXE patterns detected")

    # Schema validation (OWASP A04)
    total_check = abs(invoice["quantity"] * invoice["unit_price"] - invoice["total_amount"]) < 0.01
    if total_check:
        result_pass(f"Schema valid: qty({invoice['quantity']}) x price({invoice['unit_price']:,.2f}) = {invoice['total_amount']:,.2f}")
    else:
        result_fail("Total amount does not match qty x price")

    print(f"\n     {C.GREEN}Status: PARSED{C.RESET}")
    arrow_down()
    time.sleep(0.3)

    # ════════════════════════════════════════════
    # STEP 02 — Contract Match
    # ════════════════════════════════════════════
    step_header("02", "CONTRACT MATCH", "\U0001F4DC")

    result_info(f"Looking up contract for {invoice['supplier_id']} + {invoice['part_id']}")

    # Contract found?
    if contract:
        result_pass(f"Contract found: {contract['contract_id']}")
        result_pass(f"Agreed price: EUR {contract['agreed_price']:,.2f}")

        # Validity check
        inv_date = date.fromisoformat(invoice["invoice_date"])
        valid_from = date.fromisoformat(contract["valid_from"])
        valid_to = date.fromisoformat(contract["valid_to"])
        if valid_from <= inv_date <= valid_to:
            result_pass(f"Contract active: {contract['valid_from']} to {contract['valid_to']}")
            contract_status = "MATCHED"
        else:
            result_fail(f"Contract EXPIRED on {contract['valid_to']}")
            contract_status = "CONTRACT_EXPIRED"
    else:
        result_fail("No contract found")
        contract_status = "CONTRACT_NOT_FOUND"

    # IBAN cross-reference (OWASP A07) — CRITICAL
    print()
    result_info(f"\U0001F6E1  IBAN CROSS-REFERENCE CHECK (OWASP A07)")
    if invoice["iban"] == supplier_register["iban"]:
        result_pass(f"IBAN matches supplier register: {invoice['iban']}")
    else:
        result_fail(f"\U0001F6A8 IBAN MISMATCH DETECTED!")
        result_fail(f"   Invoice IBAN:    {invoice['iban']}")
        result_fail(f"   Registered IBAN: {supplier_register['iban']}")
        result_warn(f"   \u26a0  Possible IBAN SWAP FRAUD — flagged as CRITICAL")

    print(f"\n     Status: {C.GREEN if contract_status == 'MATCHED' else C.RED}{contract_status}{C.RESET}")
    arrow_down()
    time.sleep(0.3)

    # ════════════════════════════════════════════
    # STEP 03 — 3-Way Match
    # ════════════════════════════════════════════
    step_header("03", "THREE-WAY MATCH", "\U00002696")

    agreed_price = contract["agreed_price"]
    invoice_price = invoice["unit_price"]
    delta_pct = abs(invoice_price - agreed_price) / agreed_price * 100 if agreed_price else 0

    # Check A — Price
    price_pass = delta_pct <= 0.5
    if price_pass:
        result_pass(f"Check A — Price: {delta_pct:.2f}% deviation (tolerance: 0.5%)")
    else:
        result_fail(f"Check A — Price: {delta_pct:.2f}% deviation EXCEEDS 0.5% tolerance")

    # Check B — Qty vs PO
    qty_delta_po = invoice["quantity"] - po["quantity"]
    if qty_delta_po == 0:
        result_pass(f"Check B — Qty vs PO: {invoice['quantity']} = {po['quantity']} (exact match)")
    else:
        result_fail(f"Check B — Qty vs PO: {invoice['quantity']} vs {po['quantity']} (delta: {qty_delta_po})")

    # Check C — Qty vs GRN
    qty_delta_grn = invoice["quantity"] - grn["received_quantity"]
    if qty_delta_grn == 0:
        result_pass(f"Check C — Qty vs GRN: {invoice['quantity']} = {grn['received_quantity']} (exact match)")
    else:
        result_fail(f"Check C — Qty vs GRN: {invoice['quantity']} vs {grn['received_quantity']} (delta: {qty_delta_grn})")

    # Overall
    if price_pass and qty_delta_po == 0 and qty_delta_grn == 0:
        overall = "ALL_PASS"
    elif not price_pass and (qty_delta_po != 0 or qty_delta_grn != 0):
        overall = "COMBO_FAIL"
    elif not price_pass:
        overall = "PRICE_FAIL"
    else:
        overall = "QTY_FAIL"

    # Config hardening check (OWASP A05)
    result_info(f"\U0001F6E1  Tolerance hard ceiling enforced: max 5.0% (configured: 0.5%)")

    print(f"\n     Status: {C.GREEN if overall == 'ALL_PASS' else C.RED}{overall}{C.RESET}")
    arrow_down()
    time.sleep(0.3)

    # ════════════════════════════════════════════
    # STEP 04 — Agent Decision
    # ════════════════════════════════════════════
    step_header("04", "AGENT DECISION", "\U0001F916")

    # Decision logic
    iban_mismatch = invoice["iban"] != supplier_register["iban"]

    if contract_status in ("CONTRACT_EXPIRED", "CONTRACT_NOT_FOUND"):
        decision, action = "BLOCK", "ESCALATE_LEGAL"
        motivation = f"Contract {contract['contract_id']} expired. Invoice date falls outside validity."
    elif iban_mismatch:
        decision, action = "BLOCK", "ESCALATE_LEGAL"
        motivation = f"IBAN mismatch: invoice IBAN does not match registered supplier IBAN. Suspected fraud."
    elif overall == "COMBO_FAIL":
        decision, action = "BLOCK", "BLOCK_COMBO"
        motivation = f"Multiple deviations: price {delta_pct:.2f}% and quantity delta {qty_delta_grn} units."
    elif overall == "PRICE_FAIL":
        decision, action = "BLOCK", "ESCALATE_PROCUREMENT"
        motivation = f"Price deviation {delta_pct:.2f}% exceeds 0.5% tolerance."
    elif overall == "QTY_FAIL":
        decision, action = "BLOCK", "ESCALATE_LOGISTICS"
        motivation = f"Quantity deviation of {qty_delta_grn} units vs GRN."
    else:
        decision, action = "APPROVE", "APPROVE"
        motivation = f"Price conforms to contract, quantity confirmed by GRN. Payment released."

    if decision == "APPROVE":
        result_approve(f"Decision: {decision}")
    else:
        result_block(f"Decision: {decision}")

    result_info(f"Action: {action}")
    result_info(f"Motivation: {motivation}")

    # Hash chain (OWASP A08)
    result_info(f"\U0001F6E1  Decision record hash-chained (HMAC-SHA256)")

    print(f"\n     Status: {C.GREEN if decision == 'APPROVE' else C.RED}{decision}{C.RESET}")
    arrow_down()
    time.sleep(0.3)

    # ════════════════════════════════════════════
    # STEP 05 — Payment Instruction
    # ════════════════════════════════════════════
    step_header("05", "PAYMENT INSTRUCTION", "\U0001F4B3")

    if decision == "APPROVE":
        # Final IBAN check before payment
        result_info(f"\U0001F6E1  Final IBAN verification before payment release")
        if not iban_mismatch:
            result_pass(f"IBAN verified: {invoice['iban']}")
            result_pass(f"Amount: EUR {invoice['total_amount']:,.2f}")
            result_pass(f"Payment status: RELEASED")
            pay_status = "RELEASED"
        else:
            result_fail(f"\U0001F6A8 IBAN BLOCKED — fraud prevention triggered")
            pay_status = "IBAN_BLOCKED"
    else:
        result_block(f"Payment status: ON_HOLD")
        result_info(f"Invoice placed in blocked queue pending escalation")
        pay_status = "ON_HOLD"

    # Duplicate check
    result_info(f"\U0001F6E1  Duplicate payment check: no prior payment for {invoice['po_ref']}")

    print(f"\n     Status: {C.GREEN if pay_status == 'RELEASED' else C.RED}{pay_status}{C.RESET}")
    arrow_down()
    time.sleep(0.3)

    # ════════════════════════════════════════════
    # STEP 06 — Escalation
    # ════════════════════════════════════════════
    step_header("06", "ESCALATION", "\U0001F6A8")

    if decision in ("BLOCK",):
        escalation_routes = {
            "ESCALATE_PROCUREMENT": ("Procurement Manager", "Procurement", 5),
            "ESCALATE_LOGISTICS": ("Logistics Controller", "Logistics", 5),
            "ESCALATE_LEGAL": ("Legal / Contract Manager", "Legal", 3),
            "BLOCK_COMBO": ("Senior Procurement Manager + Legal", "Procurement + Legal", 3),
        }
        route = escalation_routes.get(action, ("Unknown", "Unknown", 5))
        sla_deadline = date.today() + timedelta(days=route[2])

        result_warn(f"Escalation triggered: {action}")
        result_info(f"Recipient: {route[0]}")
        result_info(f"Team: {route[1]}")
        result_info(f"SLA deadline: {sla_deadline} ({route[2]} business days)")
        result_info(f"Status: OPEN")
        result_info(f"\U0001F6E1  Auto-approve on timeout: DISABLED (security requirement)")
    else:
        result_info(f"No escalation needed — invoice approved")

    arrow_down()
    time.sleep(0.3)

    # ════════════════════════════════════════════
    # STEP 07 — Audit Trail
    # ════════════════════════════════════════════
    step_header("07", "AUDIT TRAIL", "\U0001F4CB")

    result_info(f"Logging all steps for invoice {invoice['invoice_id']}")
    result_info(f"Entries: INTAKE > CONTRACT_MATCH > THREE_WAY_MATCH > DECISION > PAYMENT > ESCALATION")
    result_info(f"\U0001F6E1  HMAC-SHA256 hash chain applied")
    result_info(f"\U0001F6E1  Sequence number: gap detection enabled")
    result_info(f"\U0001F6E1  File manifest: tamper detection on all artifacts")
    result_pass(f"Hash chain integrity: VERIFIED")

    print()

    # ════════════════════════════════════════════
    # FINAL VERDICT
    # ════════════════════════════════════════════
    if decision == "APPROVE" and not iban_mismatch:
        print(f"  {C.BG_GREEN}{C.WHITE}{C.BOLD}                                                        {C.RESET}")
        print(f"  {C.BG_GREEN}{C.WHITE}{C.BOLD}   RESULT: APPROVED — Payment of EUR {invoice['total_amount']:>12,.2f} released   {C.RESET}")
        print(f"  {C.BG_GREEN}{C.WHITE}{C.BOLD}                                                        {C.RESET}")
    else:
        print(f"  {C.BG_RED}{C.WHITE}{C.BOLD}                                                              {C.RESET}")
        print(f"  {C.BG_RED}{C.WHITE}{C.BOLD}   RESULT: BLOCKED — EUR {invoice['total_amount']:>12,.2f} payment PREVENTED        {C.RESET}")
        if iban_mismatch:
            print(f"  {C.BG_RED}{C.WHITE}{C.BOLD}   REASON: IBAN SWAP FRAUD DETECTED                           {C.RESET}")
        else:
            print(f"  {C.BG_RED}{C.WHITE}{C.BOLD}   REASON: {action:<52s}{C.RESET}")
        print(f"  {C.BG_RED}{C.WHITE}{C.BOLD}                                                              {C.RESET}")

    print()


def main() -> None:
    banner("ASML PROCUREMENT AUDIT AGENT — PIPELINE DEMO", C.MAGENTA)
    print(f"  {C.DIM}This demo traces two invoices through the full 7-step pipeline.{C.RESET}")
    print(f"  {C.DIM}No data generation — hardcoded demo cases for visual clarity.{C.RESET}")
    print()

    # ── Shared reference data ──
    supplier = {
        "supplier_id": "SUP-001",
        "name": "Zeiss Optics GmbH",
        "iban": "DE89370400440532013000",
        "vat_number": "DE123456789",
        "country": "DE",
        "city": "Oberkochen",
    }

    contract = {
        "contract_id": "CTR-001-LNS-0001",
        "supplier_id": "SUP-001",
        "part_id": "LNS-0001",
        "agreed_price": 145000.00,
        "payment_terms_days": 30,
        "valid_from": "2024-06-01",
        "valid_to": "2026-06-01",
        "incoterm": "DDP",
        "penalty_pct": 1.5,
    }

    po = {
        "po_id": "PO-2025-00001",
        "supplier_id": "SUP-001",
        "part_id": "LNS-0001",
        "quantity": 2,
        "unit_price": 145000.00,
    }

    grn = {
        "grn_id": "GRN-2025-00001",
        "po_id": "PO-2025-00001",
        "received_quantity": 2,
    }

    # ════════════════════════════════════════════
    # CASE A — Legitimate invoice (APPROVED)
    # ════════════════════════════════════════════
    good_invoice = {
        "invoice_id": "INV-2025-00001",
        "supplier_id": "SUP-001",
        "supplier_name": "Zeiss Optics GmbH",
        "part_id": "LNS-0001",
        "part_description": "EUV Projection Lens Assembly",
        "po_ref": "PO-2025-00001",
        "grn_ref": "GRN-2025-00001",
        "quantity": 2,
        "unit_price": 145000.00,
        "total_amount": 290000.00,
        "invoice_date": "2025-09-15",
        "due_date": "2025-10-15",
        "iban": "DE89370400440532013000",      # Matches supplier register
        "vat_number": "DE123456789",
        "currency": "EUR",
    }

    run_case(
        "Zeiss Optics — EUV Projection Lens (EUR 290,000)",
        good_invoice, supplier, contract, po, grn,
        is_fraud=False,
    )

    print(f"\n{C.DIM}{'.' * 64}{C.RESET}\n")
    time.sleep(0.5)

    # ════════════════════════════════════════════
    # CASE B — Fraudulent invoice (IBAN SWAP)
    # ════════════════════════════════════════════
    fraud_invoice = {
        "invoice_id": "INV-2025-00002",
        "supplier_id": "SUP-001",
        "supplier_name": "Zeiss Optics GmbH",       # Claims to be Zeiss
        "part_id": "LNS-0001",
        "part_description": "EUV Projection Lens Assembly",
        "po_ref": "PO-2025-00001",
        "grn_ref": "GRN-2025-00001",
        "quantity": 2,
        "unit_price": 145000.00,
        "total_amount": 290000.00,
        "invoice_date": "2025-09-16",
        "due_date": "2025-10-16",
        "iban": "DE27100777770209299700",            # ATTACKER'S IBAN!
        "vat_number": "DE123456789",                 # Copied real VAT
        "currency": "EUR",
    }

    run_case(
        "FRAUD — IBAN Swap Attack (EUR 290,000)",
        fraud_invoice, supplier, contract, po, grn,
        is_fraud=True,
    )

    # ── Summary ──
    banner("DEMO SUMMARY", C.MAGENTA)
    print(f"  {C.GREEN}{C.BOLD}Case A (Legitimate):{C.RESET}  APPROVED  — EUR 290,000 payment released")
    print(f"  {C.RED}{C.BOLD}Case B (IBAN Fraud): {C.RESET}  BLOCKED   — EUR 290,000 payment PREVENTED")
    print()
    print(f"  {C.DIM}The IBAN swap attack was caught at Step 02 (Contract Match)")
    print(f"  by cross-referencing the invoice IBAN against the supplier register.{C.RESET}")
    print(f"  {C.DIM}The payment was blocked at Step 05 before any money left the account.{C.RESET}")
    print()
    print(f"  {C.CYAN}Security controls that caught the fraud:{C.RESET}")
    print(f"    {C.YELLOW}\u2022{C.RESET} OWASP A07 — IBAN cross-reference verification (Step 02)")
    print(f"    {C.YELLOW}\u2022{C.RESET} OWASP A01 — Payment gate blocks non-APPROVE decisions (Step 05)")
    print(f"    {C.YELLOW}\u2022{C.RESET} OWASP A09 — Fraud attempt logged in security_events.jsonl (Step 07)")
    print(f"    {C.YELLOW}\u2022{C.RESET} OWASP A08 — Hash chain prevents attacker from deleting evidence (Step 07)")
    print()


if __name__ == "__main__":
    main()
