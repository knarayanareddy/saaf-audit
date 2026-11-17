"""
docx_to_text.py — Extract plain text from a Word (.docx) document.

Usage:
    python3 tools/scripts/docx_to_text.py <path-to-docx>

Output:
    Writes extracted text to <original-name>.txt in the same directory as the input file.
    Also prints the output path to stdout for use in skill pipelines.

Part of the SAAF analyze-policy skill pipeline.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def extract_text_from_docx(docx_path: Path) -> Optional[str]:
    """Extract all text from a .docx file, preserving heading structure."""
    try:
        from docx import Document  # type: ignore
    except ImportError:
        logger.error("python-docx is not installed. Run: pip3 install python-docx")
        return None

    try:
        doc = Document(str(docx_path))
    except Exception as exc:
        logger.error("Could not open %s: %s", docx_path, exc)
        return None

    lines: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = para.style.name if para.style else ""

        # Prefix headings with Markdown markers for structure
        if style_name.startswith("Heading 1"):
            lines.append(f"\n# {text}")
        elif style_name.startswith("Heading 2"):
            lines.append(f"\n## {text}")
        elif style_name.startswith("Heading 3"):
            lines.append(f"\n### {text}")
        elif style_name.startswith("List"):
            lines.append(f"- {text}")
        else:
            lines.append(text)

    # Also extract text from tables
    for table in doc.tables:
        lines.append("")
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            lines.append(" | ".join(cells))
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: python3 {Path(__file__).name} <path-to-docx>", file=sys.stderr)
        return 1

    docx_path = Path(sys.argv[1]).resolve()

    if not docx_path.exists():
        logger.error("File not found: %s", docx_path)
        return 1

    if docx_path.suffix.lower() != ".docx":
        logger.error("Expected a .docx file, got: %s", docx_path.suffix)
        return 1

    logger.info("Extracting text from: %s", docx_path)
    text = extract_text_from_docx(docx_path)

    if text is None:
        return 1

    output_path = docx_path.with_suffix(".txt")
    output_path.write_text(text, encoding="utf-8")

    logger.info("Text extracted to: %s (%d characters)", output_path, len(text))
    # Print output path to stdout for use in skill pipelines
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
