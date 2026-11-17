import json


def _refuse(c):
    raise ValueError("NaN/Infinity not allowed: " + c)


def check_totals(payload: str, tolerance: float = 0.05):
    data = json.loads(payload, parse_constant=_refuse)
    diff = data["invoice_total"] - data["po_total"]
    if not (abs(diff) <= tolerance):
        return "DISCREPANCY"
    return "OK"
