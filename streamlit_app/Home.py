import os
import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from sidebar_theme import inject_sidebar_theme, render_sidebar_nav


API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")
ROOT = Path(__file__).resolve().parents[1]
SKYLINE_PATH = ROOT / "Montgomery_Skyline.jpg"
EMBLEM_PATH = ROOT / "Montgomery_Emblem.jpg"

st.set_page_config(page_title="Montgomery City Civic Services Smart Assistant", layout="wide")
inject_sidebar_theme()


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
    totals = pd.DataFrame(
        [
            {
                "Department": "Aggregated Total",
                "Open": int(pivot["Open"].sum()),
                "In Progress": int(pivot["In Progress"].sum()),
                "Closed": int(pivot["Closed"].sum()),
                "Total": int(pivot["Total"].sum()),
            }
        ]
    )
    return pd.concat([pivot, totals], ignore_index=True)


def style_table(df: pd.DataFrame):
    styled = (
        df.style.set_table_styles(
            [
                {
                    "selector": "thead th",
                    "props": [
                        ("background-color", "#0d3f67"),
                        ("color", "#ffffff"),
                        ("font-size", "0.8rem"),
                        ("font-weight", "800"),
                        ("text-transform", "uppercase"),
                        ("letter-spacing", "0.04em"),
                    ],
                },
                {
                    "selector": "tbody td",
                    "props": [
                        ("font-size", "1.02rem"),
                        ("color", "#123a5e"),
                        ("border", "1px solid #d2e2f0"),
                    ],
                },
                {"selector": "tbody tr:nth-child(even) td", "props": [("background-color", "#f6fbff")]},
                {"selector": "tbody tr:nth-child(odd) td", "props": [("background-color", "#ffffff")]},
            ]
        )
        .set_properties(subset=[df.columns[0]], **{"text-align": "left", "font-weight": "800"})
    )
    if len(df.columns) > 1:
        styled = styled.set_properties(subset=df.columns[1:], **{"text-align": "right", "font-weight": "700"})
    return styled


def render_aggregate_table(df: pd.DataFrame, updated_at: datetime | None = None) -> None:
    if df.empty:
        return
    row = df.iloc[0]
    value_col = "Value"
    if updated_at:
        value_col = f"Value ({updated_at.strftime('%B %d, %Y %I:%M %p')})"

    table_df = pd.DataFrame(
        {
            "Metric": ["Total Tickets", "Open Backlog", "Avg Days to Close"],
            value_col: [
                str(row["Total Tickets"]),
                str(row["Open Backlog"]),
                f"{float(row['Avg Days to Close']):.2f}",
            ],
        }
    )
    st.dataframe(style_table(table_df.reset_index(drop=True)), use_container_width=True, hide_index=True)


css = """
<style>
.stApp {
    background: transparent !important;
}
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -2;
    background:
        linear-gradient(rgba(6, 14, 24, 0.40), rgba(6, 14, 24, 0.58)),
        url('data:image/jpeg;base64,__SKYLINE__') center center / cover no-repeat;
}
.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -1;
    background: linear-gradient(rgba(10, 18, 28, 0.12), rgba(10, 18, 28, 0.18));
}
.block-container {
    padding-top: 1.0rem;
    padding-bottom: 2rem;
}
.app-header-shell {
    background: linear-gradient(90deg, rgba(240, 248, 255, 0.96) 0%, rgba(223, 241, 255, 0.96) 100%);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 12px 30px rgba(0,0,0,0.25);
    border: 1px solid rgba(9, 52, 97, 0.28);
    margin-bottom: 0.75rem;
    text-align: center;
}
.app-header-flex {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
}
.header-copy {
    max-width: 1100px;
    margin: 0 auto;
}
.assistant-title {
    color: #0a2f5a;
    font-size: 2.8rem;
    font-weight: 900;
    line-height: 1.06;
    margin-bottom: 0.45rem;
    letter-spacing: 0.006em;
    text-shadow: 0 2px 6px rgba(9, 52, 97, 0.14);
}
.assistant-desc {
    color: #123d6a;
    font-size: 0.84rem;
    line-height: 1.25;
    margin: 0 auto;
    font-weight: 500;
    white-space: nowrap;
    text-align: center;
}
.panel-title {
    color: #123d6a;
    font-size: 1.15rem;
    font-weight: 900;
    margin-bottom: 0.8rem;
    display: inline-block;
    background: #ffffff;
    border: 1px solid rgba(9, 52, 97, 0.2);
    border-radius: 10px;
    padding: 0.45rem 0.75rem;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
}
.skyline-hero-shell {
    border-radius: 20px;
    overflow: hidden;
    margin-bottom: 0.9rem;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.24);
    border: 1px solid rgba(255, 255, 255, 0.24);
    position: relative;
}
.skyline-hero-image {
    width: 100%;
    height: 230px;
    display: block;
    object-fit: cover;
    object-position: center 34%;
}
.skyline-hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, rgba(4, 20, 38, 0.16), rgba(4, 20, 38, 0.44));
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
}
.skyline-emblem-wrap {
    width: 106px;
    height: 106px;
    border-radius: 50%;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.94);
    padding: 4px;
    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.24);
}
.skyline-city-label {
    color: #ffffff;
    font-weight: 800;
    font-size: 0.95rem;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.48);
    letter-spacing: 0.03em;
    margin-top: 8px;
}
@media (max-width: 1000px) {
    .assistant-title {
        font-size: 2.2rem;
        line-height: 1.02;
    }
}
@media (max-width: 700px) {
    .skyline-hero-image {
        height: 180px;
        object-position: center 30%;
    }
    .skyline-emblem-wrap {
        width: 86px;
        height: 86px;
    }
    .skyline-city-label {
        font-size: 0.84rem;
    }
    .assistant-title {
        font-size: 1.7rem;
    }
    .assistant-desc {
        font-size: 0.84rem;
        line-height: 1.5;
        white-space: normal;
    }
}
</style>
""".replace("__SKYLINE__", skyline_b64).replace("__EMBLEM__", emblem_b64)

st.markdown(css, unsafe_allow_html=True)

skyline_preview = """
<div class="skyline-hero-shell">
    <img src="data:image/jpeg;base64,__SKYLINE__" alt="Montgomery Skyline" class="skyline-hero-image" />
    <div class="skyline-hero-overlay">
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
            <div class="skyline-emblem-wrap">
                <img src="data:image/jpeg;base64,__EMBLEM__" alt="Montgomery emblem" style="width:100%; height:100%; object-fit:cover; border-radius:50%;" />
            </div>
            <div class="skyline-city-label">City of Montgomery</div>
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
                An official civic service transparency and smart operations portal for service requests, department performance, and resident communication across the City of Montgomery.
            </div>
        </div>
    </div>
</div>
"""

st.markdown(skyline_preview, unsafe_allow_html=True)
st.markdown(header_block, unsafe_allow_html=True)

try:
    k = fetch_kpis()
    aggregate_df = pd.DataFrame(
        [
            {
                "Total Tickets": f"{k.get('total', 0):,}",
                "Open Backlog": f"{k.get('open', 0):,}",
                "Avg Days to Close": round(k.get("mean_time_to_close_days", 0.0), 2),
            }
        ]
    )
    kpi_fetched_at = datetime.now()
except Exception as e:
    st.warning(f"KPI service unavailable: {e}")
    aggregate_df = pd.DataFrame()
    kpi_fetched_at = None

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

render_sidebar_nav()

st.markdown('<div class="panel-title">Service Request Status Summary Review</div>', unsafe_allow_html=True)

if not aggregate_df.empty:
    render_aggregate_table(aggregate_df, kpi_fetched_at)
else:
    st.info("Aggregate KPIs are unavailable right now.")

try:
    df = fetch_summary()
    summary = build_status_department_summary(df)
    if summary.empty:
        st.info("No ticket data available yet. Please run ingestion from the Admin page.")
    else:
        st.markdown('<div class="panel-title">Department-wise ticket summary</div>', unsafe_allow_html=True)
        st.dataframe(
            style_table(summary.reset_index(drop=True)),
            use_container_width=True,
            hide_index=True,
            height=560,
        )
except Exception as e:
    st.warning(f"Unable to build summary table: {e}")