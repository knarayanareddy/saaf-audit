"""Streamlit front-end: upload a policy PDF, get a summary. Advisory only — no tools."""

import logging

import anthropic
import streamlit as st
from pdfplumber import open as open_pdf

from prompts import SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
client = anthropic.Anthropic()


def summarize(text: str) -> str:
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text


def main() -> None:
    uploaded = st.file_uploader("Policy PDF")
    if uploaded:
        with open_pdf(uploaded) as pdf:
            body = "\n".join(page.extract_text() or "" for page in pdf.pages)
        st.write(summarize(body))


if __name__ == "__main__":
    main()
