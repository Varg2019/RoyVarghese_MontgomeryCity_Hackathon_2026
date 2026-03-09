import os
import base64
from pathlib import Path

import pandas as pd
import requests
import streamlit as st


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")
ROOT = Path(__file__).resolve().parents[1]
SKYLINE_PATH = ROOT / "Montgomery_Skyline.jpg"
EMBLEM_PATH = ROOT / "Montgomery_Emblem.jpg"

st.set_page_config(page_title="Montgomery City Civic Services Smart Assistant", layout="wide")


def image_to_base64(path: Path) -> str:
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


skyline_b64 = image_to_base64(SKYLINE_PATH)
emblem_b64 = image_to_base64(EMBLEM_PATH)


@st.cache_data(ttl=30)
def fetch_kpis():
    r = requests.get(f"{API_BASE}/ops/kpis", timeout=30)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=45)
def fetch_summary(limit: int = 5000):
    r = requests.get(f"{API_BASE}/tickets", params={"limit": limit}, timeout=60)
    r.raise_for_status()
    return pd.DataFrame(r.json().get("items", []))


def build_status_department_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    pivot = (
        df.pivot_table(
            index="Department",
            columns="Status",
            values="Request_ID",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for col in ["Open", "In Progress", "Closed"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["Total"] = pivot[["Open", "In Progress", "Closed"]].sum(axis=1)
    pivot = pivot[["Department", "Open", "In Progress", "Closed", "Total"]].sort_values("Total", ascending=False)
    pivot = pivot[pivot["Department"].astype(str).str.strip().str.lower() != "faq"]
    totals = pd.DataFrame([
        {
            "Department": "Aggregated Total",
            "Open": int(pivot["Open"].sum()),
            "In Progress": int(pivot["In Progress"].sum()),
            "Closed": int(pivot["Closed"].sum()),
            "Total": int(pivot["Total"].sum()),
        }
    ])
    return pd.concat([pivot, totals], ignore_index=True)


css = """
<style>
.stApp {{
    background: transparent !important;
}}
.stApp::before {{
    content: "";
    position: fixed;
    inset: 0;
    z-index: -2;
    background:
        linear-gradient(rgba(6, 14, 24, 0.40), rgba(6, 14, 24, 0.58)),
        url('data:image/jpeg;base64,__SKYLINE__') center center / cover no-repeat;
}}
.stApp::after {{
    content: "";
    position: fixed;
    inset: 0;
    z-index: -1;
    background: linear-gradient(rgba(10, 18, 28, 0.12), rgba(10, 18, 28, 0.18));
}}
.block-container {{
    padding-top: 1.0rem;
    padding-bottom: 2rem;
}}
.top-ribbon {{
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 18px;
    padding: 0.75rem 1rem;
    color: #f3f7fb;
    font-size: 0.95rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
}}
.app-header-shell {{
    background: linear-gradient(90deg, rgba(6, 22, 40, 0.96) 0%, rgba(16, 61, 108, 0.95) 55%, rgba(32, 92, 145, 0.92) 100%);
    border-radius: 28px;
    padding: 2.35rem 2.4rem;
    box-shadow: 0 24px 55px rgba(0,0,0,0.34);
    border: 2px solid rgba(255,255,255,0.22);
    margin-bottom: 1.25rem;
    text-align: center;
}}
.app-header-flex {{
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
}}
.header-copy {{
    max-width: 1100px;
    margin: 0 auto;
}}
.assistant-title {{
    color: #ffffff;
    font-size: 4.25rem;
    font-weight: 900;
    line-height: 0.98;
    margin-bottom: 0.8rem;
    letter-spacing: 0.015em;
    text-shadow: 0 3px 18px rgba(0,0,0,0.28);
}}
.assistant-desc {{
    color: #e7f1fb;
    font-size: 1.2rem;
    line-height: 1.75;
    max-width: 920px;
    margin: 0 auto;
}}
.panel-card {{
    background: rgba(255,255,255,0.90);
    border-radius: 22px;
    padding: 1.2rem;
    border: 1px solid #dfe7f1;
    box-shadow: 0 14px 34px rgba(0,0,0,0.15);
    position: relative;
    overflow: hidden;
}}
.panel-title {{
    color: #123d6a;
    font-size: 1.15rem;
    font-weight: 900;
    margin-bottom: 0.8rem;
}}
div[data-testid="metric-container"] {{
    background: rgba(255,255,255,0.96);
    border: 1px solid #dce7f3;
    border-radius: 18px;
    padding: 1rem;
    box-shadow: 0 12px 25px rgba(0,0,0,0.12);
}}
.watermark-shell {{
    position: relative;
    border-radius: 26px;
    overflow: hidden;
    padding: 1.2rem;
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 18px 40px rgba(0,0,0,0.18);
    background: rgba(255,255,255,0.16);
    backdrop-filter: blur(8px);
}}
.subtle-watermark {{
    display: none !important;
}}
.subtle-watermark img {{
    width: 420px;
    opacity: 0.08;
    filter: grayscale(8%) saturate(90%);
}}
.watermark-content {{
    position: relative;
    z-index: 1;
}}
.transparent-table-note {{
    color: #10385f;
    font-size: 0.92rem;
    margin-bottom: 0.6rem;
    font-weight: 600;
}}
</style>
""".replace("__SKYLINE__", skyline_b64).replace("__EMBLEM__", emblem_b64)

st.markdown(css, unsafe_allow_html=True)

skyline_preview = """
<div style="
    border-radius: 24px;
    overflow: hidden;
    margin-bottom: 1rem;
    box-shadow: 0 18px 40px rgba(0,0,0,0.22);
    border: 1px solid rgba(255,255,255,0.20);
    position: relative;
">
    <img src="data:image/jpeg;base64,__SKYLINE__" alt="Montgomery Skyline" style="width:100%; display:block; max-height:180px; object-fit:cover;" />
    <div style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; pointer-events:none;">
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
            <div style="width:110px; height:110px; border-radius:50%; overflow:hidden; background:rgba(255,255,255,0.92); padding:4px; box-shadow:0 10px 24px rgba(0,0,0,0.25);">
                <img src="data:image/jpeg;base64,__EMBLEM__" alt="Montgomery emblem" style="width:100%; height:100%; object-fit:cover; border-radius:50%;" />
            </div>
            <div style="color:#ffffff; font-weight:800; font-size:1rem; text-shadow:0 2px 10px rgba(0,0,0,0.45); letter-spacing:0.03em;">City of Montgomery</div>
        </div>
    </div>
</div>
""".replace("__SKYLINE__", skyline_b64).replace("__EMBLEM__", emblem_b64)

header_block = """
<div class="app-header-shell">
    <div class="app-header-flex">
        <div class="header-copy">
            <div class="assistant-title"><strong>Montgomery City Civic Services Smart Assistant</strong></div>
            <div class="assistant-desc">
                A civic transparency and smart operations workspace for service requests, department performance,
                and resident communication across the City of Montgomery.
            </div>
        </div>
    </div>
</div>
"""

st.markdown(skyline_preview, unsafe_allow_html=True)
st.markdown(header_block, unsafe_allow_html=True)

try:
    k = fetch_kpis()
    aggregate_df = pd.DataFrame([
        {
            "Total Tickets": f"{k.get('total', 0):,}",
            "Open Backlog": f"{k.get('open', 0):,}",
            "Avg Days to Close": round(k.get("mean_time_to_close_days", 0.0), 2),
        }
    ])
except Exception as e:
    st.warning(f"KPI service unavailable: {e}")
    aggregate_df = pd.DataFrame()

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

st.sidebar.caption("Tip: Use the page descriptions below to understand each menu item.")
with st.sidebar.expander("What does Triage Console do?"):
    st.write("Review active requests with routing suggestions and ETA guidance.")
with st.sidebar.expander("What does Possible Misroutes do?"):
    st.write("See tickets whose assigned department may be inconsistent with historical patterns.")
with st.sidebar.expander("What do Clusters / Hotspots show?"):
    st.write("Identify clusters of similar requests that suggest proactive field action.")
with st.sidebar.expander("What is Resident Lookup for?"):
    st.write("Search a request by ID and show plain-language resident updates.")
with st.sidebar.expander("What can I do in Admin?"):
    st.write("Manage ingestion, SLA configuration, and demo workflow controls.")

st.markdown('<div class="watermark-shell"><div class="watermark-content">', unsafe_allow_html=True)
st.markdown(
    """
    <style>
    div[data-testid="stDataFrame"] {
        background: transparent !important;
    }
    div[data-testid="stDataFrame"] [data-testid="stTable"] {
        background: rgba(255,255,255,0.28) !important;
    }
    div[data-testid="stDataFrame"] * {
        background-color: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="panel-title">Service request overview</div>', unsafe_allow_html=True)

if not aggregate_df.empty:
    st.markdown('<div class="transparent-table-note">Aggregate ticket summary</div>', unsafe_allow_html=True)
    st.dataframe(aggregate_df, use_container_width=True, hide_index=True)

try:
    df = fetch_summary()
    summary = build_status_department_summary(df)
    if summary.empty:
        st.info("No ticket data available yet. Please run ingestion from the Admin page.")
    else:
        st.markdown('<div class="transparent-table-note">Department-wise ticket summary</div>', unsafe_allow_html=True)
        st.dataframe(summary, use_container_width=True, hide_index=True, height=560)
except Exception as e:
    st.warning(f"Unable to build summary table: {e}")

st.markdown('</div></div>', unsafe_allow_html=True)
