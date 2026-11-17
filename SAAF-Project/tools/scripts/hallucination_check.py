#!/usr/bin/env python3
"""
hallucination_check.py
Validate factual claims in SAAF audit findings using Claude API.

Usage:
    python3 tools/scripts/hallucination_check.py outputs/examples/synthetic-findings/F-0101.json
    python3 tools/scripts/hallucination_check.py outputs/examples/synthetic-findings/  # batch

Output:
    <input_stem>_checked.json   Annotated finding with hallucination_check block
    outputs/logs/hallucination-checks.jsonl  Append-only audit log
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import anthropic

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
LOG_PATH = Path(__file__).parents[2] / "outputs" / "logs" / "hallucination-checks.jsonl"

# ── Prompts ────────────────────────────────────────────────────────────────────

CLAIM_EXTRACTION_SYSTEM = """\
You are an audit quality control assistant. Extract every factual claim from an \
audit finding.

A "factual claim" references:
- A specific standard, framework, regulation, or article number \
(e.g. "ISO 27001 clause 6.1", "DORA Article 13")
- A specific control name, control number, or control domain
- A date, deadline, or time-bound requirement
- A numeric threshold or percentage
- A named system, tool, vendor, or process

Return a JSON array. Each element:
{
  "claim": "<exact quoted text>",
  "claim_type": "<standard_reference|control_name|date_threshold|numeric_value|system_name|other>",
  "verifiable": <true|false>
}

Return ONLY the JSON array, no prose."""

CLAIM_VERIFICATION_SYSTEM = """\
You are an audit evidence verification assistant with knowledge of common audit \
standards: ISO 27001:2022, IIA Standards (2024), DORA, NIS2, GDPR, EU AI Act, \
COBIT 2019, and BIO.

For each claim determine:
- SUPPORTED: accurately matches the referenced source
- UNVERIFIED: cannot confirm or deny from available knowledge
- LIKELY_HALLUCINATED: appears factually incorrect (wrong article, non-existent \
clause, misquoted threshold)

Return a JSON object only:
{
  "verdict": "SUPPORTED|UNVERIFIED|LIKELY_HALLUCINATED",
  "confidence": "High|Medium|Low",
  "reason": "<one sentence>",
  "corrected_reference": "<correct reference if LIKELY_HALLUCINATED, else null>"
}"""

RISK_AGGREGATION_SYSTEM = """\
You are an audit quality gate. Aggregate claim verification results into an \
overall hallucination risk score.

Rules:
- ANY LIKELY_HALLUCINATED with High confidence → overall_risk = HIGH (blocked = true)
- 2+ UNVERIFIED claims → overall_risk = MEDIUM (blocked = false)
- Otherwise → overall_risk = LOW (blocked = false)

Return a JSON object only:
{
  "overall_risk": "HIGH|MEDIUM|LOW",
  "blocked": <true|false>,
  "summary": "<one sentence for the auditor>",
  "flagged_claims": [<LIKELY_HALLUCINATED claim texts>],
  "unverified_claims": [<UNVERIFIED claim texts>]
}"""


# ── API helpers ────────────────────────────────────────────────────────────────

def _call(client: anthropic.Anthropic, system: str, user: str, max_tokens: int) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def extract_claims(client: anthropic.Anthropic, finding_text: str) -> List[Dict]:
    raw = _call(client, CLAIM_EXTRACTION_SYSTEM, f"Finding:\n{finding_text}", 1024)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Claim extraction returned non-JSON; returning empty list")
        return []


def verify_claim(client: anthropic.Anthropic, claim: Dict) -> Dict:
    user = (
        f"Claim: {claim['claim']}\n"
        f"Claim type: {claim['claim_type']}"
    )
    raw = _call(client, CLAIM_VERIFICATION_SYSTEM, user, 512)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "UNVERIFIED", "confidence": "Low",
                "reason": "Verification response was not valid JSON.",
                "corrected_reference": None}


def aggregate_risk(client: anthropic.Anthropic, claim_results: List[Dict]) -> Dict:
    if not claim_results:
        return {
            "overall_risk": "LOW",
            "blocked": False,
            "summary": "No verifiable claims found in this finding.",
            "flagged_claims": [],
            "unverified_claims": [],
        }
    raw = _call(client, RISK_AGGREGATION_SYSTEM, json.dumps(claim_results), 512)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Risk aggregation returned non-JSON; defaulting to MEDIUM")
        return {
            "overall_risk": "MEDIUM",
            "blocked": False,
            "summary": "Risk aggregation failed; manual review required.",
            "flagged_claims": [],
            "unverified_claims": [],
        }


# ── Core logic ─────────────────────────────────────────────────────────────────

def check_finding(client: anthropic.Anthropic, finding: Dict) -> Dict:
    finding_id = finding.get("id", "unknown")
    text = " ".join(filter(None, [
        finding.get("title"),
        finding.get("observation"),
        finding.get("recommendation"),
        finding.get("control_objective"),
    ]))

    claims = extract_claims(client, text)
    log.info(f"{finding_id}: extracted {len(claims)} claims")

    verifiable = [c for c in claims if c.get("verifiable")]
    log.info(f"{finding_id}: verifying {len(verifiable)} verifiable claims")

    results: List[Dict] = []
    for claim in verifiable:
        verdict = verify_claim(client, claim)
        results.append({"claim": claim["claim"], "claim_type": claim["claim_type"], **verdict})
        log.info(f"  [{verdict['verdict']}] {claim['claim'][:80]}")

    risk = aggregate_risk(client, results)

    finding["hallucination_check"] = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "claims_checked": len(results),
        **risk,
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": finding["hallucination_check"]["run_at"],
            "finding_id": finding_id,
            "claims_checked": len(results),
            "supported": sum(1 for r in results if r.get("verdict") == "SUPPORTED"),
            "unverified": sum(1 for r in results if r.get("verdict") == "UNVERIFIED"),
            "hallucinated": sum(1 for r in results if r.get("verdict") == "LIKELY_HALLUCINATED"),
            "overall_risk": risk["overall_risk"],
            "blocked": risk["blocked"],
        }) + "\n")

    return finding


def process_path(client: anthropic.Anthropic, input_path: Path) -> None:
    if input_path.is_dir():
        paths = sorted(input_path.glob("*.json"))
        log.info(f"Batch mode: {len(paths)} findings in {input_path}")
    else:
        paths = [input_path]

    for path in paths:
        finding = json.loads(path.read_text(encoding="utf-8"))
        annotated = check_finding(client, finding)
        out = path.with_stem(path.stem + "_checked")
        out.write_text(json.dumps(annotated, indent=2), encoding="utf-8")
        risk = annotated["hallucination_check"]["overall_risk"]
        blocked = annotated["hallucination_check"]["blocked"]
        log.info(f"{path.name} → {out.name} | risk={risk} blocked={blocked}")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <finding.json | findings_dir/>")
        sys.exit(1)

    client = anthropic.Anthropic()
    process_path(client, Path(sys.argv[1]))
