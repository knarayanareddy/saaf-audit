#!/usr/bin/env python3
"""
access_review_ui.py
Locally-hosted Streamlit UI for the SAAF Access Review Agent.

Usage:
    pip install streamlit anthropic
    streamlit run tools/scripts/access_review_ui.py
"""

import csv
import io
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import streamlit as st


def render_table(rows: list[dict]) -> None:
    """Render a list of dicts as a markdown table — no pandas/numpy needed."""
    if not rows:
        st.info("No records.")
        return
    headers = list(rows[0].keys())
    header_row = "| " + " | ".join(headers) + " |"
    sep_row   = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_rows = [
        "| " + " | ".join(str(r.get(h, "")) for h in headers) + " |"
        for r in rows
    ]
    st.markdown("\n".join([header_row, sep_row] + data_rows))

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="SAAF Access Review Agent",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

REPO_ROOT = Path(__file__).parents[2]
PROMPT_FILE = REPO_ROOT / "prompts" / "audit-use-cases" / "access-review-agent.md"
SCHEMA_FILE = REPO_ROOT / "outputs" / "schemas" / "finding-schema.json"

RISK_COLOURS = {
    "High": "#d9534f",
    "Medium": "#f0ad4e",
    "Low": "#5bc0de",
    "Informational": "#5cb85c",
}

RISK_BADGES = {
    "High":          "🔴 High",
    "Medium":        "🟡 Medium",
    "Low":           "🔵 Low",
    "Informational": "🟢 Informational",
}

# ---------------------------------------------------------------------------
# Helper: CSV parsing from UploadedFile or Path
# ---------------------------------------------------------------------------

def parse_csv_upload(uploaded) -> list[dict]:
    content = uploaded.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def parse_csv_path(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Detection logic (mirrors access_review_agent.py)
# ---------------------------------------------------------------------------

def anonymise(users: list[dict], counter_start: int = 1) -> tuple[list[dict], dict[str, str]]:
    mapping: dict[str, str] = {}
    result: list[dict] = []
    for i, user in enumerate(users, start=counter_start):
        placeholder = f"USER-{i:03d}"
        mapping[placeholder] = user.get("username", "")
        anon = dict(user)
        anon["username"] = placeholder
        result.append(anon)
    return result, mapping


def find_orphaned(ad: list[dict], hr: list[dict]) -> list[dict]:
    hr_names = {u["username"] for u in hr}
    return [u for u in ad if u["username"] not in hr_names]


def find_stale(ad: list[dict], threshold: int) -> list[dict]:
    today = date.today()
    stale = []
    for u in ad:
        try:
            last = datetime.strptime(u.get("last_login", ""), "%Y-%m-%d").date()
            if (today - last).days > threshold:
                stale.append(u)
        except ValueError:
            pass
    return stale


def find_mismatches(ad: list[dict], hr: list[dict]) -> list[dict]:
    hr_map = {u["username"]: u for u in hr}
    out = []
    for a in ad:
        h = hr_map.get(a["username"])
        if h and a.get("department") != h.get("department"):
            out.append({
                "username": a["username"],
                "ad_department": a.get("department", ""),
                "hr_department": h.get("department", ""),
                "role": a.get("role", ""),
                "last_login": a.get("last_login", ""),
            })
    return out


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def load_system_prompt() -> str:
    if not PROMPT_FILE.exists():
        return ""
    text = PROMPT_FILE.read_text(encoding="utf-8")
    match = re.search(r"## System Context\n\n(.+?)(?=\n---\n)", text, re.DOTALL)
    return match.group(1).strip() if match else text


def build_user_prompt(orphaned, stale, mismatches, threshold):
    lines = [
        "I am performing a user access review.",
        "All usernames have been anonymised to USER-NNN placeholders.",
        "",
    ]
    if orphaned:
        lines.append(f"Orphaned AD accounts (no matching HR record — {len(orphaned)} found):")
        for u in orphaned:
            lines.append(f"  {u['username']}, department: {u.get('department','N/A')}, "
                         f"role: {u.get('role','N/A')}, last_login: {u.get('last_login','N/A')}")
    else:
        lines.append("Orphaned AD accounts: none found.")
    lines.append("")
    if stale:
        lines.append(f"Stale accounts (no login in >{threshold} days — {len(stale)} found):")
        for u in stale:
            lines.append(f"  {u['username']}, department: {u.get('department','N/A')}, "
                         f"last_login: {u.get('last_login','N/A')}")
    else:
        lines.append(f"Stale accounts (>{threshold} days): none found.")
    lines.append("")
    if mismatches:
        lines.append(f"Role mismatches (department differs — {len(mismatches)} found):")
        for m in mismatches:
            lines.append(f"  {m['username']}: AD department = {m['ad_department']}, "
                         f"HR department = {m['hr_department']}")
    else:
        lines.append("Role mismatches: none found.")
    lines += ["", "Please produce SAAF findings for all exceptions listed above."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claude call
# ---------------------------------------------------------------------------

def call_claude(api_key: str, system: str, user: str) -> Optional[str]:
    try:
        import anthropic
    except ImportError:
        st.error("anthropic package not installed. Run: pip install anthropic")
        return None
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def validate_findings(raw: str) -> list[dict]:
    required = {"id", "title", "risk_rating", "observation", "recommendation"}
    valid_ratings = {"High", "Medium", "Low", "Informational"}
    id_pat = re.compile(r"^F-\d{2,4}$")
    match = re.search(r"```json\s*(\[.*?\])\s*```", raw, re.DOTALL)
    block = match.group(1) if match else raw.strip()
    try:
        findings = json.loads(block)
    except json.JSONDecodeError:
        return []
    out = []
    for f in findings:
        if required - set(f.keys()):
            continue
        if not id_pat.match(f["id"]):
            continue
        if f["risk_rating"] not in valid_ratings:
            continue
        out.append(f)
    return out


# ---------------------------------------------------------------------------
# UI — Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/security-checked.png", width=60)
    st.title("SAAF Access Review")
    st.caption("Automated user access review agent")
    st.divider()

    st.subheader("Configuration")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Required to generate Claude findings. Leave blank to run detection only.",
    )
    threshold = st.slider("Stale account threshold (days)", 30, 365, 90, step=10)
    st.divider()

    st.subheader("Test data")
    use_sample = st.checkbox("Use built-in synthetic test data", value=True)
    st.caption("Uncheck to upload your own CSV files.")

# ---------------------------------------------------------------------------
# UI — Main
# ---------------------------------------------------------------------------

st.title("🔐 SAAF Access Review Agent")
st.markdown(
    "Upload an **Active Directory export** and an **HR active-employee list** to identify "
    "orphaned accounts, stale accounts, and role mismatches. Findings conform to the "
    "[SAAF finding schema](outputs/schemas/finding-schema.json)."
)

# --- File inputs -----------------------------------------------------------

col1, col2 = st.columns(2)

ad_data: Optional[list[dict]] = None
hr_data: Optional[list[dict]] = None

with col1:
    st.subheader("Active Directory export")
    if use_sample:
        sample_ad = REPO_ROOT / "tools" / "scripts" / "test_data" / "ad_export.csv"
        if sample_ad.exists():
            ad_data = parse_csv_path(sample_ad)
            st.success(f"Loaded sample: `ad_export.csv` ({len(ad_data)} rows)")
        else:
            st.warning("Sample file not found.")
    else:
        up_ad = st.file_uploader("Upload AD export CSV", type="csv", key="ad")
        if up_ad:
            ad_data = parse_csv_upload(up_ad)
            st.success(f"Loaded: {up_ad.name} ({len(ad_data)} rows)")

    if ad_data:
        with st.expander("Preview AD data"):
            render_table(ad_data)

with col2:
    st.subheader("HR active-employee list")
    if use_sample:
        sample_hr = REPO_ROOT / "tools" / "scripts" / "test_data" / "hr_export.csv"
        if sample_hr.exists():
            hr_data = parse_csv_path(sample_hr)
            st.success(f"Loaded sample: `hr_export.csv` ({len(hr_data)} rows)")
        else:
            st.warning("Sample file not found.")
    else:
        up_hr = st.file_uploader("Upload HR list CSV", type="csv", key="hr")
        if up_hr:
            hr_data = parse_csv_upload(up_hr)
            st.success(f"Loaded: {up_hr.name} ({len(hr_data)} rows)")

    if hr_data:
        with st.expander("Preview HR data"):
            render_table(hr_data)

st.divider()

# --- Run button ------------------------------------------------------------

run_disabled = not (ad_data and hr_data)
run = st.button("▶  Run Access Review", type="primary", disabled=run_disabled,
                help="Both CSV files must be loaded before running.")

if run_disabled and not (ad_data and hr_data):
    st.info("Load both CSV files to enable the review.")

# --- Execution & results ---------------------------------------------------

if run and ad_data and hr_data:

    with st.spinner("Detecting exceptions…"):
        ad_anon, anon_map = anonymise(ad_data)
        orig_to_ph = {v: k for k, v in anon_map.items()}
        hr_anon = [{**u, "username": orig_to_ph.get(u["username"], u["username"])} for u in hr_data]

        orphaned = find_orphaned(ad_anon, hr_anon)
        stale    = find_stale(ad_anon, threshold)
        mismatches = find_mismatches(ad_anon, hr_anon)

    # Summary metrics
    st.subheader("Detection summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AD accounts",     len(ad_data))
    m2.metric("Orphaned",        len(orphaned),   delta=f"{'⚠' if orphaned else '✓'}",   delta_color="inverse")
    m3.metric("Stale accounts",  len(stale),      delta=f"{'⚠' if stale else '✓'}",      delta_color="inverse")
    m4.metric("Role mismatches", len(mismatches), delta=f"{'⚠' if mismatches else '✓'}", delta_color="inverse")

    total_exceptions = len(orphaned) + len(stale) + len(mismatches)

    if total_exceptions == 0:
        st.success("No exceptions found. No findings to produce.")
        st.stop()

    # Detail expanders
    if orphaned:
        with st.expander(f"🔴 Orphaned accounts ({len(orphaned)})"):
            render_table(orphaned)
    if stale:
        with st.expander(f"🔵 Stale accounts — no login >{threshold} days ({len(stale)})"):
            render_table(stale)
    if mismatches:
        with st.expander(f"🟡 Role mismatches ({len(mismatches)})"):
            render_table(mismatches)

    st.divider()

    # Claude findings
    if not api_key:
        st.warning(
            "No API key provided — showing detection results only. "
            "Enter your Anthropic API key in the sidebar to generate full audit findings."
        )
    else:
        st.subheader("Generating findings with Claude…")
        system_prompt = load_system_prompt()
        user_prompt   = build_user_prompt(orphaned, stale, mismatches, threshold)

        with st.spinner("Calling Claude API…"):
            raw = call_claude(api_key, system_prompt, user_prompt)

        if raw:
            findings = validate_findings(raw)

            if not findings:
                st.error("Could not parse findings from Claude's response.")
                with st.expander("Raw response"):
                    st.text(raw)
            else:
                st.subheader(f"Findings ({len(findings)})")

                for f in findings:
                    rating  = f.get("risk_rating", "Informational")
                    colour  = RISK_COLOURS.get(rating, "#aaa")
                    badge   = RISK_BADGES.get(rating, rating)

                    with st.container(border=True):
                        header_col, badge_col = st.columns([5, 1])
                        header_col.markdown(f"**{f['id']} — {f['title']}**")
                        badge_col.markdown(
                            f"<span style='background:{colour};color:white;"
                            f"padding:3px 10px;border-radius:12px;font-size:0.8rem'>"
                            f"{badge}</span>",
                            unsafe_allow_html=True,
                        )

                        if f.get("control_objective"):
                            st.caption(f"Control: {f['control_objective']}")

                        tabs = st.tabs(["Observation", "Root cause", "Impact", "Recommendation"])
                        tabs[0].write(f.get("observation", "—"))
                        tabs[1].write(f.get("root_cause",  "—"))
                        tabs[2].write(f.get("impact",       "—"))
                        tabs[3].write(f.get("recommendation", "—"))

                # Save to file
                out_dir = REPO_ROOT / "outputs" / "access-review"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / "findings.json"
                out_file.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")

                st.success(f"Findings saved to `{out_file.relative_to(REPO_ROOT)}`")

                # Download button
                st.download_button(
                    label="⬇  Download findings.json",
                    data=json.dumps(findings, indent=2, ensure_ascii=False),
                    file_name="access-review-findings.json",
                    mime="application/json",
                )
