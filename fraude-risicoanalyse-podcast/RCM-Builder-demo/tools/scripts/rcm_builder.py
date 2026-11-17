"""
RCM Builder — Stages 1 & 2
Ingests structured audit use-case inputs, normalizes and deduplicates risks,
drafts mitigating controls, scores inherent/residual risk, and prepares the
Draft RCM for Stage 3 IT validation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

_RISK_STMT_RE = re.compile(
    r"As a result of (.+), there is a risk that (.+), leading to (.+)\.",
    re.IGNORECASE,
)

_DESCRIPTION_SPLIT_PATTERNS = [
    re.compile(r"(.+?)\s+may\s+result\s+in\s+(.+?)\s+leading\s+to\s+(.+)\.?$", re.IGNORECASE),
    re.compile(r"(.+?)\s+could\s+lead\s+to\s+(.+?)\s+resulting\s+in\s+(.+)\.?$", re.IGNORECASE),
]

_COLLECTION_KEYS = (
    "risks",
    "findings",
    "incidents",
    "issues",
    "fraud_scenarios",
    "regulatory_risks",
    "compliance_risks",
    "historical_risks",
    "items",
    "records",
)

_TRACE_REFERENCE_KEYS = (
    "source_reference",
    "reference",
    "report_reference",
    "incident_id",
    "finding_id",
    "issue_id",
    "regulation_reference",
    "id",
)

_TEXT_KEYS = (
    "risk_description",
    "description",
    "statement",
    "summary",
    "scenario",
    "finding",
    "issue",
    "title",
)

_EVIDENCE_TYPES = {
    "System Generated",
    "Workflow Approval",
    "Documentation-Based",
    "Data Analysis",
    "Observation",
    "Inquiry",
}

_TOKEN_STOPWORDS = {
    "about", "after", "against", "before", "being", "control", "controls",
    "could", "entity", "ensure", "from", "have", "into", "leading", "over",
    "perform", "process", "review", "risk", "system", "that", "there", "this",
    "using", "with",
}

_DESIGN_REDUCTION = {"Strong": 0.60, "Moderate": 0.35, "Weak": 0.15, None: 0.00}

_CATEGORY_ALIASES = {
    "financial reporting": "Financial",
    "financial": "Financial",
    "fr": "Financial",
    "operational": "Operational",
    "operations": "Operational",
    "it": "IT",
    "technology": "IT",
    "cyber": "IT",
    "information technology": "IT",
    "compliance": "Compliance",
    "regulatory": "Compliance",
    "fraud": "Fraud",
    "strategic": "Strategic",
}

_CATEGORY_DEFAULTS = {
    "Financial": (4, 4),
    "Operational": (3, 3),
    "IT": (4, 3),
    "Compliance": (4, 3),
    "Fraud": (5, 4),
    "Strategic": (4, 2),
}

_RISK_APPETITE_KEYS = {
    "Financial": ("financial", "financial_reporting"),
    "Operational": ("operational",),
    "IT": ("it", "technology", "operational"),
    "Compliance": ("compliance",),
    "Fraud": ("fraud", "financial", "operational"),
    "Strategic": ("strategic",),
}

_SOURCE_TYPE_DEFAULTS = {
    "uc2": ("UC2", "Historical Audit Findings"),
    "historical_risks": ("UC2", "Historical Audit Findings"),
    "historical_findings": ("UC2", "Historical Audit Findings"),
    "uc3": ("UC3", "Incident and Issue Data"),
    "incident_risks": ("UC3", "Incident and Issue Data"),
    "incidents": ("UC3", "Incident and Issue Data"),
    "issues": ("UC3", "Incident and Issue Data"),
    "uc4": ("UC4", "Fraud Scenarios"),
    "fraud_scenarios": ("UC4", "Fraud Scenarios"),
    "fraud_risks": ("UC4", "Fraud Scenarios"),
    "uc5": ("UC5", "Regulatory and Compliance Inputs"),
    "regulatory_risks": ("UC5", "Regulatory and Compliance Inputs"),
    "compliance_risks": ("UC5", "Regulatory and Compliance Inputs"),
    "risk_sources": ("UC2-UC5", "Consolidated Risk Sources"),
}

_SCENARIO_BLUEPRINTS = [
    {
        "name": "Journal and Financial Close",
        "keywords": {"journal", "ledger", "revenue", "close", "reconciliation", "financial"},
        "controls": [
            {
                "description": "Supervisor approval of high-risk journal and close activities",
                "who": "Financial Reporting Manager",
                "control_owner": "Financial Reporting Manager",
                "what": "Reviews supporting evidence, approver authority, and segregation-of-duties exceptions before transactions are finalized.",
                "when": "Before posting and during the monthly close cycle",
                "frequency": "Monthly",
                "where": "ERP close and journal workflow",
                "how": "Uses workflow approvals and exception reports to confirm that risky financial adjustments are justified and authorized.",
                "why": "Mitigates the risk that financial reporting transactions are processed inaccurately or without authorization.",
                "evidence": "Approved journal workflow, exception reports, and documented reviewer comments",
                "evidence_type": "Workflow Approval",
                "execution_type": "IT-Dependent",
                "nature": "Preventive",
                "significance": "Key",
                "control_design_effectiveness": "Strong",
                "it_dependent": True,
            },
            {
                "description": "Independent analytics of unusual financial close activity",
                "who": "Controller",
                "control_owner": "Controller",
                "what": "Performs trend and exception analysis over unusual entries, timing differences, and post-close adjustments.",
                "when": "After each close cycle",
                "frequency": "Monthly",
                "where": "Financial reporting analytics workspace",
                "how": "Analyzes system-generated reports and investigates anomalies against close support files.",
                "why": "Detects residual financial reporting anomalies that were not prevented by the approval workflow.",
                "evidence": "Exception analysis workbook, investigation notes, and management sign-off",
                "evidence_type": "Data Analysis",
                "execution_type": "IT-Dependent",
                "nature": "Detective",
                "significance": "Key",
                "control_design_effectiveness": "Moderate",
                "it_dependent": True,
            },
        ],
    },
    {
        "name": "Access Management",
        "keywords": {"access", "user", "identity", "privileged", "provision", "credential", "account"},
        "controls": [
            {
                "description": "Workflow approval and segregation-of-duties validation for access changes",
                "who": "Access Administration Lead",
                "control_owner": "Access Administration Lead",
                "what": "Confirms requester approval, role appropriateness, and segregation-of-duties compliance before access is provisioned or modified.",
                "when": "Before each access change is fulfilled",
                "frequency": "Real-time",
                "where": "Identity and access management workflow",
                "how": "Routes requests through the access workflow, blocks incompatible role combinations, and requires documented approval.",
                "why": "Prevents unauthorized or excessive access from being granted.",
                "evidence": "Approved access tickets, workflow history, and segregation-of-duties exception logs",
                "evidence_type": "Workflow Approval",
                "execution_type": "IT-Dependent",
                "nature": "Preventive",
                "significance": "Key",
                "control_design_effectiveness": "Strong",
                "it_dependent": True,
            },
            {
                "description": "Periodic recertification of active and privileged access",
                "who": "IT Security Manager",
                "control_owner": "IT Security Manager",
                "what": "Reviews active user populations, privileged accounts, and recent leavers to remove inappropriate access promptly.",
                "when": "Within ten business days of quarter-end",
                "frequency": "Quarterly",
                "where": "IAM reporting and HR termination roster",
                "how": "Compares system-generated access listings to HR records and remediation tickets.",
                "why": "Detects unauthorized or stale access that bypassed the provisioning workflow.",
                "evidence": "Quarterly access review package, reviewer sign-off, and remediation tickets",
                "evidence_type": "Data Analysis",
                "execution_type": "IT-Dependent",
                "nature": "Detective",
                "significance": "Key",
                "control_design_effectiveness": "Moderate",
                "it_dependent": True,
            },
        ],
    },
    {
        "name": "Change Management",
        "keywords": {"change", "deploy", "release", "testing", "production", "implementation", "code"},
        "controls": [
            {
                "description": "Formal approval and testing gate for production changes",
                "who": "Change Advisory Board Chair",
                "control_owner": "Change Advisory Board Chair",
                "what": "Approves production changes only after documented testing, business sign-off, and emergency change justification have been completed.",
                "when": "Before deployment to production",
                "frequency": "Per request",
                "where": "Change management system",
                "how": "Requires complete change records, attached evidence, and approver sign-off before promotion to production is allowed.",
                "why": "Prevents unauthorized or insufficiently tested changes from reaching production.",
                "evidence": "Approved change tickets, test evidence, and deployment authorization logs",
                "evidence_type": "Workflow Approval",
                "execution_type": "IT-Dependent",
                "nature": "Preventive",
                "significance": "Key",
                "control_design_effectiveness": "Strong",
                "it_dependent": True,
            },
            {
                "description": "Post-implementation review of emergency and high-risk changes",
                "who": "IT Service Delivery Manager",
                "control_owner": "IT Service Delivery Manager",
                "what": "Reviews emergency and failed changes to confirm issues were resolved and root causes were addressed.",
                "when": "After implementation of high-risk or emergency changes",
                "frequency": "Weekly",
                "where": "Change review board meeting",
                "how": "Uses incident tickets, deployment logs, and review minutes to investigate exceptions.",
                "why": "Detects change failures and recurring breakdowns not prevented earlier in the lifecycle.",
                "evidence": "Post-implementation review minutes, incident tickets, and action logs",
                "evidence_type": "Documentation-Based",
                "execution_type": "IT-Dependent",
                "nature": "Detective",
                "significance": "Key",
                "control_design_effectiveness": "Moderate",
                "it_dependent": True,
            },
        ],
    },
    {
        "name": "Payment Processing",
        "keywords": {"payment", "beneficiary", "bank", "vendor", "invoice", "cash", "treasury"},
        "controls": [
            {
                "description": "Dual authorization of payment setup and release activities",
                "who": "Treasury Manager",
                "control_owner": "Treasury Manager",
                "what": "Verifies beneficiary details and requires independent approval before high-risk or new payment instructions are released.",
                "when": "Before payment execution",
                "frequency": "Real-time",
                "where": "Treasury payment platform",
                "how": "Validates master-data changes against supporting documentation and blocks release until dual approval is complete.",
                "why": "Prevents payments from being made to fraudulent or unauthorized accounts.",
                "evidence": "Approved payment workflow, vendor validation records, and release logs",
                "evidence_type": "Workflow Approval",
                "execution_type": "IT-Dependent",
                "nature": "Preventive",
                "significance": "Key",
                "control_design_effectiveness": "Strong",
                "it_dependent": True,
            },
            {
                "description": "Independent reconciliation of payment output to bank activity",
                "who": "Cash Operations Supervisor",
                "control_owner": "Cash Operations Supervisor",
                "what": "Reconciles processed payments to bank statements and investigates unmatched or duplicate transactions.",
                "when": "After payment processing",
                "frequency": "Daily",
                "where": "Treasury reconciliation workspace",
                "how": "Uses bank statements and system-generated payment reports to identify and resolve exceptions.",
                "why": "Detects unauthorized or erroneous payments that escaped preventive controls.",
                "evidence": "Daily reconciliation file, exception tracker, and supervisor sign-off",
                "evidence_type": "Data Analysis",
                "execution_type": "IT-Dependent",
                "nature": "Detective",
                "significance": "Key",
                "control_design_effectiveness": "Moderate",
                "it_dependent": True,
            },
        ],
    },
    {
        "name": "Privacy and Compliance",
        "keywords": {"privacy", "consent", "regulatory", "gdpr", "pii", "encryption", "subject", "compliance"},
        "controls": [
            {
                "description": "Formal compliance review of high-risk personal data processing activities",
                "who": "Compliance Officer",
                "control_owner": "Compliance Officer",
                "what": "Approves new or changed processing activities only after lawful basis, privacy obligations, and monitoring responsibilities are documented.",
                "when": "Before processing changes are implemented",
                "frequency": "Per request",
                "where": "Compliance case management workflow",
                "how": "Uses privacy impact assessments, approvals, and obligation trackers to confirm regulatory requirements are met.",
                "why": "Prevents non-compliant processing or control breakdowns before they occur.",
                "evidence": "Approved compliance assessments, workflow approvals, and obligation tracker updates",
                "evidence_type": "Workflow Approval",
                "execution_type": "IT-Dependent",
                "nature": "Preventive",
                "significance": "Key",
                "control_design_effectiveness": "Strong",
                "it_dependent": True,
            },
            {
                "description": "Monitoring of compliance exceptions and unresolved privacy obligations",
                "who": "Privacy Operations Manager",
                "control_owner": "Privacy Operations Manager",
                "what": "Reviews outstanding privacy requests, consent exceptions, and encryption gaps for timely remediation.",
                "when": "After exceptions are generated",
                "frequency": "Monthly",
                "where": "Compliance and privacy dashboard",
                "how": "Uses case reports and issue trackers to escalate unresolved items to management.",
                "why": "Detects unresolved compliance breaches that could result in fines or customer harm.",
                "evidence": "Monthly dashboard pack, issue tracker, and escalation records",
                "evidence_type": "Documentation-Based",
                "execution_type": "IT-Dependent",
                "nature": "Detective",
                "significance": "Key",
                "control_design_effectiveness": "Moderate",
                "it_dependent": True,
            },
        ],
    },
    {
        "name": "Fraud Prevention",
        "keywords": {"fraud", "override", "misappropriation", "collusion", "unauthorized"},
        "controls": [
            {
                "description": "Segregation-of-duties and approval control over high-risk transactions",
                "who": "Process Control Owner",
                "control_owner": "Process Control Owner",
                "what": "Prevents one individual from initiating and approving the same high-risk transaction or override.",
                "when": "At the time of transaction processing",
                "frequency": "Real-time",
                "where": "Core transaction processing workflow",
                "how": "Uses role-based controls and approval checkpoints to block unauthorized override activity.",
                "why": "Reduces the opportunity for intentional manipulation or concealment of fraud.",
                "evidence": "Role conflict reports, approval logs, and exception approvals",
                "evidence_type": "Workflow Approval",
                "execution_type": "IT-Dependent",
                "nature": "Preventive",
                "significance": "Key",
                "control_design_effectiveness": "Strong",
                "it_dependent": True,
            },
            {
                "description": "Targeted monitoring of anomalous transactions and override activity",
                "who": "Fraud Risk Manager",
                "control_owner": "Fraud Risk Manager",
                "what": "Investigates unusual activity patterns, manual overrides, and abnormal transaction combinations.",
                "when": "After anomalies are identified",
                "frequency": "Weekly",
                "where": "Fraud analytics monitoring environment",
                "how": "Uses exception reports and trend analytics to escalate suspicious activity for investigation.",
                "why": "Detects fraudulent behavior that bypassed preventive controls.",
                "evidence": "Fraud investigation log, anomaly reports, and escalation documentation",
                "evidence_type": "Data Analysis",
                "execution_type": "IT-Dependent",
                "nature": "Detective",
                "significance": "Key",
                "control_design_effectiveness": "Moderate",
                "it_dependent": True,
            },
        ],
    },
    {
        "name": "General IT and Operations",
        "keywords": {"backup", "restore", "interface", "configuration", "availability", "report", "application"},
        "controls": [
            {
                "description": "Configuration and exception review over critical system operations",
                "who": "IT Operations Manager",
                "control_owner": "IT Operations Manager",
                "what": "Reviews critical configuration settings, batch exceptions, and failed operational jobs for timely remediation.",
                "when": "After each reporting cycle or operational exception",
                "frequency": "Daily",
                "where": "IT operations dashboard",
                "how": "Uses automated system alerts and job-monitoring reports to investigate and resolve exceptions.",
                "why": "Prevents and detects system operation failures that could undermine business processing.",
                "evidence": "Job-monitoring report, incident tickets, and remediation records",
                "evidence_type": "System Generated",
                "execution_type": "Automated",
                "nature": "Detective",
                "significance": "Key",
                "control_design_effectiveness": "Moderate",
                "it_dependent": True,
            }
        ],
    },
]


def _dedupe_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _content_key(risk_statement: str) -> str:
    m = _RISK_STMT_RE.match(risk_statement)
    if m:
        return " ".join(m.groups())
    return risk_statement


def _normalize_business_objectives(
    objectives: list[Any],
    start_index: int,
) -> tuple[list[dict[str, str]], int]:
    normalized: list[dict[str, str]] = []
    next_index = start_index

    for objective in objectives:
        if isinstance(objective, dict):
            objective_id = objective.get("objective_id") or f"OBJ-{next_index:04d}"
            objective_description = (
                objective.get("objective_description")
                or objective.get("objective")
                or ""
            )
        else:
            objective_id = f"OBJ-{next_index:04d}"
            objective_description = str(objective)

        normalized.append({
            "objective_id": objective_id,
            "objective_description": objective_description,
        })
        next_index += 1

    return normalized, next_index


def parse_context(input_data: dict) -> dict:
    context = input_data.get("context", {})
    processes = input_data.get("processes", [])

    process_map = {}
    objective_index = 1

    for proc in processes:
        proc_id = proc.get("process_id", "")
        sub_processes = []
        for sp in proc.get("sub_processes", []):
            objectives, objective_index = _normalize_business_objectives(
                sp.get("business_objectives", []),
                objective_index,
            )
            sub_processes.append({
                "sub_process_id": sp.get("sub_process_id", ""),
                "sub_process_name": sp.get("sub_process_name", ""),
                "business_objectives": objectives,
            })
        process_map[proc_id] = {
            "process_name": proc.get("process_name", ""),
            "description": proc.get("description", ""),
            "sub_processes": sub_processes,
        }

    return {
        "organization_name": context.get("organization_name", ""),
        "assessment_period": context.get("assessment_period", ""),
        "risk_appetite": context.get("risk_appetite", {}),
        "processes": process_map,
    }


def _build_objective_lookup(context: dict, use_cases: list[dict]) -> dict[tuple[str, str, str], str]:
    lookup: dict[tuple[str, str, str], str] = {}
    max_index = 0

    for process_id, process in context.get("processes", {}).items():
        for sub_process in process.get("sub_processes", []):
            sub_process_id = sub_process.get("sub_process_id", "")
            for objective in sub_process.get("business_objectives", []):
                objective_id = objective.get("objective_id", "")
                objective_description = objective.get("objective_description", "")
                if objective_description and objective_id:
                    lookup[(process_id, sub_process_id, objective_description)] = objective_id
                    if objective_id.startswith("OBJ-"):
                        try:
                            max_index = max(max_index, int(objective_id.split("-")[1]))
                        except (ValueError, IndexError):
                            pass

    next_index = max_index + 1 if max_index else 1
    for use_case in use_cases:
        key = (
            use_case.get("process_id", ""),
            use_case.get("sub_process_id", ""),
            use_case.get("objective", ""),
        )
        if key[2] and key not in lookup:
            lookup[key] = f"OBJ-{next_index:04d}"
            next_index += 1

    return lookup


def _get_objective_id(risk: dict, objective_lookup: dict[tuple[str, str, str], str]) -> str:
    return objective_lookup.get(
        (
            risk.get("process_id", ""),
            risk.get("sub_process_id", ""),
            risk.get("objective", ""),
        ),
        "",
    )


def _normalize_category(raw_category: str | None, risk_source: str | None = None) -> str:
    if raw_category:
        normalized = _CATEGORY_ALIASES.get(raw_category.strip().lower())
        if normalized:
            return normalized

    source_text = (risk_source or "").lower()
    if "fraud" in source_text:
        return "Fraud"
    if "regulatory" in source_text or "compliance" in source_text:
        return "Compliance"
    if "incident" in source_text or "technology" in source_text or "it" in source_text:
        return "IT"
    return "Operational"


def _default_source_metadata(name: str) -> tuple[str, str]:
    key = name.lower()
    if key in _SOURCE_TYPE_DEFAULTS:
        return _SOURCE_TYPE_DEFAULTS[key]
    match = re.search(r"uc\s*([2-5])", key)
    if match:
        return (f"UC{match.group(1)}", f"UC{match.group(1)} Risk Output")
    return ("UC2-UC5", "Consolidated Risk Sources")


def _parse_statement_parts(text: str) -> tuple[str, str, str] | None:
    if not text:
        return None
    match = _RISK_STMT_RE.match(text.strip())
    if match:
        return tuple(part.strip().rstrip(".") for part in match.groups())
    for pattern in _DESCRIPTION_SPLIT_PATTERNS:
        match = pattern.match(text.strip())
        if match:
            return tuple(part.strip().rstrip(".") for part in match.groups())
    return None


def _extract_reference(raw_risk: dict, fallback: str) -> str:
    for key in _TRACE_REFERENCE_KEYS:
        value = raw_risk.get(key)
        if value:
            return str(value)
    return fallback


def _extract_cause_event_impact(raw_risk: dict) -> tuple[str, str, str]:
    if all(raw_risk.get(field) for field in ("cause", "event", "impact")):
        return (
            str(raw_risk["cause"]).strip(),
            str(raw_risk["event"]).strip(),
            str(raw_risk["impact"]).strip(),
        )

    for key in _TEXT_KEYS:
        value = raw_risk.get(key)
        if value:
            parsed = _parse_statement_parts(str(value))
            if parsed:
                return parsed

    cause = str(
        raw_risk.get("cause")
        or raw_risk.get("condition")
        or raw_risk.get("driver")
        or raw_risk.get("title")
        or raw_risk.get("summary")
        or raw_risk.get("description")
        or "Control weaknesses or external pressures arise"
    ).strip()

    event = str(
        raw_risk.get("event")
        or raw_risk.get("risk_event")
        or raw_risk.get("scenario")
        or raw_risk.get("exposure")
        or raw_risk.get("finding")
        or "the related business process fails or is bypassed"
    ).strip()

    impact = str(
        raw_risk.get("impact")
        or raw_risk.get("consequence")
        or raw_risk.get("business_impact")
        or raw_risk.get("result")
        or "financial, operational, or compliance consequences occur"
    ).strip()

    return (cause, event, impact)


def _flatten_risk_items(group_context: dict, items: list[dict]) -> list[dict]:
    flattened: list[dict] = []
    for index, raw_risk in enumerate(items, start=1):
        if not isinstance(raw_risk, dict):
            continue

        cause, event, impact = _extract_cause_event_impact(raw_risk)
        risk_source = str(raw_risk.get("risk_source") or group_context.get("risk_source") or "Consolidated Risk Sources")
        source_reference = _extract_reference(raw_risk, f"{group_context['source_use_case']} risk {index}")

        flattened.append({
            "source_use_case": group_context["source_use_case"],
            "risk_source": risk_source,
            "source_reference": source_reference,
            "process_id": raw_risk.get("process_id") or group_context.get("process_id", ""),
            "process_name": raw_risk.get("process_name") or group_context.get("process_name", ""),
            "sub_process_id": raw_risk.get("sub_process_id") or group_context.get("sub_process_id", ""),
            "sub_process_name": raw_risk.get("sub_process_name") or group_context.get("sub_process_name", ""),
            "objective": raw_risk.get("objective") or group_context.get("objective", ""),
            "cause": cause.strip(),
            "event": event.strip(),
            "impact": impact.strip(),
            "risk_category": _normalize_category(
                raw_risk.get("risk_category") or group_context.get("risk_category"),
                risk_source,
            ),
            "raw_source_text": str(
                raw_risk.get("risk_description")
                or raw_risk.get("description")
                or raw_risk.get("summary")
                or raw_risk.get("statement")
                or ""
            ).strip(),
        })
    return flattened


def _extract_group_items(container: Any) -> list[dict]:
    if isinstance(container, list):
        return [item for item in container if isinstance(item, dict)]

    if not isinstance(container, dict):
        return []

    for key in _COLLECTION_KEYS:
        value = container.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    if any(container.get(field) for field in ("cause", "risk_description", "description", "summary", "event", "impact")):
        return [container]
    return []


def _parse_named_collection(name: str, value: Any) -> list[dict]:
    source_use_case, risk_source = _default_source_metadata(name)
    flattened: list[dict] = []

    if isinstance(value, dict) and "use_cases" in value:
        nested = dict(value)
        nested.setdefault("use_cases", value.get("use_cases", []))
        return parse_use_cases(nested)

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and any(isinstance(item.get(key), list) for key in _COLLECTION_KEYS):
                group_context = {
                    "source_use_case": item.get("use_case_id") or item.get("id") or source_use_case,
                    "risk_source": item.get("risk_source") or item.get("source_type") or risk_source,
                    "process_id": item.get("process_id", ""),
                    "process_name": item.get("process_name", ""),
                    "sub_process_id": item.get("sub_process_id", ""),
                    "sub_process_name": item.get("sub_process_name", ""),
                    "objective": item.get("objective", ""),
                    "risk_category": item.get("risk_category"),
                }
                flattened.extend(_flatten_risk_items(group_context, _extract_group_items(item)))
            elif isinstance(item, dict):
                group_context = {
                    "source_use_case": item.get("use_case_id") or source_use_case,
                    "risk_source": item.get("risk_source") or item.get("source_type") or risk_source,
                    "process_id": item.get("process_id", ""),
                    "process_name": item.get("process_name", ""),
                    "sub_process_id": item.get("sub_process_id", ""),
                    "sub_process_name": item.get("sub_process_name", ""),
                    "objective": item.get("objective", ""),
                    "risk_category": item.get("risk_category"),
                }
                flattened.extend(_flatten_risk_items(group_context, [item]))
        return flattened

    if isinstance(value, dict):
        group_context = {
            "source_use_case": value.get("use_case_id") or value.get("id") or source_use_case,
            "risk_source": value.get("risk_source") or value.get("source_type") or risk_source,
            "process_id": value.get("process_id", ""),
            "process_name": value.get("process_name", ""),
            "sub_process_id": value.get("sub_process_id", ""),
            "sub_process_name": value.get("sub_process_name", ""),
            "objective": value.get("objective", ""),
            "risk_category": value.get("risk_category"),
        }
        flattened.extend(_flatten_risk_items(group_context, _extract_group_items(value)))

    return flattened


def parse_use_cases(input_data: dict) -> list[dict]:
    """
    Flatten audit risk inputs into a single risk list.

    Supported structures:
    - legacy `use_cases[]`
    - consolidated collections like `historical_risks`, `incidents`,
      `fraud_scenarios`, `regulatory_risks`, and `risk_sources`
    """
    flat: list[dict] = []

    for use_case in input_data.get("use_cases", []):
        use_case_id = use_case.get("id", "<unknown>")
        required_fields = ["id", "process_id", "process_name"]
        missing = [field for field in required_fields if field not in use_case]
        if missing:
            raise ValueError(f"Use case '{use_case_id}' is missing required fields: {missing}")

        group_context = {
            "source_use_case": use_case["id"],
            "risk_source": use_case.get("risk_source") or _default_source_metadata(use_case["id"])[1],
            "process_id": use_case["process_id"],
            "process_name": use_case["process_name"],
            "sub_process_id": use_case.get("sub_process_id", ""),
            "sub_process_name": use_case.get("sub_process_name", ""),
            "objective": use_case.get("objective", ""),
            "risk_category": use_case.get("risk_category"),
        }
        risks = use_case.get("risks", [])
        for index, raw_risk in enumerate(risks, start=1):
            if not isinstance(raw_risk, dict):
                continue
            if not any(raw_risk.get(field) for field in ("cause", "risk_description", "description", "summary", "event", "impact")):
                raise ValueError(
                    f"Use case '{use_case_id}' risk #{index} is missing risk content fields"
                )
        flat.extend(_flatten_risk_items(group_context, [risk for risk in risks if isinstance(risk, dict)]))

    handled_keys = {"context", "processes", "use_cases"}
    for key, value in input_data.items():
        if key in handled_keys:
            continue
        if isinstance(value, (dict, list)):
            flat.extend(_parse_named_collection(key, value))

    return flat


def normalize_risk(risk: dict) -> dict:
    cause = risk["cause"].strip().rstrip(".")
    event = risk["event"].strip().rstrip(".")
    impact = risk["impact"].strip().rstrip(".")
    statement = (
        f"As a result of {cause}, "
        f"there is a risk that {event}, "
        f"leading to {impact}."
    )
    return {**risk, "risk_statement": statement, "risk_category": _normalize_category(risk.get("risk_category"), risk.get("risk_source"))}


def deduplicate_risks(
    risks: list[dict],
    similarity_threshold: float = 0.65,
) -> list[dict]:
    canonical: list[dict] = []

    for risk in risks:
        stmt_key = _content_key(risk.get("risk_statement", ""))
        merged = False
        for canon in canonical:
            score = fuzz.token_sort_ratio(stmt_key, _content_key(canon["risk_statement"]))
            same_context = (
                canon.get("process_id") == risk.get("process_id")
                and canon.get("sub_process_id") == risk.get("sub_process_id")
            ) or not canon.get("sub_process_id") or not risk.get("sub_process_id")
            if same_context and score >= similarity_threshold * 100:
                source_use_cases = list(risk.get("source_use_cases", []))
                if not source_use_cases and risk.get("source_use_case"):
                    source_use_cases = [risk["source_use_case"]]
                risk_sources = list(risk.get("risk_sources", []))
                if not risk_sources and risk.get("risk_source"):
                    risk_sources = [risk["risk_source"]]
                source_references = list(risk.get("source_references", []))
                if not source_references and risk.get("source_reference"):
                    source_references = [risk["source_reference"]]
                raw_source_texts = list(risk.get("raw_source_texts", []))
                if not raw_source_texts and risk.get("raw_source_text"):
                    raw_source_texts = [risk["raw_source_text"]]
                canon["source_use_cases"] = _dedupe_list(
                    canon.get("source_use_cases", []) + source_use_cases
                )
                canon["risk_sources"] = _dedupe_list(
                    canon.get("risk_sources", []) + risk_sources
                )
                canon["source_references"] = _dedupe_list(
                    canon.get("source_references", []) + source_references
                )
                canon["raw_source_texts"] = _dedupe_list(
                    canon.get("raw_source_texts", []) + raw_source_texts
                )
                merged = True
                break
        if merged:
            continue

        new_entry = dict(risk)
        source_use_case = new_entry.pop("source_use_case", None)
        risk_source = new_entry.pop("risk_source", None)
        source_reference = new_entry.pop("source_reference", None)
        raw_source_text = new_entry.pop("raw_source_text", None)
        new_entry["source_use_cases"] = _dedupe_list(
            new_entry.get("source_use_cases", []) + ([source_use_case] if source_use_case else [])
        )
        new_entry["risk_sources"] = _dedupe_list(
            new_entry.get("risk_sources", []) + ([risk_source] if risk_source else [])
        )
        new_entry["source_references"] = _dedupe_list(
            new_entry.get("source_references", []) + ([source_reference] if source_reference else [])
        )
        new_entry["raw_source_texts"] = _dedupe_list(
            new_entry.get("raw_source_texts", []) + ([raw_source_text] if raw_source_text else [])
        )
        canonical.append(new_entry)

    return canonical


def score_inherent_risk(impact: int, likelihood: int) -> int:
    impact = max(1, min(5, impact))
    likelihood = max(1, min(5, likelihood))
    return impact * likelihood


def calculate_preliminary_residual(
    inherent_score: int,
    control_design_effectiveness: str | None,
) -> float:
    reduction = _DESIGN_REDUCTION.get(control_design_effectiveness, 0.00)
    return round(inherent_score * (1 - reduction), 2)


def _parse_risk_appetite_level(value: str) -> str:
    lowered = value.lower()
    if "zero" in lowered:
        return "Zero"
    if "low" in lowered or "minimal" in lowered:
        return "Low"
    if "high" in lowered:
        return "High"
    return "Moderate"


def _risk_appetite_adjustment(risk_category: str, risk_appetite: dict) -> tuple[int, int]:
    keys = _RISK_APPETITE_KEYS.get(risk_category, ())
    appetite_text = ""
    for key in keys:
        if key in risk_appetite and risk_appetite[key]:
            appetite_text = str(risk_appetite[key])
            break
    level = _parse_risk_appetite_level(appetite_text) if appetite_text else "Moderate"
    return {
        "Zero": (1, 1),
        "Low": (1, 0),
        "Moderate": (0, 0),
        "High": (-1, 0),
    }.get(level, (0, 0))


def _source_signal_adjustment(risk: dict) -> tuple[int, int]:
    impact_delta = 0
    likelihood_delta = 0
    risk_sources = {source.lower() for source in risk.get("risk_sources", [])}
    source_references = " ".join(risk.get("source_references", [])).lower()
    risk_text = " ".join([
        risk.get("cause", ""),
        risk.get("event", ""),
        risk.get("impact", ""),
        source_references,
    ]).lower()

    if len(risk_sources) > 1:
        likelihood_delta += 1
    if any("incident" in source for source in risk_sources):
        likelihood_delta += 1
    if any("fraud" in source for source in risk_sources) or risk.get("risk_category") == "Fraud":
        impact_delta += 1
        likelihood_delta += 1
    if any(token in risk_text for token in ("material", "critical", "breach", "outage", "misstatement", "penalt", "fine")):
        impact_delta += 1
    if any(token in risk_text for token in ("repeated", "repeat", "recurring", "history", "trend")):
        likelihood_delta += 1

    return impact_delta, likelihood_delta


def _assign_inherent_scores(risk: dict, risk_appetite: dict) -> tuple[int, int]:
    impact, likelihood = _CATEGORY_DEFAULTS.get(risk.get("risk_category", "Operational"), (3, 3))
    appetite_impact, appetite_likelihood = _risk_appetite_adjustment(risk.get("risk_category", "Operational"), risk_appetite)
    source_impact, source_likelihood = _source_signal_adjustment(risk)
    impact = max(1, min(5, impact + appetite_impact + source_impact))
    likelihood = max(1, min(5, likelihood + appetite_likelihood + source_likelihood))
    return impact, likelihood


def get_risk_rating(score: float) -> str:
    if score <= 9:
        return "Low"
    if score <= 15:
        return "Medium"
    return "High"


def _normalize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            return token[:-len(suffix)]
    return token


def _meaningful_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in re.findall(r"[A-Za-z0-9]+", value.lower()):
            normalized = _normalize_token(token)
            if len(normalized) < 4 or normalized in _TOKEN_STOPWORDS:
                continue
            tokens.add(normalized)
    return tokens


def _select_scenario_blueprint(risk: dict) -> dict:
    stage1 = risk.get("stage1", risk)
    tokens = _meaningful_tokens(
        stage1.get("process_name", ""),
        stage1.get("sub_process_name", ""),
        stage1.get("objective", ""),
        stage1.get("cause", ""),
        stage1.get("event", ""),
        stage1.get("impact", ""),
        stage1.get("risk_category", ""),
    )

    best_match = _SCENARIO_BLUEPRINTS[-1]
    best_score = -1
    for blueprint in _SCENARIO_BLUEPRINTS:
        score = len(tokens & blueprint["keywords"])
        if score > best_score:
            best_match = blueprint
            best_score = score
    return best_match


def _render_control_blueprint(template: dict, stage1: dict, control_id: str) -> dict:
    objective = stage1.get("objective") or stage1.get("sub_process_name") or stage1.get("process_name")
    event = stage1.get("event", "the risk event occurs")
    description = f"{template['description']} for {objective}"
    what = f"{template['what']} The activity is tailored to the risk that {event}."
    how = f"{template['how']} It focuses on the context of {stage1.get('sub_process_name') or stage1.get('process_name', 'the process')}."
    why = f"{template['why']} Specifically addresses the risk that {event}."
    return {
        "control_id": control_id,
        "description": description,
        "who": template["who"],
        "control_owner": template["control_owner"],
        "what": what,
        "when": template["when"],
        "frequency": template["frequency"],
        "where": template["where"],
        "how": how,
        "why": why,
        "evidence": template["evidence"],
        "evidence_type": template["evidence_type"],
        "execution_type": template["execution_type"],
        "nature": template["nature"],
        "significance": template["significance"],
        "control_design_effectiveness": template["control_design_effectiveness"],
        "it_dependent": template["it_dependent"],
    }


def draft_controls(risk: dict, start_index: int) -> list[dict]:
    stage1 = risk.get("stage1", risk)
    scenario = _select_scenario_blueprint(risk)
    controls: list[dict] = []
    for offset, template in enumerate(scenario["controls"]):
        controls.append(_render_control_blueprint(template, stage1, f"CTRL-{start_index + offset:04d}"))
    return controls


def draft_control(risk: dict, control_index: int) -> dict:
    return draft_controls(risk, control_index)[0]


def _control_is_unmapped(risk: dict, control: dict) -> bool:
    stage1 = risk.get("stage1", {})
    risk_tokens = _meaningful_tokens(
        stage1.get("sub_process_name", ""),
        stage1.get("objective", ""),
        stage1.get("cause", ""),
        stage1.get("event", ""),
        stage1.get("impact", ""),
    )
    control_tokens = _meaningful_tokens(
        control.get("description", ""),
        control.get("what", ""),
        control.get("why", ""),
        control.get("where", ""),
    )
    return not (risk_tokens & control_tokens)


def _find_redundant_risk_ids(risks: list[dict]) -> set[str]:
    signature_to_risk_ids: dict[tuple[str, ...], list[str]] = {}

    for risk in risks:
        stage1 = risk.get("stage1", {})
        if not stage1.get("sub_process_id"):
            continue
        for control in risk.get("stage2", {}).get("controls", []):
            signature = (
                stage1.get("process_id", ""),
                stage1.get("sub_process_id", ""),
                stage1.get("objective_id", ""),
                control.get("description", ""),
                control.get("execution_type", ""),
                control.get("nature", ""),
                control.get("significance", ""),
                control.get("frequency", ""),
            )
            signature_to_risk_ids.setdefault(signature, []).append(risk["risk_id"])

    redundant_risk_ids: set[str] = set()
    for risk_ids in signature_to_risk_ids.values():
        if len(risk_ids) > 1:
            redundant_risk_ids.update(risk_ids[1:])
    return redundant_risk_ids


def _evaluate_design_gap(risk: dict, controls: list[dict], is_redundant: bool) -> tuple[bool, str, str]:
    if not controls:
        return True, "Missing", "Risk has no mitigating controls assigned."
    if all(_control_is_unmapped(risk, control) for control in controls):
        return True, "Unmapped", "Linked control design does not align to the mapped risk and objective context."
    if all(control.get("control_design_effectiveness") == "Weak" for control in controls):
        return True, "Weak", "All linked controls are weak by design and may not sufficiently mitigate the risk."
    if is_redundant:
        return True, "Redundant", "Control design duplicates another control already linked to the same sub-process and objective."
    return False, "None", "No design gap identified."


def _find_empty_sub_processes(context: dict, raw_risks: list[dict]) -> list[dict]:
    mapped_sub_process_ids = {
        risk.get("sub_process_id", "")
        for risk in raw_risks
        if risk.get("sub_process_id")
    }

    empty_sub_processes: list[dict] = []
    for process_id, process in context.get("processes", {}).items():
        for sub_process in process.get("sub_processes", []):
            sub_process_id = sub_process.get("sub_process_id", "")
            if sub_process_id and sub_process_id not in mapped_sub_process_ids:
                empty_sub_processes.append({
                    "process_id": process_id,
                    "process_name": process.get("process_name", ""),
                    "sub_process_id": sub_process_id,
                    "sub_process_name": sub_process.get("sub_process_name", ""),
                })
    return empty_sub_processes


def _assess_mapping_integrity(risks: list[dict]) -> dict[str, Any]:
    orphan_risk_ids = [
        risk["risk_id"]
        for risk in risks
        if not risk.get("stage2", {}).get("controls")
    ]
    orphan_control_ids: list[str] = []
    return {
        "passed": not orphan_risk_ids and not orphan_control_ids,
        "orphan_risk_ids": orphan_risk_ids,
        "orphan_control_ids": orphan_control_ids,
    }


def _assess_taxonomy_validation(risks: list[dict]) -> dict[str, Any]:
    issues: list[str] = []
    valid_categories = {"Operational", "IT", "Compliance", "Fraud", "Financial", "Strategic"}
    for risk in risks:
        stage1 = risk.get("stage1", {})
        risk_id = risk.get("risk_id", "<unknown>")
        if not _RISK_STMT_RE.match(stage1.get("risk_statement", "")):
            issues.append(f"{risk_id}: risk statement is not in Cause-Event-Impact format.")
        if stage1.get("risk_category") not in valid_categories:
            issues.append(f"{risk_id}: risk category is not aligned to the supported UC7 taxonomy.")
        if not stage1.get("objective_id") or not stage1.get("objective"):
            issues.append(f"{risk_id}: missing business objective linkage.")
        for control in risk.get("stage2", {}).get("controls", []):
            control_id = control.get("control_id", "<unknown>")
            if len(control.get("description", "").split()) < 5:
                issues.append(f"{control_id}: control description is too short for audit use.")
            if control.get("evidence_type") not in _EVIDENCE_TYPES:
                issues.append(f"{control_id}: evidence type is outside the standard taxonomy.")
    return {"passed": not issues, "issues": issues}


def _build_quality_checks(context: dict, raw_risks: list[dict], output_risks: list[dict]) -> tuple[list[str], dict[str, Any]]:
    empty_sub_processes = _find_empty_sub_processes(context, raw_risks)
    mapping_integrity = _assess_mapping_integrity(output_risks)
    taxonomy_validation = _assess_taxonomy_validation(output_risks)

    warnings = [
        (
            "Structural Integrity warning: "
            f"sub-process '{item['sub_process_id']} - {item['sub_process_name']}' "
            f"in process '{item['process_name']}' has no associated risks."
        )
        for item in empty_sub_processes
    ]
    warnings.extend(
        f"Mapping Integrity warning: risk '{risk_id}' has no linked controls."
        for risk_id in mapping_integrity["orphan_risk_ids"]
    )
    warnings.extend(
        f"Taxonomy Validation warning: {issue}"
        for issue in taxonomy_validation["issues"]
    )

    quality_checks = {
        "structural_integrity": {
            "passed": not empty_sub_processes,
            "empty_sub_processes": empty_sub_processes,
        },
        "mapping_integrity": mapping_integrity,
        "taxonomy_validation": taxonomy_validation,
    }
    return warnings, quality_checks


def build_draft_rcm(input_data: dict) -> dict:
    context = parse_context(input_data)
    objective_lookup = _build_objective_lookup(context, input_data.get("use_cases", []))
    raw_risks = parse_use_cases(input_data)
    normalized = [normalize_risk(risk) for risk in raw_risks]
    deduped = deduplicate_risks(normalized)

    output_risks: list[dict] = []
    control_index = 1
    for index, risk in enumerate(deduped, start=1):
        risk_id = f"RISK-{index:04d}"
        impact, likelihood = _assign_inherent_scores(risk, context.get("risk_appetite", {}))
        inherent_score = score_inherent_risk(impact, likelihood)
        objective_id = _get_objective_id(risk, objective_lookup)

        stage1 = {
            "process_id": risk.get("process_id", ""),
            "process_name": risk.get("process_name", ""),
            "sub_process_id": risk.get("sub_process_id", ""),
            "sub_process_name": risk.get("sub_process_name", ""),
            "objective_id": objective_id,
            "objective": risk.get("objective", ""),
            "cause": risk["cause"],
            "event": risk["event"],
            "impact": risk["impact"],
            "risk_statement": risk["risk_statement"],
            "risk_category": risk["risk_category"],
            "source_use_cases": risk.get("source_use_cases", []),
            "risk_sources": risk.get("risk_sources", []),
            "source_references": risk.get("source_references", []),
            "gias_compliance": {
                "standard_13_2": True,
                "standard_13_6": True,
            },
        }

        staged_risk = {"risk_id": risk_id, "stage1": stage1}
        controls = draft_controls(staged_risk, control_index)
        control_index += len(controls)
        strongest_design = next(
            (
                level
                for level in ("Strong", "Moderate", "Weak")
                if any(control.get("control_design_effectiveness") == level for control in controls)
            ),
            None,
        )
        preliminary_residual = calculate_preliminary_residual(inherent_score, strongest_design)

        staged_risk["stage2"] = {
            "inherent_impact": impact,
            "inherent_likelihood": likelihood,
            "inherent_risk_score": inherent_score,
            "inherent_risk_rating": get_risk_rating(inherent_score),
            "preliminary_residual_risk": preliminary_residual,
            "preliminary_residual_rating": get_risk_rating(preliminary_residual),
            "design_gap": False,
            "design_gap_type": "None",
            "design_gap_description": "No design gap identified.",
            "controls": controls,
        }
        output_risks.append(staged_risk)

    redundant_risk_ids = _find_redundant_risk_ids(output_risks)
    for risk in output_risks:
        controls = risk.get("stage2", {}).get("controls", [])
        design_gap, gap_type, gap_description = _evaluate_design_gap(
            risk,
            controls,
            risk["risk_id"] in redundant_risk_ids,
        )
        risk["stage2"].update({
            "design_gap": design_gap,
            "design_gap_type": gap_type,
            "design_gap_description": gap_description,
        })

    warnings, quality_checks = _build_quality_checks(context, raw_risks, output_risks)

    return {
        "rcm_version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "warnings": warnings,
        "quality_checks": quality_checks,
        "risks": output_risks,
    }


_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from rcm_it_validator import apply_it_validation  # noqa: E402


def validate_against_schema(rcm: dict, schema_path: Path) -> None:
    import jsonschema

    schema = json.loads(schema_path.read_text())
    jsonschema.validate(rcm, schema)


def to_markdown_table(rcm: dict) -> str:
    headers = [
        "Risk ID",
        "Objective ID",
        "Sub-Process",
        "Process",
        "Objective",
        "Risk Sources",
        "Source References",
        "Risk Statement",
        "Category",
        "Impact",
        "Likelihood",
        "Inherent Risk",
        "Inherent Rating",
        "Control ID",
        "Control Description",
        "Control Owner",
        "Frequency",
        "Evidence Type",
        "Exec Type",
        "Nature",
        "Significance",
        "Design Effectiveness",
        "Design Gap",
        "System",
        "Report",
        "ITGC Dependency",
        "IPE Validation",
        "Control Reliability",
        "Additional ITGC Control",
        "Final Residual Risk",
        "Final Rating",
        "Residual Change",
        "New UC6 Risk",
        "Source Use Cases",
    ]
    rows = [headers, ["---"] * len(headers)]

    for risk in rcm.get("risks", []):
        stage1 = risk["stage1"]
        stage2 = risk["stage2"]
        stage3 = risk.get("stage3", {})
        assessments = {item["control_id"]: item for item in stage3.get("controls_it_assessment", [])}

        for control in stage2.get("controls", []):
            assessment = assessments.get(control["control_id"], {})
            rows.append([
                risk["risk_id"],
                stage1.get("objective_id", ""),
                stage1.get("sub_process_name", "N/A"),
                stage1.get("process_name", ""),
                stage1.get("objective", ""),
                ", ".join(stage1.get("risk_sources", [])),
                ", ".join(stage1.get("source_references", [])),
                stage1.get("risk_statement", ""),
                stage1.get("risk_category", ""),
                str(stage2.get("inherent_impact", "")),
                str(stage2.get("inherent_likelihood", "")),
                str(stage2.get("inherent_risk_score", "")),
                stage2.get("inherent_risk_rating", ""),
                control.get("control_id", ""),
                control.get("description", ""),
                control.get("control_owner", ""),
                control.get("frequency", ""),
                control.get("evidence_type", ""),
                control.get("execution_type", ""),
                control.get("nature", ""),
                control.get("significance", ""),
                control.get("control_design_effectiveness", ""),
                stage2.get("design_gap_type", ""),
                assessment.get("system_name", ""),
                assessment.get("report_name", ""),
                ", ".join(assessment.get("itgc_dependency_type", [])),
                assessment.get("ipe_validation_level", "N/A"),
                assessment.get("control_reliability", "Not Assessed"),
                assessment.get("itgc_control_description", ""),
                str(stage3.get("final_residual_risk", stage2.get("preliminary_residual_risk", ""))),
                stage3.get("final_residual_rating", stage2.get("preliminary_residual_rating", "")),
                str(stage3.get("residual_risk_change", 0.0)),
                stage3.get("new_risk_description", ""),
                ", ".join(stage1.get("source_use_cases", [])),
            ])

    def _cell(value: str) -> str:
        return str(value).replace("|", "\\|")

    return "\n".join("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)


def run_pipeline(input_data: dict, it_matrix: dict) -> dict:
    draft = build_draft_rcm(input_data)
    return apply_it_validation(draft, it_matrix)


def main() -> None:
    parser = argparse.ArgumentParser(description="RCM Builder Pipeline")
    parser.add_argument("--input", required=True, help="Path to use-case input JSON")
    parser.add_argument("--it-matrix", required=True, help="Path to IT dependency matrix JSON")
    parser.add_argument("--out-json", default="outputs/rcm_output.json", help="Output JSON path")
    parser.add_argument("--out-md", default="outputs/rcm_output.md", help="Output Markdown path")
    parser.add_argument("--schema", default="outputs/schemas/rcm-schema.json", help="Schema path")
    args = parser.parse_args()

    input_data = json.loads(Path(args.input).read_text())
    it_matrix = json.loads(Path(args.it_matrix).read_text())
    result = run_pipeline(input_data, it_matrix)

    schema_path = Path(args.schema)
    if schema_path.exists():
        validate_against_schema(result, schema_path)
        print("Schema validation: PASSED")
    else:
        print(f"Warning: schema file not found at '{schema_path}' — validation skipped.")

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2))
    print(f"JSON output written to: {out_json}")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(to_markdown_table(result))
    print(f"Markdown output written to: {out_md}")


if __name__ == "__main__":
    main()
