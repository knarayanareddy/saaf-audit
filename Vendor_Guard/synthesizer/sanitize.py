"""
Spreadsheet formula-injection guards.

Finding text is model output derived from vendor documents, i.e. attacker-influenced.
A cell starting with "=", "+", "-", "@" (or a tab/CR) can be executed as a formula
when the CSV is opened in Excel or Google Sheets (OWASP: CSV Injection).
"""

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Prefix risky strings with an apostrophe so spreadsheets treat them as text."""
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def set_text_cell(ws, row: int, column: int, value):
    """Write a cell, forcing strings to be stored as text rather than formulas.
    openpyxl otherwise stores any string starting with "=" as a formula."""
    cell = ws.cell(row=row, column=column, value=value)
    if isinstance(value, str):
        cell.data_type = "s"
    return cell
