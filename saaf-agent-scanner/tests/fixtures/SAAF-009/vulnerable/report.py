"""HTML run report and Streamlit viewer for the audit agent."""
import streamlit as st
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

env = Environment(loader=FileSystemLoader("templates"), autoescape=False)


def render_rows(rows):
    body = []
    for r in rows:
        control = r.get("control_description") or "<span>no control</span>"
        body.append(
            "<tr>"
            f"<td>{r.get('risk_description')}</td>"
            f"<td>{control}</td>"
            f"<td>{r.get('verdict', '')}</td>"
            "</tr>"
        )
    return "<table>" + "".join(body) + "</table>"


def show(result):
    st.markdown(f"<div class='box'>{result['summary']}</div>", unsafe_allow_html=True)
    st.markdown(f"**Observation:** {result.get('observation', '')}")
    st.markdown(f"> {result['evidence_quote']}")


def badge(answer):
    return Markup(f"<b>{answer}</b>")
