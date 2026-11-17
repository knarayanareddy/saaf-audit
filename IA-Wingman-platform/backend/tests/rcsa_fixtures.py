"""Two RCSA exports that differ on purpose.

`photo_shape` is modelled on a real template: a title block above the header, a
banded multi-row header with merged group cells, two residual bands each with
their own Likelihood/Impact/Exposure, ratings written as "(4) Likely", and a
control column that holds a cross-reference rather than a description.

`other_shape` is the same audit content under a different template — other
names, other order, a deeper title block, one residual band, and ratings written
as bare words. If the mapping only works on the first, it is a hardcoded parser
with extra steps.
"""
from pathlib import Path


def _write(path: Path, rows: list[list[str]], merges: list[str] | None = None) -> str:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Risk Assessment"
    for row in rows:
        ws.append(row)
    for ref in merges or []:
        ws.merge_cells(ref)
    wb.save(path)
    return str(path)


def photo_shape(path: Path) -> str:
    """The shape of the real export, as far as its columns go."""
    rows = [
        ["Risk Assessment"],
        ["Business Unit", "Asset Management"],
        ["Assessment year", "2026"],
        [],
        # Band row: merged group cells over the columns they cover.
        ["", "", "", "", "", "", "",
         "Inherent Risk Rating (before controls)", "", "", "", "", "", "", "",
         "Residual Risk Rating during Change implementation", "", "", "",
         "Residual Risk rating when going live (Change to Run)", "", "", ""],
        # Sub-band row.
        ["", "", "", "", "", "", "",
         "Likelihood", "", "", "", "", "", "", "",
         "", "", "", "",
         "", "", "", ""],
        # The header itself.
        ["Risk ID", "(Sub)process", "Risk title", "ORX Risk event level 2",
         "Undesirable event", "ORX Cause level 1 and 2", "Impact categories",
         "Probability for one time events", "Frequency for repeating events",
         "Resulting in", "Impact", "Exposure (inherent)", "Key risk",
         "Inherent Risk Rating Rationale", "Controls in place (existing) Descriptive",
         "Effectiveness Control environment", "Exposure (residual)",
         "Residual Risk Rating Rationale", "Risk Response",
         "Exposure (Mitigated)", "Likelihood", "Impact",
         "Residual Risk Rating Rationale"],
        ["1", "Analyse Financial Information", "Incorrect information", "Poor data quality",
         "Financial loss and/or reputation damage",
         "Due to having incorrect or not detailed enough investee information you get to the "
         "wrong valuation resulting in financial loss",
         "Financial loss, Reputational", "Not applicable", "Monthly", "(4) Likely",
         "(2) Moderate", "High", "Yes",
         "Lack of data, wrong data could be imported daily", "See R48",
         "(3) Partially effective", "(2) Moderate",
         "Controls reduce the frequency but not the impact", "Mitigate",
         "(1) Minor", "(2) Unlikely", "(1) Minor",
         "After go-live the daily reconciliation applies"],
        ["2", "Analyse Financial Information", "Wrong methodology",
         "Processing/execution failure", "Financial loss",
         "Due to using the wrong methodology", "Financial loss", "Not applicable", "Monthly",
         "(4) Likely", "(2) Minor", "Medium", "No",
         "Choosing a wrong methodology systemically is not very likely", "See R48",
         "(2) Largely effective", "(1) Low", "Methodology is reviewed quarterly", "Accept",
         "(1) Low", "(2) Unlikely", "(1) Minor", "Unchanged at go-live"],
        ["3", "Report to investors", "Late reporting", "Process failure",
         "Regulatory breach", "Due to manual consolidation steps",
         "Regulatory, Reputational", "Yearly", "Not applicable", "(2) Unlikely",
         "(3) Significant", "Medium", "Yes", "Deadlines are externally set", "See R12",
         "(3) Partially effective", "(2) Moderate", "Manual steps remain", "Mitigate",
         "(2) Moderate", "(2) Unlikely", "(3) Significant", "Automation planned"],
    ]
    merges = ["H5:O5", "P5:S5", "T5:W5", "H6:J6"]
    return _write(path, rows, merges)


def other_shape(path: Path) -> str:
    """The same content, a template that shares almost no column name with it."""
    rows = [
        ["RISK & CONTROL SELF ASSESSMENT"],
        ["Entity", "Retail Banking"],
        ["Period", "H1 2026"],
        ["Prepared by", "Second line of defence"],
        [],
        ["Nr", "Scenario", "Business process", "Root cause", "Consequence type",
         "Gross likelihood", "Gross impact", "Gross score", "Mitigating measures",
         "Control rating", "Net score", "Net score explanation", "Top risk?",
         "Action agreed", "Owner", "Last reviewed"],
        ["R-001", "Incorrect information", "Analyse Financial Information",
         "Investee information is incomplete", "Financial loss", "Likely", "Moderate",
         "High", "See R48", "Partially effective", "Moderate",
         "Controls reduce frequency, not impact", "Yes", "Mitigate", "A. Jansen", "2026-03-01"],
        ["R-002", "Wrong methodology", "Analyse Financial Information",
         "Methodology not applied consistently", "Financial loss", "Likely", "Minor",
         "Medium", "Quarterly review", "Largely effective", "Low",
         "Reviewed each quarter", "No", "Accept", "A. Jansen", "2026-03-01"],
        ["R-003", "Late reporting", "Report to investors", "Manual consolidation",
         "Regulatory breach", "Unlikely", "Significant", "Medium", "See R12",
         "Partially effective", "Moderate", "Manual steps remain", "Yes",
         "Mitigate", "P. de Vries", "2026-02-14"],
    ]
    return _write(path, rows)
