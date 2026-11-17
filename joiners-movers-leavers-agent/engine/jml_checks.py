"""Deterministic joiner, mover and leaver (JML) tests.

The tests compare HR lifecycle events, entitlement exports and Jira access-request
tickets over one audit period. They do not call a model: the same inputs always
give the same exceptions. Every exception carries the source records it rests on
(file name and line number), so an auditor can trace it back.

The baseline account checks (account enabled after termination, directory profile
differs from HR, accounts without an HR record, stale and duplicate accounts) come
from the Track 2 engine in engine/access_review.py.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from engine.access_review import anonymize_users, detect_exceptions, normalize_key
from engine.sources import Sources

log = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"

ISO_ACCESS = "ISO/IEC 27001:2022 A.5.18 Access rights"
ISO_PRIV = "ISO/IEC 27001:2022 A.8.2 Privileged access rights"
ISO_SOD = "ISO/IEC 27001:2022 A.5.3 Segregation of duties"
SOC_PROV = "SOC 2 CC6.2 Provisioning and removal of access"
SOC_MOD = "SOC 2 CC6.3 Role-based access and changes"
COBIT = "COBIT 2019 DSS05.04 Manage identity and logical access"
COSO = "COSO 2013 Principle 10 Control activities"

TESTS: list[dict] = [
    {"id": "J1", "lifecycle": "joiner", "name": "Access granted without an approved ticket",
     "control": "Every access right granted in the period is backed by an approved request.",
     "control_refs": [ISO_ACCESS, SOC_PROV, COBIT], "population": "grants"},
    {"id": "J2", "lifecycle": "joiner", "name": "More access granted than requested",
     "control": "Granted access matches what the approved request asked for.",
     "control_refs": [ISO_ACCESS, ISO_PRIV, SOC_PROV], "population": "grants"},
    {"id": "J3", "lifecycle": "joiner", "name": "Access provisioned before approval",
     "control": "Access is provisioned only after the request is approved.",
     "control_refs": [ISO_ACCESS, SOC_PROV], "population": "grants"},
    {"id": "J4", "lifecycle": "joiner", "name": "Request approved by the requester",
     "control": "Access requests are approved by someone other than the requester.",
     "control_refs": [ISO_SOD, SOC_PROV, COSO], "population": "tickets"},
    {"id": "J5", "lifecycle": "joiner", "name": "Request does not specify the access",
     "control": "An approved request names the specific roles or groups to be granted.",
     "control_refs": [ISO_ACCESS, SOC_PROV], "population": "tickets"},
    {"id": "M1", "lifecycle": "mover", "name": "Previous role access not removed after transfer",
     "control": "Access that belongs to the previous role is removed within the mover SLA.",
     "control_refs": [ISO_ACCESS, SOC_MOD, COBIT], "population": "movers"},
    {"id": "M2", "lifecycle": "mover", "name": "Segregation of duties conflict",
     "control": "No user holds a combination of rights that the SoD rules forbid.",
     "control_refs": [ISO_SOD, SOC_MOD, COSO], "population": "active_users"},
    {"id": "M3", "lifecycle": "mover", "name": "Directory profile not updated after transfer",
     "control": "The directory reflects the department and role recorded in HR.",
     "control_refs": [ISO_ACCESS, SOC_MOD], "population": "movers", "engine": "track2"},
    {"id": "L1", "lifecycle": "leaver", "name": "Directory account still enabled after termination",
     "control": "Accounts of leavers are disabled on the last working day.",
     "control_refs": [ISO_ACCESS, SOC_PROV, COBIT], "population": "leavers", "engine": "track2"},
    {"id": "L2", "lifecycle": "leaver", "name": "Access removed later than the SLA",
     "control": "Leaver access is removed within the leaver SLA.",
     "control_refs": [ISO_ACCESS, SOC_PROV], "population": "leavers"},
    {"id": "L3", "lifecycle": "leaver", "name": "Login after termination date",
     "control": "No account is used after the holder has left.",
     "control_refs": [ISO_ACCESS, SOC_PROV], "population": "leavers"},
    {"id": "L4", "lifecycle": "leaver", "name": "Application access still assigned after termination",
     "control": "Application roles of leavers are removed, not only the directory account.",
     "control_refs": [ISO_ACCESS, ISO_PRIV, SOC_PROV], "population": "leavers"},
]

BASELINE_TESTS: dict[str, dict] = {
    "orphaned": {"id": "B1", "name": "Account without an HR record", "risk": "High"},
    "departed": {"id": "B2", "name": "Account enabled for a person who left before the period", "risk": "High"},
    "role_mismatch": {"id": "B3", "name": "Directory profile differs from HR", "risk": "Low"},
    "stale": {"id": "B4", "name": "Stale account", "risk": "Low"},
    "duplicate": {"id": "B5", "name": "Duplicate enabled accounts", "risk": "Medium"},
}

TEST_ORDER = [t["id"] for t in TESTS] + [b["id"] for b in BASELINE_TESTS.values()]


# --- helpers -----------------------------------------------------------------


def to_date(val: object) -> Optional[date]:
    """Parse 'YYYY-MM-DD' or an ISO timestamp; return None for empty or unparseable values."""
    s = str(val or "").strip()
    if not s or s.lower() in ("nan", "never"):
        return None
    try:
        return datetime.fromisoformat(s[:19]).date() if "T" in s else datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def split_access(val: object) -> list[str]:
    return [x.strip() for x in str(val or "").replace(",", ";").split(";") if x.strip()]


def is_active(row: dict, on: date) -> bool:
    """An entitlement is active on a date when it was granted on or before it and not yet removed."""
    granted = to_date(row.get("granted_date"))
    removed = to_date(row.get("removed_date"))
    return (granted is None or granted <= on) and (removed is None or removed > on)


def _fmt(d: Optional[date]) -> str:
    return d.isoformat() if d else "not recorded"


# --- main review -------------------------------------------------------------


def run_review(src: Sources) -> dict:
    """Run all JML tests over the loaded sources and return a JSON-serialisable review."""
    pol = src.policy
    start = to_date(pol["audit_period"]["start"])
    end = to_date(pol["audit_period"]["end"])
    as_of = to_date(pol["extraction_date"])
    assert start and end and as_of, "audit_period and extraction_date must be ISO dates"
    leaver_sla = int(pol.get("leaver_revocation_sla_days", 1))
    mover_sla = int(pol.get("mover_revocation_sla_days", 5))
    birthright = set(pol.get("birthright_entitlements", []))
    privileged = set(pol.get("privileged_entitlements", []))
    approved_statuses = {s.lower() for s in pol.get("approved_ticket_statuses", ["Done", "Closed"])}
    role_matrix: dict = pol["role_matrix"]
    catalog: dict = pol.get("entitlement_catalog", {})

    def in_period(d: Optional[date]) -> bool:
        return d is not None and start <= d <= end

    hr_rows = src.hr.rows
    hr = {normalize_key(r["username"]): r for r in hr_rows}
    accounts: dict[str, dict] = {}
    for r in src.accounts.rows:
        accounts.setdefault(normalize_key(r["username"]), r)

    ents: list[dict] = []
    for s in src.systems:
        for r in s["file"].rows:
            r["_system"] = s["name"]
            r["_system_type"] = s["type"]
            r["_source"] = s["label"]
            r["_key"] = normalize_key(r["username"])
            ents.append(r)
    ents_by_user: dict[str, list[dict]] = {}
    for r in ents:
        ents_by_user.setdefault(r["_key"], []).append(r)

    tickets = src.tickets.rows
    request_tickets: dict[tuple, list[dict]] = {}
    removal_tickets: dict[str, list[dict]] = {}
    for t in tickets:
        key = normalize_key(t["subject_username"])
        if "removal" in str(t.get("issue_type", "")).lower():
            removal_tickets.setdefault(key, []).append(t)
        else:
            request_tickets.setdefault((key, str(t["system"]).strip()), []).append(t)

    def approved(t: dict) -> bool:
        return str(t.get("status", "")).strip().lower() in approved_statuses and to_date(t.get("approved_at")) is not None

    joiners = [r for r in hr_rows if in_period(to_date(r["start_date"]))]
    movers = [r for r in hr_rows if in_period(to_date(r["transfer_date"]))]
    leavers = [r for r in hr_rows if in_period(to_date(r["termination_date"]))]
    joiner_keys = {normalize_key(r["username"]) for r in joiners}
    mover_keys = {normalize_key(r["username"]) for r in movers}
    leaver_keys = {normalize_key(r["username"]) for r in leavers}

    def lifecycle_of(key: str) -> str:
        if key in joiner_keys:
            return "joiner"
        if key in mover_keys:
            return "mover"
        if key in leaver_keys:
            return "leaver"
        return "existing" if key in hr else "unknown"

    people = set(hr) | set(accounts) | {r["_key"] for r in ents}
    for t in tickets:
        people |= {normalize_key(t[c]) for c in ("subject_username", "reporter", "approver") if t.get(c)}
    anon_map, reveal_map = anonymize_users(sorted(people))

    def name_of(key: str) -> str:
        rec = hr.get(key)
        if rec and rec.get("full_name"):
            return str(rec["full_name"])
        acc = accounts.get(key)
        return str(acc.get("display_name") or key) if acc else key

    # --- evidence helpers ----------------------------------------------------
    def ev_hr(key: str) -> dict:
        r = hr[key]
        fields = {k: r.get(k, "") for k in ("employee_id", "department", "role", "status", "start_date",
                                            "transfer_date", "previous_role", "termination_date", "manager_username")}
        return {"source": src.hr.label, "ref": r["_ref"], "fields": fields}

    def ev_account(key: str) -> Optional[dict]:
        r = accounts.get(key)
        if not r:
            return None
        fields = {k: r.get(k, "") for k in ("department", "access_role", "enabled", "last_login", "disabled_date")
                  if k in r}
        return {"source": src.accounts.label, "ref": r["_ref"], "fields": fields}

    def ev_ent(r: dict) -> dict:
        return {"source": r["_source"], "ref": r["_ref"],
                "fields": {"system": r["_system"], "entitlement": r["entitlement"], "granted_date": r["granted_date"],
                           "removed_date": r["removed_date"]}}

    def ev_ticket(t: dict) -> dict:
        fields = {k: t.get(k, "") for k in ("ticket_id", "issue_type", "status", "summary", "description", "reporter",
                                            "system", "requested_access", "approver", "created_at", "approved_at",
                                            "resolved_at")}
        return {"source": src.tickets.label, "ref": t["_ref"], "ticket_id": t["ticket_id"], "fields": fields}

    def ent_brief(r: dict) -> dict:
        return {"system": r["_system"], "entitlement": r["entitlement"], "granted_date": r["granted_date"],
                "removed_date": r["removed_date"], "privileged": r["entitlement"] in privileged,
                "description": catalog.get(r["entitlement"], {}).get("description", ""), "ref": r["_ref"]}

    exceptions: list[dict] = []

    def add(test_id: str, key: str, risk: str, summary: str, entitlements: Optional[list[dict]] = None,
            ticket_rows: Optional[list[dict]] = None, extra_evidence: Optional[list[dict]] = None,
            facts: Optional[dict] = None, params: Optional[dict] = None) -> None:
        evidence: list[dict] = []
        if key in hr:
            evidence.append(ev_hr(key))
        acc = ev_account(key)
        if acc:
            evidence.append(acc)
        seen_refs = set()
        for r in entitlements or []:
            if r["_ref"] not in seen_refs:
                evidence.append(ev_ent(r))
                seen_refs.add(r["_ref"])
        for t in ticket_rows or []:
            if t["_ref"] not in seen_refs:
                evidence.append(ev_ticket(t))
                seen_refs.add(t["_ref"])
        evidence.extend(extra_evidence or [])
        exceptions.append({
            "test_id": test_id,
            "risk_rating": risk,
            "username": key,
            "full_name": name_of(key),
            "user_ref": anon_map.get(key, "USER-???"),
            "user_lifecycle": lifecycle_of(key),
            "summary": summary,
            "entitlements": [ent_brief(r) for r in entitlements or []],
            "tickets": sorted({t["ticket_id"] for t in ticket_rows or []}),
            "evidence": evidence,
            "facts": facts or {},
            "params": {"name": name_of(key), "username": key, **(params or {})},
        })

    # --- J1-J5: every grant in the period against Jira -----------------------
    grants = [r for r in ents if in_period(to_date(r["granted_date"])) and r["entitlement"] not in birthright
              and r["_key"] in hr]
    j: dict[tuple, dict] = {}

    def collect(test_id: str, key: str, grant: Optional[dict], ticket: Optional[dict]) -> None:
        bucket = j.setdefault((test_id, key), {"grants": [], "tickets": []})
        if grant is not None and grant not in bucket["grants"]:
            bucket["grants"].append(grant)
        if ticket is not None and ticket not in bucket["tickets"]:
            bucket["tickets"].append(ticket)

    tested_tickets: dict[str, dict] = {}
    for g in grants:
        key, system, ent = g["_key"], g["_system"], g["entitlement"]
        candidates = request_tickets.get((key, system), [])
        ok = sorted([t for t in candidates if approved(t)], key=lambda t: str(t.get("approved_at")))
        if not ok:
            collect("J1", key, g, None)
            for t in candidates:  # unapproved tickets are context, not cover
                collect("J1", key, None, t)
            continue
        for t in ok:
            tested_tickets[t["ticket_id"]] = t
        specified = [t for t in ok if split_access(t.get("requested_access"))]
        covering = [t for t in specified if ent in split_access(t.get("requested_access"))]
        if not specified:
            for t in ok:
                collect("J5", key, g, t)
            continue
        if not covering:
            collect("J2", key, g, None)
            for t in specified:
                collect("J2", key, None, t)
            continue
        t = covering[0]
        granted, appr = to_date(g["granted_date"]), to_date(t.get("approved_at"))
        if granted and appr and granted < appr:
            collect("J3", key, g, t)

    for t in tested_tickets.values():
        rep, appr = normalize_key(t.get("reporter", "")), normalize_key(t.get("approver", ""))
        key = normalize_key(t["subject_username"])
        if rep and rep == appr:
            linked = [g for g in grants if g["_key"] == key and g["_system"] == str(t["system"]).strip()]
            for g in linked:
                collect("J4", key, g, t)
            if not linked:
                collect("J4", key, None, t)

    for (test_id, key), b in j.items():
        gl, tl = b["grants"], b["tickets"]
        names = ", ".join(f"{g['entitlement']} ({g['_system']})" for g in gl)
        priv = any(g["entitlement"] in privileged for g in gl)
        nm = name_of(key)
        if test_id == "J1":
            extra = (" A ticket exists but is not approved: " + ", ".join(t["ticket_id"] for t in tl) + ".") if tl else ""
            add("J1", key, "High", f"{nm} received {names} in the period without an approved Jira ticket.{extra}",
                gl, tl, facts={"grant_count": len(gl)},
                params={"entitlements": names, "unapproved": ", ".join(t["ticket_id"] for t in tl)})
        elif test_id == "J2":
            req = "; ".join(f"{t['ticket_id']} requested {t['requested_access']}" for t in tl)
            add("J2", key, "High" if priv else "Medium",
                f"{nm} received {names}, which no approved ticket requested ({req}).", gl, tl,
                params={"entitlements": names, "requested": req})
        elif test_id == "J3":
            t = tl[0]
            days = (to_date(t["approved_at"]) - min(to_date(g["granted_date"]) for g in gl)).days
            add("J3", key, "Medium", f"{nm} received {names} {days} day(s) before {t['ticket_id']} was approved "
                f"on {_fmt(to_date(t['approved_at']))}.", gl, tl, facts={"days_before_approval": days},
                params={"entitlements": names, "days": days, "ticket": t["ticket_id"],
                        "approved": _fmt(to_date(t["approved_at"]))})
        elif test_id == "J4":
            t = tl[0]
            add("J4", key, "High" if priv else "Medium",
                f"{t['ticket_id']} for {nm} was raised and approved by the same person ({t['approver']}).", gl, tl,
                params={"ticket": t["ticket_id"], "approver": name_of(normalize_key(t["approver"])),
                        "entitlements": names})
        elif test_id == "J5":
            ids = ", ".join(t["ticket_id"] for t in tl)
            add("J5", key, "High" if priv else "Medium",
                f"{ids} for {nm} was approved without naming the roles to grant; {names} was provisioned on it.",
                gl, tl, params={"tickets": ids, "entitlements": names})

    # --- M1: previous-role access retained -----------------------------------
    for m in movers:
        key = normalize_key(m["username"])
        transfer = to_date(m["transfer_date"])
        prev_role, new_role = str(m.get("previous_role", "")), str(m.get("role", ""))
        if prev_role not in role_matrix or new_role not in role_matrix:
            log.warning("Mover %s: role %s or %s not in role matrix, M1 skipped", key, prev_role, new_role)
            continue
        systems = [s["name"] for s in src.systems]
        prev_set = {e for s in systems for e in role_matrix[prev_role].get(s, [])}
        new_set = {e for s in systems for e in role_matrix[new_role].get(s, [])}
        deadline = transfer + timedelta(days=mover_sla)
        retained = []
        for r in ents_by_user.get(key, []):
            granted, removed = to_date(r["granted_date"]), to_date(r["removed_date"])
            if r["entitlement"] in prev_set - new_set - birthright and granted and granted < transfer:
                if removed is None or removed > deadline:
                    retained.append(r)
        if retained:
            names = ", ".join(f"{r['entitlement']} ({r['_system']})" for r in retained)
            priv = any(r["entitlement"] in privileged for r in retained)
            add("M1", key, "High" if priv else "Medium",
                f"{name_of(key)} moved from {prev_role} to {new_role} on {_fmt(transfer)} and still holds {names} "
                f"from the previous role (SLA {mover_sla} days).", retained,
                facts={"previous_role": prev_role, "new_role": new_role},
                params={"previous_role": prev_role, "new_role": new_role, "transfer": _fmt(transfer),
                        "entitlements": names, "sla": mover_sla})

    # --- M2: segregation of duties -------------------------------------------
    active_users = sorted({r["_key"] for r in ents if is_active(r, as_of)})
    for key in active_users:
        active = {r["entitlement"]: r for r in ents_by_user.get(key, []) if is_active(r, as_of)}
        for rule in pol.get("sod_rules", []):
            if all(e in active for e in rule["entitlements"]):
                rows = [active[e] for e in rule["entitlements"]]
                add("M2", key, rule.get("risk", "High"),
                    f"{name_of(key)} holds {' + '.join(rule['entitlements'])} on {_fmt(as_of)} ({rule['rule_id']}: "
                    f"{rule['description']})", rows, facts={"sod_rule": rule["rule_id"]},
                    params={"entitlements": " + ".join(rule["entitlements"]), "date": _fmt(as_of),
                            "rule": rule["rule_id"], "rule_description": rule["description"]})

    # --- Track 2 baseline engine (Bart van den Broek) -------------------------
    track2 = detect_exceptions(src.hr.df, src.accounts.df, stale_days=int(pol.get("stale_days", 90)), as_of=as_of)
    t2_reveal = track2.pop("_reveal_map")
    track2.pop("_anon_map")
    baseline: list[dict] = []
    for f in track2["findings"]:
        key = t2_reveal.get(f["affected_user_ref"], "")
        cat = f["category"]
        acc = accounts.get(key, {})
        hr_rec = hr.get(key, {})
        if cat == "departed" and key in leaver_keys:
            add("L1", key, "High",
                f"{name_of(key)} left on {_fmt(to_date(hr_rec.get('termination_date')))}, but the directory account is "
                f"still enabled on {_fmt(as_of)}.", ticket_rows=removal_tickets.get(key, []),
                facts={"track2_category": cat},
                params={"termination": _fmt(to_date(hr_rec.get("termination_date"))), "date": _fmt(as_of)})
        elif cat == "role_mismatch" and key in mover_keys:
            add("M3", key, "Low",
                f"After the transfer on {_fmt(to_date(hr_rec.get('transfer_date')))}, the directory still shows "
                f"{acc.get('department')} / {acc.get('access_role')} while HR shows {hr_rec.get('department')} / "
                f"{hr_rec.get('role')}.", facts={"track2_category": cat},
                params={"transfer": _fmt(to_date(hr_rec.get("transfer_date"))), "dir_department": acc.get("department"),
                        "dir_role": acc.get("access_role"), "hr_department": hr_rec.get("department"),
                        "hr_role": hr_rec.get("role")})
        else:
            meta = BASELINE_TESTS.get(cat)
            if not meta:
                continue
            baseline.append({"key": key, "category": cat, "meta": meta, "observation": f["observation"]})

    # --- L2-L4: leaver timing --------------------------------------------------
    for lv in leavers:
        key = normalize_key(lv["username"])
        term = to_date(lv["termination_date"])
        deadline = term + timedelta(days=leaver_sla)
        acc = accounts.get(key, {})
        user_ents = ents_by_user.get(key, [])
        rem_tickets = removal_tickets.get(key, [])

        late = [r for r in user_ents if to_date(r["removed_date"]) and to_date(r["removed_date"]) > deadline]
        disabled = to_date(acc.get("disabled_date"))
        account_late = disabled is not None and disabled > deadline
        if late or account_late:
            worst = max([(to_date(r["removed_date"]) - term).days for r in late] +
                        ([(disabled - term).days] if account_late else []))
            items = ", ".join(f"{r['entitlement']} ({r['_system']}) on {r['removed_date']}" for r in late)
            acc_txt = f"directory account disabled on {_fmt(disabled)}" if account_late else ""
            parts = "; ".join(x for x in (acc_txt, items) if x)
            priv = any(r["entitlement"] in privileged for r in late)
            add("L2", key, "High" if priv else "Medium",
                f"{name_of(key)} left on {_fmt(term)}; access was removed up to {worst} days later ({parts}). "
                f"SLA is {leaver_sla} day(s).", late, rem_tickets, facts={"max_days_late": worst},
                params={"termination": _fmt(term), "days": worst, "items": parts, "sla": leaver_sla})

        last_login = to_date(acc.get("last_login"))
        if last_login and last_login > term:
            add("L3", key, "High",
                f"{name_of(key)} left on {_fmt(term)}, but the directory account was used on {_fmt(last_login)} "
                f"({(last_login - term).days} days later).", ticket_rows=rem_tickets,
                facts={"days_after_termination": (last_login - term).days},
                params={"termination": _fmt(term), "login": _fmt(last_login), "days": (last_login - term).days})

        still = [r for r in user_ents if r["_system_type"] == "application" and is_active(r, as_of)]
        if still:
            names = ", ".join(f"{r['entitlement']} ({r['_system']})" for r in still)
            priv = any(r["entitlement"] in privileged for r in still)
            add("L4", key, "High" if priv else "Medium",
                f"{name_of(key)} left on {_fmt(term)}; {names} {'are' if len(still) > 1 else 'is'} still assigned on "
                f"{_fmt(as_of)}.", still, rem_tickets,
                params={"termination": _fmt(term), "entitlements": names, "date": _fmt(as_of)})

    for b in baseline:
        key, meta = b["key"], b["meta"]
        add(meta["id"], key, meta["risk"], f"{meta['name']}: {name_of(key)} ({key}).",
            facts={"track2_category": b["category"]})
        exceptions[-1]["track2_observation"] = b["observation"]

    # --- order, ids, test results ---------------------------------------------
    exceptions.sort(key=lambda e: (TEST_ORDER.index(e["test_id"]), e["username"]))
    for i, e in enumerate(exceptions, start=1):
        e["id"] = f"EX-{i:02d}"

    population = {
        "grants": len(grants),
        "tickets": len(tested_tickets),
        "movers": len(movers),
        "leavers": len(leavers),
        "active_users": len(active_users),
    }
    tests_out = []
    for t in TESTS:
        hits = [e for e in exceptions if e["test_id"] == t["id"]]
        tests_out.append({**t, "tested": population[t["population"]], "exceptions": len(hits),
                          "exception_ids": [e["id"] for e in hits]})
    for cat, meta in BASELINE_TESTS.items():
        hits = [e for e in exceptions if e["test_id"] == meta["id"]]
        tests_out.append({"id": meta["id"], "lifecycle": "baseline", "name": meta["name"], "engine": "track2",
                          "control": "Directory accounts match HR and are in use.",
                          "control_refs": [ISO_ACCESS, SOC_PROV], "population": "accounts",
                          "tested": len(src.accounts.df), "exceptions": len(hits),
                          "exception_ids": [e["id"] for e in hits]})

    by_lifecycle = {lc: [e["id"] for e in exceptions if _lc(e["test_id"]) == lc]
                    for lc in ("joiner", "mover", "leaver", "baseline")}

    return {
        "engine_version": ENGINE_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "review_name": src.name,
        "organisation": pol.get("organisation", ""),
        "audit_period": {"start": start.isoformat(), "end": end.isoformat()},
        "extraction_date": as_of.isoformat(),
        "policy": {"leaver_revocation_sla_days": leaver_sla, "mover_revocation_sla_days": mover_sla,
                   "stale_days": int(pol.get("stale_days", 90)), "sod_rules": pol.get("sod_rules", []),
                   "privileged_entitlements": sorted(privileged)},
        "sources": src.summaries(),
        "fingerprint": src.fingerprint(),
        "population": {
            "people": len(hr_rows),
            "accounts": len(src.accounts.df),
            "entitlements": len(ents),
            "tickets_total": len(tickets),
            "joiners": [r["username"] for r in joiners],
            "movers": [r["username"] for r in movers],
            "leavers": [r["username"] for r in leavers],
            **{f"tested_{k}": v for k, v in population.items()},
        },
        "tests": tests_out,
        "exceptions": exceptions,
        "by_lifecycle": by_lifecycle,
        "timelines": {e["username"]: person_timeline(e["username"], hr, accounts, ents_by_user, tickets)
                      for e in exceptions},
        "_reveal_map": reveal_map,
        "_anon_map": anon_map,
        "_people": {k: name_of(k) for k in people},
    }


def _lc(test_id: str) -> str:
    for t in TESTS:
        if t["id"] == test_id:
            return t["lifecycle"]
    return "baseline"


def person_timeline(key: str, hr: dict, accounts: dict, ents_by_user: dict, tickets: list[dict]) -> list[dict]:
    """All dated events for one person, oldest first, each with its source reference."""
    events: list[dict] = []
    r = hr.get(key)
    if r:
        for col, kind in (("start_date", "hr_start"), ("transfer_date", "hr_transfer"),
                          ("termination_date", "hr_termination")):
            d = to_date(r.get(col))
            if d:
                detail = r.get("role", "")
                if kind == "hr_start" and r.get("previous_role") and r.get("transfer_date"):
                    detail = r.get("previous_role", "")
                if kind == "hr_transfer":
                    detail = f"{r.get('previous_role', '')} to {r.get('role', '')}"
                events.append({"date": d.isoformat(), "kind": kind, "detail": detail, "ref": r["_ref"]})
    for t in tickets:
        if normalize_key(t["subject_username"]) != key:
            continue
        for col, kind in (("created_at", "ticket_created"), ("approved_at", "ticket_approved"),
                          ("resolved_at", "ticket_resolved")):
            d = to_date(t.get(col))
            if d:
                detail = t.get("requested_access") or t.get("issue_type", "")
                if kind == "ticket_approved":
                    detail = f"approved by {t.get('approver', '')}"
                events.append({"date": d.isoformat(), "kind": kind, "detail": f"{t['ticket_id']} {detail}".strip(),
                               "ticket_id": t["ticket_id"], "ref": t["_ref"]})
    for e in ents_by_user.get(key, []):
        g, rm = to_date(e.get("granted_date")), to_date(e.get("removed_date"))
        if g:
            events.append({"date": g.isoformat(), "kind": "access_granted",
                           "detail": f"{e['entitlement']} ({e['_system']})", "ref": e["_ref"]})
        if rm:
            events.append({"date": rm.isoformat(), "kind": "access_removed",
                           "detail": f"{e['entitlement']} ({e['_system']})", "ref": e["_ref"]})
    a = accounts.get(key)
    if a:
        d = to_date(a.get("disabled_date"))
        if d:
            events.append({"date": d.isoformat(), "kind": "account_disabled", "detail": "", "ref": a["_ref"]})
        d = to_date(a.get("last_login"))
        if d:
            events.append({"date": d.isoformat(), "kind": "last_login", "detail": "", "ref": a["_ref"]})
    order = {"hr_start": 0, "hr_transfer": 0, "ticket_created": 1, "ticket_approved": 2, "access_granted": 3,
             "ticket_resolved": 4, "access_removed": 5, "account_disabled": 5, "hr_termination": 6, "last_login": 7}
    events.sort(key=lambda ev: (ev["date"], order.get(ev["kind"], 9)))
    return events


def public_review(review: dict) -> dict:
    """The review without the private re-identification maps."""
    return {k: v for k, v in review.items() if not k.startswith("_")}
