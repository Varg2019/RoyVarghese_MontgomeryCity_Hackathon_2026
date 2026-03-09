import os
from typing import Dict, Any

import pandas as pd
import requests
import streamlit as st


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Triage Console", layout="wide")
st.title("Triage Console")


@st.cache_data(ttl=60)
def get_distinct(field: str):
    r = requests.get(f"{API_BASE}/meta/distincts", params={"field": field}, timeout=30)
    r.raise_for_status()
    return r.json().get("values", [])


with st.sidebar:
    st.header("Filters")
    status = st.selectbox("Status", ["All", "Open", "In Progress", "Closed"], index=1)
    dept = st.selectbox("Department", ["All"] + get_distinct("Department"))
    rtype = st.selectbox("Request Type", ["All"] + get_distinct("Request_Type"))
    district = st.selectbox("District", ["All"] + get_distinct("District"))
    origin = st.selectbox("Origin", ["All"] + get_distinct("Origin"))
    limit = st.slider("Max rows", 10, 300, 100)


params: Dict[str, Any] = {"limit": limit}
if status != "All":
    params["status"] = status
if dept != "All":
    params["department"] = dept
if rtype != "All":
    params["request_type"] = rtype
if district != "All":
    params["district"] = district
if origin != "All":
    params["origin"] = origin

r = requests.get(f"{API_BASE}/tickets", params=params, timeout=60)
data = r.json().get("items", [])
df = pd.DataFrame(data)

def fetch_details(req_id: str):
    rr = requests.get(f"{API_BASE}/tickets/{req_id}", timeout=30)
    if rr.status_code == 200:
        return rr.json()
    return {}


if not df.empty:
    # Compute recommendation and ETA for preview subset
    preview_count = min(len(df), 50)
    recs = []
    for rid in df["Request_ID"].head(preview_count):
        detail = fetch_details(str(rid))
        route = (detail or {}).get("routing_recommendation", {})
        eta = (detail or {}).get("eta", {})
        recs.append({
            "Request_ID": rid,
            "rec_department": route.get("recommended_department"),
            "confidence": route.get("confidence"),
            "eta": eta.get("eta_range_label"),
        })
    rdf = pd.DataFrame(recs).set_index("Request_ID")
    show = df.set_index("Request_ID").join(rdf)
    st.dataframe(show, use_container_width=True, height=600)
else:
    st.info("No tickets match the current filters.")
