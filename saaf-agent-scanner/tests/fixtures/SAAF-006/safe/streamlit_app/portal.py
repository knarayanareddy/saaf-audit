import streamlit as st

if not st.user.is_logged_in:
    st.login()
    st.stop()
doc = st.file_uploader("Upload evidence")
if st.button("Analyse") and doc:
    st.write("analysing", doc.name)
