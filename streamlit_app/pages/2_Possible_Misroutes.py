import os
import io
import json
import pandas as pd
import requests
import streamlit as st
from sidebar_theme import inject_sidebar_theme, render_sidebar_nav


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Possible Misroutes", layout="wide")
inject_sidebar_theme()
render_sidebar_nav()
st.title("Possible Misroutes")


with st.sidebar:
    st.divider()
    st.header("Filters")
    status = st.selectbox("Status", ["All", "Open", "In Progress"], index=1)
    min_conf = st.slider("Min confidence", 0.5, 0.99, 0.8, 0.01)


@st.cache_data(ttl=30)
def fetch_queue(status: str, min_conf: float):
    r = requests.get(f"{API_BASE}/ops/misroutes", params={"status": status, "min_conf": min_conf}, timeout=60)
    r.raise_for_status()
    return r.json()


resp = fetch_queue(status, min_conf)
rows = []
for item in resp.get("items", []):
    t = item.get("ticket", {})
    rec = item.get("recommendation", {})
    rows.append({
        "Request_ID": t.get("Request_ID"),
        "Status": t.get("Status"),
        "Request_Type": t.get("Request_Type"),
        "Department": t.get("Department"),
        "Recommended": rec.get("recommended_department"),
        "Confidence": rec.get("confidence"),
        "Why": json.dumps(rec.get("explanation")),
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, height=600)

if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Export CSV", data=csv, file_name="possible_misroutes.csv", mime="text/csv")
