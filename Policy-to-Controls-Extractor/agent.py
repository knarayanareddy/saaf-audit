#!/usr/bin/env python3
"""Policy-to-Controls Extractor — verwerkt PDF/DOCX beleidsdocumenten naar gestructureerde controls."""

import argparse
import shutil
import statistics
import sys
from collections import Counter
from pathlib import Path

import anthropic

from services.config import get_runtime_settings, load_config, resolve_input_files
from services.pdf_extractor import extract_text_from_pdf
from services.docx_extractor import extract_text_from_docx
from services.write_output import write_json, write_xlsx

from models import ExtractionResult
from prompts import SYSTEM_PROMPT

CONFIG_FILE = Path("P2C.conf")


# ============================================================================
# Bestandsopbouw
# 1. Configuratie laden -> config.py
# 2. Tekst extracteren uit bronbestanden -> text_extractor.py
# 3. Controls laten extraheren door Claude -> extract_controls() in agent.py
# 4. Resultaten wegschrijven naar JSON/XLSX -> write_output.py
# 5. Bestanden verwerken en CLI-aansturing
# ============================================================================

def extract_text(path: Path) -> str:
    # Routeer per bestandstype naar de juiste extractor.
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(path)
    raise ValueError(f"Niet-ondersteund bestandstype: {path.suffix}. Gebruik PDF of DOCX.")

# ============================================================================
# 3. Claude-extractie en schema-validatie
# ============================================================================
# Bouwt de LLM-aanvraag op en dwingt een strikt JSON-resultaat af via het modelschema.

def _strict_schema(schema: dict) -> dict:
    """Voeg recursief additionalProperties: false toe aan alle object-types."""
    schema = dict(schema)
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
        if "properties" in schema:
            schema["properties"] = {k: _strict_schema(v) for k, v in schema["properties"].items()}
    if "$defs" in schema:
        schema["$defs"] = {k: _strict_schema(v) for k, v in schema["$defs"].items()}
    if "items" in schema:
        schema["items"] = _strict_schema(schema["items"])
    return schema


def extract_controls(text: str, domain: str, scope: str, model: str, api_key: str) -> ExtractionResult:
    import json

    client = anthropic.Anthropic(api_key=api_key or None)
    user_message = (
        f"Domein: {domain}\n"
        f"Toepassingsscope: {scope}\n\n"
        f"--- BELEIDSTEKST ---\n\n{text}"
    )
    received = 0
    with client.messages.stream(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": _strict_schema(ExtractionResult.model_json_schema()),
            }
        },
    ) as stream:
        for chunk in stream.text_stream:
            received += len(chunk)
            print(f"\r  Ontvangen: {received:,} tekens...  ", end="", flush=True)
        final = stream.get_final_message()
    print(f"\r  Ontvangen: {received:,} tekens — klaar.      ")
    data = json.loads(final.content[0].text)
    return ExtractionResult.model_validate(data)

# ============================================================================
# 5. Bestandsverwerking
# ============================================================================
# Doorloopt de volledige pipeline voor één document: extractie, analyse, output en archivering.

def process_file(
    path: Path,
    text: str,
    output_dir: Path,
    domain: str,
    scope: str,
    model: str,
    api_key: str,
) -> None:
    print(f"  Claude analyseert... (model: {model})")
    result = extract_controls(text, domain=domain, scope=scope, model=model, api_key=api_key)
    n = len(result.controls)
    print(f"  {n} control{'s' if n != 1 else ''} gevonden | Domein: {result.domain_detected}")

    stem = path.stem
    write_json(result, output_dir / f"{stem}.json")
    write_xlsx(result, output_dir / f"{stem}.xlsx")
    shutil.move(str(path), output_dir / path.name)

    print(f"  Output: {stem}.json + {stem}.xlsx")

    if result.controls:
        counts = {level: sum(1 for c in result.controls if c.confidence == level)
                  for level in ("High", "Medium", "Low")}
        open_q = sum(len(c.open_questions) for c in result.controls)
        print(f"  Kwaliteit: High={counts['High']} | Medium={counts['Medium']} | Low={counts['Low']}")
        if open_q:
            print(f"  Open vragen: {open_q} (zie JSON/XLSX voor details)")


# ============================================================================
# 6. CLI en programma-start
# ============================================================================
# Verwerkt command line-argumenten, bepaalt welke bestanden worden verwerkt en start de batch.

def _segmentation_stats(result: dict) -> dict:
    """Bereken kwaliteitsindicatoren over een segmentatie-resultaat.

    De spreiding van de segmentlengtes is de belangrijkste signaalbron:
    - veel level-0-segmenten        -> headings niet herkend
    - veel korte segmenten          -> ruis (inhoudsopgave, losse regels)
    - een zeer hoge max of stdev    -> heading(s) gemist, alles in één blok
    """
    segments = result["segments"]
    lengths = [s["word_count"] for s in segments]
    levels = Counter(s["level"] for s in segments)
    return {
        "n_segments": len(segments),
        "total_words": sum(lengths),
        "mean_words": statistics.mean(lengths) if lengths else 0.0,
        "median_words": statistics.median(lengths) if lengths else 0.0,
        "stdev_words": statistics.stdev(lengths) if len(lengths) > 1 else 0.0,
        "min_words": min(lengths) if lengths else 0,
        "max_words": max(lengths) if lengths else 0,
        "level_counts": dict(sorted(levels.items())),
        "n_short": sum(1 for w in lengths if w < 20),       # mogelijke ruis
        "n_empty": sum(1 for w in lengths if w == 0),       # heading zonder tekst
        "n_no_heading": sum(1 for s in segments if s["level"] == 0),
    }


def _summarize_extraction(result: dict) -> str:
    """Vat een segmentatie-resultaat samen: statistieken + alle segmenttitels."""
    if "segments" not in result:
        return f"  >> Tekst geëxtraheerd uit {result['source']} (geen segmentatie)"

    s = _segmentation_stats(result)
    lines = [
        f"  >> {result['source']} (mode: {result['mode']})",
        f"     segmenten      : {s['n_segments']}  |  {s['total_words']:,} woorden totaal",
        f"     lengte/segment : gem {s['mean_words']:.0f}  mediaan {s['median_words']:.0f}  "
        f"sd {s['stdev_words']:.0f}  min {s['min_words']}  max {s['max_words']}",
        f"     niveau-verdeling: {s['level_counts']}",
        f"     signalen       : {s['n_short']} kort (<20w)  |  {s['n_empty']} leeg  |  "
        f"{s['n_no_heading']} zonder heading (lvl 0)",
        f"     titels:",
    ]
    for seg in result["segments"]:
        indent = "  " * max(seg["level"], 0)
        lines.append(f"       {indent}- {seg['heading']}  ({seg['word_count']}w)")
    return "\n".join(lines)

def main() -> None:
    config = load_config(CONFIG_FILE)
    todo_dir, output_dir, halfway_dir, default_domain, default_scope, model, header_model, api_key = get_runtime_settings(config)

    parser = argparse.ArgumentParser(
        description="Extraheer controls uit beleidsdocumenten (PDF/DOCX)"
    )
    parser.add_argument(
        "--domain",
        default=default_domain,
        help="Domein, bijv. IAM, Change, Logging, Vendor (default uit P2C.conf)",
    )
    parser.add_argument(
        "--scope",
        default=default_scope,
        help="Toepassingsscope, bijv. 'Organisatie X' (default uit P2C.conf)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Verwerk één specifiek bestand i.p.v. alle bestanden in to-do/",
    )
    args = parser.parse_args()

    output_dir.mkdir(parents=True, exist_ok=True)
    input_files = resolve_input_files(todo_dir, args.file)


    print(f"Policy-to-Controls Extractor")
    print(f"Bestanden: {len(input_files['pdf_files'])} pdf-bestanden en {len(input_files['doc_files'])} doc-bestanden")


    for file in input_files["pdf_files"]:
        text = extract_text_from_pdf(file, halfway_dir, header_model, api_key)
        print(_summarize_extraction(text)) 
    
    for file in input_files["doc_files"]:
        text = extract_text_from_docx(file, halfway_dir, header_model, api_key)
        print(_summarize_extraction(text)) 


    # for file_path in files:
    #     print(f"\n  Verwerken: {file_path.name}")
    #     text = extract_text(file_path)
    #     print(f"  Tekst geextraheerd ({len(text):,} tekens)")
    #     print(text[:200].replace("\n", " ") + "..." if len(text) > 200 else text)

    #     process_file(
    #         file_path,
    #         text=text,
    #         output_dir=output_dir,
    #         domain=args.domain,
    #         scope=args.scope,
    #         model=model,
    #         api_key=api_key,
    #     )

    print(f"\nKlaar. Output staat in {output_dir}/")


if __name__ == "__main__":
    main()
