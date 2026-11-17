"""Generate the synthetic sample data set for the joiners-movers-leavers agent.

Everything here is fictional: the organisation, the people and the tickets.
The data is written out explicitly (no randomness), so every run produces the
same files and the tests can assert exact results.

Planted exceptions (audit period 2026-07-01 to 2026-09-30, extraction 2026-10-15):

Joiners
  J1  daan.smit     access provisioned without any approved ticket
  J2  sara.koch     received AD_IT_ADMINS, ticket only asked for AD_IT_SUPPORT
  J3  emma.jansen   ERP role provisioned 9 days before the ticket was approved
  J4  noah.visser   payroll request approved by the person who raised it
  J5  mila.peters   ticket says "same access as a colleague" and names no role
Movers
  M1  lucas.mulder  kept ERP_AP_CLERK after moving to Treasury
  M2  lucas.mulder  now holds ERP_AP_CLERK + ERP_PAYMENT_RELEASE (SoD)
  M1  julia.dekker  kept ERP_VENDOR_MASTER after moving to Finance
  M3  julia.dekker  directory profile still shows the old department and role
Leavers
  L1  ruben.hendriks  directory account still enabled after termination
  L3  ruben.hendriks  logged in 6 days after termination
  L2  anna.vos        directory account disabled 21 days after termination
  L4  kevin.meijer    ERP roles still assigned after termination
Baseline (Track 2 engine)
  orphaned  ext.consultant01  account without an HR record
  stale     yvonne.smits      no login for more than 90 days

Clean cases are included on purpose (lotte.willems, omar.haddad, sem.bos,
chris.vermeulen) so the agent visibly passes correct records too.

Usage:
    python3 tools/generate_sample_data.py
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

OUT_DIR = Path(__file__).parents[1] / "sample_data"

ORGANISATION = "Harbourline Services (fictional)"
PERIOD_START = "2026-07-01"
PERIOD_END = "2026-09-30"
EXTRACTION_DATE = "2026-10-15"

# Role model: role -> department and standard entitlements per system.
ROLES: dict[str, dict] = {
    "Managing Director": {"department": "Management", "AD": ["AD_ALL_STAFF", "AD_BOARD_SHARE"], "ERP": ["ERP_REPORTING"]},
    "Financial Controller": {"department": "Finance", "AD": ["AD_ALL_STAFF", "AD_FINANCE_SHARE"], "ERP": ["ERP_GL_ACCOUNTANT", "ERP_REPORTING"]},
    "Accounts Payable Clerk": {"department": "Finance", "AD": ["AD_ALL_STAFF", "AD_FINANCE_SHARE"], "ERP": ["ERP_AP_CLERK"]},
    "Treasury Officer": {"department": "Finance", "AD": ["AD_ALL_STAFF", "AD_FINANCE_SHARE"], "ERP": ["ERP_PAYMENT_RELEASE"]},
    "Procurement Officer": {"department": "Procurement", "AD": ["AD_ALL_STAFF", "AD_PROCUREMENT_SHARE"], "ERP": ["ERP_VENDOR_MASTER", "ERP_PO_REQUESTER"]},
    "HR Advisor": {"department": "HR", "AD": ["AD_ALL_STAFF", "AD_HR_SHARE"], "ERP": ["ERP_HR_PAYROLL"]},
    "Sales Representative": {"department": "Sales", "AD": ["AD_ALL_STAFF", "AD_SALES_CRM"], "ERP": []},
    "IT Support Engineer": {"department": "IT", "AD": ["AD_ALL_STAFF", "AD_IT_SUPPORT"], "ERP": []},
    "System Administrator": {"department": "IT", "AD": ["AD_ALL_STAFF", "AD_IT_ADMINS"], "ERP": []},
    "Operations Coordinator": {"department": "Operations", "AD": ["AD_ALL_STAFF", "AD_OPS_SHARE"], "ERP": ["ERP_PO_REQUESTER"]},
}

CATALOG: dict[str, dict] = {
    "AD_ALL_STAFF": {"system": "AD", "description": "Default staff group (birthright)"},
    "AD_BOARD_SHARE": {"system": "AD", "description": "Board documents share"},
    "AD_FINANCE_SHARE": {"system": "AD", "description": "Finance department share"},
    "AD_PROCUREMENT_SHARE": {"system": "AD", "description": "Procurement department share"},
    "AD_HR_SHARE": {"system": "AD", "description": "HR department share (personnel files)"},
    "AD_SALES_CRM": {"system": "AD", "description": "CRM access group"},
    "AD_IT_SUPPORT": {"system": "AD", "description": "Service desk tooling"},
    "AD_IT_ADMINS": {"system": "AD", "description": "Domain administrators"},
    "AD_OPS_SHARE": {"system": "AD", "description": "Operations share"},
    "ERP_REPORTING": {"system": "ERP", "description": "Read-only financial reporting"},
    "ERP_GL_ACCOUNTANT": {"system": "ERP", "description": "Post and approve journal entries"},
    "ERP_AP_CLERK": {"system": "ERP", "description": "Enter and change supplier invoices"},
    "ERP_PAYMENT_RELEASE": {"system": "ERP", "description": "Release payment runs to the bank"},
    "ERP_VENDOR_MASTER": {"system": "ERP", "description": "Create and change supplier master data (incl. bank accounts)"},
    "ERP_PO_REQUESTER": {"system": "ERP", "description": "Create purchase requisitions"},
    "ERP_HR_PAYROLL": {"system": "ERP", "description": "Maintain payroll and salary data"},
}

POLICY: dict = {
    "organisation": ORGANISATION,
    "audit_period": {"start": PERIOD_START, "end": PERIOD_END},
    "extraction_date": EXTRACTION_DATE,
    "leaver_revocation_sla_days": 1,
    "mover_revocation_sla_days": 5,
    "stale_days": 90,
    "approved_ticket_statuses": ["Done", "Closed"],
    "birthright_entitlements": ["AD_ALL_STAFF"],
    "privileged_entitlements": [
        "AD_IT_ADMINS",
        "ERP_PAYMENT_RELEASE",
        "ERP_VENDOR_MASTER",
        "ERP_HR_PAYROLL",
        "ERP_GL_ACCOUNTANT",
    ],
    "sod_rules": [
        {
            "rule_id": "SOD-01",
            "entitlements": ["ERP_AP_CLERK", "ERP_PAYMENT_RELEASE"],
            "risk": "High",
            "description": "One person can enter a supplier invoice and release its payment.",
        },
        {
            "rule_id": "SOD-02",
            "entitlements": ["ERP_VENDOR_MASTER", "ERP_PAYMENT_RELEASE"],
            "risk": "High",
            "description": "One person can change supplier bank details and release payments.",
        },
    ],
    "role_matrix": {role: {"department": r["department"], "AD": r["AD"], "ERP": r["ERP"]} for role, r in ROLES.items()},
    "entitlement_catalog": CATALOG,
}

# --- People ------------------------------------------------------------------
# Each person: username, full name, role, start, plus optional lifecycle events.

DEPARTMENT_HEADS = {
    "Management": "olaf.brandt",
    "Finance": "irene.kuipers",
    "Procurement": "marco.rossi",
    "HR": "helen.dijkstra",
    "Sales": "nina.claes",
    "IT": "tim.hoekstra",
    "Operations": "wout.peeters",
}

# Existing staff (started before the audit period, unchanged in the period).
EXISTING: list[tuple[str, str, str, str]] = [
    ("olaf.brandt", "Olaf Brandt", "Managing Director", "2018-02-01"),
    ("irene.kuipers", "Irene Kuipers", "Financial Controller", "2017-09-04"),
    ("pieter.vandam", "Pieter van Dam", "Accounts Payable Clerk", "2021-04-12"),
    ("fatima.elamrani", "Fatima El Amrani", "Accounts Payable Clerk", "2022-10-03"),
    ("bas.groen", "Bas Groen", "Treasury Officer", "2020-06-15"),
    ("marco.rossi", "Marco Rossi", "Procurement Officer", "2019-01-07"),
    ("lieke.janssens", "Lieke Janssens", "Procurement Officer", "2023-05-22"),
    ("helen.dijkstra", "Helen Dijkstra", "HR Advisor", "2016-11-01"),
    ("priya.raman", "Priya Raman", "HR Advisor", "2024-02-05"),
    ("nina.claes", "Nina Claes", "Sales Representative", "2018-08-20"),
    ("jeroen.wolters", "Jeroen Wolters", "Sales Representative", "2022-03-14"),
    ("sofie.lambrecht", "Sofie Lambrecht", "Sales Representative", "2023-09-11"),
    ("tim.hoekstra", "Tim Hoekstra", "System Administrator", "2017-03-13"),
    ("ahmed.benali", "Ahmed Benali", "System Administrator", "2021-01-18"),
    ("joris.maes", "Joris Maes", "IT Support Engineer", "2022-07-04"),
    ("wout.peeters", "Wout Peeters", "Operations Coordinator", "2019-10-21"),
    ("eva.schouten", "Eva Schouten", "Operations Coordinator", "2021-06-07"),
    ("yvonne.smits", "Yvonne Smits", "Operations Coordinator", "2020-04-01"),
    ("max.verhoeven", "Max Verhoeven", "Operations Coordinator", "2024-11-04"),
    ("hanna.berg", "Hanna Berg", "Financial Controller", "2023-01-09"),
]

# Joiners in the period: username, name, role, start date.
JOINERS: list[tuple[str, str, str, str]] = [
    ("sara.koch", "Sara Koch", "IT Support Engineer", "2026-07-06"),
    ("lotte.willems", "Lotte Willems", "Sales Representative", "2026-07-13"),
    ("daan.smit", "Daan Smit", "Procurement Officer", "2026-07-20"),
    ("emma.jansen", "Emma Jansen", "Accounts Payable Clerk", "2026-08-03"),
    ("noah.visser", "Noah Visser", "HR Advisor", "2026-08-17"),
    ("mila.peters", "Mila Peters", "Treasury Officer", "2026-09-07"),
    ("omar.haddad", "Omar Haddad", "Operations Coordinator", "2026-09-14"),
]

# Movers in the period: username, name, old role, original start, new role, transfer date.
MOVERS: list[tuple[str, str, str, str, str, str]] = [
    ("lucas.mulder", "Lucas Mulder", "Accounts Payable Clerk", "2023-03-01", "Treasury Officer", "2026-07-15"),
    ("julia.dekker", "Julia Dekker", "Procurement Officer", "2022-05-09", "Financial Controller", "2026-08-01"),
    ("sem.bos", "Sem Bos", "Sales Representative", "2024-01-08", "HR Advisor", "2026-09-01"),
]

# Leavers in the period: username, name, role, start, termination date.
LEAVERS: list[tuple[str, str, str, str, str]] = [
    ("anna.vos", "Anna Vos", "HR Advisor", "2020-02-03", "2026-07-31"),
    ("ruben.hendriks", "Ruben Hendriks", "Sales Representative", "2021-05-17", "2026-08-28"),
    ("kevin.meijer", "Kevin Meijer", "Financial Controller", "2019-04-01", "2026-09-11"),
    ("chris.vermeulen", "Chris Vermeulen", "Operations Coordinator", "2022-01-10", "2026-09-25"),
]


def head_of(department: str, username: str) -> str:
    """Return the line manager: the department head, or the MD for heads."""
    head = DEPARTMENT_HEADS[department]
    return "olaf.brandt" if head == username else head


def write_csv(name: str, fieldnames: list[str], rows: list[dict]) -> None:
    path = OUT_DIR / name
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %s (%d rows)", path.relative_to(OUT_DIR.parent), len(rows))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    hr: list[dict] = []
    ad_accounts: list[dict] = []
    ad_groups: list[dict] = []
    erp_roles: list[dict] = []
    tickets: list[dict] = []
    next_ticket = [1101]

    def grant(username: str, system: str, entitlement: str, granted: str, removed: str = "") -> None:
        row = {"username": username, "entitlement": entitlement, "granted_date": granted, "removed_date": removed}
        (ad_groups if system == "AD" else erp_roles).append(row)

    def ticket(
        subject: str,
        system: str,
        requested: list[str],
        reporter: str,
        approver: str,
        created: str,
        approved: str,
        resolved: str,
        summary: str,
        description: str,
        issue_type: str = "Access Request",
        status: str = "Done",
    ) -> str:
        tid = f"IAM-{next_ticket[0]}"
        next_ticket[0] += 1
        tickets.append(
            {
                "ticket_id": tid,
                "issue_type": issue_type,
                "status": status,
                "summary": summary,
                "description": description,
                "reporter": reporter,
                "subject_username": subject,
                "system": system,
                "requested_access": ";".join(requested),
                "approver": approver,
                "created_at": f"{created}T09:12:00",
                "approved_at": f"{approved}T14:05:00" if approved else "",
                "resolved_at": f"{resolved}T16:40:00" if resolved else "",
            }
        )
        return tid

    def hr_row(username: str, name: str, role: str, start: str, status: str = "Active", termination: str = "",
               transfer: str = "", prev_role: str = "") -> None:
        dept = ROLES[role]["department"]
        hr.append(
            {
                "employee_id": f"E{len(hr) + 1:03d}",
                "username": username,
                "full_name": name,
                "department": dept,
                "role": role,
                "manager_username": head_of(dept, username),
                "status": status,
                "start_date": start,
                "transfer_date": transfer,
                "previous_department": ROLES[prev_role]["department"] if prev_role else "",
                "previous_role": prev_role,
                "termination_date": termination,
            }
        )

    def ad_account(username: str, name: str, role: str, enabled: bool, last_login: str, disabled: str = "",
                   dept_override: Optional[str] = None) -> None:
        ad_accounts.append(
            {
                "username": username,
                "display_name": name,
                "department": dept_override or ROLES[role]["department"],
                "access_role": role,
                "enabled": "true" if enabled else "false",
                "last_login": last_login,
                "disabled_date": disabled,
            }
        )

    def standard_access(username: str, role: str, granted: str, removed: str = "",
                        skip: Optional[list[str]] = None) -> None:
        for system in ("AD", "ERP"):
            for ent in ROLES[role][system]:
                if skip and ent in skip:
                    continue
                grant(username, system, ent, granted, removed)

    # --- existing staff -------------------------------------------------------
    for i, (u, n, role, start) in enumerate(EXISTING):
        hr_row(u, n, role, start)
        last_login = "2026-05-20" if u == "yvonne.smits" else f"2026-10-{8 + i % 7:02d}"
        ad_account(u, n, role, True, last_login)
        standard_access(u, role, start)

    # --- joiners --------------------------------------------------------------
    for u, n, role, start in JOINERS:
        hr_row(u, n, role, start)
        ad_account(u, n, role, True, "2026-10-14")
        dept = ROLES[role]["department"]
        mgr = head_of(dept, u)
        ad_req = [e for e in ROLES[role]["AD"] if e not in POLICY["birthright_entitlements"]]
        erp_req = ROLES[role]["ERP"]

        if u == "daan.smit":
            # J1: everything provisioned, no ticket raised at all.
            standard_access(u, role, start)
            continue

        if u == "sara.koch":
            # J2: ticket asks for service desk tooling, admin group granted as well.
            ticket(u, "AD", ad_req, "helen.dijkstra", mgr, "2026-06-29", "2026-07-02", "2026-07-06",
                   f"New starter {n}: AD access", f"{n} joins the service desk on 6 July. Please set up standard IT support access.")
            standard_access(u, role, start)
            grant(u, "AD", "AD_IT_ADMINS", start)
            continue

        if u == "emma.jansen":
            # J3: ERP role provisioned on day one, ticket approved nine days later.
            ticket(u, "AD", ad_req, "helen.dijkstra", mgr, "2026-07-27", "2026-07-28", "2026-08-03",
                   f"New starter {n}: AD access", f"{n} starts in Accounts Payable on 3 August.")
            ticket(u, "ERP", erp_req, "helen.dijkstra", mgr, "2026-07-27", "2026-08-12", "2026-08-12",
                   f"New starter {n}: ERP access", f"{n} needs the AP clerk role to process supplier invoices.")
            standard_access(u, role, start)
            continue

        if u == "noah.visser":
            # J4: the payroll request is raised and approved by the same person.
            ticket(u, "AD", ad_req, "priya.raman", mgr, "2026-08-10", "2026-08-11", "2026-08-17",
                   f"New starter {n}: AD access", f"{n} joins HR on 17 August.")
            ticket(u, "ERP", erp_req, "helen.dijkstra", "helen.dijkstra", "2026-08-10", "2026-08-10", "2026-08-17",
                   f"New starter {n}: payroll access", f"Please grant {n} payroll maintenance in the ERP.")
            standard_access(u, role, start)
            continue

        if u == "mila.peters":
            # J5: the ERP ticket names no role, only a colleague to copy.
            ticket(u, "AD", ad_req, "helen.dijkstra", mgr, "2026-08-31", "2026-09-01", "2026-09-07",
                   f"New starter {n}: AD access", f"{n} joins Treasury on 7 September.")
            ticket(u, "ERP", [], "helen.dijkstra", mgr, "2026-08-31", "2026-09-02", "2026-09-07",
                   f"New starter {n}: ERP access",
                   f"{n} starts in Treasury on 7 September. Please give her the same ERP access as Bas Groen so she can cover the payment runs.")
            standard_access(u, role, start)
            continue

        # Clean joiners: proper tickets, approved before provisioning.
        ticket(u, "AD", ad_req, "helen.dijkstra", mgr, "2026-07-01" if start < "2026-08-01" else "2026-09-01",
               "2026-07-03" if start < "2026-08-01" else "2026-09-04", start,
               f"New starter {n}: AD access", f"{n} starts as {role} on {start}.")
        if erp_req:
            ticket(u, "ERP", erp_req, "helen.dijkstra", mgr, "2026-09-01", "2026-09-04", start,
                   f"New starter {n}: ERP access", f"{n} needs the standard {role} ERP role.")
        standard_access(u, role, start)

    # --- movers ---------------------------------------------------------------
    for u, n, old_role, start, new_role, transfer in MOVERS:
        hr_row(u, n, new_role, start, transfer=transfer, prev_role=old_role)
        new_dept = ROLES[new_role]["department"]
        mgr = head_of(new_dept, u)
        old_set = {e for s in ("AD", "ERP") for e in ROLES[old_role][s]}
        new_set = {e for s in ("AD", "ERP") for e in ROLES[new_role][s]}

        if u == "lucas.mulder":
            ad_account(u, n, new_role, True, "2026-10-13")
            ticket(u, "ERP", ["ERP_PAYMENT_RELEASE"], "priya.raman", mgr, "2026-07-08", "2026-07-13", "2026-07-15",
                   f"Internal transfer {n}: Treasury access",
                   f"{n} moves from Accounts Payable to Treasury on 15 July. Please add payment release.")
            # Old AP clerk role is never removed (M1) and creates SoD-01 (M2).
            standard_access(u, old_role, start)
            grant(u, "ERP", "ERP_PAYMENT_RELEASE", transfer)
            continue

        if u == "julia.dekker":
            # Directory profile not updated after the move (M3).
            ad_account(u, n, old_role, True, "2026-10-14", dept_override=ROLES[old_role]["department"])
            ticket(u, "AD", ["AD_FINANCE_SHARE"], "priya.raman", mgr, "2026-07-24", "2026-07-27", "2026-08-03",
                   f"Internal transfer {n}: Finance share", f"{n} joins Finance as controller on 1 August.")
            ticket(u, "ERP", ["ERP_GL_ACCOUNTANT", "ERP_REPORTING"], "priya.raman", "olaf.brandt", "2026-07-24", "2026-07-28", "2026-08-03",
                   f"Internal transfer {n}: controller ERP roles", f"Please assign the standard controller roles to {n}.")
            for system in ("AD", "ERP"):
                for ent in ROLES[old_role][system]:
                    if ent == "ERP_VENDOR_MASTER":
                        grant(u, system, ent, start)  # retained (M1)
                    elif ent in new_set:
                        grant(u, system, ent, start)
                    else:
                        grant(u, system, ent, start, "2026-08-04")
            for system in ("AD", "ERP"):
                for ent in ROLES[new_role][system]:
                    if ent not in old_set:
                        grant(u, system, ent, "2026-08-03")
            continue

        # Clean mover (sem.bos): tickets in order, old access removed next day.
        ad_account(u, n, new_role, True, "2026-10-12")
        ticket(u, "AD", ["AD_HR_SHARE"], "priya.raman", mgr, "2026-08-24", "2026-08-26", "2026-09-01",
               f"Internal transfer {n}: HR share", f"{n} moves from Sales to HR on 1 September.")
        ticket(u, "ERP", ["ERP_HR_PAYROLL"], "priya.raman", "olaf.brandt", "2026-08-24", "2026-08-27", "2026-09-01",
               f"Internal transfer {n}: payroll access", f"{n} needs payroll maintenance as HR advisor.")
        for system in ("AD", "ERP"):
            for ent in ROLES[old_role][system]:
                grant(u, system, ent, start, "" if ent in new_set else "2026-09-02")
            for ent in ROLES[new_role][system]:
                if ent not in old_set:
                    grant(u, system, ent, transfer)

    # --- leavers --------------------------------------------------------------
    for u, n, role, start, term in LEAVERS:
        hr_row(u, n, role, start, status="Terminated", termination=term)
        dept = ROLES[role]["department"]
        mgr = head_of(dept, u)
        ticket(u, "AD", [], "priya.raman", mgr, term, term, "", f"Leaver {n}: remove all access",
               f"{n} leaves on {term}. Please disable the account and remove all access.",
               issue_type="Access Removal", status="Done" if u != "ruben.hendriks" else "Open")

        if u == "ruben.hendriks":
            # L1 + L3: account left enabled, login after the last working day.
            ad_account(u, n, role, True, "2026-09-03")
            standard_access(u, role, start)
        elif u == "anna.vos":
            # L2: directory account disabled 21 days late, ERP removed on time.
            ad_account(u, n, role, False, "2026-07-31", disabled="2026-08-21")
            for ent in ROLES[role]["AD"]:
                grant(u, "AD", ent, start, "2026-08-21")
            for ent in ROLES[role]["ERP"]:
                grant(u, "ERP", ent, start, "2026-08-01")
        elif u == "kevin.meijer":
            # L4: directory account disabled on time, ERP roles never removed.
            ad_account(u, n, role, False, "2026-09-11", disabled="2026-09-11")
            for ent in ROLES[role]["AD"]:
                grant(u, "AD", ent, start, "2026-09-11")
            for ent in ROLES[role]["ERP"]:
                grant(u, "ERP", ent, start)
        else:
            ad_account(u, n, role, False, term, disabled=term)
            standard_access(u, role, start, removed=term)

    # --- accounts outside HR -------------------------------------------------
    ad_account("ext.consultant01", "External Consultant", "Procurement Officer", True, "2026-10-02",
               dept_override="Procurement")
    grant("ext.consultant01", "AD", "AD_ALL_STAFF", "2025-11-03")
    grant("ext.consultant01", "AD", "AD_PROCUREMENT_SHARE", "2025-11-03")
    ad_accounts.append({"username": "svc_backup", "display_name": "Backup service", "department": "IT",
                        "access_role": "Service account", "enabled": "true", "last_login": "2026-10-15",
                        "disabled_date": ""})

    write_csv("hr_employees.csv", list(hr[0].keys()), hr)
    write_csv("ad_accounts.csv", list(ad_accounts[0].keys()), ad_accounts)
    write_csv("ad_group_memberships.csv", ["username", "entitlement", "granted_date", "removed_date"], ad_groups)
    write_csv("erp_user_roles.csv", ["username", "entitlement", "granted_date", "removed_date"], erp_roles)
    write_csv("jira_access_requests.csv", list(tickets[0].keys()), tickets)
    policy_path = OUT_DIR / "access_policy.json"
    policy_path.write_text(json.dumps(POLICY, indent=2) + "\n", encoding="utf-8")
    log.info("Wrote %s", policy_path.relative_to(OUT_DIR.parent))


if __name__ == "__main__":
    main()
