"""Main Streamlit dashboard for Job Hunter."""

import streamlit as st

st.set_page_config(
    page_title="Job Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
from ..database.db import init_db
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
    from .pages import jobs
    jobs.render()
elif page == "Applications":
    from .pages import applications
    applications.render()
elif page == "Analytics":
    from .pages import analytics
    analytics.render()
elif page == "Settings":
    from .pages import settings
    settings.render()
