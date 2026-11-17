"""Escalation agent — Step 06.

Routes blocked/flagged invoices to responsible teams.
Tracks SLA compliance. Never auto-approves on timeout.

OWASP mitigations:
- A01: Escalation routing matrix enforced
- A04: SLA tracking prevents forgotten escalations
- A09: All escalation actions logged
"""

import json
from datetime import datetime, timedelta, timezone, date as dt_date
from pathlib import Path


ESCALATION_MATRIX: dict[str, dict] = {
    "ESCALATE_PROCUREMENT": {
        "recipient": "Procurement Manager",
        "team": "Procurement",
        "sla_days": 5,
    },
    "ESCALATE_LOGISTICS": {
        "recipient": "Logistics Controller",
        "team": "Logistics",
        "sla_days": 5,
    },
    "ESCALATE_LEGAL": {
        "recipient": "Legal / Contract Manager",
        "team": "Legal",
        "sla_days": 3,
    },
    "BLOCK_COMBO": {
        "recipient": "Senior Procurement Manager + Legal",
        "team": "Procurement + Legal",
        "sla_days": 3,
    },
    "FLAG_FINANCE": {
        "recipient": "Finance Controller",
        "team": "Finance",
        "sla_days": 5,
    },
}


def run(settings: dict) -> dict:
    """Generate escalation notifications and register."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]

    # Load decisions
    with open(output_dir / "decisions.json", encoding="utf-8") as f:
        decisions = json.load(f)

    escalations: list[dict] = []
    counts = {"OPEN": 0, "OVERDUE": 0}
    today = dt_date.today()

    for record in decisions:
        decision = record.get("decision", "")
        action = record.get("action", "")

        # Only escalate BLOCK and FLAG decisions
        if decision not in ("BLOCK", "FLAG"):
            continue

        route = ESCALATION_MATRIX.get(action)
        if route is None:
            continue

        inv_id = record.get("invoice_id", "")
        decision_ts = record.get("decision_timestamp", "")

        # Calculate SLA deadline
        try:
            decision_dt = datetime.fromisoformat(decision_ts).date()
        except (ValueError, TypeError):
            decision_dt = today
        sla_deadline = decision_dt + timedelta(days=route["sla_days"])

        # Determine status
        if today > sla_deadline:
            escalation_status = "OVERDUE"
            counts["OVERDUE"] += 1
        else:
            escalation_status = "OPEN"
            counts["OPEN"] += 1

        escalation = {
            "escalation_id": f"ESC-{inv_id.replace('INV-', '')}",
            "invoice_id": inv_id,
            "supplier_id": record.get("supplier_id", ""),
            "error_type": action,
            "severity": "HIGH" if decision == "BLOCK" else "MEDIUM",
            "delta_pct": record.get("delta_pct", 0.0),
            "qty_delta_grn": record.get("qty_delta_grn", 0),
            "contract_ref": record.get("matched_contract_id", ""),
            "motivation": record.get("motivation", ""),
            "recipient": route["recipient"],
            "team": route["team"],
            "sla_days": route["sla_days"],
            "decision_date": str(decision_dt),
            "sla_deadline": str(sla_deadline),
            "escalation_status": escalation_status,
            "reminder_sent": escalation_status == "OVERDUE",
            "auto_approved": False,  # NEVER auto-approve on timeout
            "resolution": None,
            "resolution_date": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        escalations.append(escalation)

    # Write output
    output_path = output_dir / "escalation_register.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(escalations, f, indent=2, ensure_ascii=False)

    print(f"  escalation_register.json: {len(escalations)} escalations")
    print(f"  Escalation: {counts['OPEN']} open, {counts['OVERDUE']} overdue")
    if counts["OVERDUE"] > 0:
        print(f"  WARNING: {counts['OVERDUE']} escalations exceeded SLA deadline")

    return counts
