#!/usr/bin/env python3
"""Generate deterministic synthetic datasets for the SAAF Strapi sandbox.

Usage:
  python3 tools/scripts/generate_synthetic_data.py

The script writes canonical JSON seed files into tools/strapi/seed/.
It does not call external APIs; the output is deterministic so teams can
regenerate the same fixture set and compare agent results consistently.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

BASE_DATE = date(2026, 4, 21)
SEED = 20260421
SEED_DIR = Path(__file__).resolve().parents[1] / "strapi" / "seed"

INCIDENT_COUNT = 500
ACCESS_REVIEW_COUNT = 200
CHANGE_TICKET_COUNT = 150
VENDOR_COUNT = 50
FINDING_COUNT = 100

PRIORITIES = ["P1", "P2", "P3", "P4"]
INCIDENT_CATEGORIES = [
    "Network Outage",
    "Access Issue",
    "Application Error",
    "Security Alert",
    "Data Quality",
]
TEAMS = [
    "Platform Engineering",
    "IAM Operations",
    "Payments Reliability",
    "Security Operations",
    "Data Services",
]
SYSTEMS = ["Active Directory", "SAP", "AWS", "Azure", "Okta", "ServiceNow"]
ROLES = [
    "System Administrator",
    "Read-Only Analyst",
    "Payments Developer",
    "Security Engineer",
    "Finance Operator",
    "Vendor Manager",
]
ENTITLEMENTS = [
    "Domain Admin",
    "Billing Approver",
    "Production Deploy",
    "Read-Only Finance",
    "Vendor Portal Admin",
    "Security Dashboard",
]
CHANGE_SYSTEMS = ["Payments API", "Core ERP", "Identity Platform", "Data Warehouse", "Customer Portal"]
CHANGE_TYPES = ["Standard", "Normal", "Emergency"]
CHANGE_STATUSES = ["Planned", "Implemented", "Backed Out", "Closed"]
SERVICES = [
    "Cloud Hosting",
    "Payroll Processing",
    "Identity Verification",
    "Threat Monitoring",
    "Managed SOC",
    "CRM Platform",
]
CRITICALITIES = ["Critical", "High", "Medium", "Low"]
RISK_RATINGS = ["High", "Medium", "Low"]
SLA_TIERS = ["Always On", "Business Hours", "Best Effort"]
TPRM_STATUSES = ["In Review", "Approved", "Expired", "Remediation Required"]
FINDING_RATINGS = ["High", "Medium", "Low", "Informational"]
FINDING_STATUSES = ["Open", "In Progress", "Closed"]

PERSON_PREFIXES = [
    "Aela",
    "Brin",
    "Cael",
    "Daro",
    "Eris",
    "Fenn",
    "Galen",
    "Hali",
    "Iven",
    "Jora",
    "Kael",
    "Lumi",
    "Mira",
    "Neris",
    "Orin",
    "Pavo",
    "Quin",
    "Riva",
    "Soren",
    "Tarin",
]
PERSON_SUFFIXES = [
    "Nor",
    "Vale",
    "Dred",
    "Mere",
    "Sel",
    "Tor",
    "Wyn",
    "Lark",
    "Venn",
    "Crest",
]
ORG_PREFIXES = [
    "Nexa",
    "Velora",
    "Kintara",
    "Solvix",
    "Marova",
    "Terniq",
    "Aureli",
    "Cindor",
    "Noviq",
    "Halcyo",
]
ORG_SUFFIXES = [
    "Works",
    "Systems",
    "Cloud",
    "Labs",
    "Metrics",
    "Partners",
    "Holdings",
    "Services",
]


@dataclass(frozen=True)
class SyntheticPerson:
    name: str


def rng() -> random.Random:
    return random.Random(SEED)


def person_name(index: int) -> str:
    first = PERSON_PREFIXES[index % len(PERSON_PREFIXES)]
    second = PERSON_SUFFIXES[(index * 3) % len(PERSON_SUFFIXES)]
    return f"{first} {second}"


def org_name(index: int) -> str:
    prefix = ORG_PREFIXES[index % len(ORG_PREFIXES)]
    suffix = ORG_SUFFIXES[(index * 5) % len(ORG_SUFFIXES)]
    return f"{prefix} {suffix}"


def iso_datetime(day_offset: int, hour: int, minute: int) -> str:
    dt = datetime.combine(BASE_DATE - timedelta(days=day_offset), time(hour=hour, minute=minute))
    return dt.isoformat() + "Z"


def iso_date(day_offset: int) -> str:
    return (BASE_DATE - timedelta(days=day_offset)).isoformat()


def write_dataset(name: str, records: list[dict]) -> None:
    path = SEED_DIR / f"{name}.json"
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def generate_incidents() -> list[dict]:
    records: list[dict] = []
    exception_indices = {i for i in range(INCIDENT_COUNT) if i % 7 == 0}

    for i in range(INCIDENT_COUNT):
        priority = PRIORITIES[0 if i < 35 else 1 if i < 75 else 2 if i % 2 == 0 else 3]
        category = INCIDENT_CATEGORIES[i % len(INCIDENT_CATEGORIES)]
        reported_offset = 1 + (i % 340)
        duration_hours = round(0.75 + ((i * 37) % 420) / 24, 2)
        duration_minutes = int(duration_hours * 60)
        resolved_dt = datetime.fromisoformat(iso_datetime(reported_offset, 8 + (i % 8), (i * 7) % 60).replace("Z", ""))
        reported_dt = resolved_dt - timedelta(minutes=duration_minutes)
        is_exception = i in exception_indices
        exception_type = None
        post_incident_review_completed = not is_exception or i % 3 == 0
        if is_exception:
            exception_type = [
                "No post-incident review within SLA (5 business days)",
                "Root cause not documented",
                "Escalation path bypassed for major incident",
            ][i % 3]

        records.append(
            {
                "ticket_id": f"INC-2026-{i + 1:04d}",
                "title": f"{category} disruption affecting control process {((i % 12) + 1):02d}",
                "priority": priority,
                "category": category,
                "reported_at": reported_dt.isoformat() + "Z",
                "resolved_at": resolved_dt.isoformat() + "Z",
                "mttr_hours": duration_hours,
                "assigned_team": TEAMS[i % len(TEAMS)],
                "root_cause": [
                    "Database connection pool exhausted during peak workload",
                    "Privileged access sync job failed after malformed entitlement update",
                    "Firewall rule promotion omitted one production subnet",
                    "Certificate rotation missed a dependent integration endpoint",
                    "Inbound validation rule rejected a valid payment status message",
                ][i % 5],
                "resolution_summary": [
                    "Service restored after rollback and cache flush.",
                    "Access sync rerun completed and stale grants removed.",
                    "Firewall rule corrected and traffic verified end-to-end.",
                    "Certificate chain redeployed and dependent service restarted.",
                    "Validation rules updated and replay queue drained.",
                ][i % 5],
                "post_incident_review_completed": post_incident_review_completed,
                "is_exception": is_exception,
                "exception_type": exception_type,
            }
        )
    return records


def generate_access_reviews() -> list[dict]:
    records: list[dict] = []
    exception_indices = {i for i in range(ACCESS_REVIEW_COUNT) if i % 7 == 0 or i % 29 == 0}

    for i in range(ACCESS_REVIEW_COUNT):
        is_exception = i in exception_indices
        review_outcome = "Approved"
        reviewer = person_name(i + 60)
        employment_end_date = None
        days_since_termination = None
        exception_type = None

        if is_exception:
            exception_type = [
                "Leaver with active account",
                "SoD conflict",
                "Overdue review",
                "Privileged access without business justification",
            ][i % 4]
            if exception_type == "Leaver with active account":
                review_outcome = "Not reviewed"
                reviewer = None
                days_since_termination = 12 + (i % 90)
                employment_end_date = iso_date(days_since_termination)
            elif exception_type == "SoD conflict":
                review_outcome = "Escalated"
            elif exception_type == "Overdue review":
                review_outcome = "Not reviewed"
                reviewer = None
            else:
                review_outcome = "Escalated"
        elif i % 17 == 0:
            review_outcome = "Revoked"

        records.append(
            {
                "user_id": f"USR-{i + 1:04d}",
                "user_name": person_name(i),
                "role": ROLES[i % len(ROLES)],
                "system": SYSTEMS[i % len(SYSTEMS)],
                "entitlement": ENTITLEMENTS[i % len(ENTITLEMENTS)],
                "last_review_date": iso_date(7 + (i % 120)),
                "review_outcome": review_outcome,
                "reviewer": reviewer,
                "employment_end_date": employment_end_date,
                "days_since_termination": days_since_termination,
                "is_exception": is_exception,
                "exception_type": exception_type,
            }
        )
    return records[:ACCESS_REVIEW_COUNT]


def generate_change_tickets() -> list[dict]:
    records: list[dict] = []
    exception_indices = {i for i in range(CHANGE_TICKET_COUNT) if i % 6 == 0}

    for i in range(CHANGE_TICKET_COUNT):
        requested_dt = datetime.fromisoformat(iso_datetime(4 + (i % 250), 9 + (i % 6), (i * 11) % 60).replace("Z", ""))
        implemented_dt = requested_dt + timedelta(days=1 + (i % 4), hours=2 + (i % 5))
        approved_dt = requested_dt + timedelta(hours=6 + (i % 10))
        tested_dt = implemented_dt - timedelta(hours=2)
        change_type = CHANGE_TYPES[i % len(CHANGE_TYPES)]
        status = "Closed" if i % 9 != 0 else "Implemented"
        is_exception = i in exception_indices
        emergency_flag = change_type == "Emergency" or i % 13 == 0
        exception_type = None

        if is_exception:
            exception_type = [
                "Implemented before approval",
                "Missing testing evidence",
                "Emergency change without retrospective approval",
            ][i % 3]
            if exception_type == "Implemented before approval":
                approved_dt = implemented_dt + timedelta(hours=4)
            if exception_type == "Missing testing evidence":
                tested_dt = None
            if exception_type == "Emergency change without retrospective approval":
                approved_dt = None
                emergency_flag = True

        records.append(
            {
                "change_id": f"CHG-2026-{i + 1:04d}",
                "summary": f"{CHANGE_SYSTEMS[i % len(CHANGE_SYSTEMS)]} release batch {((i % 20) + 1):02d}",
                "requested_at": requested_dt.isoformat() + "Z",
                "approved_at": approved_dt.isoformat() + "Z" if approved_dt else None,
                "implemented_at": implemented_dt.isoformat() + "Z",
                "tested_at": tested_dt.isoformat() + "Z" if tested_dt else None,
                "requested_by": person_name(i + 200),
                "approved_by": person_name(i + 260) if approved_dt else None,
                "implemented_by": person_name(i + 320),
                "system": CHANGE_SYSTEMS[i % len(CHANGE_SYSTEMS)],
                "change_type": change_type,
                "status": status,
                "emergency_flag": emergency_flag,
                "testing_evidence": None if tested_dt is None else f"Regression pack TP-{i + 1:04d} attached to CAB record.",
                "is_exception": is_exception,
                "exception_type": exception_type,
            }
        )
    return records


def generate_vendor_contracts() -> list[dict]:
    records: list[dict] = []
    exception_indices = {i for i in range(VENDOR_COUNT) if i % 6 == 0}

    for i in range(VENDOR_COUNT):
        criticality = CRITICALITIES[i % len(CRITICALITIES)]
        risk_rating = RISK_RATINGS[0 if criticality == "Critical" else 1 if criticality == "High" else 2]
        is_exception = i in exception_indices
        tprm_status = "Approved"
        exception_type = None

        if is_exception:
            tprm_status = ["Expired", "Remediation Required", "In Review"][i % 3]
            exception_type = [
                "Vendor assessment overdue",
                "Critical vendor without current contract review",
                "Data processing addendum missing",
            ][i % 3]

        records.append(
            {
                "vendor_id": f"VND-{i + 1:03d}",
                "vendor_name": org_name(i),
                "service": SERVICES[i % len(SERVICES)],
                "criticality": criticality,
                "risk_rating": risk_rating,
                "sla_tier": SLA_TIERS[i % len(SLA_TIERS)],
                "last_audit_date": iso_date(25 + (i * 9) % 320),
                "contract_end_date": (BASE_DATE + timedelta(days=45 + (i * 17) % 480)).isoformat(),
                "tprm_status": tprm_status,
                "data_processing": i % 2 == 0,
                "is_exception": is_exception,
                "exception_type": exception_type,
            }
        )
    return records


def generate_findings() -> list[dict]:
    records: list[dict] = []
    control_objectives = [
        "ISO 27001 A.5.18 Access rights",
        "COBIT BAI06 Manage IT Changes",
        "SOC 2 CC6 Logical access",
        "Third-party risk management policy",
        "Incident response standard",
    ]

    for i in range(FINDING_COUNT):
        rating = FINDING_RATINGS[0 if i < 18 else 1 if i < 50 else 2 if i < 82 else 3]
        status = FINDING_STATUSES[i % len(FINDING_STATUSES)]
        records.append(
            {
                "id": f"F-{i + 1:03d}",
                "title": [
                    "Privileged account remained active after termination",
                    "Major incident review not completed within SLA",
                    "Change implemented before formal approval",
                    "Critical vendor assessment expired",
                    "Access review evidence incomplete",
                ][i % 5],
                "risk_rating": rating,
                "control_objective": control_objectives[i % len(control_objectives)],
                "observation": [
                    "Synthetic testing shows a terminated user retained privileged access beyond the expected deprovisioning window.",
                    "Synthetic incident logs indicate the post-incident review was not completed within the required five-business-day SLA.",
                    "Synthetic change records show implementation activity preceding recorded approver sign-off.",
                    "Synthetic vendor records indicate the latest assurance review expired before contract renewal.",
                    "Synthetic access review records show missing reviewer evidence for a subset of privileged users.",
                ][i % 5],
                "root_cause": [
                    "Joiner-mover-leaver workflow was not consistently monitored.",
                    "Incident management team did not track PIR due dates centrally.",
                    "Emergency implementation pressure bypassed normal CAB timing.",
                    "Third-party review calendar did not alert on upcoming expiries.",
                    "Review workflow allowed closure without mandatory evidence attachment.",
                ][i % 5],
                "impact": [
                    "Excess access could allow unauthorized changes or data exposure.",
                    "Recurring incident causes may remain unidentified and unaddressed.",
                    "Unapproved production changes increase operational and compliance risk.",
                    "The organization may rely on a vendor without current assurance evidence.",
                    "Management cannot demonstrate timely completion of access governance controls.",
                ][i % 5],
                "recommendation": [
                    "Enforce automated deprovisioning checks for terminated identities and review exceptions weekly.",
                    "Track PIR due dates and require closure evidence before incident closure.",
                    "Block production implementation when approver sign-off is missing unless emergency workflow is documented.",
                    "Introduce automated reminders for vendor reviews before contract renewal dates.",
                    "Require reviewer identity and review outcome evidence before marking a review complete.",
                ][i % 5],
                "management_response": [
                    "Management will review IAM exception handling and automate stale-account reporting.",
                    "Operations will add a PIR tracking board to the major incident process.",
                    "CAB will enforce workflow gating in the change tool.",
                    "TPRM will align renewal reminders with procurement checkpoints.",
                    "IAM governance will update the review checklist and evidence controls.",
                ][i % 5],
                "target_date": (BASE_DATE + timedelta(days=30 + (i % 120))).isoformat(),
                "owner": ["IAM Lead", "SRE Manager", "CAB Chair", "TPRM Lead", "Security Governance"][i % 5],
                "status": status,
                "ai_assisted": i % 3 == 0,
                "evidence_references": [
                    f"INC-2026-{(i % INCIDENT_COUNT) + 1:04d}",
                    f"USR-{(i % ACCESS_REVIEW_COUNT) + 1:04d}",
                ],
            }
        )
    return records


def generate_all() -> dict[str, list[dict]]:
    return {
        "jira-incidents": generate_incidents(),
        "access-reviews": generate_access_reviews(),
        "change-tickets": generate_change_tickets(),
        "vendor-contracts": generate_vendor_contracts(),
        "audit-findings": generate_findings(),
    }


def main() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    datasets = generate_all()
    for name, records in datasets.items():
        write_dataset(name, records)

    summary = {name: len(records) for name, records in datasets.items()}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
