import json


def check_totals(payload: str, tolerance: float = 0.05):
    data = json.loads(payload)
    diff = data["invoice_total"] - data["po_total"]
    if abs(diff) > tolerance:
        return "DISCREPANCY"
    return "OK"
