"""Main Streamlit dashboard for Job Hunter - Single Page Home."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta

import streamlit as st
from sqlalchemy.orm import joinedload

st.set_page_config(
    page_title="Job Hunter - Home",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    h1, h2, h3 { font-weight: 600; }
    [data-testid="metric-container"] {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
from src.database.db import get_db, init_db
from src.database.models import Application, ApplicationStatus, Job

init_db()


def _get_clean_company(company):
    """Get clean company name."""
    if not company:
        return "Company not available"
    garbage = ["favoritt", "legg til", "lagre", "saved", "publisert"]
    if any(g in company.lower() for g in garbage):
        return "Company not available"
    return company


# Sidebar
st.sidebar.markdown("""
# 🎯 Job Hunter
**Norwegian Job Search**
""")
st.sidebar.markdown("---")

# Quick stats
with get_db() as db:
    total_jobs = db.query(Job).count()
    saved_jobs = db.query(Application).filter(Application.status == ApplicationStatus.INTERESTED).count()
    applied_jobs = db.query(Application).filter(Application.status == ApplicationStatus.APPLIED).count()

st.sidebar.markdown("### 📈 Stats")
st.sidebar.metric("Jobs Scraped", total_jobs)
st.sidebar.metric("Saved", saved_jobs)
st.sidebar.metric("Applied", applied_jobs)

st.sidebar.markdown("---")
st.sidebar.caption("Built with [Claude Code](https://claude.com/claude-code)")

# Main content - HOME
st.title("🎯 Job Hunter - Home")
st.caption("Find your next job in Norway")

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    days_filter = st.selectbox(
        "Time period",
        options=[1, 7, 14, 30, 90],
        index=1,
        format_func=lambda x: f"Last {x} days",
    )

with col2:
    source_filter = st.selectbox(
        "Source",
        options=["All", "finn", "arbeidsplassen"],
        format_func=lambda x: {"All": "All Sources", "finn": "🔵 Finn.no", "arbeidsplassen": "🟢 NAV"}.get(x, x),
    )

with col3:
    keyword_filter = st.text_input("Search", placeholder="e.g., Python")

# Query jobs
with get_db() as db:
    query = db.query(Job).options(joinedload(Job.application))

    since = datetime.utcnow() - timedelta(days=days_filter)
    query = query.filter(Job.scraped_at >= since)

    if source_filter != "All":
        query = query.filter(Job.source == source_filter)

    if keyword_filter:
        query = query.filter(
            (Job.title.ilike(f"%{keyword_filter}%")) |
            (Job.company.ilike(f"%{keyword_filter}%"))
        )

    jobs = query.order_by(Job.scraped_at.desc()).all()

# Stats row
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Total Jobs", len(jobs))
new_today = len([j for j in jobs if j.scraped_at and j.scraped_at.date() == datetime.utcnow().date()])
col2.metric("New Today", new_today)
col3.metric("Saved", len([j for j in jobs if j.application and j.application.status == ApplicationStatus.INTERESTED]))

st.markdown("---")

# Jobs list
if not jobs:
    st.info("No jobs found. Run a scrape or adjust filters.")
else:
    for job in jobs:
        col1, col2 = st.columns([4, 1])

        with col1:
            status_badge = ""
            if job.application:
                badges = {
                    ApplicationStatus.INTERESTED: "⭐",
                    ApplicationStatus.APPLIED: "📤",
                    ApplicationStatus.INTERVIEW: "🎯",
                    ApplicationStatus.OFFER: "🎉",
                    ApplicationStatus.REJECTED: "❌",
                }
                status_badge = badges.get(job.application.status, "")

            source_icon = "🔵" if job.source == "finn" else "🟢"
            company = _get_clean_company(job.company)

            st.markdown(f"### {status_badge} {job.title}")
            st.markdown(f"**{company}** • {job.location or 'Oslo'} • {source_icon} {job.source.title()}")

            if job.scraped_at:
                st.caption(f"Scraped: {job.scraped_at.strftime('%Y-%m-%d %H:%M')}")

        with col2:
            st.link_button("View Job", job.url, use_container_width=True)

            current_status = job.application.status if job.application else None

            if current_status != ApplicationStatus.INTERESTED:
                if st.button("⭐ Save", key=f"int_{job.id}", use_container_width=True):
                    with get_db() as db:
                        j = db.query(Job).filter(Job.id == job.id).first()
                        if j:
                            if not j.application:
                                j.application = Application(job_id=job.id)
                                db.add(j.application)
                            j.application.status = ApplicationStatus.INTERESTED
                    st.rerun()

            if current_status == ApplicationStatus.INTERESTED:
                if st.button("📤 Applied", key=f"app_{job.id}", use_container_width=True):
                    with get_db() as db:
                        j = db.query(Job).filter(Job.id == job.id).first()
                        if j and j.application:
                            j.application.status = ApplicationStatus.APPLIED
                            j.application.applied_date = datetime.utcnow()
                    st.rerun()

        st.markdown("---")
