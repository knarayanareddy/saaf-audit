import math


def parse_amount(v):
    """Parse a number from an uploaded invoice cell; reject NaN/inf."""
    if v is None or v == "":
        return None
    s = str(v).strip().replace(",", ".")
    try:
        x = float(s)
    except ValueError as e:
        raise ValueError(f"unreadable number: {v}") from e
    if not math.isfinite(x):
        raise ValueError(f"non-finite number: {v}")
    return x
