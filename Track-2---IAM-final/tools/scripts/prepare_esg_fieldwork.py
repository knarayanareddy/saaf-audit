#!/usr/bin/env python3
"""
prepare_esg_fieldwork.py
Generates ESG audit fieldwork artefacts using the Claude API.

Reads the ESG fieldwork preparation system prompt from
prompts/audit-use-cases/ia-fieldwork-preparation-esg.md, sends it to Claude
together with the audit scope and selected standards, and writes three output
files to hackathon-recap/esg-fieldwork/ (or a custom output directory):
  - fieldwork-plan.md   — test procedures and interview questions
  - pbc-list.md         — document request list
  - findings.json       — indicative findings in SAAF finding schema format

Usage:
    python3 tools/scripts/prepare_esg_fieldwork.py \\
        --scope "Climate risk integration in the credit risk framework" \\
        --standards "ECB Guide expectations 7-9" "EBA loan origination guidelines" \\
        --institution "Dutch commercial bank" \\
        --period "January 2025 - December 2025"

Requirements:
    pip install anthropic
    ANTHROPIC_API_KEY environment variable must be set.
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parents[2]
PROMPT_FILE = REPO_ROOT / "prompts" / "audit-use-cases" / "ia-fieldwork-preparation-esg.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "hackathon-recap" / "esg-fieldwork"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192


def load_system_prompt() -> str:
    if not PROMPT_FILE.exists():
        logger.error("System prompt not found: %s", PROMPT_FILE)
        raise SystemExit(1)
    text = PROMPT_FILE.read_text(encoding="utf-8")
    # Extract the system context block (between the two --- separators after metadata)
    match = re.search(r"## System Context\n\n(.+?)(?=\n---\n)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fall back to full file if structure differs
    return text


def build_user_prompt(
    scope: str,
    standards: list,
    institution: str,
    period: str,
    context: Optional[str],
) -> str:
    standards_block = "\n".join(f"- {s}" for s in standards)
    context_block = f"\nAdditional context:\n- {context}" if context else ""

    return f"""\
I am performing an internal audit of {scope} at {institution}.

Audit period: {period}

Applicable standards:
{standards_block}
{context_block}

Please produce the following:

1. **Fieldwork plan** — for each applicable supervisory expectation, provide:
   - Two to four test procedures (what to inspect, sample, or observe)
   - Two to three interview questions (for risk managers, the CRO, or business line owners)
   - The risk rating of non-compliance (High / Medium / Low)

2. **PBC list** — a Markdown table with columns: #, Document requested, Responsible owner, Standard reference

3. **Indicative findings** — for each test procedure, provide an indicative finding in this JSON structure:
   {{
     "id": "F-01",
     "title": "<Short finding title>",
     "risk_rating": "High | Medium | Low | Informational",
     "control_objective": "<Regulatory expectation reference>",
     "observation": "<What the auditor would observe if the control is absent or inadequate>",
     "recommendation": "<What the institution should do to remediate>",
     "ai_assisted": true,
     "status": "Open"
   }}

Present the fieldwork plan and PBC list in Markdown. Present findings as a JSON array enclosed in a ```json code block.
Do not include real names, client data, or confidential information in your output.
"""


def split_response(text: str) -> tuple:
    """Split Claude's response into (fieldwork_plan, pbc_list, findings_json)."""
    # Extract JSON findings block
    json_match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    findings_raw = json_match.group(1) if json_match else "[]"

    # Remove JSON block from text for cleaner Markdown splitting
    markdown_text = re.sub(r"```json.*?```", "", text, flags=re.DOTALL).strip()

    # Split fieldwork plan and PBC list on the PBC section header
    pbc_match = re.search(r"(#+\s*(?:PBC|Document Request|PBC List).*)", markdown_text, re.IGNORECASE)
    if pbc_match:
        split_pos = pbc_match.start()
        fieldwork_plan = markdown_text[:split_pos].strip()
        pbc_list = markdown_text[split_pos:].strip()
    else:
        fieldwork_plan = markdown_text
        pbc_list = ""

    return fieldwork_plan, pbc_list, findings_raw


def validate_findings(findings_raw: str) -> list:
    """Parse and basic-validate findings against required SAAF schema fields."""
    required_fields = {"id", "title", "risk_rating", "observation", "recommendation"}
    valid_ratings = {"High", "Medium", "Low", "Informational"}
    id_pattern = re.compile(r"^F-\d{2,4}$")

    try:
        findings = json.loads(findings_raw)
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse findings JSON: %s", exc)
        return []

    validated = []
    for i, finding in enumerate(findings):
        missing = required_fields - set(finding.keys())
        if missing:
            logger.warning("Finding %d missing required fields: %s — skipped", i + 1, missing)
            continue
        if not id_pattern.match(finding["id"]):
            logger.warning("Finding %s has invalid id format — skipped", finding.get("id"))
            continue
        if finding["risk_rating"] not in valid_ratings:
            logger.warning("Finding %s has invalid risk_rating '%s' — skipped", finding["id"], finding["risk_rating"])
            continue
        validated.append(finding)

    logger.info("Validated %d/%d findings", len(validated), len(findings))
    return validated


def write_outputs(
    output_dir: Path,
    scope: str,
    fieldwork_plan: str,
    pbc_list: str,
    findings: list,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_file = output_dir / "fieldwork-plan.md"
    pbc_file = output_dir / "pbc-list.md"
    findings_file = output_dir / "findings.json"

    header = f"# ESG Audit Fieldwork Plan\n\n**Audit scope:** {scope}\n\n---\n\n"
    plan_file.write_text(header + fieldwork_plan, encoding="utf-8")
    logger.info("Written fieldwork plan → %s", plan_file)

    if pbc_list:
        pbc_file.write_text(f"# PBC List — ESG Audit\n\n**Audit scope:** {scope}\n\n---\n\n" + pbc_list, encoding="utf-8")
        logger.info("Written PBC list → %s", pbc_file)

    findings_file.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Written %d findings → %s", len(findings), findings_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ESG audit fieldwork artefacts using Claude API.")
    parser.add_argument("--scope", required=True, help="Audit scope description (e.g. 'Climate risk in credit risk framework')")
    parser.add_argument("--standards", required=True, nargs="+", help="Applicable standards (one or more strings)")
    parser.add_argument("--institution", default="a financial institution", help="Institution type (e.g. 'Dutch commercial bank')")
    parser.add_argument("--period", default="current year", help="Audit period (e.g. 'January 2025 - December 2025')")
    parser.add_argument("--context", default=None, help="Optional additional context for the audit scope")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to write output files")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        raise SystemExit(1)

    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed — run: pip install anthropic")
        raise SystemExit(1)

    system_prompt = load_system_prompt()
    user_prompt = build_user_prompt(
        scope=args.scope,
        standards=args.standards,
        institution=args.institution,
        period=args.period,
        context=args.context,
    )

    logger.info("Calling Claude API (model: %s)", MODEL)
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text
    logger.info("Received response (%d chars)", len(raw_text))

    fieldwork_plan, pbc_list, findings_raw = split_response(raw_text)
    findings = validate_findings(findings_raw)

    output_dir = Path(args.output_dir)
    write_outputs(output_dir, args.scope, fieldwork_plan, pbc_list, findings)

    print(f"\nDone — outputs written to {output_dir}/")
    print(f"  fieldwork-plan.md  ({len(fieldwork_plan)} chars)")
    print(f"  pbc-list.md        ({len(pbc_list)} chars)")
    print(f"  findings.json      ({len(findings)} findings)")


if __name__ == "__main__":
    main()
