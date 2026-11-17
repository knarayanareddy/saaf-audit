"""SAAF Track 2 — IAM Access Review Agent (Streamlit App)

Cross-references an Active Directory export against an HR active-employee list
to identify access control exceptions, then uses Claude to generate structured
audit findings conforming to finding-schema.json.

Usage:
    streamlit run tools/scripts/access_review_app.py

Requires:
    pip install streamlit anthropic
    ANTHROPIC_API_KEY environment variable (or enter in sidebar)
"""

import csv
import io
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import streamlit as st

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parents[2]
TEST_DATA_DIR = Path(__file__).parent / "test_data"
PROMPT_PATH = REPO_ROOT / "prompts" / "audit-use-cases" / "access-review.md"

PRIVILEGED_ROLES = {"admin", "superuser", "root", "domain admin", "global admin"}


# --- Data loading ---


def parse_csv(content: str) -> list[dict]:
    """Parse CSV string into list of dicts."""
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def load_sample_data() -> tuple[list[dict], list[dict]]:
    """Load bundled synthetic test data."""
    ad_path = TEST_DATA_DIR / "ad_export.csv"
    hr_path = TEST_DATA_DIR / "hr_active_employees.csv"
    ad_data = parse_csv(ad_path.read_text(encoding="utf-8"))
    hr_data = parse_csv(hr_path.read_text(encoding="utf-8"))
    return ad_data, hr_data


# --- Analysis logic ---


def analyse_access(ad_users: list[dict], hr_users: list[dict]) -> dict:
    """Cross-reference AD and HR data to find exceptions."""
    hr_lookup = {u["username"]: u for u in hr_users}
    today = date.today()

    orphaned = []
    role_mismatches = []
    stale_accounts = []
    privileged_accounts = []
    clean_accounts = []

    for user in ad_users:
        username = user["username"]
        hr_record = hr_lookup.get(username)
        is_privileged = user.get("role", "").strip().lower() in PRIVILEGED_ROLES

        if is_privileged:
            privileged_accounts.append({**user, "hr_record": hr_record})

        # Orphaned: in AD but not in HR
        if hr_record is None:
            orphaned.append(user)
            continue

        # Role mismatch: department differs between AD and HR
        ad_dept = user.get("department", "").strip()
        hr_dept = hr_record.get("department", "").strip()
        if ad_dept and hr_dept and ad_dept.lower() != hr_dept.lower():
            role_mismatches.append({
                **user,
                "hr_department": hr_dept,
                "ad_department": ad_dept,
            })

        # Stale: no login in >90 days
        last_login_str = user.get("last_login", "").strip()
        if last_login_str and last_login_str.lower() != "never":
            try:
                last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date()
                days_since = (today - last_login).days
                if days_since > 90:
                    stale_accounts.append({**user, "days_since_login": days_since})
            except ValueError:
                pass
        elif last_login_str.lower() == "never":
            stale_accounts.append({**user, "days_since_login": -1})

        # Clean if none of the above triggered (and not just privileged)
        if hr_record and not is_privileged:
            ad_dept = user.get("department", "").strip()
            hr_dept = hr_record.get("department", "").strip()
            dept_match = not ad_dept or not hr_dept or ad_dept.lower() == hr_dept.lower()
            not_stale = True
            last_login_str = user.get("last_login", "").strip()
            if last_login_str and last_login_str.lower() != "never":
                try:
                    last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date()
                    not_stale = (today - last_login).days <= 90
                except ValueError:
                    pass
            elif last_login_str.lower() == "never":
                not_stale = False
            if dept_match and not_stale:
                clean_accounts.append(user)

    return {
        "total_accounts": len(ad_users),
        "total_hr_records": len(hr_users),
        "orphaned": orphaned,
        "role_mismatches": role_mismatches,
        "stale_accounts": stale_accounts,
        "privileged_accounts": privileged_accounts,
        "clean_accounts": clean_accounts,
    }


# --- Claude API ---


def build_exception_summary(results: dict) -> str:
    """Build a text summary of all exceptions for the Claude prompt."""
    lines = []

    if results["orphaned"]:
        lines.append("## Orphaned Accounts (in AD, no HR record)")
        for u in results["orphaned"]:
            lines.append(f"- {u['username']} | Dept: {u.get('department','')} | Role: {u.get('role','')} | Last login: {u.get('last_login','')}")

    if results["role_mismatches"]:
        lines.append("\n## Role/Department Mismatches")
        for u in results["role_mismatches"]:
            lines.append(f"- {u['username']} | AD dept: {u['ad_department']} | HR dept: {u['hr_department']} | Role: {u.get('role','')}")

    if results["stale_accounts"]:
        lines.append("\n## Stale Accounts (no login >90 days)")
        for u in results["stale_accounts"]:
            days = u["days_since_login"]
            days_str = "Never logged in" if days == -1 else f"{days} days since last login"
            lines.append(f"- {u['username']} | Dept: {u.get('department','')} | {days_str}")

    if results["privileged_accounts"]:
        lines.append("\n## Privileged Accounts")
        for u in results["privileged_accounts"]:
            lines.append(f"- {u['username']} | Role: {u.get('role','')} | Last login: {u.get('last_login','')}")

    return "\n".join(lines)


def generate_findings_with_claude(results: dict, api_key: str) -> list[dict]:
    """Call Claude to generate structured findings from the exceptions."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are an AI audit assistant specialised in user access management.
You will receive a list of access control exceptions identified by comparing an Active Directory
export against an HR active-employee list.

For each exception, produce a structured audit finding in JSON format.

Return a JSON array where each finding has these fields:
- id: "F-01", "F-02", etc.
- title: Short descriptive title (max 100 chars)
- risk_rating: "High" for orphaned accounts, "Medium" for role mismatches and privileged accounts without justification, "Low" for stale accounts
- control_objective: The ISO 27001 / SOC 2 control this relates to
- observation: Factual description of what was found (2-3 sentences)
- recommendation: Recommended corrective action (1-2 sentences)
- evidence_references: Array of evidence items (e.g. "AD export row: username")

Group related exceptions into single findings where appropriate (e.g. all orphaned accounts = one finding).
Return ONLY valid JSON array, no markdown fences or extra text."""

    exception_text = build_exception_summary(results)

    user_prompt = f"""Analyse these access control exceptions and produce audit findings:

{exception_text}

Context:
- Total AD accounts reviewed: {results['total_accounts']}
- Total HR records: {results['total_hr_records']}
- Review date: {date.today().isoformat()}

Produce findings in JSON array format. Group related exceptions into logical findings."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    findings = json.loads(raw)

    # Ensure each finding has ai_assisted flag
    for f in findings:
        f["ai_assisted"] = True
        if "status" not in f:
            f["status"] = "Open"

    return findings


# --- Streamlit UI ---


def main():
    st.set_page_config(
        page_title="SAAF — IAM Access Review",
        page_icon="🔐",
        layout="wide",
    )

    st.title("IAM Access Review Agent")
    st.caption("Track 2 — Evidence Collection & Extraction | ISO 27001 A.5.18, SOC 2 CC6.2")

    # --- Sidebar ---
    with st.sidebar:
        st.header("Configuration")

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        api_key_input = st.text_input(
            "Anthropic API Key",
            value=api_key,
            type="password",
            help="Required for generating finding narratives. Set ANTHROPIC_API_KEY env var or enter here.",
        )
        if api_key_input:
            api_key = api_key_input

        st.divider()
        st.header("Data Source")

        use_sample = st.button("Use Sample Data", use_container_width=True)

        st.markdown("**— or upload your own —**")
        ad_file = st.file_uploader("AD Export (CSV)", type=["csv"])
        hr_file = st.file_uploader("HR Active Employees (CSV)", type=["csv"])

        st.divider()
        st.caption("SAAF Hackathon #4 — May 2026")
        st.caption("Synthetic data only — no real PII")

    # --- Load data ---
    ad_data = None
    hr_data = None

    if use_sample:
        ad_data, hr_data = load_sample_data()
        st.session_state["ad_data"] = ad_data
        st.session_state["hr_data"] = hr_data
        st.session_state["data_source"] = "Sample data (synthetic)"
    elif ad_file and hr_file:
        ad_data = parse_csv(ad_file.read().decode("utf-8"))
        hr_data = parse_csv(hr_file.read().decode("utf-8"))
        st.session_state["ad_data"] = ad_data
        st.session_state["hr_data"] = hr_data
        st.session_state["data_source"] = "Uploaded files"

    # Restore from session state
    if "ad_data" in st.session_state:
        ad_data = st.session_state["ad_data"]
        hr_data = st.session_state["hr_data"]

    if ad_data is None:
        st.info("Upload AD and HR CSV files, or click **Use Sample Data** in the sidebar to get started.")
        st.markdown("""
        ### Expected CSV formats

        **AD Export** columns: `username`, `display_name`, `email`, `department`, `role`, `last_login`, `account_status`, `created_date`

        **HR Active Employees** columns: `employee_id`, `username`, `full_name`, `department`, `job_title`, `start_date`, `status`
        """)
        return

    # --- Run analysis ---
    st.subheader(f"Data loaded: {st.session_state.get('data_source', '')}")

    results = analyse_access(ad_data, hr_data)

    # --- Summary metrics ---
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Accounts", results["total_accounts"])
    col2.metric("Orphaned", len(results["orphaned"]), delta=None)
    col3.metric("Role Mismatch", len(results["role_mismatches"]))
    col4.metric("Stale (>90d)", len(results["stale_accounts"]))
    col5.metric("Privileged", len(results["privileged_accounts"]))

    total_exceptions = len(results["orphaned"]) + len(results["role_mismatches"]) + len(results["stale_accounts"])

    if total_exceptions == 0:
        st.success("No exceptions found. All accounts match HR records.")
        return

    st.warning(f"{total_exceptions} exception(s) identified across {results['total_accounts']} accounts.")

    # --- Exception details ---
    tab1, tab2, tab3, tab4 = st.tabs(["Orphaned Accounts", "Role Mismatches", "Stale Accounts", "Privileged Accounts"])

    with tab1:
        if results["orphaned"]:
            st.error(f"{len(results['orphaned'])} account(s) in AD with no HR record")
            for u in results["orphaned"]:
                st.markdown(f"- **{u['username']}** — {u.get('department', 'N/A')} — Role: {u.get('role', 'User')} — Last login: {u.get('last_login', 'Unknown')}")
        else:
            st.success("No orphaned accounts found.")

    with tab2:
        if results["role_mismatches"]:
            st.warning(f"{len(results['role_mismatches'])} account(s) with department mismatch")
            for u in results["role_mismatches"]:
                st.markdown(f"- **{u['username']}** — AD: _{u['ad_department']}_ vs HR: _{u['hr_department']}_")
        else:
            st.success("No role mismatches found.")

    with tab3:
        if results["stale_accounts"]:
            st.info(f"{len(results['stale_accounts'])} account(s) inactive >90 days")
            for u in results["stale_accounts"]:
                days = u["days_since_login"]
                days_str = "Never logged in" if days == -1 else f"{days} days"
                st.markdown(f"- **{u['username']}** — {u.get('department', 'N/A')} — {days_str}")
        else:
            st.success("No stale accounts found.")

    with tab4:
        if results["privileged_accounts"]:
            st.info(f"{len(results['privileged_accounts'])} privileged account(s)")
            for u in results["privileged_accounts"]:
                st.markdown(f"- **{u['username']}** — Role: {u.get('role', '')} — Last login: {u.get('last_login', 'Unknown')}")
        else:
            st.success("No privileged accounts found.")

    # --- Generate findings ---
    st.divider()
    st.subheader("Generate Audit Findings")

    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar to generate findings with Claude.")
        return

    if st.button("Generate Findings with Claude", type="primary", use_container_width=True):
        with st.spinner("Calling Claude API to generate structured findings..."):
            try:
                findings = generate_findings_with_claude(results, api_key)
                st.session_state["findings"] = findings
            except Exception as e:
                st.error(f"Error generating findings: {e}")
                return

    # --- Display findings ---
    if "findings" in st.session_state:
        findings = st.session_state["findings"]
        st.success(f"{len(findings)} finding(s) generated")

        for finding in findings:
            risk = finding.get("risk_rating", "")
            icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Informational": "ℹ️"}.get(risk, "")

            with st.expander(f"{icon} {finding.get('id', '')} — {finding.get('title', '')}", expanded=False):
                st.markdown(f"**Risk Rating:** {risk}")
                if finding.get("control_objective"):
                    st.markdown(f"**Control Objective:** {finding['control_objective']}")
                st.markdown(f"**Observation:** {finding.get('observation', '')}")
                st.markdown(f"**Recommendation:** {finding.get('recommendation', '')}")
                if finding.get("evidence_references"):
                    st.markdown(f"**Evidence:** {', '.join(finding['evidence_references'])}")

        # --- Export ---
        st.divider()
        findings_json = json.dumps(findings, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download Findings (JSON)",
            data=findings_json,
            file_name=f"access-review-findings-{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True,
        )

        with st.expander("Raw JSON output"):
            st.code(findings_json, language="json")


if __name__ == "__main__":
    main()
