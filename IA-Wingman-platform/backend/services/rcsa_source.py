"""Where the RCSA rows come from — and the one thing the domain must not learn.

Excel today, an MCP connection to the risk system later. Everything above this
module sees a grid of strings and a list of header candidates; nothing above it
knows what a worksheet is.

The header is the hard part, and it is hard for a reason that only shows up in a
real export. A bank's RCSA does not start with its column names. It starts with a
title block — "Risk Assessment", "Business Unit", "Assessment year" — and the
header underneath it is banded and multi-row: a merged group cell reading
"Inherent Risk Rating (before controls)" spanning several columns, a "Likelihood"
cell spanning three of those, and only then the names that actually label a
column. Reading row 1 gets you the word "Risk Assessment" and nothing else.

So this module proposes and never decides. `header_candidates` ranks the rows
that could be a header; a person picks in the UI, and their pick becomes part of
the template. A merged group cell is expanded across **the range it actually
covers**, read from the sheet, so a column reads as "Inherent Risk Rating ·
Likelihood · Impact". That is also the only way the two residual bands in that
export stay distinguishable, since each contains a column simply called
"Likelihood".

Carrying a band rightwards until the next one starts would have been easier and
is wrong: the last band on a row has no next one, so its name runs off the end
and lands on every column after it. The sheet says where a merge stops. Reading
that is not more work than guessing, it is just less comfortable — openpyxl
exposes merged ranges only on a full load, so the preview pays for a full load
and the data pass, which needs no header, stays on the fast read-only one.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

#: How much of a sheet is read for a preview. Enough to see the shape; a full
#: import reads on from here.
PREVIEW_ROWS = 40
#: Beyond this a "sheet" is something other than an RCSA export, and reading it
#: whole would be a memory question rather than an audit one.
MAX_ROWS = 20_000
MAX_COLS = 120


class RcsaSource(Protocol):
    """The port. Excel now, a risk-system connection later."""

    def sheets(self, ref: str) -> list[str]: ...

    def grid(self, ref: str, sheet: str | None = None,
             limit: int = PREVIEW_ROWS) -> list[list[str]]: ...

    def preview(self, ref: str, sheet: str | None = None,
                limit: int = PREVIEW_ROWS) -> list[list[str]]: ...


def _clean(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    # Excel leaves these behind in exported templates; they are not data.
    return "" if text.lower() in {"none", "nan", "#n/a", "#ref!"} else text


class ExcelSource:
    """openpyxl, read-only and values-only — formulas are read as their results."""

    def sheets(self, ref: str) -> list[str]:
        import openpyxl

        wb = openpyxl.load_workbook(ref, read_only=True, data_only=True)
        try:
            return list(wb.sheetnames)
        finally:
            wb.close()

    def grid(self, ref: str, sheet: str | None = None,
             limit: int = PREVIEW_ROWS) -> list[list[str]]:
        import openpyxl

        wb = openpyxl.load_workbook(ref, read_only=True, data_only=True)
        try:
            ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb[wb.sheetnames[0]]
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= min(limit, MAX_ROWS):
                    break
                rows.append([_clean(c) for c in row[:MAX_COLS]])
            return _pad(rows)
        finally:
            wb.close()

    def preview(self, ref: str, sheet: str | None = None,
                limit: int = PREVIEW_ROWS) -> list[list[str]]:
        """The first rows with merged group cells expanded across their ranges.

        A full load rather than the read-only one, because openpyxl exposes
        merged ranges only there. It happens once per import, while a person is
        looking at the sheet, and it is the difference between reading the
        header and guessing it.
        """
        import openpyxl

        wb = openpyxl.load_workbook(ref, data_only=True)
        try:
            ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb[wb.sheetnames[0]]
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= min(limit, MAX_ROWS):
                    break
                rows.append([_clean(c) for c in row[:MAX_COLS]])
            merges = [(m.min_row, m.min_col, m.max_row, m.max_col)
                      for m in ws.merged_cells.ranges]
            return expand_merges(_pad(rows), merges)
        finally:
            wb.close()


class CsvSource:
    """A CSV has one sheet and no merged cells, which makes it the easy case —
    and the one a department mails you when the .xlsx is too large."""

    def sheets(self, ref: str) -> list[str]:
        return [Path(ref).stem]

    def grid(self, ref: str, sheet: str | None = None,
             limit: int = PREVIEW_ROWS) -> list[list[str]]:
        with open(ref, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.reader(fh)
            rows = []
            for i, row in enumerate(reader):
                if i >= min(limit, MAX_ROWS):
                    break
                rows.append([_clean(c) for c in row[:MAX_COLS]])
        return _pad(rows)

    def preview(self, ref: str, sheet: str | None = None,
                limit: int = PREVIEW_ROWS) -> list[list[str]]:
        # A CSV has no merged cells, so the preview is the grid.
        return self.grid(ref, sheet, limit)


def source_for(ref: str) -> RcsaSource:
    return CsvSource() if Path(ref).suffix.lower() == ".csv" else ExcelSource()


def _pad(rows: list[list[str]]) -> list[list[str]]:
    """Every row the same width, so a column index means the same thing in all
    of them. A ragged grid is how a mapping silently shifts by one column."""
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def expand_merges(rows: list[list[str]], merges: list[tuple[int, int, int, int]]) -> list[list[str]]:
    """Write a merged cell's value into every cell of its range.

    openpyxl reports a merged range as its value in the top-left cell and None
    in the rest, which is how "Inherent Risk Rating (before controls)" arrives
    over eight empty cells. Ranges are 1-based (min_row, min_col, max_row,
    max_col), as a spreadsheet counts.
    """
    out = [list(r) for r in rows]
    for min_row, min_col, max_row, max_col in merges:
        if min_row - 1 >= len(out):
            continue
        value = out[min_row - 1][min_col - 1] if min_col - 1 < len(out[min_row - 1]) else ""
        if not value:
            continue
        for r in range(min_row - 1, min(max_row, len(out))):
            for c in range(min_col - 1, min(max_col, len(out[r]))):
                out[r][c] = value
    return out


@dataclass
class HeaderCandidate:
    """A row that could be the header, and why it looks like one."""
    row: int                 # 1-based, as a spreadsheet counts
    filled: int
    score: float
    cells: list[str]


def header_candidates(grid: list[list[str]], limit: int = 4) -> list[HeaderCandidate]:
    """The rows most likely to name the columns, best first — a proposal.

    A header row is wide, wordy and not numeric, and the rows under it look
    different from it. None of that is certain, which is why this ranks rather
    than decides: the person confirming the template picks, and their pick is
    stored with it.
    """
    scored: list[HeaderCandidate] = []
    width = max((len(r) for r in grid), default=0) or 1

    for i, row in enumerate(grid):
        cells = [c for c in row if c]
        filled = len(cells)
        if filled < 2:
            continue
        numeric = sum(1 for c in cells if _is_number(c))
        wordy = sum(1 for c in cells if any(ch.isalpha() for ch in c))
        # Mostly words, hardly any numbers, and covering much of the width.
        score = (filled / width) * 2 + (wordy / filled) - (numeric / filled) * 2
        # A header is followed by rows of data, which are usually narrower and
        # carry numbers. Compare with the row below where there is one.
        if i + 1 < len(grid):
            below = [c for c in grid[i + 1] if c]
            if below and sum(1 for c in below if _is_number(c)) > numeric:
                score += 0.5
        scored.append(HeaderCandidate(row=i + 1, filled=filled, score=round(score, 3),
                                      cells=row))

    scored.sort(key=lambda c: (-c.score, c.row))
    return scored[:limit]


def _is_number(text: str) -> bool:
    try:
        float(text.replace(",", ".").replace("%", ""))
        return True
    except ValueError:
        return False


def column_names(grid: list[list[str]], header_rows: list[int]) -> list[str]:
    """Join the chosen header rows into one name per column.

    `header_rows` is 1-based and in sheet order, so ["Inherent Risk Rating",
    "Likelihood", "Impact"] becomes "Inherent Risk Rating · Likelihood · Impact".
    Group cells are carried rightwards first; empty parts are dropped, and a
    column whose every header cell is empty keeps a positional name rather than
    disappearing — an unnamed column is still a column, and hiding it would be
    the silent loss this module exists to prevent.
    """
    chosen = [grid[r - 1] for r in header_rows if 0 < r <= len(grid)]
    if not chosen:
        return []
    width = max(len(r) for r in chosen)
    names = []
    for col in range(width):
        parts, seen = [], set()
        for row in chosen:
            cell = row[col] if col < len(row) else ""
            # A group cell carried down to a row that repeats it adds nothing.
            if cell and cell not in seen:
                parts.append(cell)
                seen.add(cell)
        names.append(" · ".join(parts) if parts else f"Column {col + 1}")
    return names


def data_rows(grid: list[list[str]], header_rows: list[int]) -> list[tuple[int, list[str]]]:
    """Everything below the header, with its sheet row number.

    Blank rows are skipped; a row that is blank except for one cell is kept,
    because that is what a continuation line looks like and dropping it would
    lose an auditee's words.
    """
    start = max(header_rows) if header_rows else 0
    out = []
    for i in range(start, len(grid)):
        row = grid[i]
        if any(c for c in row):
            out.append((i + 1, row))
    return out
