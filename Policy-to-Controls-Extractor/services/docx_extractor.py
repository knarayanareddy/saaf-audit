# ============================================================================
# 2a. Tekstextractie uit DOCX-beleidsdocumenten
# ============================================================================
# Zet DOCX-bestanden om naar gestructureerde, gesegmenteerde tekst.
#   1. Native Word heading-stijlen (Kop/Heading 1-3) -> segment_by_levels
#   2. Geen heading-stijlen -> semantische cascade (zie services/segments.py)
# Het tussenresultaat wordt als JSON in halfway_dir bewaard.

from __future__ import annotations

from pathlib import Path

from services import segments


def extract_text_from_docx(path: Path, halfway_dir: Path,
                           header_model: str | None = None,
                           api_key: str | None = None) -> dict:
    print(f"  DOCX-tekst extraheren uit {path.name}...")
    from docx import Document

    doc = Document(path)
    if document_has_headers(doc):
        print(f"  Heading-stijlen gedetecteerd in {path.name}, gebruik die voor segmentatie")
        items = [(p.text.strip(), _heading_level(p.style.name))
                 for p in doc.paragraphs if p.text.strip()]
        return segments.segment_by_levels(path, halfway_dir, items)

    print(f"  Geen heading-stijlen in {path.name}, overgaan op semantische segmentatie")
    lines = _read_paragraphs(doc)
    return segments.segment_semantically(path, halfway_dir, lines, header_model, api_key)


def document_has_headers(doc) -> bool:
    for p in doc.paragraphs[:16]:  # Check de eerste paar paragrafen
        if p.style.name.startswith("Heading") or p.style.name.startswith("Kop"):
            return True
    return False


def _heading_level(style_name: str) -> int:
    """Geef het heading-niveau (1-3) van een Word-stijl, of 0 voor bodytekst."""
    for prefix in ("Heading ", "Kop "):
        if style_name.startswith(prefix):
            suffix = style_name[len(prefix):].strip()
            if suffix.isdigit():
                return min(int(suffix), 3)
    return 0


def _read_paragraphs(doc) -> list[dict]:
    """Lees niet-lege paragrafen als regels met fontgrootte en witregel-markering."""
    lines: list[dict] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            if lines:  # een lege paragraaf is een witregel na de vorige regel
                lines[-1]["blank_after"] = True
            continue
        lines.append({"text": text, "size": _paragraph_size(p), "blank_after": False})
    return lines


def _paragraph_size(para) -> float | None:
    """Bepaal de effectieve fontgrootte (pt) van een paragraaf.

    Eerst directe run-opmaak; valt die weg, dan de (geërfde) paragraafstijl.
    """
    for run in para.runs:
        if run.font.size is not None:
            return round(run.font.size.pt, 1)
    style, depth = para.style, 0
    while style is not None and depth < 10:  # loop de base_style-keten af
        size = getattr(style.font, "size", None)
        if size is not None:
            return round(size.pt, 1)
        style = getattr(style, "base_style", None)
        depth += 1
    return None
