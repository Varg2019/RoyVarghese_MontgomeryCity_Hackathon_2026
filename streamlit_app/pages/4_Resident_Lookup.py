import os
import requests
import streamlit as st
import pandas as pd
from sidebar_theme import inject_sidebar_theme, render_sidebar_nav


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Resident Ticket Lookup", layout="centered")
inject_sidebar_theme()
render_sidebar_nav()
st.title("Resident Ticket Lookup")

req_id = st.text_input("Enter Request ID")
lang = st.radio("Language / Idioma", ["English", "Español"], horizontal=True)

if st.button("Lookup") and req_id:
    r = requests.get(f"{API_BASE}/tickets/{req_id}", timeout=30)
    if r.status_code != 200:
        st.error("Ticket not found or service unavailable.")
    else:
        payload = r.json()
        if payload.get("error") == "not_found":
            st.warning("Ticket not found.")
        else:
            t = payload.get("ticket", {})
            eta = payload.get("eta", {})
            msg = payload.get("message_es") if lang.startswith("Español") else payload.get("message_en")
            st.subheader(f"Request {t.get('Request_ID')}")
            st.text(msg)
            details_df = pd.DataFrame(
                [
                    {"Field": "Status", "Value": t.get("Status")},
                    {"Field": "Request Type", "Value": t.get("Request_Type")},
                    {"Field": "Department", "Value": t.get("Department")},
                    {"Field": "Created", "Value": t.get("created_at")},
                    {"Field": "ETA", "Value": eta.get("eta_range_label")},
                ]
            )
            st.table(details_df)
