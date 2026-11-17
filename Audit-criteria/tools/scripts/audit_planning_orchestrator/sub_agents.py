"""Sub-agent tool wrappers: UC7 (RCM), UC8 (Work Program), UC9 (Quality Guard).

Each wrapper is a thin adapter around a single Claude API call using that
agent's system prompt (see ``prompts.py``). The orchestrator calls these as
tools; it never sees the model plumbing.

A ``--mock-subagents`` mode returns deterministic fixtures instead of calling
the API, so the whole pipeline — including the No-Go recovery loop — can be
demonstrated offline. The mock UC7 returns an RCM that is missing a risk for the
"Payment" sub-process on the first pass and a complete RCM once a "correction"
is supplied, so UC9 legitimately flips from No-Go to Go.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from . import prompts

logger = logging.getLogger(__name__)

# Model roles: capable models synthesise, a cheaper model validates.
SYNTHESIS_MODEL = "claude-opus-5"
VALIDATION_MODEL = "claude-sonnet-5"


def make_client() -> Any:
    """Construct an Anthropic client.

    Honors ``ANTHROPIC_WORKSPACE_ID``: organization-scoped API keys must name a
    workspace, which the API expects in the ``anthropic-workspace-id`` header.
    Set that env var when your key is not already scoped to a single workspace.
    """
    import anthropic

    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    default_headers = {"anthropic-workspace-id": workspace} if workspace else None
    return anthropic.Anthropic(default_headers=default_headers)

_SUBAGENTS = {
    "run_rcm_builder": (prompts.RCM_BUILDER_PROMPT, SYNTHESIS_MODEL),
    "run_work_program": (prompts.WORK_PROGRAM_PROMPT, SYNTHESIS_MODEL),
    "run_quality_guard": (prompts.QUALITY_GUARD_PROMPT, VALIDATION_MODEL),
}


def _extract_json(text: str) -> Dict[str, Any]:
    """Parse a JSON object from a model response, tolerating stray fences."""
    text = text.strip()
    if text.startswith("```"):
        # Drop a leading ```json / ``` fence and the trailing fence.
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model response")
    return json.loads(text[start : end + 1])


def call_subagent(client: Any, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Run one sub-agent as a single Claude call and return its parsed JSON.

    Raises ValueError if the response cannot be parsed as JSON — the caller
    turns that into a gated error result.
    """
    system, model = _SUBAGENTS[tool_name]
    logger.info("Calling sub-agent %s on %s", tool_name, model)
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": json.dumps(tool_input, indent=2)}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    return _extract_json(text)


# --------------------------------------------------------------------------- #
# Deterministic fixtures for offline / --mock-subagents runs.
# --------------------------------------------------------------------------- #

_RCM_PARTIAL: List[Dict[str, Any]] = [
    {
        "risk_id": "R-P01-001",
        "sub_process": "Invoice Approval",
        "business_objective": "Ensure only valid, authorized invoices are approved for payment",
        "risk_description": "Invoices may be approved without adequate review, enabling duplicate or fraudulent payments",
        "risk_sources": ["UC2: 3 recurring findings", "UC3: 42 duplicate payment incidents", "UC4: ghost vendor scenario"],
        "inherent_risk": {"impact": "High", "likelihood": "High", "rating": "High"},
        "control_id": "C-P01-001",
        "control_description": "System-generated duplicate payment check blocks matching supplier + amount + date",
        "control_type": "Automated",
        "control_frequency": "Every transaction",
        "residual_risk": {"impact": "High", "likelihood": "Low", "rating": "Medium"},
    },
    {
        "risk_id": "R-P02-001",
        "sub_process": "Invoice Receipt",
        "business_objective": "Ensure all received invoices are captured completely and accurately",
        "risk_description": "Invoices received outside the system may bypass controls and go unrecorded",
        "risk_sources": ["UC3: 19 missing goods-receipt incidents"],
        "inherent_risk": {"impact": "Medium", "likelihood": "Medium", "rating": "Medium"},
        "control_id": "C-P02-001",
        "control_description": "Central mailbox intake with three-way match before posting",
        "control_type": "Manual",
        "control_frequency": "Daily",
        "residual_risk": {"impact": "Medium", "likelihood": "Low", "rating": "Low"},
    },
]

# The corrected RCM adds a risk for the "Payment" sub-process (the seeded gap).
_RCM_PAYMENT_ROW: Dict[str, Any] = {
    "risk_id": "R-P03-001",
    "sub_process": "Payment",
    "business_objective": "Ensure only approved invoices are paid, once, to the correct beneficiary",
    "risk_description": "Payments may be released to unauthorized or duplicate beneficiaries",
    "risk_sources": ["UC4: invoice-splitting scenario", "UC5: DORA payment-integrity criteria"],
    "inherent_risk": {"impact": "High", "likelihood": "Medium", "rating": "High"},
    "control_id": "C-P03-001",
    "control_description": "Dual authorization on payment release; beneficiary bank details locked after vendor onboarding",
    "control_type": "Manual",
    "control_frequency": "Every payment run",
    "residual_risk": {"impact": "High", "likelihood": "Low", "rating": "Medium"},
}


def _mock_rcm(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    rows = list(_RCM_PARTIAL)
    if tool_input.get("correction"):
        rows.append(_RCM_PAYMENT_ROW)
    return {"rcm": rows}


def _mock_work_program(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    rcm = tool_input.get("rcm", [])
    tasks: List[Dict[str, Any]] = []
    for n, row in enumerate(rcm, start=1):
        tasks.append(
            {
                "task_id": f"T-{n:03d}",
                "control_id": row.get("control_id", f"C-{n:03d}"),
                "test_type": "ToE",
                "objective": f"Verify {row.get('control_description', 'the control')} operated effectively",
                "procedure": "Extract the FY population and re-perform the control over 100% of transactions.",
                "methodology": "Analytical Procedure (CAAT)"
                if row.get("control_type") == "Automated"
                else "Inspection",
                "tool": "Python (pandas)" if row.get("control_type") == "Automated" else None,
                "evidence_required": "ERP export for the period; control configuration",
                "pass_fail": "Pass: no exceptions. Fail: one or more exceptions.",
                "assigned_to": "Data Specialist" if row.get("control_type") == "Automated" else "Senior Auditor",
                "estimated_hours": 8 if row.get("control_type") == "Automated" else 6,
                "sampling": "100% population" if row.get("control_type") == "Automated" else "Judgemental (25 items)",
            }
        )
    required = sum(t["estimated_hours"] for t in tasks)
    available = int(tool_input.get("available_hours", 160))
    return {
        "work_program": tasks,
        "resource_report": {
            "total_hours_required": required,
            "available_hours": available,
            "resource_alert": None if required <= available else "Insufficient capacity for the timeframe.",
        },
    }


def _mock_quality(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    process_map = tool_input.get("process_map", {})
    rcm = tool_input.get("rcm", [])
    work_program = tool_input.get("work_program", [])

    sub_processes = {sp.get("name") for sp in process_map.get("sub_processes", []) if sp.get("name")}
    covered = {row.get("sub_process") for row in rcm}
    controls = {row.get("control_id") for row in rcm}
    tested = {task.get("control_id") for task in work_program}

    gaps: List[str] = []
    checks = {"scoping": "pass", "orphans": "pass", "traceability": "pass", "methodology": "pass", "resources": "pass"}

    for missing in sorted(sub_processes - covered):
        gaps.append(f"Sub-process '{missing}' has no associated risk (RCM scoping gap).")
        checks["scoping"] = "fail"
    for orphan in sorted(controls - tested):
        gaps.append(f"Control '{orphan}' has no work program task (traceability gap in the work program).")
        checks["traceability"] = "fail"

    return {"verdict": "No-Go" if gaps else "Go", "gaps": gaps, "checks": checks}


_MOCKS = {
    "run_rcm_builder": _mock_rcm,
    "run_work_program": _mock_work_program,
    "run_quality_guard": _mock_quality,
}


def mock_subagent(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic fixture for ``tool_name`` (offline mode)."""
    logger.info("Mock sub-agent %s (no API call)", tool_name)
    return _MOCKS[tool_name](tool_input)


# JSON-schema tool definitions handed to the orchestrator model.
def tool_definitions() -> List[Dict[str, Any]]:
    """Return the three sub-agent tool definitions for the Messages API."""
    return [
        {
            "name": "run_rcm_builder",
            "description": (
                "UC7 RCM Builder. Consolidates multi-source risk inputs into a Risk and "
                "Control Matrix. Call first. Pass a 'correction' string to fix a gap UC9 raised."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_map": {"type": "object", "description": "Sub-processes and business objectives (from UC1)."},
                    "risks": {"type": "array", "description": "Risk inputs tagged by source (UC2-UC6)."},
                    "correction": {"type": "string", "description": "Optional fix instruction from UC9."},
                },
                "required": ["process_map", "risks"],
            },
        },
        {
            "name": "run_work_program",
            "description": (
                "UC8 Work Program agent. Turns a validated RCM into ToD/ToE test procedures, "
                "methodology, CAATs, evidence, assignments and hour estimates. Call after a valid RCM."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "rcm": {"type": "array", "description": "The 'rcm' list returned by run_rcm_builder."},
                    "auditor_directory": {"type": "array", "description": "Auditor roles, skills and availability."},
                    "available_hours": {"type": "number", "description": "Total available auditor hours."},
                    "correction": {"type": "string", "description": "Optional fix instruction from UC9."},
                },
                "required": ["rcm"],
            },
        },
        {
            "name": "run_quality_guard",
            "description": (
                "UC9 Quality & Resource Guard. Reviews the full package (process map + RCM + work "
                "program) for GIAS 13.2-13.6 compliance and returns a Go/No-Go verdict with gaps. Call last."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "process_map": {"type": "object"},
                    "rcm": {"type": "array"},
                    "work_program": {"type": "array"},
                    "resource_report": {"type": "object"},
                },
                "required": ["process_map", "rcm", "work_program"],
            },
        },
    ]
