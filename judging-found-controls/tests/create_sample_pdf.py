"""Generates tests/sample_policy.pdf — a minimal 2-page synthetic policy for CI testing."""
from pathlib import Path
from fpdf import FPDF

pdf = FPDF()

pdf.add_page()
pdf.set_font("Helvetica", size=12)
pdf.cell(0, 10, "4.2 Access Management", new_x="LMARGIN", new_y="NEXT")
pdf.multi_cell(
    0, 8,
    "The IT Security team is responsible for revoking all system credentials "
    "within 24 hours of receiving a formal termination notification from Human Resources. "
    "Access rights of employees shall be removed immediately upon termination of employment, "
    "contract, or agreement.",
)

pdf.add_page()
pdf.set_font("Helvetica", size=12)
pdf.cell(0, 10, "5.1 General", new_x="LMARGIN", new_y="NEXT")
pdf.multi_cell(
    0, 8,
    "This policy establishes baseline information security requirements for all employees "
    "and contractors of the organisation.",
)

out = Path(__file__).parent / "sample_policy.pdf"
pdf.output(str(out))
print(f"Created {out}")
