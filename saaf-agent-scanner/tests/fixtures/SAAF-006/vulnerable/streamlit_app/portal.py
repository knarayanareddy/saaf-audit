import streamlit as st

st.title("Evidence portal")
doc = st.file_uploader("Upload evidence")
if st.button("Analyse") and doc:
    st.write("analysing", doc.name)
