"""GDPR Audit Agent — Streamlit Demo UI."""

import json
import tempfile
from pathlib import Path

import streamlit as st

from pydantic import ValidationError

from gdpr_agent.audit_logger import AuditLogger
from gdpr_agent.config import PSEUDONYM_KEY_ENV_VAR, get_pseudonym_key
from gdpr_agent.models import ROLE_MASKING_MAP, AuditContext, MaskingLevel, Role
from gdpr_agent.pipeline import AuditPipeline

PURPOSES = [
    "reimbursement_review",
    "compliance_check",
    "breach_investigation",
    "deletion_verification",
    "data_access_request",
    "third_party_audit",
    "retention_review",
    "cross_border_audit",
]

SAMPLE_DATA_PATH = Path(__file__).parent / "data" / "sample_reimbursement.json"


def load_sample_data() -> list[dict]:
    with open(SAMPLE_DATA_PATH) as f:
        return json.load(f)


def main():
    st.set_page_config(page_title="GDPR Audit Agent", page_icon="🛡️", layout="wide")

    st.title("🛡️ GDPR AI Audit Agent")
    st.caption("Detect, classify, and mask PII in audit data — GDPR compliant")

    # Refuse to run rather than fall back to a shared key: pseudonyms produced
    # with a key anyone can read are reversible by anyone (GDPR Art. 4(5)).
    if not get_pseudonym_key():
        st.error(
            f"No pseudonymisation key configured. Set `{PSEUDONYM_KEY_ENV_VAR}` "
            "in your environment or `.env` file (at least 32 characters, "
            "unique to this deployment) and restart the app."
        )
        st.code(
            f'{PSEUDONYM_KEY_ENV_VAR}=$(python -c "import secrets; '
            "print(secrets.token_urlsafe(32))\")",
            language="bash",
        )
        return

    # --- Sidebar ---
    with st.sidebar:
        st.header("Audit Configuration")

        role = st.selectbox(
            "Role",
            options=[r.value for r in Role],
            format_func=lambda x: x.upper(),
            help="Auditor = full masking, DPO = partial, Admin = full access",
        )

        purpose = st.selectbox(
            "Audit Purpose",
            options=PURPOSES,
            format_func=lambda x: x.replace("_", " ").title(),
        )

        # Roles that receive unmasked data must say why; the reason is written
        # into the audit trail alongside the access.
        justification = None
        if ROLE_MASKING_MAP[Role(role)] == MaskingLevel.NONE:
            st.warning("This role receives unmasked personal data.")
            justification = st.text_area(
                "Justification (required)",
                placeholder="e.g. Investigating ticket INC-4417: corrupted export.",
                help="Recorded in the audit trail against every record accessed.",
            )

        st.divider()
        st.subheader("Data Source")
        data_source = st.radio(
            "Choose input",
            ["Sample Data", "Upload JSON"],
            label_visibility="collapsed",
        )

    # --- Load data ---
    records = None

    if data_source == "Sample Data":
        records = load_sample_data()
        st.sidebar.success(f"Loaded {len(records)} sample records")
    else:
        uploaded = st.sidebar.file_uploader("Upload JSON file", type=["json"])
        if uploaded:
            try:
                records = json.loads(uploaded.read())
                if not isinstance(records, list):
                    records = [records]
                st.sidebar.success(f"Loaded {len(records)} records")
            except json.JSONDecodeError:
                st.sidebar.error("Invalid JSON file")

    if records is None:
        st.info("Select a data source in the sidebar to get started.")
        return

    # --- Process ---
    try:
        ctx = AuditContext(
            role=Role(role),
            purpose=purpose,
            legal_basis="legitimate_interest",
            justification=justification,
        )
    except ValidationError:
        st.warning(
            "A justification is required before unmasked data can be shown. "
            "Enter one in the sidebar."
        )
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        pipeline = AuditPipeline(audit_context=ctx, log_dir=Path(tmp_dir))
        masked_records = pipeline.process_records(records)
        summary = pipeline.get_summary()
        audit_entries = pipeline.get_audit_log()

    # --- Summary metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Records Processed", summary["records_processed"])
    col2.metric("PII Fields Detected", summary["total_pii_fields"])
    col3.metric("Fields Masked", summary["total_masked"])
    col4.metric("Masking Level", summary["masking_level"].upper())

    st.divider()

    # --- Side-by-side comparison ---
    st.subheader("Original vs Masked Data")

    for i, (original, masked) in enumerate(zip(records, masked_records)):
        with st.expander(f"Record {i + 1}: {original.get('id', f'#{i+1}')}", expanded=i == 0):
            left, right = st.columns(2)

            with left:
                st.markdown("**Original**")
                for key, val in original.items():
                    str_val = str(val)
                    masked_val = str(masked.get(key, val))
                    if str_val != masked_val:
                        st.markdown(f"🔴 `{key}`: `{val}`")
                    else:
                        st.markdown(f"🟢 `{key}`: `{val}`")

            with right:
                st.markdown("**Masked**")
                for key, val in masked.items():
                    orig_val = str(original.get(key, ""))
                    masked_val = str(val)
                    if orig_val != masked_val:
                        st.markdown(f"🛡️ `{key}`: `{val}`")
                    else:
                        st.markdown(f"🟢 `{key}`: `{val}`")

    st.divider()

    # --- Audit Log ---
    st.subheader("Audit Trail")
    if AuditLogger.verify_chain(audit_entries):
        st.success("Hash chain intact — no entry has been altered or removed.")
    else:
        st.error("Hash chain broken — this trail has been tampered with.")

    for entry in audit_entries:
        with st.container():
            st.markdown(
                f"**{entry.action}** | Role: `{entry.role.value}` | "
                f"Purpose: `{entry.purpose}` | "
                f"Detected: {entry.fields_detected} | Masked: {entry.fields_masked}"
            )
            st.caption(
                f"🕐 {entry.timestamp} — record `{entry.record_id}` — {entry.reasoning}"
            )
            if entry.justification:
                st.caption(f"⚖️ Justification: {entry.justification}")

    # --- Download masked data ---
    st.divider()
    st.subheader("Export")
    col_dl1, col_dl2 = st.columns(2)

    with col_dl1:
        st.download_button(
            "📥 Download Masked Data (JSON)",
            data=json.dumps(masked_records, indent=2, default=str),
            file_name="masked_output.json",
            mime="application/json",
        )

    with col_dl2:
        log_lines = [entry.model_dump_json() for entry in audit_entries]
        st.download_button(
            "📥 Download Audit Log (JSONL)",
            data="\n".join(log_lines),
            file_name="audit_log.jsonl",
            mime="application/jsonl",
        )


if __name__ == "__main__":
    main()
