DEFAULT_PRICE_TOLERANCE = 0.01


def match_line(po_price, inv_price, price_tolerance=DEFAULT_PRICE_TOLERANCE):
    issues = []
    if po_price is not None and inv_price is not None and abs(inv_price - po_price) > price_tolerance:
        issues.append("PRICE_MISMATCH")
    return "FAIL" if issues else "MATCH"
