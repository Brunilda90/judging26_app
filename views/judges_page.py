import streamlit as st
import sqlite3
from db import get_judges, insert_judge

def show():
    st.header("Manage Judges")

    # Form to add a new judge
    with st.form("add_judge"):
        name = st.text_input("Judge name")
        email = st.text_input("Judge email")
        submitted = st.form_submit_button("Add judge")

        if submitted:
            if not name.strip() or not email.strip():
                st.error("Name and email are required.")
            else:
                try:
                    insert_judge(name.strip(), email.strip())
                    st.success(f"Added judge: {name}")
                except sqlite3.IntegrityError:
                    st.error("Email already exists.")

    st.subheader("Current judges")

    # Load and display judge list
    judges = get_judges()
    if judges:
        st.table([dict(row) for row in judges])
    else:
        st.info("No judges yet.")
