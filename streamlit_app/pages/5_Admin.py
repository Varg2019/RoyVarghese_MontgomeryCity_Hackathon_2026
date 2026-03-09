import os
from pathlib import Path
import requests
import streamlit as st


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Admin", layout="centered")
st.title("Admin & Config")

st.subheader("Ingestion")
csv_name = st.text_input("CSV filename in data/", value="requests_extract_20000.csv")
if st.button("Run Ingestion"):
    try:
        r = requests.post(f"{API_BASE}/admin/ingest", json={"csv_filename": csv_name}, timeout=120)
        r.raise_for_status()
        st.success("Ingestion complete")
        st.json(r.json().get("summary", {}))
    except Exception as e:
        st.error(f"Ingestion failed: {e}")

st.subheader("SLA Configuration")
scope = st.selectbox("Scope", ["Request_Type", "Department"])
key = st.text_input("Key (e.g., Street Light Out)")
target_days = st.number_input("Target days", min_value=0.0, step=0.5)
effective_date = st.date_input("Effective date")
notes = st.text_input("Notes", value="Hackathon demo")
if st.button("Add SLA"):
    payload = {
        "scope": scope,
        "key": key,
        "target_days": target_days,
        "effective_date": str(effective_date),
        "notes": notes,
    }
    rr = requests.post(f"{API_BASE}/admin/sla", json=payload, timeout=30)
    if rr.status_code == 200:
        st.success("SLA saved")
    else:
        st.error("Failed to save SLA")

st.subheader("Current SLA Items")
try:
    s = requests.get(f"{API_BASE}/admin/sla", timeout=30).json()
    st.dataframe(s.get("items", []))
except Exception as e:
    st.warning(f"Cannot load SLAs: {e}")

st.subheader("Demo Events Log")
try:
    ev = requests.get(f"{API_BASE}/ops/events", timeout=30).json()
    st.dataframe(ev.get("items", []))
except Exception as e:
    st.warning(f"Cannot load events: {e}")
