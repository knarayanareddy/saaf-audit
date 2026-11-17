"""
work_program_generator.py — SAAF UC 8: Audit Work Program Agent
Generates a structured audit work program from a Risk & Control Matrix (RCM).

Usage:
    python tools/scripts/work_program_generator.py rcm.json auditors.json

Input:
    rcm.json      — list of risks, each with one or more controls
    auditors.json — list of auditors with skills and available hours

Output (written to outputs/work-programs/):
    work_program.json
    work_program.md

Requires: ANTHROPIC_API_KEY environment variable
See: plans/hackathon-2/inge-garretsen-audit-work-program-agent.md
"""

import json
import logging
import os
import sys
from pathlib import Path

import anthropic

# Load .env from repo root if present (keeps API key out of shell history)
_env_file = Path(__file__).parents[2] / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an internal audit work program specialist.
Generate a work program entry for one control from a Risk & Control Matrix (RCM).
Comply with GIAS 13.5 (resources) and GIAS 13.6 (work program structure).

Structure your response in this exact phase order:

CONTEXT
  risk_id, risk, significance, control_id, control, control_type
  control_objective   — one sentence: which specific error/deviation does this control prevent or detect?
  control_frequency   — e.g. per transaction / daily / monthly / ad hoc
  control_owner       — role responsible (from input; null if not provided)

DESIGN
  test_of_design: { step, methodology, evidence, pass_criteria, estimated_hours, skill_required, assigned_to }

EXECUTION — tests_of_effectiveness (list, one or more):
  Each item:
    population          — scope universe, source system, period (e.g. "All payment runs > €10k — ERP — Jan–Dec 2025")
    sampling_approach   — { method: judgmental|random|full population|stratified|exception-based, sample_size, rationale }
    step                — what is tested
    methodology         — inquiry | observation | inspection | re-performance | analytical procedure
    caat_tool           — Python / SQL / Claude Code (null if not applicable)
    caat_pseudocode     — brief outline (null if not applicable)
    evidence            — required evidence source
    pass_criteria       — when is the test passed?
    estimated_hours
    skill_required
    assigned_to         — resolved from skill_required via auditor_pool; null if no match
    observed_exceptions — [] at planning stage
    conclusion          — null at planning stage

QA
  sufficiency_flags — list, include all that apply:
    INQUIRY_ONLY            high-significance risk with inquiry as sole method for all ToE steps
    EVIDENCE_MISSING        no evidence source specified for a test step
    SAMPLE_TOO_SMALL        sample size below 25 for population > 100 without justification
    POPULATION_NOT_RECONCILED  population has no tie-out to a system record or report
    PERIOD_INCOMPLETE       evidence period does not cover the full audit scope period
    INDEPENDENCE_GAP        control owner is also primary evidence provider with no independent corroboration

EVALUATION
  overall_conclusion — null at planning stage

Rules:
- Respond in valid JSON only. No prose outside the JSON.
- Never fabricate control descriptions, owners, or frequencies — use only what is in the input.
- Set unknown fields to null.
- assigned_to must be a name from auditor_pool matching skill_required; null if no match.
"""


def build_prompt(risk: dict, control: dict, auditors: list[dict]) -> str:
    return json.dumps({"risk": risk, "control": control, "auditor_pool": auditors}, indent=2)


def call_claude(client: anthropic.Anthropic, risk: dict, control: dict, auditors: list[dict]) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(risk, control, auditors)}],
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def _steps(entry: dict) -> list[dict]:
    """Return all test steps from an entry regardless of nesting structure."""
    tod = (entry.get("DESIGN") or entry).get("test_of_design")
    toes = (entry.get("EXECUTION") or entry).get("tests_of_effectiveness", []) or []
    return [s for s in ([tod] + toes) if s]


def check_resources(work_program: list[dict], auditors: list[dict]) -> list[dict]:
    """Return auditors whose total assigned hours exceed their availability."""
    hours_used: dict[str, float] = {}
    for entry in work_program:
        for step in _steps(entry):
            if step.get("assigned_to"):
                name = step["assigned_to"]
                hours_used[name] = hours_used.get(name, 0) + (step.get("estimated_hours") or 0)

    return [
        {
            "auditor": a["name"],
            "assigned_hours": hours_used.get(a["name"], 0),
            "available_hours": a["available_hours"],
            "overrun": hours_used.get(a["name"], 0) - a["available_hours"],
        }
        for a in auditors
        if hours_used.get(a["name"], 0) > a["available_hours"]
    ]


def _get(entry: dict, *keys: str) -> object:
    """Walk nested keys, return None if any key is missing."""
    for key in keys:
        if not isinstance(entry, dict):
            return None
        entry = entry.get(key)
    return entry


def to_markdown(work_program: list[dict], alerts: list[dict]) -> str:
    lines = ["# Audit Work Program\n"]

    for e in work_program:
        ctx = e.get("CONTEXT") or e
        control_id = ctx.get("control_id", "?")
        lines.append(f"## {control_id} — {ctx.get('control', '')}\n")
        lines.append(f"**Risk:** {ctx.get('risk_id')} · {ctx.get('risk', '')}  ")
        lines.append(f"**Significance:** {ctx.get('significance')}  ")
        lines.append(f"**Control objective:** {ctx.get('control_objective')}  ")
        lines.append(f"**Frequency:** {ctx.get('control_frequency')} · **Owner:** {ctx.get('control_owner')}\n")

        tod = ((e.get("DESIGN") or e).get("test_of_design")) or {}
        evidence = tod.get("evidence")
        if isinstance(evidence, list):
            evidence = "; ".join(evidence)
        lines += [
            "### Test of Design",
            f"- **Step:** {tod.get('step')}",
            f"- **Method:** {tod.get('methodology')} · **Evidence:** {evidence}",
            f"- **Pass criteria:** {tod.get('pass_criteria')}",
            f"- **Hours:** {tod.get('estimated_hours')} · **Assigned:** {tod.get('assigned_to')}\n",
        ]

        toes = (e.get("EXECUTION") or e).get("tests_of_effectiveness") or []
        for i, toe in enumerate(toes, 1):
            sa = toe.get("sampling_approach") or {}
            lines += [
                f"### Test of Effectiveness {i}",
                f"- **Population:** {toe.get('population')}",
                f"- **Sampling:** {sa.get('method')} · size: {sa.get('sample_size')} — {sa.get('rationale')}",
                f"- **Step:** {toe.get('step')}",
                f"- **Method:** {toe.get('methodology')}",
            ]
            if toe.get("caat_tool"):
                lines.append(f"- **CAAT:** {toe.get('caat_tool')} — `{toe.get('caat_pseudocode')}`")
            lines += [
                f"- **Evidence:** {toe.get('evidence')}",
                f"- **Pass criteria:** {toe.get('pass_criteria')}",
                f"- **Hours:** {toe.get('estimated_hours')} · **Assigned:** {toe.get('assigned_to')}\n",
            ]

        flags = (e.get("QA") or e).get("sufficiency_flags") or []
        if flags:
            # flags can be strings or dicts {"flag": "...", "reason": "..."}
            flag_labels = [f if isinstance(f, str) else f.get("flag", str(f)) for f in flags]
            lines.append(f"**Sufficiency flags:** {', '.join(flag_labels)}\n")
        lines.append("---\n")

    if alerts:
        lines.append("## Resource Alerts\n")
        for a in alerts:
            lines.append(
                f"- **{a['auditor']}**: {a['assigned_hours']}h assigned / "
                f"{a['available_hours']}h available — overrun: {a['overrun']}h"
            )

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: python tools/scripts/work_program_generator.py rcm.json auditors.json")

    rcm = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    auditors = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    client = anthropic.Anthropic()

    work_program = []
    for risk in rcm:
        for control in risk.get("controls", []):
            log.info("Processing %s / %s ...", risk["risk_id"], control["control_id"])
            entry = call_claude(client, risk, control, auditors)
            work_program.append(entry)

    alerts = check_resources(work_program, auditors)

    out_dir = Path(__file__).parents[2] / "outputs" / "work-programs"
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {"work_program": work_program, "resource_alerts": alerts}
    (out_dir / "work_program.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "work_program.md").write_text(
        to_markdown(work_program, alerts), encoding="utf-8"
    )

    log.info(
        "Done — %d entr%s, %d resource alert(s). Output: %s",
        len(work_program),
        "y" if len(work_program) == 1 else "ies",
        len(alerts),
        out_dir,
    )


if __name__ == "__main__":
    main()
