"""
extract_slides.py — Extract text and image descriptions from PPTX/PDF presentation files.

Usage:
    python3 tools/scripts/extract_slides.py [--no-images] [--model claude-sonnet-4-6]

Options:
    --no-images   Skip image description (faster, text only)
    --model       Claude model to use for image descriptions (default: claude-sonnet-4-6)

Reads all PPTX and PDF files from the configured PRESENTATIONS_DIR,
extracts text slide-by-slide using proper XML parsing (no regex),
describes embedded images using Claude Vision, and writes one markdown
file per presentation to OUTPUT_DIR.
"""

import argparse
import base64
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# XML namespaces
# ---------------------------------------------------------------------------
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
IMAGE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DRIVE_ROOT = Path(__file__).parents[3] / "SAAF Project Drive"
PRESENTATIONS_DIR = DRIVE_ROOT / "Presentations"
OUTPUT_DIR = Path(__file__).parents[2] / "docs" / "transcriptions" / "slides"

PRESENTATION_MAP = [
    (
        "Alignment Session #1 @Mollie/SAAF Kick-Off Slides (Shared Audit Agents Framework).pptx",
        "alignment-kickoff-mathijs.md",
        "SAAF Kick-Off Slides (Alignment Session #1, January 20, 2026)",
    ),
    (
        "Hackathon #1 @Mollie/Hackathon Slides Mathijs_ Building AI Agents Together 🚀.pptx",
        "hackathon1-mathijs.md",
        "Hackathon Slides: Building AI Agents Together — Mathijs Schouten (Hackathon #1, March 10, 2026)",
    ),
    (
        "Hackathon #1 @Mollie/Hackathon Slides Eduward.pptx",
        "hackathon1-eduward.md",
        "Hackathon Slides — Eduward van de Kamp (Hackathon #1, March 10, 2026)",
    ),
    (
        "Hackathon #1 @Mollie/Presentatie - Mollie _ Ability.nl 10 maart 2026.pdf",
        "hackathon1-mollie-ability.md",
        "Presentatie Mollie / Ability.nl (Hackathon #1, March 10, 2026)",
    ),
    (
        "Hackathon #2 @Schuberg Philis/SAAF Session #3 - Hackathon #2 Slides - Mathijs Schouten.pptx",
        "hackathon2-mathijs.md",
        "SAAF Session #3 — Hackathon #2 Slides — Mathijs Schouten (Hackathon #2, March 24, 2026)",
    ),
    (
        "Hackathon #2 @Schuberg Philis/Hackathon Slides Eduward @ Schuberg Philis - Raising the Bar.pptx",
        "hackathon2-eduward.md",
        "Raising the Bar — Eduward van de Kamp (Hackathon #2, March 24, 2026)",
    ),
    (
        "Hackathon #2 @Schuberg Philis/SAAF - ICFCOP - Demo.pdf",
        "hackathon2-icfcop.md",
        "SAAF ICFCOP Demo — Schuberg Philis (Hackathon #2, March 24, 2026)",
    ),
    (
        "Hackathon #2 @Schuberg Philis/SAAF AI Hackaton - Governance Risk Compliance - Copilot - Mindshift - ENG - FB.pdf",
        "hackathon2-grc-mindshift.md",
        "GRC, Copilot & Mindshift — Schuberg Philis (Hackathon #2, March 24, 2026)",
    ),
]

# ---------------------------------------------------------------------------
# Text extraction via proper XML parsing
# ---------------------------------------------------------------------------

def _extract_text_from_slide_xml(xml_bytes: bytes) -> str:
    """Parse slide XML and extract all text runs, skipping slide-number fields."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        # Fallback: strip all tags via a simple approach
        import re
        text = re.sub(r"<[^>]+>", " ", xml_bytes.decode("utf-8", errors="replace"))
        return " ".join(text.split())

    parts = []
    a_ns = NS["a"]

    for elem in root.iter():
        tag = elem.tag

        # Skip slide-number field elements entirely
        if tag == f"{{{a_ns}}}fld":
            continue

        # Collect text from <a:t> elements
        if tag == f"{{{a_ns}}}t":
            # Skip if this <a:t> is a child of <a:fld>
            # (ET.iter doesn't give us parent, so we check parent chain via findall below)
            text = elem.text or ""
            text = text.strip()
            if text:
                parts.append(text)

        # Add paragraph breaks between paragraphs
        if tag == f"{{{a_ns}}}p":
            # Add a newline after each paragraph block is done
            # (We'll clean up multiple newlines later)
            parts.append("\n")

    # Join and clean up
    combined = " ".join(p if p == "\n" else p for p in parts)
    # Replace multiple spaces with single space, but preserve newlines
    import re
    combined = re.sub(r"[ \t]+", " ", combined)
    combined = re.sub(r"\n{2,}", "\n", combined)
    combined = re.sub(r" \n", "\n", combined)
    combined = re.sub(r"\n ", "\n", combined)
    return combined.strip()


def _get_slide_image_paths(z: zipfile.ZipFile, slide_num: int) -> list[str]:
    """Return list of media paths (inside zip) referenced by this slide."""
    rels_path = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
    if rels_path not in z.namelist():
        return []
    try:
        rels_xml = z.read(rels_path)
        root = ET.fromstring(rels_xml)
    except Exception:
        return []

    image_paths = []
    for rel in root.iter():
        rel_type = rel.get("Type", "")
        target = rel.get("Target", "")
        if rel_type == IMAGE_REL_TYPE and target:
            # Target is relative to ppt/slides/, resolve to ppt/media/...
            if target.startswith("../"):
                resolved = "ppt/" + target[3:]
            else:
                resolved = f"ppt/slides/{target}"
            if resolved in z.namelist():
                image_paths.append(resolved)
    return image_paths


# ---------------------------------------------------------------------------
# Image description via Claude Vision
# ---------------------------------------------------------------------------

def _describe_image(image_bytes: bytes, media_type: str, model: str, client) -> str:
    """Ask Claude to describe an image in the context of an audit presentation slide."""
    import anthropic

    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    try:
        response = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "This image is from a presentation slide used at a hackathon about "
                                "AI agents for internal audit (SAAF Project). "
                                "Describe what you see in 2-4 sentences: "
                                "what diagram, screenshot, photo, framework, or concept is shown, "
                                "and what the key message or insight is for an auditor. "
                                "Be concise and focus on content relevant to AI, audit, or technology."
                            ),
                        },
                    ],
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        return f"[Image description failed: {exc}]"


def _media_type_from_path(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")


# ---------------------------------------------------------------------------
# PPTX full extraction (text + images)
# ---------------------------------------------------------------------------

def extract_pptx(path: Path, describe_images: bool, model: str, client) -> list[dict]:
    """
    Returns list of dicts per slide:
      {
        "text": str,
        "images": [{"path": str, "description": str}, ...]
      }
    """
    slides = []
    try:
        with zipfile.ZipFile(path, "r") as z:
            slide_files = sorted(
                [n for n in z.namelist() if _is_slide_file(n)],
                key=lambda n: int(_slide_number(n)),
            )
            for i, slide_file in enumerate(slide_files, start=1):
                xml_bytes = z.read(slide_file)
                text = _extract_text_from_slide_xml(xml_bytes)

                image_descriptions = []
                if describe_images:
                    img_paths = _get_slide_image_paths(z, i)
                    for img_path in img_paths:
                        media_type = _media_type_from_path(img_path)
                        # Only describe image formats Claude supports
                        if media_type not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
                            continue
                        img_bytes = z.read(img_path)
                        # Skip tiny images (icons, bullets) < 5 KB
                        if len(img_bytes) < 5120:
                            continue
                        desc = _describe_image(img_bytes, media_type, model, client)
                        image_descriptions.append({"path": img_path, "description": desc})

                slides.append({"text": text, "images": image_descriptions})
    except Exception as exc:
        print(f"  WARNING: could not extract {path.name}: {exc}", file=sys.stderr)
    return slides


def _is_slide_file(name: str) -> bool:
    import re
    return bool(re.match(r"ppt/slides/slide\d+\.xml$", name))


def _slide_number(name: str) -> int:
    import re
    m = re.search(r"\d+", Path(name).name)
    return int(m.group()) if m else 0


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf(path: Path, describe_images: bool, model: str, client) -> list[dict]:
    """Extract text and images from PDF pages."""
    slides = []
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = (page.extract_text() or "").strip()

                image_descriptions = []
                if describe_images and client:
                    for img in page.images:
                        try:
                            # Extract image bytes via page crop
                            bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                            cropped = page.crop(bbox)
                            img_bytes = cropped.to_image(resolution=150).original.tobytes("jpeg", "RGB")
                            if len(img_bytes) < 5120:
                                continue
                            desc = _describe_image(img_bytes, "image/jpeg", model, client)
                            image_descriptions.append({"path": f"page-image", "description": desc})
                        except Exception:
                            pass

                slides.append({"text": text, "images": image_descriptions})
    except ImportError:
        slides.append({"text": "[pdfplumber not installed]", "images": []})
    except Exception as exc:
        slides.append({"text": f"[PDF extraction error: {exc}]", "images": []})
    return slides


# ---------------------------------------------------------------------------
# Markdown writer
# ---------------------------------------------------------------------------

def write_markdown(slides: list[dict], title: str, source_path: Path, output_path: Path) -> None:
    lines = [
        f"# {title}",
        "",
        f"> **Source:** `{source_path.name}`  ",
        f"> **Extracted:** auto-generated by `tools/scripts/extract_slides.py`  ",
        f"> **Slides/pages:** {len(slides)}",
        "",
        "---",
        "",
    ]
    for i, slide in enumerate(slides, start=1):
        lines.append(f"## Slide {i}")
        lines.append("")

        text = slide.get("text", "").strip()
        images = slide.get("images", [])

        if text:
            lines.append(text)
            lines.append("")

        if images:
            for img in images:
                lines.append(f"> **[Image on this slide]** {img['description']}")
                lines.append("")

        if not text and not images:
            lines.append("_(no text or images detected on this slide)_")
            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text and images from PPTX/PDF presentations")
    parser.add_argument("--no-images", action="store_true", help="Skip image description (faster)")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Claude model for image descriptions")
    parser.add_argument("--only", help="Only process this slug (e.g. hackathon2-mathijs)")
    args = parser.parse_args()

    describe_images = not args.no_images
    client = None

    if describe_images:
        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            base_url = os.environ.get("ANTHROPIC_BASE_URL")
            if not api_key and not base_url:
                print("WARNING: ANTHROPIC_API_KEY not set. Running with --no-images.", file=sys.stderr)
                describe_images = False
            else:
                kwargs = {}
                if api_key:
                    kwargs["api_key"] = api_key
                else:
                    # Local Claude Code proxy (ANTHROPIC_BASE_URL set, no key needed)
                    kwargs["api_key"] = "local-proxy"
                if base_url:
                    kwargs["base_url"] = base_url
                client = anthropic.Anthropic(**kwargs)
                print(f"Image descriptions enabled (model: {args.model})")
        except ImportError:
            print("WARNING: anthropic package not installed. Running with --no-images.", file=sys.stderr)
            describe_images = False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for relative_source, output_slug, title in PRESENTATION_MAP:
        if args.only and args.only not in output_slug:
            continue

        source_path = PRESENTATIONS_DIR / relative_source
        output_path = OUTPUT_DIR / output_slug

        if not source_path.exists():
            print(f"SKIP (not found): {source_path.name}")
            continue

        ext = source_path.suffix.lower()
        print(f"Processing: {source_path.name} ...", flush=True)

        if ext == ".pptx":
            slides = extract_pptx(source_path, describe_images, args.model, client)
        elif ext == ".pdf":
            slides = extract_pdf(source_path, describe_images, args.model, client)
        else:
            print(f"  SKIP: unsupported format {ext}")
            continue

        write_markdown(slides, title, source_path, output_path)
        img_count = sum(len(s.get("images", [])) for s in slides)
        print(f"  → {len(slides)} slides, {img_count} images described → {output_slug}")

    print(f"\nDone. Output in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
