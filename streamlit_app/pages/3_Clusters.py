import os
import json
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium
import folium


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

st.set_page_config(page_title="Clusters / Hotspots", layout="wide")
st.title("Clusters / Hotspots")


@st.cache_data(ttl=60)
def get_request_types():
    r = requests.get(f"{API_BASE}/meta/distincts", params={"field": "Request_Type"}, timeout=30)
    r.raise_for_status()
    return ["All"] + r.json().get("values", [])


with st.sidebar:
    days = st.slider("Last N days", 7, 120, 30, 1)
    rt = st.selectbox("Request Type", get_request_types())
    eps = st.slider("DBSCAN eps (meters)", 50, 1000, 200, 10)
    min_samples = st.slider("DBSCAN min_samples", 3, 20, 5, 1)


params = {"days": days, "eps": eps, "min_samples": min_samples}
if rt != "All":
    params["request_type"] = rt
r = requests.get(f"{API_BASE}/ops/clusters", params=params, timeout=60)
payload = r.json()
clusters = payload.get("clusters", [])

st.subheader("Detected Clusters")
st.dataframe(pd.DataFrame(clusters), use_container_width=True, height=320)

if clusters:
    first = clusters[0]
    m = folium.Map(location=[first["centroid_lat"], first["centroid_lon"]], zoom_start=12)
    for c in clusters:
        folium.CircleMarker(
            location=[c["centroid_lat"], c["centroid_lon"]],
            radius=max(5, min(20, c["count"])),
            popup=f"#{c['cluster_id']} {c['primary_request_type']} (n={c['count']})",
            color="red",
            fill=True,
            fill_color="red",
        ).add_to(m)
    st_folium(m, width=1000)
else:
    st.info("No clusters detected for the selected parameters.")
