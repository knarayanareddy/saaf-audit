# ============================================================================
# 2b. Tekstextractie uit PDF-beleidsdocumenten
# ============================================================================
# Zet PDF-bestanden om naar gestructureerde, gesegmenteerde tekst. PDF heeft
# geen native heading-stijlen, dus altijd via de semantische cascade
# (a) fontgrootte -> (c) AI -> (b) blokken (zie services/segments.py).
# Het tussenresultaat wordt als JSON in halfway_dir bewaard.

from __future__ import annotations

from pathlib import Path

from services import segments


def extract_text_from_pdf(path: Path, halfway_dir: Path,
                          header_model: str | None = None,
                          api_key: str | None = None) -> dict:
    print(f"  PDF-tekst extraheren uit {path.name}...")
    lines = _pdf_lines(path)
    return segments.segment_semantically(path, halfway_dir, lines, header_model, api_key)


def _pdf_lines(path: Path) -> list[dict]:
    """Lees de PDF als regels met tekst, fontgrootte en witregel-markering.

    Gebruikt pdfplumber's regel-assemblage (`extract_text_lines`), zodat
    woorden met x-tolerantie correct worden samengevoegd — ook bij small-caps
    koppen waar de grote beginletter en de kleine rest los staan. De
    fontgrootte van een regel is de grootste lettergrootte op die regel, zodat
    een kop herkenbaar blijft. Een witregel wordt afgeleid uit een verticaal
    gat groter dan de regelhoogte; een paginabreuk geldt ook als witregel.
    """
    import pdfplumber

    lines: list[dict] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_lines: list[dict] = []
            for text_line in page.extract_text_lines():
                text = text_line["text"].strip()
                if not text:
                    continue
                char_sizes = [c["size"] for c in text_line["chars"] if c.get("size")]
                size = round(max(char_sizes), 1) if char_sizes else 0.0
                page_lines.append({"text": text, "size": size,
                                   "top": text_line["top"], "bottom": text_line["bottom"],
                                   "blank_after": False})

            # Witregels afleiden uit verticale gaten tussen opeenvolgende regels.
            for i in range(len(page_lines) - 1):
                height = page_lines[i]["bottom"] - page_lines[i]["top"]
                gap = page_lines[i + 1]["top"] - page_lines[i]["bottom"]
                if height > 0 and gap > 0.7 * height:
                    page_lines[i]["blank_after"] = True
            if page_lines:
                page_lines[-1]["blank_after"] = True  # paginabreuk telt als witregel
            lines.extend(page_lines)

    # Interne layout-velden (top/bottom) weglaten uit het regelmodel.
    return [{"text": ln["text"], "size": ln["size"], "blank_after": ln["blank_after"]}
            for ln in lines]
