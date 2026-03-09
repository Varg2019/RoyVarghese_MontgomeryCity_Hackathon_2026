import streamlit as st


def inject_sidebar_theme() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #eaf3fb 0%, #dcecf9 100%);
            border-right: 1px solid rgba(18, 61, 106, 0.24);
        }
        [data-testid="stSidebar"] .stCaptionContainer,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: #123d6a !important;
        }
        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
            display: block;
            background: linear-gradient(90deg, #f8fcff 0%, #edf6fd 100%);
            border: 1px solid rgba(13, 63, 103, 0.18);
            border-radius: 10px;
            padding: 0.42rem 0.58rem;
            margin: 0.14rem 0 0.26rem 0;
            color: #0d3f67 !important;
            font-weight: 700;
            text-decoration: none !important;
            box-shadow: 0 2px 8px rgba(8, 45, 78, 0.08);
            transition: all 0.15s ease-in-out;
        }
        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
            border-color: rgba(13, 63, 103, 0.36);
            background: linear-gradient(90deg, #ffffff 0%, #e5f3ff 100%);
            box-shadow: 0 4px 12px rgba(8, 45, 78, 0.14);
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] {
            background: linear-gradient(90deg, #0f4f82 0%, #1d6ca7 100%);
            border-color: rgba(7, 34, 58, 0.56);
            color: #ffffff !important;
            box-shadow: 0 6px 14px rgba(8, 45, 78, 0.24);
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(16, 56, 95, 0.2);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_nav() -> None:
    with st.sidebar:
        st.caption("Navigation")
        if hasattr(st, "page_link"):
            st.page_link("Home.py", label="Home", help="Overview, citywide KPIs, and department-wise ticket summary.")
            st.page_link("pages/1_Triage_Console.py", label="Triage Console", help="Review active requests with routing suggestions and ETA guidance.")
            st.page_link("pages/2_Possible_Misroutes.py", label="Possible Misroutes", help="See tickets whose assigned department may be inconsistent with historical patterns.")
            st.page_link("pages/3_Clusters.py", label="Clusters / Hotspots", help="Identify clusters of similar requests that suggest proactive field action.")
            st.page_link("pages/4_Resident_Lookup.py", label="Resident Lookup", help="Search a request by ID and show plain-language resident updates.")
            st.page_link("pages/5_Admin.py", label="Admin", help="Manage ingestion, SLA configuration, and demo workflow controls.")
        else:
            st.info("Upgrade Streamlit to use sidebar tooltips for page links.")
