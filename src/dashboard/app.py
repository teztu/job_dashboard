"""Main Streamlit dashboard for Job Hunter."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

st.set_page_config(
    page_title="Job Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
from src.database.db import init_db
init_db()

# Page navigation
pages = {
    "Jobs": "pages.jobs",
    "Applications": "pages.applications",
    "Analytics": "pages.analytics",
    "Settings": "pages.settings",
}

# Sidebar navigation
st.sidebar.title("🎯 Job Hunter")
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigation", list(pages.keys()))

st.sidebar.markdown("---")
st.sidebar.markdown("Built with [Claude Code](https://claude.com/claude-code)")

# Load selected page
if page == "Jobs":
    from src.dashboard.pages import jobs
    jobs.render()
elif page == "Applications":
    from src.dashboard.pages import applications
    applications.render()
elif page == "Analytics":
    from src.dashboard.pages import analytics
    analytics.render()
elif page == "Settings":
    from src.dashboard.pages import settings
    settings.render()
