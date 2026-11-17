"""Streamlit portal — SAAF AI Control Assessment.

Run from the repo root:

    export ANTHROPIC_API_KEY=sk-...
    streamlit run tools/scripts/compliance_qa_app.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from compliance_qa import (
    DEFAULT_LOG_PATH,
    ComplianceVerdict,
    append_to_log,
    ask,
    extract_pdf_text,
)

# --- Translations ------------------------------------------------------------

STATUS_COLORS = {
    "Voldaan": "🟢",
    "Niet voldaan": "🔴",
    "Niet van toepassing": "⚪",
    "Geen antwoord": "🟡",
}
STATUS_OPTIONS = list(STATUS_COLORS.keys())

# Display labels for statuses per language
STATUS_DISPLAY = {
    "nl": {s: s for s in STATUS_OPTIONS},
    "en": {
        "Voldaan": "Compliant",
        "Niet voldaan": "Non-compliant",
        "Niet van toepassing": "Not applicable",
        "Geen antwoord": "No answer",
    },
}

LANGUAGES = {
    "nl": "🇳🇱 Nederlands",
    "en": "🇬🇧 English",
}

# GIAS 8-step labels per language
GIAS_STEP_LABELS = {
    "nl": {
        "objective_scope":         "1. Objective & Scope (GIAS 13.3)",
        "risk_context":            "2. Risk Context",
        "evidence_gathering":      "3. Evidence Gathering (relevant · reliable · sufficient)",
        "professional_skepticism": "4. Professional Skepticism",
        "analysis":                "5. Analysis (risk · design · operating effectiveness)",
        "evidence_sufficiency":    "6. Evidence Sufficiency",
        "conclusion":              "7. Conclusion (GIAS 14.5)",
        "audit_trail":             "8. Audit Trail (Conclusion → Finding → Evidence)",
    },
    "en": {
        "objective_scope":         "1. Objective & Scope (GIAS 13.3)",
        "risk_context":            "2. Risk Context",
        "evidence_gathering":      "3. Evidence Gathering (relevant · reliable · sufficient)",
        "professional_skepticism": "4. Professional Skepticism",
        "analysis":                "5. Analysis (risk · design · operating effectiveness)",
        "evidence_sufficiency":    "6. Evidence Sufficiency",
        "conclusion":              "7. Conclusion (GIAS 14.5)",
        "audit_trail":             "8. Audit Trail (Conclusion → Finding → Evidence)",
    },
}

T = {
    "nl": {
        "page_title": "SAAF AI Control Assessment",
        "title": "🔍 SAAF AI Control Assessment",
        "caption": (
            "Definieer een beheersmaatregel. Voeg bewijs toe (één of meer PDF's). "
            "Ontvang een assessment met evidence, onderbouwing en de mogelijkheid "
            "aanvullende informatie mee te geven."
        ),
        "lang_label": "Taal",
        "sb_q_header": "1. Beheersmaatregel",
        "sb_q_label": "Welke control/compliance-vraag wil je toetsen?",
        "sb_q_placeholder": "Bijv. Wordt MFA afgedwongen voor alle gebruikers?",
        "sb_up_header": "2. Voeg bewijs toe",
        "sb_up_label": "Upload één of meerdere PDF's",
        "sb_reading": "PDF's lezen…",
        "sb_loaded": "{n} bestand(en) geladen · {chars:,} tekens totaal",
        "sb_start": "🤖 Start assessment",
        "running": "Claude beoordeelt het bewijs…",
        "intro_hint": (
            "← Definieer een **beheersmaatregel** en upload **bewijs** in de "
            "sidebar, klik daarna op **Start assessment**."
        ),
        "status_label": "Status (AI)",
        "conf_bar": "Confidence: {n}/100",
        "reeval_tag": "🔄 _Herbeoordeeld met auditor-context_",
        "conf_card_title": "ℹ️ Onderbouwing confidence-score + benodigde informatie",
        "conf_reason": "**Onderbouwing:**",
        "conf_empty": "_(geen)_",
        "conf_needed": "**Nodig voor hogere score:**",
        "conf_no_needed": "_Geen aanvullende informatie nodig volgens de AI._",
        "add_header": "➕ Aanvullende informatie (auditor)",
        "add_caption": (
            "Voeg tekst toe **en/of** upload aanvullende PDF's (procedure, "
            "test-rapport, e.d.). Klik op **Save & herbeoordeel** om een nieuw "
            "verdict te berekenen."
        ),
        "add_text_label": "Tekstuele aanvulling",
        "add_text_placeholder": (
            "Bijv. mondelinge bevestiging CISO, procedure-referentie, …"
        ),
        "add_files_label": "Aanvullende PDF's (optioneel)",
        "add_btn": "💾 Save & herbeoordeel",
        "add_reading": "Aanvullende PDF's lezen…",
        "add_files_added": "📎 Toegevoegd: {names}",
        "reeval_running": "Herbeoordelen met aanvullende informatie…",
        "reeval_ok": "Nieuw verdict berekend — pagina ververst.",
        "ai_reasoning_header": "🧠 AI reasoning (samenvatting)",
        "gias_badge": "🧭 GIAS v2024-aligned",
        "gias_tooltip": (
            "Deze applicatie past een gestructureerd audit-redeneer model toe, "
            "geïnspireerd op de Global Internal Audit Standards v2024 (effective "
            "2025): 8 stappen — objective · risk · evidence · skepticism · "
            "analysis · sufficiency · conclusion · audit trail."
        ),
        "gias_trail_header": "🧭 GIAS Reasoning Trail (8 stappen)",
        "gias_trail_caption": (
            "Gestructureerde onderbouwing van het AI-oordeel volgens de GIAS v2024 "
            "methodiek. Elk oordeel is reproduceerbaar via deze 8 stappen."
        ),
        "evidence_header": "📑 Evidence",
        "evidence_none": (
            "_Geen evidence-quotes gevonden — het document beantwoordt deze vraag "
            "waarschijnlijk niet._"
        ),
        "evidence_page": "**📄 Page {p}**",
        "evidence_auditor": "**🧑 Auditor-context**",
        "final_header": "⚖️ Eindoordeel auditor",
        "final_label": "Vrij tekstveld — jouw professionele conclusie bovenop de AI-verdict.",
        "action_title": "**Actie**",
        "accept_title": "##### ✅ Neem AI-oordeel over",
        "accept_btn": "Accepteer & save naar audit log",
        "accept_saved": "Geaccepteerd en opgeslagen in {path}",
        "override_title": "##### ❌ Negeer AI-oordeel",
        "override_select": "Auditor-status (override)",
        "override_btn": "Override & save naar audit log",
        "override_saved": "Override opgeslagen: **{new}** (AI: {old}) — in {path}",
        "download": "⬇️ Download verdict JSON",
        "log_path": "🔒 Audit log (read-only): `{path}`",
        "failed": "Assessment faalde: {e}",
        "reeval_failed": "Herbeoordelen faalde: {e}",
    },
    "en": {
        "page_title": "SAAF AI Control Assessment",
        "title": "🔍 SAAF AI Control Assessment",
        "caption": (
            "Define a control/compliance question. Add evidence (one or more "
            "PDFs). Receive an assessment with evidence, reasoning and the option "
            "to supply additional context."
        ),
        "lang_label": "Language",
        "sb_q_header": "1. Control / Question",
        "sb_q_label": "Which control or compliance question do you want to assess?",
        "sb_q_placeholder": "E.g. Is MFA enforced for all users?",
        "sb_up_header": "2. Add evidence",
        "sb_up_label": "Upload one or more PDFs",
        "sb_reading": "Reading PDFs…",
        "sb_loaded": "{n} file(s) loaded · {chars:,} chars total",
        "sb_start": "🤖 Start assessment",
        "running": "Claude is assessing the evidence…",
        "intro_hint": (
            "← Define a **control** and upload **evidence** in the sidebar, "
            "then click **Start assessment**."
        ),
        "status_label": "Status (AI)",
        "conf_bar": "Confidence: {n}/100",
        "reeval_tag": "🔄 _Re-assessed with auditor context_",
        "conf_card_title": "ℹ️ Confidence score reasoning + information needed",
        "conf_reason": "**Reasoning:**",
        "conf_empty": "_(none)_",
        "conf_needed": "**Needed to raise the score:**",
        "conf_no_needed": "_AI reports no additional information needed._",
        "add_header": "➕ Additional information (auditor)",
        "add_caption": (
            "Add text **and/or** upload additional PDFs (procedure, test report, "
            "etc.). Click **Save & re-assess** to recompute the verdict."
        ),
        "add_text_label": "Additional text",
        "add_text_placeholder": (
            "E.g. verbal confirmation from CISO, procedure reference, …"
        ),
        "add_files_label": "Additional PDFs (optional)",
        "add_btn": "💾 Save & re-assess",
        "add_reading": "Reading additional PDFs…",
        "add_files_added": "📎 Added: {names}",
        "reeval_running": "Re-assessing with additional information…",
        "reeval_ok": "New verdict computed — page refreshed.",
        "ai_reasoning_header": "🧠 AI reasoning (summary)",
        "gias_badge": "🧭 GIAS v2024-aligned",
        "gias_tooltip": (
            "This application applies a structured audit reasoning model "
            "aligned with the Global Internal Audit Standards v2024 (effective "
            "2025): 8 steps — objective · risk · evidence · skepticism · "
            "analysis · sufficiency · conclusion · audit trail."
        ),
        "gias_trail_header": "🧭 GIAS Reasoning Trail (8 steps)",
        "gias_trail_caption": (
            "Structured underpinning of the AI verdict following the GIAS v2024 "
            "methodology. Every verdict is reproducible through these 8 steps."
        ),
        "evidence_header": "📑 Evidence",
        "evidence_none": (
            "_No evidence quotes found — the document likely does not answer this "
            "question._"
        ),
        "evidence_page": "**📄 Page {p}**",
        "evidence_auditor": "**🧑 Auditor context**",
        "final_header": "⚖️ Auditor final judgement",
        "final_label": "Free-text — your professional conclusion on top of the AI verdict.",
        "action_title": "**Action**",
        "accept_title": "##### ✅ Accept AI verdict",
        "accept_btn": "Accept & save to audit log",
        "accept_saved": "Accepted and saved to {path}",
        "override_title": "##### ❌ Override AI verdict",
        "override_select": "Auditor status (override)",
        "override_btn": "Override & save to audit log",
        "override_saved": "Override saved: **{new}** (AI: {old}) — in {path}",
        "download": "⬇️ Download verdict JSON",
        "log_path": "🔒 Audit log (read-only): `{path}`",
        "failed": "Assessment failed: {e}",
        "reeval_failed": "Re-assessment failed: {e}",
    },
}

# --- Session state -----------------------------------------------------------

for key, default in {
    "verdict": None,
    "combined_text": None,
    "document_names": [],
    "uploaded_signature": None,
    "last_question": "",
    "additional_info": "",
    "lang": "nl",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

lang = st.session_state.lang
t = T[lang]

# --- Page setup --------------------------------------------------------------

st.set_page_config(
    page_title=t["page_title"],
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    [data-testid="stSidebar"][aria-expanded="true"]{min-width:340px; max-width:340px;}
    [data-testid="collapsedControl"]{display:none;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Top bar with GIAS badge + language dropdown (right) --------------------

top_title, top_gias, top_lang = st.columns([5, 2, 1])
with top_title:
    st.title(t["title"])
with top_gias:
    st.write("")
    # Badge with hover tooltip via native help= arg
    st.info(t["gias_badge"], icon="🧭")
    st.caption(t["gias_tooltip"])
with top_lang:
    st.write("")
    chosen = st.selectbox(
        t["lang_label"],
        options=list(LANGUAGES.keys()),
        format_func=lambda k: LANGUAGES[k],
        index=list(LANGUAGES.keys()).index(st.session_state.lang),
        key="lang_select",
        label_visibility="collapsed",
    )
    if chosen != st.session_state.lang:
        st.session_state.lang = chosen
        st.rerun()

st.caption(t["caption"])

# --- Helpers -----------------------------------------------------------------


def _combine_docs(files) -> tuple[str, list[str]]:
    chunks: list[str] = []
    names: list[str] = []
    for f in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(f.getbuffer())
            tmp_path = Path(tmp.name)
        text = extract_pdf_text(tmp_path)
        chunks.append(f"=== FILE: {f.name} ===\n{text}")
        names.append(f.name)
    return ("\n\n".join(chunks), names)


def _status_label(status: str) -> str:
    return STATUS_DISPLAY[lang].get(status, status)


# --- Sidebar -----------------------------------------------------------------

with st.sidebar:
    st.header(t["sb_q_header"])
    question = st.text_area(
        t["sb_q_label"],
        value=st.session_state.last_question,
        placeholder=t["sb_q_placeholder"],
        height=140,
        key="question_input",
    )

    st.header(t["sb_up_header"])
    uploaded = st.file_uploader(
        t["sb_up_label"],
        type=["pdf"],
        accept_multiple_files=True,
    )

    sig = tuple((f.name, f.size) for f in uploaded) if uploaded else None
    if uploaded and sig != st.session_state.uploaded_signature:
        with st.spinner(t["sb_reading"]):
            text, names = _combine_docs(uploaded)
            st.session_state.combined_text = text
            st.session_state.document_names = names
            st.session_state.uploaded_signature = sig
            st.session_state.verdict = None
            st.session_state.additional_info = ""
        st.success(t["sb_loaded"].format(n=len(names), chars=len(text)))

    ask_clicked = st.button(
        t["sb_start"],
        type="primary",
        disabled=not (st.session_state.combined_text and question.strip()),
        use_container_width=True,
    )

# --- Initial assessment ------------------------------------------------------

if ask_clicked:
    st.session_state.last_question = question
    st.session_state.additional_info = ""
    with st.spinner(t["running"]):
        try:
            v = ask(
                st.session_state.combined_text,
                question,
                document_name="; ".join(st.session_state.document_names),
                language=lang,
            )
            v.documents = list(st.session_state.document_names)
            v.log_stage = "initial_ai"
            st.session_state.verdict = v
            append_to_log(v)
        except Exception as e:
            st.error(t["failed"].format(e=e))
            st.session_state.verdict = None

verdict: ComplianceVerdict | None = st.session_state.verdict

if verdict is None:
    st.info(t["intro_hint"])
    st.stop()

# --- Header + status ---------------------------------------------------------

header_col, status_col = st.columns([3, 1])
with header_col:
    st.subheader(f"_{verdict.question}_")
    docs_line = ", ".join(verdict.documents) if verdict.documents else "—"
    st.caption(f"📄 {docs_line}")
    if verdict.reevaluated:
        st.caption(t["reeval_tag"])
with status_col:
    icon = STATUS_COLORS.get(verdict.status, "")
    st.metric(t["status_label"], f"{icon} {_status_label(verdict.status)}")
    st.progress(
        verdict.confidence / 100,
        text=t["conf_bar"].format(n=verdict.confidence),
    )

# --- Compact confidence card -------------------------------------------------

with st.expander(t["conf_card_title"], expanded=True):
    st.markdown(f"{t['conf_reason']} {verdict.confidence_reasoning or t['conf_empty']}")
    if verdict.information_needed:
        needed = " · ".join(f"`{x}`" for x in verdict.information_needed)
        st.markdown(f"{t['conf_needed']} {needed}")
    else:
        st.caption(t["conf_no_needed"])

# --- Additional info + re-assess --------------------------------------------

st.divider()
st.subheader(t["add_header"])
st.caption(t["add_caption"])

a1, a2 = st.columns([3, 2])
with a1:
    additional_info_text = st.text_area(
        t["add_text_label"],
        value=st.session_state.additional_info,
        height=160,
        key="additional_info_text_input",
        placeholder=t["add_text_placeholder"],
    )
with a2:
    extra_files = st.file_uploader(
        t["add_files_label"],
        type=["pdf"],
        accept_multiple_files=True,
        key="extra_files_uploader",
    )

if st.button(
    t["add_btn"],
    type="primary",
    disabled=not (additional_info_text.strip() or extra_files),
):
    extra_blocks = []
    if additional_info_text.strip():
        extra_blocks.append(additional_info_text.strip())
    if extra_files:
        with st.spinner(t["add_reading"]):
            text, names = _combine_docs(extra_files)
            extra_blocks.append(text)
            st.caption(t["add_files_added"].format(names=", ".join(names)))
    additional_context = "\n\n".join(extra_blocks)

    with st.spinner(t["reeval_running"]):
        try:
            new_v = ask(
                st.session_state.combined_text,
                verdict.question,
                document_name="; ".join(st.session_state.document_names),
                additional_context=additional_context,
                language=lang,
            )
            new_v.documents = list(st.session_state.document_names)
            new_v.log_stage = "reevaluated_ai"
            st.session_state.verdict = new_v
            st.session_state.additional_info = additional_info_text
            append_to_log(new_v)
            st.success(t["reeval_ok"])
            st.rerun()
        except Exception as e:
            st.error(t["reeval_failed"].format(e=e))

# --- GIAS Reasoning Trail (above AI reasoning) ------------------------------

st.divider()
if verdict.reasoning_trail is not None:
    with st.expander(t["gias_trail_header"], expanded=False):
        st.caption(t["gias_trail_caption"])
        step_labels = GIAS_STEP_LABELS[lang]
        trail = verdict.reasoning_trail
        for key in [
            "objective_scope",
            "risk_context",
            "evidence_gathering",
            "professional_skepticism",
            "analysis",
            "evidence_sufficiency",
            "conclusion",
            "audit_trail",
        ]:
            st.markdown(f"**{step_labels[key]}**")
            st.write(getattr(trail, key))

# --- AI reasoning (summary, above evidence) ---------------------------------

st.subheader(t["ai_reasoning_header"])
st.write(verdict.ai_reasoning)

# --- Evidence ----------------------------------------------------------------

st.subheader(t["evidence_header"])
if not verdict.evidence:
    st.caption(t["evidence_none"])
for q in verdict.evidence:
    with st.container(border=True):
        label = (
            t["evidence_page"].format(p=q.page) if q.page > 0 else t["evidence_auditor"]
        )
        if q.section:
            label += f" · _{q.section}_"
        if not q.verified:
            label += " · ⚠️ _unverified_"
        st.markdown(label)
        st.markdown(f"> {q.exact_quote}")
        if not q.verified:
            warn = (
                "Deze quote komt niet letterlijk voor in het document of de "
                "aanvullende context. Mogelijk is het een parafrase of verkeerde "
                "paginaverwijzing — controleer handmatig voor je dit als evidence "
                "gebruikt."
                if lang == "nl"
                else "This quote is not a verbatim match with the source document "
                     "or additional context. It may be a paraphrase or wrong page "
                     "reference — verify manually before citing as evidence."
            )
            st.warning(warn)

# --- Eindoordeel + actions --------------------------------------------------

st.divider()
st.subheader(t["final_header"])
judgement = st.text_area(
    t["final_label"],
    value=verdict.auditor_judgement or "",
    height=160,
    key="judgement_input",
)

st.markdown(t["action_title"])
c_accept, c_override = st.columns(2)

with c_accept:
    st.markdown(t["accept_title"])
    if st.button(
        t["accept_btn"],
        type="primary",
        use_container_width=True,
    ):
        verdict.auditor_judgement = judgement.strip() or None
        verdict.auditor_override_status = None
        verdict.log_stage = "auditor_accepted"
        path = append_to_log(verdict)
        st.success(t["accept_saved"].format(path=path))

with c_override:
    st.markdown(t["override_title"])
    override = st.selectbox(
        t["override_select"],
        options=STATUS_OPTIONS,
        format_func=_status_label,
        index=STATUS_OPTIONS.index(verdict.status),
        key="override_status",
    )
    if st.button(
        t["override_btn"],
        type="secondary",
        use_container_width=True,
    ):
        verdict.auditor_judgement = judgement.strip() or None
        verdict.auditor_override_status = override
        verdict.log_stage = "auditor_override"
        path = append_to_log(verdict)
        st.warning(
            t["override_saved"].format(
                new=_status_label(override),
                old=_status_label(verdict.status),
                path=path,
            )
        )

# --- Footer ------------------------------------------------------------------

st.divider()
d1, d2 = st.columns([1, 3])
with d1:
    st.download_button(
        t["download"],
        data=verdict.model_dump_json(indent=2),
        file_name="verdict.json",
        mime="application/json",
    )
with d2:
    st.caption(t["log_path"].format(path=DEFAULT_LOG_PATH))
