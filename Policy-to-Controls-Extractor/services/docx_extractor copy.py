# ============================================================================
# 2a. Tekstextractie uit beleidsdocumenten
# ============================================================================
# Zet ondersteunde bronbestanden om naar gestructureerde, gesegmenteerde tekst
# voor verdere analyse. Het tussenresultaat wordt als JSON in halfway_dir bewaard.
#
# Strategie voor DOCX:
#   1. Native Word heading-stijlen (Kop/Heading 1-3)         -> extract_text_with_headers
#   2. Geen heading-stijlen -> semantische cascade:
#        (a) terugkerende grotere fontgrootte
#        (c) headings laten bepalen door Claude
#        (b) blokken tussen witregels (basis-fallback)

import json
from collections import Counter
from pathlib import Path

# H2/H3-subsecties met minder woorden dan dit vouwen we in het bovenliggende
# segment; grotere subsecties worden een eigen segment.
_MIN_SEGMENT_WORDS = 50
# Streefgrootte en harde bovengrens voor blok-segmentatie zonder headings.
_TARGET_SEGMENT_WORDS = 150
_MAX_SEGMENT_WORDS = 400


def extract_text_from_docx(path: Path, halfway_dir: Path,
                           model: str | None = None, api_key: str | None = None) -> dict:
    print(f"  DOCX-tekst extraheren uit {path.name}...")
    if document_has_headers(path):
        print(f"  Headers gedetecteerd in {path.name}, gebruik die voor segmentatie")
        return extract_text_with_headers(path, halfway_dir)
    else:
        print(f"  Geen headers gedetecteerd in {path.name}, overgaan op semantische segmentatie")
        return extract_text_semantic(path, halfway_dir, model, api_key)


def document_has_headers(path: Path) -> bool:
    from docx import Document
    doc = Document(path)
    for p in doc.paragraphs[:16]:  # Check de eerste paar paragrafen
        if p.style.name.startswith("Heading") or p.style.name.startswith("Kop"):
            return True
    return False


# ----------------------------------------------------------------------------
# 1. Extractie met native Word heading-stijlen (Heading/Kop 1-3)
# ----------------------------------------------------------------------------

def extract_text_with_headers(path: Path, halfway_dir: Path) -> dict:
    """Ontleed het DOCX-bestand naar segmenten op basis van heading-stijlen.

    Elke 'Heading 1'/'Kop 1' wordt een segment; H2/H3-subsecties met >= ~50
    woorden worden losse segmenten, kleinere worden in het bovenliggende
    segment gevouwen.
    """
    from docx import Document

    doc = Document(path)
    items = [(p.text.strip(), _heading_level(p.style.name))
             for p in doc.paragraphs if p.text.strip()]
    segments = _fold_segments(_raw_blocks(items))

    result = {"source": path.name, "mode": "headers", "segments": segments}
    _write_halfway(path, halfway_dir, result)
    print(f"  {len(segments)} segment(en) op basis van headers")
    return result


def _heading_level(style_name: str) -> int:
    """Geef het heading-niveau (1-3) van een Word-stijl, of 0 voor bodytekst."""
    for prefix in ("Heading ", "Kop "):
        if style_name.startswith(prefix):
            suffix = style_name[len(prefix):].strip()
            if suffix.isdigit():
                return min(int(suffix), 3)
    return 0


# ----------------------------------------------------------------------------
# 2. Semantische extractie — cascade (a) fontgrootte -> (c) AI -> (b) blokken
# ----------------------------------------------------------------------------

def extract_text_semantic(path: Path, halfway_dir: Path,
                          model: str | None = None, api_key: str | None = None) -> dict:
    """Segmenteer een DOCX zonder native heading-stijlen.

    Doorloopt een cascade: eerst headings afleiden uit terugkerende grotere
    fontgroottes (a); lukt dat niet, dan Claude de headings laten bepalen (c);
    en als laatste terugval het document opdelen in blokken tussen witregels (b).
    """
    from docx import Document

    doc = Document(path)
    lines = _read_paragraphs(doc)

    # (a) Headings afleiden uit fontgrootte.
    items = _levels_by_font_size(lines)
    mode = "semantic-fontsize"

    # (c) Geen grootteverschil gevonden -> Claude de headings laten bepalen.
    if items is None and model:
        print("  Geen grotere koppen gevonden op fontgrootte, headings bepalen via AI...")
        items = _ai_heading_levels(lines, model, api_key)
        mode = "semantic-ai"

    if items is not None:
        segments = _fold_segments(_raw_blocks(items))
    else:
        # (b) Basis-fallback: opdelen in blokken tussen witregels.
        print("  Terugvallen op blok-segmentatie (witregels)")
        segments = _bundle_blocks(lines)
        mode = "semantic-blocks"

    result = {"source": path.name, "mode": mode, "segments": segments}
    _write_halfway(path, halfway_dir, result)
    print(f"  {len(segments)} segment(en) ({mode})")
    return result


def _read_paragraphs(doc) -> list[dict]:
    """Lees niet-lege paragrafen met fontgrootte en witregel-markering."""
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


# --- (a) fontgrootte -------------------------------------------------------

def _levels_by_font_size(lines: list[dict]) -> list[tuple[str, int]] | None:
    """Map regels op heading-niveaus via fontgrootte; None als dat niet kan."""
    sizes = [ln["size"] for ln in lines if ln["size"] is not None]
    if not sizes or len(sizes) < 0.5 * len(lines):
        return None  # te weinig betrouwbare grootte-informatie
    body_size = Counter(sizes).most_common(1)[0][0]
    heading_sizes = sorted({s for s in sizes if s > body_size}, reverse=True)[:3]
    if not heading_sizes:
        return None  # geen terugkerende grotere letters -> geen headings
    size_level = {size: level for level, size in enumerate(heading_sizes, start=1)}
    return [(ln["text"], size_level.get(ln["size"], 0)) for ln in lines]


# --- (c) AI/agent ----------------------------------------------------------

def _ai_heading_levels(lines: list[dict], model: str,
                       api_key: str | None) -> list[tuple[str, int]] | None:
    """Laat Claude bepalen welke regels headings zijn; None bij een fout."""
    import anthropic

    numbered = "\n".join(f"[{i}] {ln['text']}" for i, ln in enumerate(lines))
    prompt = (
        "Hieronder staan genummerde tekstregels uit een beleidsdocument, zonder "
        "opmaakinformatie. Bepaal welke regels een kop (heading) zijn en op welk "
        "niveau: 1 = hoofdstuk, 2 = paragraaf, 3 = subparagraaf. Gewone lopende "
        "tekst neem je niet op.\n"
        'Antwoord UITSLUITEND met JSON in de vorm:\n'
        '{"headings": [{"index": <regelnummer>, "level": <1-3>}]}\n\n'
        f"{numbered}"
    )
    try:
        client = anthropic.Anthropic(api_key=api_key or None)
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception as exc:  # netwerk-, parse- of API-fout -> nette terugval
        print(f"  AI-headingdetectie mislukt ({exc})")
        return None
    levels = {h["index"]: h["level"] for h in data.get("headings", [])}
    return [(ln["text"], levels.get(i, 0)) for i, ln in enumerate(lines)]


# --- (b) blokken tussen witregels ------------------------------------------

def _bundle_blocks(lines: list[dict]) -> list[dict]:
    """Bundel paragrafen tot segmenten; breek bij voorkeur op een witregel."""
    segments: list[dict] = []
    chunk: list[str] = []
    words = 0
    for line in lines:
        chunk.append(line["text"])
        words += len(line["text"].split())
        # Knip bij een witregel zodra het segment groot genoeg is, of bij de
        # harde bovengrens als er geen witregels (meer) volgen.
        if (words >= _TARGET_SEGMENT_WORDS and line["blank_after"]) or words >= _MAX_SEGMENT_WORDS:
            segments.append(_semantic_segment(len(segments) + 1, chunk))
            chunk, words = [], 0
    if chunk:
        segments.append(_semantic_segment(len(segments) + 1, chunk))
    return segments


def _semantic_segment(index: int, paragraphs: list[str]) -> dict:
    text = "\n\n".join(paragraphs)
    heading = f"Segment {index}"
    return {
        "path": [heading],
        "level": 0,
        "heading": heading,
        "text": text,
        "word_count": len(text.split()),
    }


# ----------------------------------------------------------------------------
# Gedeelde segmentopbouw
# ----------------------------------------------------------------------------

def _raw_blocks(items: list[tuple[str, int]]) -> list[dict]:
    """Bouw ruwe blokken (tekst onder elke heading) uit (tekst, niveau)-paren."""
    raw: list[dict] = []
    section_path: list[str] = []
    current = {"level": 0, "heading": "(inleiding)", "path": ["(inleiding)"], "buf": []}
    for text, level in items:
        if level == 0:  # bodytekst -> toevoegen aan huidig blok
            current["buf"].append(text)
            continue
        raw.append(current)
        section_path = section_path[: level - 1] + [text]
        current = {"level": level, "heading": text, "path": list(section_path), "buf": []}
    raw.append(current)
    # Lege inleiding (document begint meteen met een heading) overslaan.
    return [r for r in raw if r["buf"] or r["level"] > 0]


def _fold_segments(raw: list[dict]) -> list[dict]:
    """Vouw kleine H2/H3-subsecties in hun dichtstbijzijnde bewaarde voorouder."""
    kept: list[dict] = []
    ancestors: dict[int, dict] = {}
    for r in raw:
        text = " ".join(r["buf"]).strip()
        word_count = len(text.split())
        segment = {
            "path": r["path"],
            "level": r["level"],
            "heading": r["heading"],
            "text": text,
            "word_count": word_count,
        }
        if r["level"] <= 1 or word_count >= _MIN_SEGMENT_WORDS:
            kept.append(segment)
            ancestors[r["level"]] = segment
            for deeper in [lvl for lvl in ancestors if lvl > r["level"]]:
                del ancestors[deeper]
        else:
            parent = next((ancestors[lvl] for lvl in range(r["level"] - 1, -1, -1)
                           if lvl in ancestors), None)
            if parent is None:  # geen voorouder -> toch eigen segment
                kept.append(segment)
                ancestors[r["level"]] = segment
                continue
            parent["text"] += f"\n\n{r['heading']}\n{text}".rstrip()
            parent["word_count"] = len(parent["text"].split())
    return kept


# ----------------------------------------------------------------------------
# Tussenresultaat wegschrijven
# ----------------------------------------------------------------------------

def _write_halfway(path: Path, halfway_dir: Path, data: dict) -> Path:
    """Schrijf het gesegmenteerde resultaat als JSON naar halfway_dir."""
    halfway_dir = Path(halfway_dir)
    halfway_dir.mkdir(parents=True, exist_ok=True)
    out_path = halfway_dir / f"{path.stem}.segments.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Tussenresultaat: {out_path}")
    return out_path
