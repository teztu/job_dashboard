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
from src.database.models import Application, ApplicationStatus
from src.analytics.recommendations import get_daily_recommendation

init_db()

# Sidebar navigation
st.sidebar.title("🎯 Job Hunter")
st.sidebar.markdown("---")

# Daily Recommendation in sidebar
st.sidebar.markdown("### 💡 Today's Pick")
rec = get_daily_recommendation()
if rec:
    job = rec["job"]
    st.sidebar.markdown(f"**{job.title}**")
    st.sidebar.caption(f"{job.company or 'Unknown'}" )
    st.sidebar.progress(rec["match_percentage"] / 100, text=f"{rec['match_percentage']}% match")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("⭐", key="sidebar_interested", help="Mark Interested", use_container_width=True):
            from src.database.db import get_db
            from src.database.models import Job
            with get_db() as db:
                j = db.query(Job).filter(Job.id == job.id).first()
                if j:
                    if not j.application:
                        j.application = Application(job_id=job.id)
                        db.add(j.application)
                    j.application.status = ApplicationStatus.INTERESTED
            st.rerun()
    with col2:
        st.link_button("View", job.url, use_container_width=True)
else:
    st.sidebar.info("No new jobs to recommend")

st.sidebar.markdown("---")

page = st.sidebar.radio("Navigation", ["Jobs", "Applications", "Analytics", "Settings"])

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
