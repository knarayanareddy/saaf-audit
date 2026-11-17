# ============================================================================
# 4. Output schrijven
# ============================================================================
# Converteert het extractieresultaat naar de twee uitvoerformaten van de tool.

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pathlib import Path
from models import Control, ExtractionResult


# ============================================================================
# 4a. Basic definitions and constraints
# ============================================================================
 
XLSX_HEADERS = [
    "control_id", "domain", "who", "what", "why", "when", "where", "how",
    "source_anchors", "evidence_hints", "confidence", "open_questions",
]

COLUMN_WIDTHS = [15, 12, 20, 50, 35, 20, 25, 40, 40, 35, 12, 45]

CONFIDENCE_COLORS = {"High": "C6EFCE", "Medium": "FFEB9C", "Low": "FFC7CE"}

# ============================================================================
# 4b. Output schrijven naar JSON en XLSX
# ============================================================================

# Hulpfuncties voor serialisatie en spreadsheet-opbouw.
def control_to_row(c: Control) -> list:
    return [
        c.control_id,
        c.domain,
        c.who,
        c.what,
        c.why,
        c.when,
        c.where,
        c.how,
        "; ".join(f"{a.section}: «{a.quote}»" for a in c.source_anchors),
        "; ".join(c.evidence_hints),
        c.confidence,
        "; ".join(c.open_questions),
    ]


def write_json(result: ExtractionResult, path: Path) -> None:
    # JSON blijft het meest complete en machine-leesbare resultaat.
    path.write_text(result.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")


def write_xlsx(result: ExtractionResult, path: Path) -> None:
    # XLSX maakt review door eindgebruikers makkelijker met opmaak en kleurcodering.
    wb = Workbook()
    ws = wb.active
    ws.title = "Controls"

    header_fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_idx, header in enumerate(XLSX_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True)

    for row_idx, control in enumerate(result.controls, start=2):
        for col_idx, value in enumerate(control_to_row(control), start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if XLSX_HEADERS[col_idx - 1] == "confidence":
                color = CONFIDENCE_COLORS.get(control.confidence, "FFFFFF")
                cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

    wb.save(path)