def parse_amount(v):
    """Parse a number from an uploaded invoice cell."""
    if v is None or v == "":
        return None
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError as e:
        raise ValueError(f"unreadable number: {v}") from e
