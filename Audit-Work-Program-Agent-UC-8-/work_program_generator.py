"""
UC8 — Audit Work Program Agent
SAAF pillar: Tools
Standards: GIAS 13.5, GIAS 13.6

Usage:
    python work_program_generator.py \
        --rcm Input/rcm_output.json \
        --resources Input/resource_directory.json \
        --output outputs/work_program.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv()  # loads .env if present; silent in CI/CD where env vars are injected

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    sys.exit(
        "ERROR: ANTHROPIC_API_KEY is not set.\n"
        "Copy .env.example to .env and add your key, or set the environment variable."
    )

AUDIT_SCOPE_PERIOD = os.environ.get("AUDIT_SCOPE_PERIOD", "Jan-Dec 2025")
## MODEL = "claude-sonnet-4-6"
## MODEL = "claude-haiku-4-5-20251001"
MODEL = "claude-opus-4-7"
MAX_TOKENS = 10000
API_ENTRYPOINT = "https://api.anthropic.com/v1/messages/batches"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# System prompt (mirrors prompts/audit-use-cases/work-program-agent.md)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an internal audit work program specialist.
Your role is to translate a Risk & Control Matrix (RCM) into a detailed,
executable engagement work program compliant with GIAS 13.5 and 13.6.

Structure every work program entry in the following phase order:

CONTEXT (FROM RCM INPUT)
- risk_id and risk description
- control_id and control description 
- control_objective: one sentence stating which specific risk or error/deviation
  this control prevents or detects
- control_frequency: (e.g. daily / monthly / per transaction / ad hoc)
- control_owner: role responsible for the control

DESIGN
- test_of_design: step, methodology, evidence, pass_criteria, estimated_hours,
  skill_required

EXECUTION (per test of effectiveness)
- population: scope universe, source system, period
- sampling_approach: method (judgmental / random / full population / stratified /
  exception-based) and sample_size
- step: what is tested
- methodology: inquiry / observation / inspection / re-performance /
  analytical procedure
- caat_tool: Python / SQL / Claude Code (null if not applicable)
- caat_pseudocode: outline of the analysis (null if not applicable)
- evidence: required evidence source
- pass_criteria: when is the test passed?
- estimated_hours
- skill_required

EVALUATION
- observed_exceptions: empty list [] at planning stage
- conclusion: null at planning stage

Always respond in valid JSON only — no markdown fences, no preamble.
Never fabricate control descriptions, owners, or frequencies.
If a field is not in the input, set it to null.

Return exactly this JSON structure per control:
{
  "risk_id": "...",
  "risk": "...",
  "significance": "...",
  "control_id": "...",
  "control": "...",
  "control_objective": "...",
  "control_frequency": "...",
  "control_owner": "...",
  "control_type": "...",
  "test_of_design": {
    "step": "...",
    "methodology": "...",
    "evidence": "...",
    "pass_criteria": "...",
    "estimated_hours": 0,
    "skill_required": "...",
    "assigned_to": null
  },
  "tests_of_effectiveness": [
    {
      "population": "...",
      "sampling_approach": {
        "method": "...",
        "sample_size": null,
        "rationale": "..."
      },
      "step": "...",
      "methodology": "...",
      "caat_tool": null,
      "caat_pseudocode": null,
      "evidence": "...",
      "pass_criteria": "...",
      "estimated_hours": 0,
      "skill_required": "...",
      "assigned_to": null,
      "observed_exceptions": [],
      "conclusion": null
    }
  ],
  "sufficiency_flags": [],
  "overall_conclusion": null
}"""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_user_prompt(control: dict, auditors: list[dict]) -> str:
    return (
        f"Here is the RCM entry:\n{json.dumps(control, indent=2, ensure_ascii=False)}\n\n"
        f"Audit scope period: {AUDIT_SCOPE_PERIOD}\n\n"
        f"Auditor resource pool:\n{json.dumps(auditors, indent=2, ensure_ascii=False)}\n\n"
        "Generate the work program steps for this control. "
        "Assign auditors based on skill_required matching their skills array. "
        "Respond in valid JSON only."
    )


# ---------------------------------------------------------------------------
# Claude API call — batch mode
# ---------------------------------------------------------------------------

def _parse_raw_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def call_claude_batch(
    controls: list[dict], auditors: list[dict]
) -> tuple[dict[str, dict | Exception], dict]:
    """Submit all controls as one batch; return (results_by_id, run_log)."""
    run_log: dict = {
        "run_started_at": datetime.now().isoformat(),
        "api_entrypoint": API_ENTRYPOINT,
        "model": MODEL,
        "system_prompt": SYSTEM_PROMPT,
        "batch_id": None,
        "requests": [],
        "responses": [],
        "token_totals": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "run_finished_at": None,
    }

    batch_requests = []
    for ctrl in controls:
        user_prompt = build_user_prompt(ctrl, auditors)
        run_log["requests"].append({
            "custom_id": ctrl["control_id"],
            "user_prompt": user_prompt,
        })
        batch_requests.append({
            "custom_id": ctrl["control_id"],
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        })

    print(f"  Submitting batch ({len(batch_requests)} requests)...")
    batch = client.messages.batches.create(requests=batch_requests)
    run_log["batch_id"] = batch.id
    print(f"  Batch ID: {batch.id}")

    while batch.processing_status != "ended":
        time.sleep(10)
        batch = client.messages.batches.retrieve(batch.id)
        c = batch.request_counts
        print(f"  Polling... {c.processing} processing / {c.succeeded} succeeded / {c.errored} errored")

    results: dict[str, dict | Exception] = {}
    total_input = 0
    total_output = 0

    for result in client.messages.batches.results(batch.id):
        response_entry: dict = {
            "custom_id": result.custom_id,
            "status": result.result.type,
            "raw_response": None,
            "input_tokens": None,
            "output_tokens": None,
        }
        if result.result.type == "succeeded":
            raw = result.result.message.content[0].text
            usage = result.result.message.usage
            response_entry["raw_response"] = raw
            response_entry["input_tokens"] = usage.input_tokens
            response_entry["output_tokens"] = usage.output_tokens
            total_input += usage.input_tokens
            total_output += usage.output_tokens
            try:
                results[result.custom_id] = _parse_raw_json(raw)
            except json.JSONDecodeError as exc:
                results[result.custom_id] = exc
        else:
            response_entry["error"] = str(result.result.error)
            results[result.custom_id] = Exception(f"Batch error: {result.result.error}")
        run_log["responses"].append(response_entry)

    run_log["token_totals"] = {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
    }
    run_log["run_finished_at"] = datetime.now().isoformat()

    return results, run_log


# ---------------------------------------------------------------------------
# Sufficiency checks (GIAS 13.6 QA flags)
# ---------------------------------------------------------------------------

SUFFICIENCY_FLAGS = {
    "INQUIRY_ONLY": (
        "All ToE steps use inquiry as sole method for a High-significance risk"
    ),
    "EVIDENCE_MISSING": (
        "No evidence source specified for a test step"
    ),
    "SAMPLE_TOO_SMALL": (
        "Sample size below 25 for population > 100 without justification"
    ),
    "POPULATION_NOT_RECONCILED": (
        "Population has no tie-out to a system record or report"
    ),
    "PERIOD_INCOMPLETE": (
        "Evidence period does not cover the full audit scope period"
    ),
    "INDEPENDENCE_GAP": (
        "Control owner is also the primary evidence provider with no independent "
        "corroboration, or the auditor assigned to test the control is also its "
        "control owner"
    ),
}


def sufficiency_check(entry: dict, significance: str) -> dict:
    flags = []
    toe_steps = entry.get("tests_of_effectiveness", [])

    # INQUIRY_ONLY
    if significance == "High" and toe_steps:
        all_inquiry = all(
            (s.get("methodology") or "").lower() == "inquiry"
            for s in toe_steps
        )
        if all_inquiry:
            flags.append("INQUIRY_ONLY")

    # EVIDENCE_MISSING: any step is missing an evidence source
    if any(not step.get("evidence") for step in toe_steps):
        flags.append("EVIDENCE_MISSING")

    # SAMPLE_TOO_SMALL: any step has sample < 25 with no rationale
    for step in toe_steps:
        sampling = step.get("sampling_approach", {})
        sample_size = sampling.get("sample_size")
        rationale = sampling.get("rationale", "")
        if (
            sample_size is not None
            and isinstance(sample_size, int)
            and sample_size < 25
            and not rationale
        ):
            flags.append("SAMPLE_TOO_SMALL")
            break

    # POPULATION_NOT_RECONCILED: no step references a traceable source
    reconciled_keywords = [
        "reconciled", "tie-out", "tieout", "gl total", "ledger",
        "system", "report", "register", "subledger", "sub-ledger",
        "erp", "database", "source system", "extract", "log", "workflow",
    ]
    if toe_steps and not any(
        any(kw in (step.get("population", "") or "").lower() for kw in reconciled_keywords)
        for step in toe_steps
    ):
        flags.append("POPULATION_NOT_RECONCILED")

    # PERIOD_INCOMPLETE: any step's population doesn't reference the scope year
    scope_year = AUDIT_SCOPE_PERIOD.split("-")[-1].strip()
    if any(scope_year not in (step.get("population", "") or "") for step in toe_steps):
        flags.append("PERIOD_INCOMPLETE")

    # INDEPENDENCE_GAP
    control_owner = (entry.get("control_owner") or "").lower()
    if control_owner:
        for step in toe_steps:
            evidence = (step.get("evidence") or "").lower()
            if control_owner in evidence and step.get("methodology", "").lower() != "re-performance":
                flags.append("INDEPENDENCE_GAP")
                break

    # Deduplicate while preserving order
    seen = set()
    unique_flags = [f for f in flags if not (f in seen or seen.add(f))]
    entry["sufficiency_flags"] = unique_flags
    return entry


# ---------------------------------------------------------------------------
# Auditor assignment — proportional distribution across the full work program
# ---------------------------------------------------------------------------

def distribute_assignments(work_program: list[dict], auditors: list[dict]) -> None:
    """
    Assign auditors to all test steps across the full work program, weighted by
    available_hours. Steps are grouped by skill_required; within each skill group
    each step is assigned to the matching auditor who still has the most remaining
    capacity. Mutates assigned_to in-place.
    """
    steps_by_skill: dict[str, list[dict]] = {}
    for entry in work_program:
        if "error" in entry:
            continue
        tod = entry.get("test_of_design") or {}
        skill = (tod.get("skill_required") or "").strip().lower()
        if skill:
            steps_by_skill.setdefault(skill, []).append(tod)
        for step in entry.get("tests_of_effectiveness", []):
            skill = (step.get("skill_required") or "").strip().lower()
            if skill:
                steps_by_skill.setdefault(skill, []).append(step)

    for skill, steps in steps_by_skill.items():
        matching = [
            a for a in auditors
            if any(skill in s.lower() or s.lower() in skill for s in a.get("skills", []))
        ]
        if not matching:
            for step in steps:
                step["assigned_to"] = None
            continue

        # Seed remaining capacity from available_hours so distribution is proportional
        remaining: dict[str, float] = {a["name"]: float(a["available_hours"]) for a in matching}

        for step in steps:
            chosen = max(remaining, key=lambda n: remaining[n])
            step["assigned_to"] = chosen
            remaining[chosen] -= float(step.get("estimated_hours") or 0)


# ---------------------------------------------------------------------------
# Assignment independence check (GIAS 13.6 / IIA independence)
# ---------------------------------------------------------------------------

def check_assignment_independence(work_program: list[dict]) -> None:
    """
    Flag INDEPENDENCE_GAP when the auditor assigned to test a control is also
    that control's control_owner. Runs after distribute_assignments() — unlike
    the evidence-provider check inside sufficiency_check(), this one needs
    assigned_to, which isn't known until assignment has happened. Mutates
    sufficiency_flags in-place; never removes a flag sufficiency_check()
    already raised.

    Limitation: this only catches the case where control_owner in the RCM is
    literally the same name as an assigned auditor (some RCMs do name a
    specific person as owner). It cannot catch a role-to-person link like
    "Finance Manager" = Jan Bakker, because the resource directory schema
    (name, skills, available_hours) carries no role/title field to match
    control_owner against. Closing that gap needs a richer resource
    directory, not a bigger check.
    """
    for entry in work_program:
        if "error" in entry:
            continue
        owner = (entry.get("control_owner") or "").strip().lower()
        if not owner:
            continue

        assigned_names = set()
        tod = entry.get("test_of_design") or {}
        if tod.get("assigned_to"):
            assigned_names.add(tod["assigned_to"].strip().lower())
        for step in entry.get("tests_of_effectiveness", []):
            if step.get("assigned_to"):
                assigned_names.add(step["assigned_to"].strip().lower())

        if owner in assigned_names:
            flags = entry.setdefault("sufficiency_flags", [])
            if "INDEPENDENCE_GAP" not in flags:
                flags.append("INDEPENDENCE_GAP")


# ---------------------------------------------------------------------------
# Resource totals and alerts (GIAS 13.5)
# ---------------------------------------------------------------------------

def calculate_hours(entry: dict) -> dict[str, float]:
    """Return {auditor_name: hours} for one work program entry."""
    totals: dict[str, float] = {}

    tod = entry.get("test_of_design", {})
    if tod.get("assigned_to"):
        name = tod["assigned_to"]
        totals[name] = totals.get(name, 0) + (tod.get("estimated_hours") or 0)

    for step in entry.get("tests_of_effectiveness", []):
        if step.get("assigned_to"):
            name = step["assigned_to"]
            totals[name] = totals.get(name, 0) + (step.get("estimated_hours") or 0)

    return totals


def check_resource_totals(
    work_program: list[dict], auditors: list[dict]
) -> dict:
    """Aggregate hours per auditor and flag overruns."""
    aggregated: dict[str, float] = {}
    for entry in work_program:
        for name, hours in calculate_hours(entry).items():
            aggregated[name] = aggregated.get(name, 0) + hours

    alerts = []
    summary = []
    for auditor in auditors:
        name = auditor["name"]
        assigned = aggregated.get(name, 0)
        available = auditor["available_hours"]
        overrun = assigned - available
        summary.append({
            "auditor": name,
            "assigned_hours": assigned,
            "available_hours": available,
            "status": "OVERRUN" if overrun > 0 else "OK",
            "delta": round(overrun, 1),
        })
        if overrun > 0:
            alerts.append(
                f"{name}: {assigned}h assigned vs {available}h available "
                f"(+{round(overrun,1)}h overrun)"
            )

    return {"resource_summary": summary, "alerts": alerts}


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def to_markdown(work_program: list[dict], resource_alert: dict) -> str:
    lines = [
        "# Audit Work Program",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} — Scope: {AUDIT_SCOPE_PERIOD}_",
        "",
    ]

    for entry in work_program:
        lines += [
            f"---",
            f"## {entry['control_id']} — {entry['control']}",
            f"**Risk:** {entry['risk_id']} — {entry['risk']}  ",
            f"**Significance:** {entry['significance']}  ",
            f"**Control objective:** {entry.get('control_objective', 'n/a')}  ",
            f"**Frequency:** {entry.get('control_frequency', 'n/a')}  ",
            f"**Owner:** {entry.get('control_owner', 'n/a')}",
            "",
            "### Test of Design",
        ]
        tod = entry.get("test_of_design", {})
        lines += [
            f"- **Step:** {tod.get('step')}",
            f"- **Methodology:** {tod.get('methodology')}",
            f"- **Evidence:** {tod.get('evidence')}",
            f"- **Pass criteria:** {tod.get('pass_criteria')}",
            f"- **Hours:** {tod.get('estimated_hours')} — **Assigned to:** {tod.get('assigned_to')}",
            "",
            "### Tests of Effectiveness",
        ]
        for i, step in enumerate(entry.get("tests_of_effectiveness", []), 1):
            sampling = step.get("sampling_approach", {})
            lines += [
                f"**ToE {i}**",
                f"- **Population:** {step.get('population')}",
                f"- **Sampling:** {sampling.get('method')} — size: {sampling.get('sample_size')} — {sampling.get('rationale')}",
                f"- **Step:** {step.get('step')}",
                f"- **Methodology:** {step.get('methodology')}",
            ]
            if step.get("caat_tool"):
                lines += [
                    f"- **CAAT tool:** {step['caat_tool']}",
                    f"- **CAAT pseudocode:** `{step.get('caat_pseudocode')}`",
                ]
            lines += [
                f"- **Evidence:** {step.get('evidence')}",
                f"- **Pass criteria:** {step.get('pass_criteria')}",
                f"- **Hours:** {step.get('estimated_hours')} — **Assigned to:** {step.get('assigned_to')}",
                "",
            ]

        flags = entry.get("sufficiency_flags", [])
        if flags:
            lines += ["### ⚠️ Sufficiency Flags", ""]
            for flag in flags:
                lines.append(f"- `{flag}` — {SUFFICIENCY_FLAGS.get(flag, '')}")
            lines.append("")

    # Resource summary
    lines += ["---", "## Resource Summary", ""]
    for row in resource_alert.get("resource_summary", []):
        status_icon = "🔴" if row["status"] == "OVERRUN" else "🟢"
        lines.append(
            f"{status_icon} **{row['auditor']}**: {row['assigned_hours']}h assigned / "
            f"{row['available_hours']}h available (delta: {row['delta']}h)"
        )
    if resource_alert.get("alerts"):
        lines += ["", "### 🚨 Resource Alerts", ""]
        for alert in resource_alert["alerts"]:
            lines.append(f"- {alert}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Excel output
# ---------------------------------------------------------------------------

HEADER_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF")
WRAP_TOP = Alignment(wrap_text=True, vertical="top")
FILL_GREEN = PatternFill("solid", fgColor="C6EFCE")
FILL_RED = PatternFill("solid", fgColor="FFC7CE")


def to_excel(work_program: list[dict], resource_alert: dict, output_path: Path) -> None:
    wb = Workbook()

    # --- Sheet 1: Work Program (one row per test step) ---
    ws = wb.active
    assert ws is not None
    ws.title = "Work Program"

    headers = [
        "Control ID", "Control Description", "Risk ID", "Significance", "Control Owner", "Control Type",
        "Frequency", "Test Type", "Step", "Methodology", "Evidence",
        "Pass Criteria", "Est. Hours", "Assigned To",
        "Population", "Sampling Method", "Sample Size", "CAAT Tool",
        "Sufficiency Flags",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP_TOP

    for entry in work_program:
        if "error" in entry:
            ws.append([entry.get("control_id"), "", "", "", "", "", "", "ERROR", entry.get("error")])
            continue

        flags = ", ".join(entry.get("sufficiency_flags", []))
        base = [
            entry.get("control_id"),
            entry.get("control"),
            entry.get("risk_id"),
            entry.get("significance"),
            entry.get("control_owner"),
            entry.get("control_type"),
            entry.get("control_frequency"),
        ]

        tod = entry.get("test_of_design", {}) or {}
        ws.append(base + [
            "Design",
            tod.get("step"),
            tod.get("methodology"),
            tod.get("evidence"),
            tod.get("pass_criteria"),
            tod.get("estimated_hours"),
            tod.get("assigned_to"),
            "", "", "", "",
            flags,
        ])

        for i, step in enumerate(entry.get("tests_of_effectiveness", []), 1):
            sampling = step.get("sampling_approach", {}) or {}
            ws.append(base + [
                f"Effectiveness {i}",
                step.get("step"),
                step.get("methodology"),
                step.get("evidence"),
                step.get("pass_criteria"),
                step.get("estimated_hours"),
                step.get("assigned_to"),
                step.get("population"),
                sampling.get("method"),
                sampling.get("sample_size"),
                step.get("caat_tool"),
                "",
            ])

    col_widths = [12, 45, 10, 12, 22, 14, 12, 16, 45, 16, 45, 45, 10, 22, 45, 16, 12, 14, 35]
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = WRAP_TOP
    ws.freeze_panes = "A2"

    # --- Sheet 2: Resource Summary ---
    ws2 = wb.create_sheet("Resource Summary")
    ws2.append(["Auditor", "Assigned Hours", "Available Hours", "Status", "Delta (h)"])
    for cell in ws2[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    for row_data in resource_alert.get("resource_summary", []):
        ws2.append([
            row_data["auditor"],
            row_data["assigned_hours"],
            row_data["available_hours"],
            row_data["status"],
            row_data["delta"],
        ])
        fill = FILL_RED if row_data["status"] == "OVERRUN" else FILL_GREEN
        for cell in ws2[ws2.max_row]:
            cell.fill = fill

    for col, width in zip("ABCDE", [22, 15, 15, 10, 10]):
        ws2.column_dimensions[col].width = width
    ws2.freeze_panes = "A2"

    wb.save(output_path)


# ---------------------------------------------------------------------------
# RCM format adapter
# ---------------------------------------------------------------------------

def flatten_rcm(rcm_data: dict) -> list[dict]:
    """Normalize UC7 hierarchical format (risks[].stage2.controls[]) to a flat control list."""
    # UC7 hierarchical format: risks[].stage2.controls[]
    controls = []
    for risk in rcm_data.get("risks", []):
        stage1 = risk.get("stage1", {})
        stage2 = risk.get("stage2", {})
        stage3 = risk.get("stage3", {})
        it_assessments = {
            a["control_id"]: a
            for a in stage3.get("controls_it_assessment", [])
            if "control_id" in a
        }

        for ctrl in stage2.get("controls", []):
            it = it_assessments.get(ctrl.get("control_id"), {})
            controls.append({
                "risk_id": risk.get("risk_id"),
                "risk": stage1.get("risk_statement"),
                "control_id": ctrl.get("control_id"),
                "control": ctrl.get("description"),
                "control_type": ctrl.get("execution_type"),
                "control_owner": ctrl.get("control_owner"),
                "control_frequency": ctrl.get("frequency"),
                # Use inherent_risk_rating (High/Medium/Low) for sufficiency checks
                "significance": stage2.get("inherent_risk_rating"),
                # Enrichment fields from the richer UC7 schema
                "risk_category": stage1.get("risk_category"),
                "control_nature": ctrl.get("nature"),
                "control_evidence_type": ctrl.get("evidence_type"),
                "control_design_effectiveness": ctrl.get("control_design_effectiveness"),
                "it_dependency_reliability": it.get("control_reliability"),
            })
    return controls


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def generate_work_program(rcm_data: dict, auditors: list[dict]) -> dict:
    controls = flatten_rcm(rcm_data)
    work_program = []

    batch_results, run_log = call_claude_batch(controls, auditors)

    for control in controls:
        ctrl_id = control["control_id"]
        result = batch_results.get(ctrl_id)
        print(f"  {ctrl_id}...", end=" ")

        if isinstance(result, Exception) or result is None:
            print(f"ERROR — {result}")
            work_program.append({"control_id": ctrl_id, "error": str(result)})
            continue

        try:
            entry = sufficiency_check(result, control.get("significance", ""))
            work_program.append(entry)
            print(f"OK — {len(entry.get('sufficiency_flags', []))} flag(s)")
        except (KeyError, TypeError) as exc:
            print(f"ERROR — {exc}")
            work_program.append({"control_id": ctrl_id, "error": str(exc)})

    distribute_assignments(work_program, auditors)
    check_assignment_independence(work_program)
    resource_alert = check_resource_totals(work_program, auditors)
    return {"work_program": work_program, "resource_alert": resource_alert, "run_log": run_log}


def main() -> None:
    parser = argparse.ArgumentParser(description="UC8 Audit Work Program Generator")
    parser.add_argument(
        "--rcm",
        default="Input/rcm_output.json",
        help="Path to RCM JSON file (flat rcm_sample or UC7 rcm_output format)",
    )
    parser.add_argument(
        "--resources",
        default="Input/resource_directory.json",
        help="Path to auditor resource directory JSON",
    )
    parser.add_argument(
        "--output",
        default="outputs/work_program.json",
        help="Output path for the work program JSON",
    )
    args = parser.parse_args()

    # Load inputs
    rcm_path = Path(args.rcm)
    resources_path = Path(args.resources)

    if not rcm_path.exists():
        sys.exit(f"ERROR: RCM file not found: {rcm_path}")
    if not resources_path.exists():
        sys.exit(f"ERROR: Resource directory not found: {resources_path}")

    with open(rcm_path, encoding="utf-8") as f:
        rcm_data = json.load(f)
    with open(resources_path, encoding="utf-8") as f:
        auditors = json.load(f)

    controls_flat = flatten_rcm(rcm_data)
    print(f"\n{'='*60}")
    print(f"UC8 Audit Work Program Agent")
    print(f"Model  : {MODEL}")
    print(f"Scope  : {AUDIT_SCOPE_PERIOD}")
    print(f"RCM    : {rcm_path} ({len(controls_flat)} controls across {len(rcm_data.get('risks', []))} risks)")
    print(f"Output : {args.output}")
    print(f"{'='*60}\n")

    result = generate_work_program(rcm_data, auditors)

    # Write JSON output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON written to {output_path}")

    # Write Markdown output
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(to_markdown(result["work_program"], result["resource_alert"]))
    print(f"✅ Markdown written to {md_path}")

    # Write Excel output
    xl_path = output_path.with_suffix(".xlsx")
    to_excel(result["work_program"], result["resource_alert"], xl_path)
    print(f"✅ Excel written to {xl_path}")

    # Write run log
    log_path = output_path.with_name(output_path.stem + "_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result["run_log"], f, indent=2, ensure_ascii=False)
    print(f"✅ Log written to {log_path}")

    # Print resource alerts to console
    alerts = result["resource_alert"].get("alerts", [])
    if alerts:
        print("\n🚨 Resource alerts:")
        for alert in alerts:
            print(f"   {alert}")
    else:
        print("\n🟢 No resource overruns detected.")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
