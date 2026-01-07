"""Main Streamlit dashboard for Job Hunter."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

st.set_page_config(
    page_title="Job Hunter - Norwegian Job Search",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better UI
st.markdown("""
<style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Navigation radio buttons */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.5rem;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        transition: background 0.2s;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.1);
    }
    
    /* Headers */
    h1, h2, h3 {
        font-weight: 600;
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
from src.database.db import init_db
from src.database.models import Application, ApplicationStatus
from src.analytics.recommendations import get_daily_recommendation

init_db()

# Sidebar header
st.sidebar.markdown("""
# 🎯 Job Hunter
**Norwegian Job Search Assistant**
""")
st.sidebar.markdown("---")

# Daily Recommendation
st.sidebar.markdown("### 💡 Today's Top Pick")
rec = get_daily_recommendation()
if rec:
    job = rec["job"]
    company = job.company if job.company else "Company not listed"
    st.sidebar.markdown(f"**{job.title[:40]}{'...' if len(job.title) > 40 else ''}**")
    st.sidebar.caption(company)
    st.sidebar.progress(rec["match_percentage"] / 100, text=f"{rec['match_percentage']}% match")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("⭐ Save", key="sidebar_interested", use_container_width=True):
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
    st.sidebar.info("Run a scrape to get recommendations")

st.sidebar.markdown("---")

# Navigation with icons
st.sidebar.markdown("### Navigate")
page = st.sidebar.radio(
    "nav",
    ["🔍 Browse Jobs", "📋 My Applications", "📊 Statistics", "⚙️ Settings", "❓ Help"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# Quick stats in sidebar
from src.database.db import get_db
from src.database.models import Job, Application
with get_db() as db:
    total_jobs = db.query(Job).count()
    saved_jobs = db.query(Application).filter(Application.status == ApplicationStatus.INTERESTED).count()
    applied_jobs = db.query(Application).filter(Application.status == ApplicationStatus.APPLIED).count()

st.sidebar.markdown("### 📈 Quick Stats")
st.sidebar.caption(f"📁 {total_jobs} jobs scraped")
st.sidebar.caption(f"⭐ {saved_jobs} saved")
st.sidebar.caption(f"📤 {applied_jobs} applied")

st.sidebar.markdown("---")
st.sidebar.caption("Built with [Claude Code](https://claude.com/claude-code)")

# Load selected page
if page == "🔍 Browse Jobs":
    from src.dashboard.pages import jobs
    jobs.render()
elif page == "📋 My Applications":
    from src.dashboard.pages import applications
    applications.render()
elif page == "📊 Statistics":
    from src.dashboard.pages import analytics
    analytics.render()
elif page == "⚙️ Settings":
    from src.dashboard.pages import settings
    settings.render()
elif page == "❓ Help":
    from src.dashboard.pages import help_page
    help_page.render()
