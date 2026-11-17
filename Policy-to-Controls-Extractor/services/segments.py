# ============================================================================
# 2c. Gedeelde segmentlogica voor de PDF- en DOCX-extractors
# ============================================================================
# Zet "regels" (tekst + optionele fontgrootte + witregel-markering) om naar
# gestructureerde segmenten. Twee ingangen:
#   - segment_by_levels()    : niveaus zijn al bekend (native Word-stijlen)
#   - segment_semantically() : cascade (a) fontgrootte -> (c) AI -> (b) blokken
#
# Een "regel" is een dict: {"text": str, "size": float|None, "blank_after": bool}
# Een "segment" is een dict: {"path", "level", "heading", "text", "word_count"}

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

# H2/H3-subsecties kleiner dan dit worden in het bovenliggende segment gevouwen.
MIN_SEGMENT_WORDS = 50
# Streefgrootte en harde bovengrens voor blok-segmentatie zonder headings.
TARGET_SEGMENT_WORDS = 150
MAX_SEGMENT_WORDS = 400


# ----------------------------------------------------------------------------
# Publieke ingangen
# ----------------------------------------------------------------------------

def segment_by_levels(path: Path, halfway_dir: Path,
                      items: list[tuple[str, int]], mode: str = "headers") -> dict:
    """Bouw segmenten uit reeds bekende (tekst, niveau)-paren."""
    segments = _fold_segments(_raw_blocks(items))
    result = {"source": path.name, "mode": mode, "segments": segments}
    write_halfway(path, halfway_dir, result)
    print(f"  {len(segments)} segment(en) op basis van {mode}")
    return result


def segment_semantically(path: Path, halfway_dir: Path, lines: list[dict],
                         header_model: str | None, api_key: str | None) -> dict:
    """Segmenteer zonder bekende heading-niveaus via een cascade.

    (a) headings afleiden uit terugkerende grotere fontgroottes;
    (c) lukt dat niet, dan Claude de headings laten bepalen;
    (b) als laatste terugval het document opdelen in blokken tussen witregels.
    """
    print(f"  Cascade gestart op {len(lines)} regels...")
    items = _levels_by_font_size(lines)
    mode = "semantic-fontsize"
    route = "(a) fontgrootte"

    if items is None and header_model:
        print("  Geen grotere koppen op fontgrootte, headings bepalen via AI...")
        items = _ai_heading_levels(lines, header_model, api_key)
        mode = "semantic-ai"
        route = "(c) AI/agent"

    if items is not None:
        n_headings = sum(1 for _, level in items if level > 0)
        print(f"  {n_headings} heading(s) herkend via route {route}")
        segments = _fold_segments(_raw_blocks(items))
    else:
        print("  Terugvallen op blok-segmentatie (witregels)")
        segments = _bundle_blocks(lines)
        mode = "semantic-blocks"
        route = "(b) blokken tussen witregels"

    result = {"source": path.name, "mode": mode, "segments": segments}
    write_halfway(path, halfway_dir, result)
    print(f"  >> Route gekozen: {route} | {len(segments)} segment(en) [{mode}]")
    return result


# ----------------------------------------------------------------------------
# (a) Headings uit fontgrootte
# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------
# (c) Headings via Claude
# ----------------------------------------------------------------------------

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
        print(f"  AI-headingdetectie aanroepen (model: {model})...")
        client = anthropic.Anthropic(api_key=api_key or None)
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = msg.usage
        total = usage.input_tokens + usage.output_tokens
        print(f"  AI-tokens: {usage.input_tokens:,} in + {usage.output_tokens:,} out "
              f"= {total:,} totaal")
        raw = msg.content[0].text
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception as exc:  # netwerk-, parse- of API-fout -> nette terugval
        print(f"  AI-headingdetectie mislukt ({exc})")
        return None
    levels = {h["index"]: h["level"] for h in data.get("headings", [])}
    return [(ln["text"], levels.get(i, 0)) for i, ln in enumerate(lines)]


# ----------------------------------------------------------------------------
# (b) Blokken tussen witregels
# ----------------------------------------------------------------------------

def _bundle_blocks(lines: list[dict]) -> list[dict]:
    """Bundel regels tot segmenten; breek bij voorkeur op een witregel."""
    segments: list[dict] = []
    chunk: list[str] = []
    words = 0
    for line in lines:
        chunk.append(line["text"])
        words += len(line["text"].split())
        # Knip bij een witregel zodra het segment groot genoeg is, of bij de
        # harde bovengrens als er geen witregels (meer) volgen.
        if (words >= TARGET_SEGMENT_WORDS and line["blank_after"]) or words >= MAX_SEGMENT_WORDS:
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
# Segmentopbouw uit (tekst, niveau)-paren
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
        if r["level"] <= 1 or word_count >= MIN_SEGMENT_WORDS:
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

def write_halfway(path: Path, halfway_dir: Path, data: dict) -> Path:
    """Schrijf het gesegmenteerde resultaat als JSON naar halfway_dir."""
    halfway_dir = Path(halfway_dir)
    halfway_dir.mkdir(parents=True, exist_ok=True)
    out_path = halfway_dir / f"{path.stem}.segments.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Tussenresultaat: {out_path}")
    return out_path
