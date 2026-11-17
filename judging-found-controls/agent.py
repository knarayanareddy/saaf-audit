"""
Judging Found Controls — judge-as-LLM agent for policy control validation.

Validates that each control in an extractor output JSON is grounded in the source
policy PDF. Writes judge_verdicts.json to the working directory.

Usage:
    python agent.py --controls controls.json --policy policy.pdf

Environment variables required:
    ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import anthropic
import pdfplumber

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 512

SYSTEM_PROMPT = """You are a rigorous audit evidence examiner. Your sole task is to determine whether a
structured control object is actually grounded in a supplied policy document.

## Context you will receive

The user message will contain two parts, clearly delimited:

1. POLICY TEXT — the full text of the source policy document, with page boundaries marked
   as "--- PAGE <n> ---". Treat page numbers as authoritative.
2. CONTROL JSON — a single control object extracted from that policy by an automated tool.
   It has the following fields: id, who, what, why, when, where, how, source_anchor,
   open_questions.

## Your task

Read the POLICY TEXT carefully. Then decide whether the normative requirement described in
the CONTROL's `what` field is actually stated in, or clearly and unambiguously implied by,
a specific passage in the POLICY TEXT.

Apply the following decision rules:

FOUND = "yes" if and only if:
  - The policy contains explicit normative language (shall, must, is required to, will) that
    directly supports the control's `what` field, OR
  - The policy contains language that unambiguously implies the requirement with no
    reasonable alternative interpretation.

FOUND = "no" if:
  - The control's `what` describes a requirement not mentioned in the policy at all.
  - The policy mentions the topic but only in an informative, explanatory, or aspirational
    way (e.g. "it is recommended", "may", "should consider") — normative intent is absent.
  - The control combines two separate policy statements whose combination creates a new
    requirement not individually stated.
  - The source_anchor reference in the control JSON points to a section that does not
    contain the claimed language.

PARTIAL SUPPORT: There is no "partial" verdict. If the policy partially supports the
control but key normative elements are missing (e.g. the 24-hour deadline is absent from
the text), return `found: "no"` and use the `paragraph` field to quote the closest
matching passage so the auditor can see what is actually there.

## Output format — STRICT

Return ONLY a single valid JSON object. Do not include any prose, markdown, code fences,
or explanation outside the JSON object. The object must have exactly these three keys:

{
  "found": "yes" | "no",
  "page_no": <integer — the page number of the supporting paragraph, or 0 if not found>,
  "paragraph": "<verbatim quote from the policy text, or empty string if no relevant text exists>"
}

Rules for the `paragraph` field:
- Copy the text exactly as it appears in the source, including punctuation and
  capitalisation. Do not paraphrase.
- If `found` is "yes", this must be the passage that provides the normative grounding.
- If `found` is "no" but a related passage exists, include that passage here so the
  auditor can investigate.
- If `found` is "no" and there is no related passage at all, return an empty string "".
- Keep the quote to the single most relevant sentence or clause.

## What you must never do

- Never invent or paraphrase policy text.
- Never return found: "yes" because the control seems reasonable or standard practice —
  your judgment must be anchored exclusively in the supplied POLICY TEXT.
- Never return prose outside the JSON object.
- Never omit a key or add extra keys."""


def load_controls(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "controls" in data:
        return data["controls"]
    raise ValueError(f"Unrecognised controls JSON structure in {path}")


def build_paged_policy_text(pdf_path: str) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text: Optional[str] = page.extract_text()
            pages.append(f"--- PAGE {i} ---\n{text or ''}")
    return "\n\n".join(pages)


def judge_control(
    client: anthropic.Anthropic,
    policy_text: str,
    control: dict,
) -> dict:
    user_prompt = (
        f"POLICY TEXT:\n{policy_text}\n\n"
        f"CONTROL JSON:\n{json.dumps(control, indent=2, ensure_ascii=False)}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text.strip()
    verdict = json.loads(raw)
    missing = {"found", "page_no", "paragraph"} - verdict.keys()
    if missing:
        raise ValueError(f"Verdict missing keys: {missing}")
    return verdict


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate extracted controls against the source policy PDF."
    )
    parser.add_argument("--controls", required=True, help="Path to controls JSON file")
    parser.add_argument("--policy", required=True, help="Path to source policy PDF")
    parser.add_argument("--output", default="judge_verdicts.json", help="Output file path")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Error: ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    controls = load_controls(args.controls)
    policy_text = build_paged_policy_text(args.policy)

    results = []
    for control in controls:
        control_id = control.get("id", "UNKNOWN")
        print(f"  Judging {control_id} ...", end=" ", flush=True)
        try:
            verdict = judge_control(client, policy_text, control)
            result = {"control_id": control_id, **verdict}
            print(f"found={verdict['found']}")
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"ERROR — {exc}")
            result = {
                "control_id": control_id,
                "found": "error",
                "page_no": 0,
                "paragraph": str(exc),
            }
        results.append(result)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    found = sum(1 for r in results if r["found"] == "yes")
    missing = sum(1 for r in results if r["found"] == "no")
    errors = sum(1 for r in results if r["found"] == "error")
    print(f"\nDone. {len(results)} controls judged: {found} found, {missing} not found, {errors} errors.")
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
