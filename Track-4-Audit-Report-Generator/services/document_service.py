import re
import io
from docx import Document


PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def extract_placeholders(docx_bytes: bytes) -> list[str]:
    """Return all unique {{PLACEHOLDER}} keys found in the template."""
    doc = Document(io.BytesIO(docx_bytes))
    found = set()

    for para in doc.paragraphs:
        for match in PLACEHOLDER_PATTERN.finditer(para.text):
            found.add(match.group(1))

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for match in PLACEHOLDER_PATTERN.finditer(para.text):
                        found.add(match.group(1))

    return sorted(found)


def fill_template(docx_bytes: bytes, content_map: dict[str, str]) -> bytes:
    """Replace all {{KEY}} placeholders in the template with generated content."""
    doc = Document(io.BytesIO(docx_bytes))

    for para in doc.paragraphs:
        _replace_in_paragraph(para, content_map)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _replace_in_paragraph(para, content_map)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def _replace_in_paragraph(para, content_map: dict[str, str]):
    """
    Replace placeholders in a paragraph while preserving formatting.
    Word sometimes splits a placeholder across multiple runs, so we
    operate on the full paragraph text, then rebuild a single run.
    """
    full_text = "".join(run.text for run in para.runs)
    if "{{" not in full_text:
        return

    new_text = full_text
    for key, value in content_map.items():
        new_text = new_text.replace("{{" + key + "}}", value or "")

    if new_text == full_text:
        return

    # Clear all runs and put the replaced text into the first run
    for i, run in enumerate(para.runs):
        if i == 0:
            run.text = new_text
        else:
            run.text = ""
