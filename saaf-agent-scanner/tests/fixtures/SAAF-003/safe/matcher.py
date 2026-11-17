def check_line(po_l, inv_l, add, tol=0.01):
    po_qty = po_l.get("quantity")
    inv_qty = inv_l.get("quantity")
    po_price = po_l.get("unit_price")
    inv_price = inv_l.get("unit_price")
    if po_qty is None or inv_qty is None:
        add("quantity_missing", "FAIL")
    elif abs(inv_qty - po_qty) > tol:
        add("qty_billed_vs_po", "FAIL")
    if po_price is not None and inv_price is not None and abs(inv_price - po_price) > tol:
        add("price_differs", "FAIL")
    else:
        add("price_not_comparable", "WARNING")
    return "MATCH"


def compare_totals(expected, actual, tolerance=0.5):
    if expected is None or actual is None:
        return "FAIL"
    return "PASS" if abs(expected - actual) <= tolerance else "FAIL"
