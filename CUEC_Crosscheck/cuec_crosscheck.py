"""
CUEC Crosscheck Agent
Matches Complementary User Entity Controls (CUECs) from a vendor assurance report
(ISAE 3402 / SOC 2) to controls in the organization's own assurance documentation.

Usage:
    python3 cuec_crosscheck.py \
        --vendor-report sample_inputs/vendor_soc2_excerpt.txt \
        --org-report sample_inputs/org_controls_excerpt.txt \
        --output-dir output

Supported input formats: PDF, DOCX, TXT
Outputs: cuec_matches.md, cuec_matches.csv, gap_findings.json, report.html
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import anthropic
from loguru import logger

# Stderr sink only at startup; file sink is added in main() once output_dir is known.
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "cuec-crosscheck.md"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192


def _read_system_prompt() -> str:
    if not SYSTEM_PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found: {SYSTEM_PROMPT_PATH}")
    text = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    # Extract the system context block (between "## System Context" and "## User Prompt Template")
    start = text.find("## System Context\n")
    end = text.find("\n## User Prompt Template")
    if start == -1 or end == -1:
        return text
    return text[start + len("## System Context\n"):end].strip()


def _extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.error("pypdf not installed. Install with: pip install pypdf")
            sys.exit(1)
    elif suffix == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            logger.error("python-docx not installed. Install with: pip install python-docx")
            sys.exit(1)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported: PDF, DOCX, TXT")


def _extract_json_block(text: str, start_marker: str) -> Optional[list]:
    """Extract the first JSON array after start_marker."""
    idx = text.find(start_marker)
    if idx == -1:
        idx = 0
    bracket_start = text.find("[", idx)
    if bracket_start == -1:
        return None
    depth = 0
    for i in range(bracket_start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[bracket_start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _count_cuecs_in_vendor_report(vendor_text: str) -> list[str]:
    """Pre-quality check: ask Claude to list every CUEC ID present in the vendor report.

    Returns a list of CUEC IDs so the caller can verify completeness after the crosscheck.
    Uses a focused, low-token call independent of the main crosscheck prompt.
    """
    client = anthropic.Anthropic()
    user_content = (
        "You are an audit assistant performing a completeness check.\n"
        "Read the vendor assurance report below and list every Complementary User Entity "
        "Control (CUEC) you can find. CUECs appear under headings such as "
        "'Complementary User Entity Controls', 'User Control Considerations', or embedded "
        "within individual control activities.\n\n"
        "Return ONLY a JSON array of CUEC IDs, e.g.: [\"UEC-01\", \"UEC-02\"]\n"
        "If the document uses no explicit IDs, assign sequential IDs (UEC-01, UEC-02, ...).\n"
        "Do not include any other text.\n\n"
        f"Vendor assurance report:\n{vendor_text}"
    )

    logger.info("Pre-quality check: scanning vendor report for CUEC inventory...")
    t0 = time.perf_counter()
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_content}],
    )
    elapsed = time.perf_counter() - t0

    raw = message.content[0].text.strip()
    logger.debug("Pre-check raw response:\n{}", raw)
    logger.info(
        "Pre-check API call | message_id={} | stop_reason={} | elapsed={:.1f}s"
        " | input_tokens={} | output_tokens={}",
        message.id,
        message.stop_reason,
        elapsed,
        message.usage.input_tokens,
        message.usage.output_tokens,
    )

    cuec_ids: list[str] = _extract_json_block(raw, "") or []
    if not cuec_ids:
        logger.warning("Pre-check: could not parse CUEC ID list from response — completeness check will be skipped")
    else:
        logger.info("Pre-check: found {} CUECs in vendor report: {}", len(cuec_ids), cuec_ids)

    return cuec_ids


def run_crosscheck(vendor_text: str, org_text: str) -> tuple[list, list]:
    """Call Claude to match CUECs. Returns (matches, gap_findings)."""
    system = _read_system_prompt()
    prompt_sha256 = hashlib.sha256(system.encode()).hexdigest()[:12]
    logger.info("System prompt SHA-256 (12-char prefix): {}", prompt_sha256)

    client = anthropic.Anthropic()

    user_content = (
        "Document 1 (vendor assurance report):\n"
        f"{vendor_text}\n\n"
        "---\n\n"
        "Document 2 (organizational control report):\n"
        f"{org_text}\n\n"
        "---\n\n"
        "Extract all CUECs from Document 1 and match each one to the most relevant control "
        "in Document 2.\n\n"
        "Return:\n"
        "1. A JSON array of CUEC match results labelled CUEC_MATCHES\n"
        "2. A JSON array of gap findings labelled GAP_FINDINGS\n\n"
        "Use these exact labels on their own lines before each array."
    )

    logger.info("Crosscheck: calling Claude (model={}, max_tokens={})...", MODEL, MAX_TOKENS)
    t0 = time.perf_counter()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    elapsed = time.perf_counter() - t0

    logger.info(
        "Crosscheck API call | message_id={} | stop_reason={} | elapsed={:.1f}s"
        " | input_tokens={} | output_tokens={}",
        message.id,
        message.stop_reason,
        elapsed,
        message.usage.input_tokens,
        message.usage.output_tokens,
    )
    if message.stop_reason == "max_tokens":
        logger.warning(
            "Response was cut off at max_tokens={} — output may be incomplete. "
            "Consider increasing MAX_TOKENS.",
            MAX_TOKENS,
        )

    raw = message.content[0].text

    # Everything Claude wrote before the CUEC_MATCHES label is its chain-of-thought reasoning.
    cot_end = raw.find("CUEC_MATCHES")
    if cot_end > 0:
        logger.debug("Claude CoT reasoning:\n{}", raw[:cot_end].strip())
    logger.debug("Claude full raw response:\n{}", raw)

    matches = _extract_json_block(raw, "CUEC_MATCHES") or []
    gap_findings = _extract_json_block(raw, "GAP_FINDINGS") or []

    if not matches:
        logger.warning("Parsing produced 0 CUEC matches — check raw response in debug log")
    if not gap_findings:
        logger.debug("No gap findings parsed (may be expected if all CUECs matched)")

    # Re-number gap finding IDs sequentially if Claude used inconsistent numbering
    for i, finding in enumerate(gap_findings, start=1):
        finding["id"] = f"F-{i:02d}"
        finding.setdefault("ai_assisted", True)
        finding.setdefault("status", "Open")

    # Log each individual match decision for audit trail
    for m in matches:
        logger.debug(
            "Match decision | {} | status={} | org_ref={} | rationale={}",
            m.get("cuec_id"),
            m.get("match_status"),
            m.get("org_control_ref") or "—",
            m.get("rationale"),
        )

    logger.info(
        "Parsed {} CUEC matches ({} gap findings)",
        len(matches),
        len(gap_findings),
    )
    return matches, gap_findings


def write_markdown_table(matches: list, output_path: Path) -> None:
    lines = [
        "# CUEC Crosscheck Results\n",
        "| CUEC ID | CUEC Description | Match Status | Org Control Ref | Org Control Description | Rationale |",
        "|---|---|---|---|---|---|",
    ]
    for m in matches:
        status = m.get("match_status", "")
        badge = {"Matched": "✅ Matched", "Partial": "⚠️ Partial", "No match": "❌ No match"}.get(status, status)
        row = [
            m.get("cuec_id", ""),
            m.get("cuec_description", "").replace("|", "\\|").replace("\n", " "),
            badge,
            m.get("org_control_ref") or "—",
            (m.get("org_control_description") or "—").replace("|", "\\|").replace("\n", " "),
            (m.get("rationale") or "").replace("|", "\\|").replace("\n", " "),
        ]
        lines.append("| " + " | ".join(row) + " |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Markdown table written to {}", output_path)


def write_csv(matches: list, output_path: Path) -> None:
    fieldnames = [
        "cuec_id", "cuec_description", "match_status",
        "org_control_ref", "org_control_description", "rationale",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(matches)
    logger.info("CSV written to {}", output_path)


def write_gap_findings(gap_findings: list, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(gap_findings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Gap findings JSON written to {}", output_path)


def _compute_rag(matches: list) -> str:
    """Red if any No match, Amber if any Partial, Green if all Matched."""
    statuses = [m.get("match_status", "") for m in matches]
    if "No match" in statuses:
        return "Red"
    if "Partial" in statuses:
        return "Amber"
    return "Green"


def write_html_report(
    matches: list,
    gap_findings: list,
    vendor_report_name: str,
    org_report_name: str,
    output_path: Path,
) -> None:
    rag = _compute_rag(matches)
    total = len(matches)
    matched = sum(1 for m in matches if m.get("match_status") == "Matched")
    partial = sum(1 for m in matches if m.get("match_status") == "Partial")
    no_match = sum(1 for m in matches if m.get("match_status") == "No match")

    rag_colors = {"Red": "#FF6B6B", "Amber": "#FFD93D", "Green": "#6BCB77"}
    rag_text_colors = {"Red": "#7a0000", "Amber": "#5c4200", "Green": "#1a4d1a"}
    rag_color = rag_colors[rag]
    rag_text = rag_text_colors[rag]

    status_styles = {
        "Matched": "background:#6BCB77; color:#1a4d1a",
        "Partial": "background:#FFD93D; color:#5c4200",
        "No match": "background:#FF6B6B; color:#7a0000",
    }
    risk_styles = {
        "High": "background:#FF6B6B; color:#7a0000",
        "Medium": "background:#FFD93D; color:#5c4200",
        "Low": "background:#FFFACD; color:#4a4a00",
        "Informational": "background:#E0E0E0; color:#333",
    }

    def esc(s: object) -> str:
        return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Build CUEC match rows
    match_rows = ""
    for m in matches:
        status = m.get("match_status", "")
        style = status_styles.get(status, "")
        match_rows += f"""
        <tr>
          <td><strong>{esc(m.get('cuec_id'))}</strong></td>
          <td>{esc(m.get('cuec_description'))}</td>
          <td><span class="badge" style="{style}">{esc(status)}</span></td>
          <td>{esc(m.get('org_control_ref') or '—')}</td>
          <td>{esc(m.get('org_control_description') or '—')}</td>
          <td>{esc(m.get('rationale'))}</td>
        </tr>"""

    # Build gap findings rows
    gap_rows = ""
    for f in gap_findings:
        risk = f.get("risk_rating", "")
        style = risk_styles.get(risk, "")
        gap_rows += f"""
        <tr>
          <td><strong>{esc(f.get('id'))}</strong></td>
          <td>{esc(f.get('title'))}</td>
          <td><span class="badge" style="{style}">{esc(risk)}</span></td>
          <td>{esc(f.get('observation'))}</td>
          <td>{esc(f.get('recommendation'))}</td>
        </tr>"""

    gaps_section = ""
    if gap_findings:
        gaps_section = f"""
    <h2>Gap Findings</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th><th>Title</th><th>Risk Rating</th>
          <th>Observation</th><th>Recommendation</th>
        </tr>
      </thead>
      <tbody>{gap_rows}</tbody>
    </table>"""

    from datetime import date
    run_date = date.today().isoformat()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CUEC Crosscheck Report</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 40px auto; color: #222; padding: 0 20px; }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #2c3e50; padding-bottom: 8px; }}
  h2 {{ color: #2c3e50; margin-top: 40px; }}
  .meta {{ color: #555; margin-bottom: 32px; font-size: 14px; }}
  .rag-banner {{
    background: {rag_color};
    color: {rag_text};
    border-radius: 8px;
    padding: 24px 32px;
    margin: 24px 0;
    display: flex;
    align-items: center;
    gap: 32px;
  }}
  .rag-label {{ font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
  .rag-status {{ font-size: 48px; font-weight: bold; }}
  .rag-desc {{ font-size: 15px; }}
  .stats {{ display: flex; gap: 16px; margin: 24px 0; flex-wrap: wrap; }}
  .stat-box {{
    background: #f5f5f5;
    border-radius: 8px;
    padding: 16px 24px;
    text-align: center;
    min-width: 120px;
  }}
  .stat-box .num {{ font-size: 36px; font-weight: bold; color: #2c3e50; }}
  .stat-box .lbl {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }}
  th {{ background: #2c3e50; color: white; padding: 10px 12px; text-align: left; }}
  td {{ border: 1px solid #ddd; padding: 8px 12px; vertical-align: top; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
  .footer {{ margin-top: 48px; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 12px; }}
</style>
</head>
<body>

<h1>CUEC Crosscheck Report</h1>
<div class="meta">
  <strong>Vendor report:</strong> {esc(vendor_report_name)} &nbsp;|&nbsp;
  <strong>Organizational report:</strong> {esc(org_report_name)} &nbsp;|&nbsp;
  <strong>Run date:</strong> {run_date}
</div>

<div class="rag-banner">
  <div>
    <div class="rag-label">Overall RAG Status</div>
    <div class="rag-status">{rag}</div>
  </div>
  <div class="rag-desc">
    {"One or more CUECs have no matching organizational control. Gaps require immediate remediation." if rag == "Red" else
     "One or more CUECs are only partially covered. Auditor review and remediation recommended." if rag == "Amber" else
     "All CUECs are matched to organizational controls. No gaps identified."}
  </div>
</div>

<div class="stats">
  <div class="stat-box"><div class="num">{total}</div><div class="lbl">Total CUECs</div></div>
  <div class="stat-box" style="background:#e8f8ec"><div class="num" style="color:#1a4d1a">{matched}</div><div class="lbl">Matched</div></div>
  <div class="stat-box" style="background:#fffbe6"><div class="num" style="color:#5c4200">{partial}</div><div class="lbl">Partial</div></div>
  <div class="stat-box" style="background:#ffe8e8"><div class="num" style="color:#7a0000">{no_match}</div><div class="lbl">No Match</div></div>
  <div class="stat-box"><div class="num">{len(gap_findings)}</div><div class="lbl">Gap Findings</div></div>
</div>

<h2>CUEC Match Results</h2>
<table>
  <thead>
    <tr>
      <th>CUEC ID</th><th>CUEC Description</th><th>Match Status</th>
      <th>Org Control Ref</th><th>Org Control Description</th><th>Rationale</th>
    </tr>
  </thead>
  <tbody>{match_rows}</tbody>
</table>
{gaps_section}

<div class="footer">
  Generated by SAAF CUEC Crosscheck Agent &mdash; AI-assisted output. Results require auditor review before reliance.
  Part of the <a href="https://saafproject.com">SAAF Project</a>.
</div>

</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    logger.info("HTML report written to {}", output_path)


def print_summary(matches: list, gap_findings: list) -> None:
    total = len(matches)
    matched = sum(1 for m in matches if m.get("match_status") == "Matched")
    partial = sum(1 for m in matches if m.get("match_status") == "Partial")
    no_match = sum(1 for m in matches if m.get("match_status") == "No match")

    print("\n" + "=" * 50)
    print("CUEC Crosscheck Summary")
    print("=" * 50)
    print(f"  Total CUECs identified : {total}")
    print(f"  Matched                : {matched}")
    print(f"  Partial match          : {partial}")
    print(f"  No match (gaps)        : {no_match}")
    print(f"  Gap findings written   : {len(gap_findings)}")
    print("=" * 50 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CUEC Crosscheck Agent — match vendor CUECs to organizational controls"
    )
    parser.add_argument(
        "--vendor-report", required=True, type=Path,
        help="Vendor assurance report (ISAE 3402 / SOC 2) — PDF, DOCX, or TXT",
    )
    parser.add_argument(
        "--org-report", required=True, type=Path,
        help="Organizational control report — PDF, DOCX, or TXT",
    )
    parser.add_argument(
        "--output-dir", default=Path("output/cuec-crosscheck"), type=Path,
        help="Directory for output files (default: output/cuec-crosscheck)",
    )
    args = parser.parse_args()

    if not args.vendor_report.exists():
        logger.error("Vendor report not found: {}", args.vendor_report)
        sys.exit(1)
    if not args.org_report.exists():
        logger.error("Organizational report not found: {}", args.org_report)
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # File sink: DEBUG level so CoT reasoning and match decisions are captured on disk.
    log_path = args.output_dir / "cuec_crosscheck.log"
    logger.add(
        log_path,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
        encoding="utf-8",
        rotation="10 MB",
    )

    # Log input document provenance for audit trail.
    vendor_path = args.vendor_report.resolve()
    org_path = args.org_report.resolve()
    logger.info(
        "Input | vendor_report={} | size={} bytes",
        vendor_path,
        vendor_path.stat().st_size,
    )
    logger.info(
        "Input | org_report={} | size={} bytes",
        org_path,
        org_path.stat().st_size,
    )
    logger.info("Output directory: {}", args.output_dir.resolve())

    logger.info("Reading vendor report: {}", args.vendor_report)
    vendor_text = _extract_text_from_file(args.vendor_report)

    logger.info("Reading organizational report: {}", args.org_report)
    org_text = _extract_text_from_file(args.org_report)

    # --- Pre-quality check: establish expected CUEC count before crosscheck ---
    expected_ids = _count_cuecs_in_vendor_report(vendor_text)
    expected_count = len(expected_ids)

    # --- Main crosscheck ---
    matches, gap_findings = run_crosscheck(vendor_text, org_text)

    # --- Completeness check: every CUEC from the pre-check must appear in the output ---
    actual_ids = [m.get("cuec_id", "") for m in matches]
    actual_count = len(actual_ids)

    if not expected_ids:
        logger.warning("Completeness check SKIPPED — pre-check returned no CUEC IDs")
    elif actual_count == expected_count and set(actual_ids) == set(expected_ids):
        logger.info(
            "Completeness check PASSED: {}/{} CUECs accounted for in output",
            actual_count,
            expected_count,
        )
    else:
        missing = sorted(set(expected_ids) - set(actual_ids))
        extra = sorted(set(actual_ids) - set(expected_ids))
        logger.error(
            "Completeness check FAILED: expected {} CUECs, output contains {}",
            expected_count,
            actual_count,
        )
        if missing:
            logger.error("CUECs present in vendor report but missing from output: {}", missing)
        if extra:
            logger.warning("CUECs in output not found in pre-check inventory: {}", extra)

    write_markdown_table(matches, args.output_dir / "cuec_matches.md")
    write_csv(matches, args.output_dir / "cuec_matches.csv")
    write_gap_findings(gap_findings, args.output_dir / "gap_findings.json")
    write_html_report(
        matches, gap_findings,
        args.vendor_report.name, args.org_report.name,
        args.output_dir / "report.html",
    )

    print_summary(matches, gap_findings)
    print(f"Outputs written to: {args.output_dir}/")
    print("  report.html           — RAG status report (open in browser)")
    print("  cuec_matches.md       — Markdown table for review")
    print("  cuec_matches.csv      — CSV for import into Google Sheets / Excel")
    print("  gap_findings.json     — Gap findings conforming to SAAF finding schema")
    print(f"  cuec_crosscheck.log   — Full audit log incl. CoT reasoning (DEBUG)")


if __name__ == "__main__":
    main()
