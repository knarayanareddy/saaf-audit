"""HTML run report and Streamlit viewer for the audit agent, with escaping."""
import html

import streamlit as st
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html"]))


def _esc(v):
    return html.escape(str(v if v is not None else ""))


def render_rows(rows):
    body = []
    for r in rows:
        control = _esc(r.get("control_description")) or "<span>no control</span>"
        body.append(
            "<tr>"
            f"<td>{_esc(r.get('risk_description'))}</td>"
            f"<td>{control}</td>"
            f"<td>{html.escape(r.get('verdict', ''))}</td>"
            "</tr>"
        )
    return "<table>" + "".join(body) + "</table>"


def show(result):
    st.markdown("<style>.box{padding:4px}</style>", unsafe_allow_html=True)
    st.text(f"Observation: {result.get('observation', '')}")
    st.code(result["evidence_quote"])
    st.markdown(f"**Count:** {len(result['items'])}")
