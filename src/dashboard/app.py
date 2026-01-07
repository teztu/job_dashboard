"""Main Streamlit dashboard for Job Hunter - All features in clean UI."""

import sys
from pathlib import Path

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
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { font-weight: 600; }
    [data-testid="metric-container"] {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

from src.database.db import get_db, init_db
from src.database.models import Application, ApplicationStatus, Job, SearchKeyword

init_db()

# Initialize session state
if "not_interested_ids" not in st.session_state:
    st.session_state.not_interested_ids = set()


def _get_clean_company(company):
    if not company:
        return "Company not available"
    garbage = ["favoritt", "legg til", "lagre", "saved", "publisert"]
    if any(g in company.lower() for g in garbage):
        return "Company not available"
    return company


def _score_job(job):
    score = 0
    title_lower = job.title.lower()
    keywords = ["python", "junior", "data", "backend", "developer", "utvikler", "sql", "api", "ml", "machine"]
    for kw in keywords:
        if kw in title_lower:
            score += 10
    if "senior" in title_lower or "lead" in title_lower:
        score -= 5
    return score


# Sidebar
st.sidebar.markdown("# 🎯 Job Hunter")
st.sidebar.markdown("**Norwegian Job Search**")
st.sidebar.markdown("---")

# Sidebar navigation
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "📋 My Applications", "📊 Statistics", "⚙️ Settings"],
)

st.sidebar.markdown("---")

# Quick stats in sidebar
with get_db() as db:
    total_jobs = db.query(Job).count()
    saved_count = db.query(Application).filter(Application.status == ApplicationStatus.INTERESTED).count()
    applied_count = db.query(Application).filter(Application.status == ApplicationStatus.APPLIED).count()

st.sidebar.markdown("### 📈 Stats")
st.sidebar.caption(f"📁 {total_jobs} jobs")
st.sidebar.caption(f"⭐ {saved_count} saved")
st.sidebar.caption(f"📤 {applied_count} applied")
st.sidebar.markdown("---")
st.sidebar.caption("Built with [Claude Code](https://claude.com/claude-code)")


# ============ HOME PAGE ============
if page == "🏠 Home":
    st.title("🎯 Job Hunter - Home")
    st.caption("Find your next job in Norway")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        days_filter = st.selectbox("Time period", [1, 7, 14, 30, 90], index=1, format_func=lambda x: f"Last {x} days")
    with col2:
        source_filter = st.selectbox("Source", ["All", "finn", "arbeidsplassen"],
            format_func=lambda x: {"All": "All", "finn": "🔵 Finn", "arbeidsplassen": "🟢 NAV"}.get(x, x))
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
            query = query.filter((Job.title.ilike(f"%{keyword_filter}%")) | (Job.company.ilike(f"%{keyword_filter}%")))
        jobs = query.order_by(Job.scraped_at.desc()).all()

    # Stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total", len(jobs))
    col2.metric("New Today", len([j for j in jobs if j.scraped_at and j.scraped_at.date() == datetime.utcnow().date()]))
    col3.metric("Saved", len([j for j in jobs if j.application and j.application.status == ApplicationStatus.INTERESTED]))

    # Top 5 Recommendations
    st.markdown("---")
    st.markdown("### 💡 Top 5 Recommended")

    rec_jobs = [j for j in jobs if (not j.application or j.application.status == ApplicationStatus.NEW)
                and j.id not in st.session_state.not_interested_ids]
    rec_jobs_sorted = sorted(rec_jobs, key=_score_job, reverse=True)[:5]

    if rec_jobs_sorted:
        for job in rec_jobs_sorted:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                source_icon = "🔵" if job.source == "finn" else "🟢"
                st.markdown(f"**{job.title}**")
                st.caption(f"{_get_clean_company(job.company)} • {source_icon}")
            with col2:
                if st.button("⭐", key=f"rec_save_{job.id}", help="Save", use_container_width=True):
                    with get_db() as db:
                        j = db.query(Job).filter(Job.id == job.id).first()
                        if j:
                            if not j.application:
                                j.application = Application(job_id=job.id)
                                db.add(j.application)
                            j.application.status = ApplicationStatus.INTERESTED
                    st.rerun()
            with col3:
                st.link_button("View", job.url, use_container_width=True)
            with col4:
                if st.button("👎", key=f"rec_skip_{job.id}", help="Not interested", use_container_width=True):
                    st.session_state.not_interested_ids.add(job.id)
                    st.rerun()
    else:
        st.info("No more recommendations. Reset skipped or run a scrape!")

    if st.session_state.not_interested_ids:
        if st.button("🔄 Reset skipped"):
            st.session_state.not_interested_ids = set()
            st.rerun()

    # All Jobs
    st.markdown("---")
    st.markdown("### 📄 All Jobs")

    if not jobs:
        st.info("No jobs found. Run a scrape or adjust filters.")
    else:
        for job in jobs:
            col1, col2 = st.columns([4, 1])
            with col1:
                badge = ""
                if job.application:
                    badges = {ApplicationStatus.INTERESTED: "⭐", ApplicationStatus.APPLIED: "📤",
                              ApplicationStatus.INTERVIEW: "🎯", ApplicationStatus.OFFER: "🎉", ApplicationStatus.REJECTED: "❌"}
                    badge = badges.get(job.application.status, "")
                source_icon = "🔵" if job.source == "finn" else "🟢"
                st.markdown(f"### {badge} {job.title}")
                st.markdown(f"**{_get_clean_company(job.company)}** • {job.location or 'Oslo'} • {source_icon}")
                if job.scraped_at:
                    st.caption(f"Scraped: {job.scraped_at.strftime('%Y-%m-%d %H:%M')}")
            with col2:
                st.link_button("View", job.url, use_container_width=True)
                curr = job.application.status if job.application else None
                if curr != ApplicationStatus.INTERESTED:
                    if st.button("⭐ Save", key=f"save_{job.id}", use_container_width=True):
                        with get_db() as db:
                            j = db.query(Job).filter(Job.id == job.id).first()
                            if j:
                                if not j.application:
                                    j.application = Application(job_id=job.id)
                                    db.add(j.application)
                                j.application.status = ApplicationStatus.INTERESTED
                        st.rerun()
                if curr == ApplicationStatus.INTERESTED:
                    if st.button("📤 Applied", key=f"apply_{job.id}", use_container_width=True):
                        with get_db() as db:
                            j = db.query(Job).filter(Job.id == job.id).first()
                            if j and j.application:
                                j.application.status = ApplicationStatus.APPLIED
                                j.application.applied_date = datetime.utcnow()
                        st.rerun()
            st.markdown("---")


# ============ MY APPLICATIONS ============
elif page == "📋 My Applications":
    st.title("📋 My Applications")
    st.caption("Track your job applications")

    with get_db() as db:
        apps = db.query(Application).options(joinedload(Application.job)).order_by(Application.updated_at.desc()).all()
        by_status = {s: [a for a in apps if a.status == s] for s in ApplicationStatus}

    if not apps:
        st.info("No saved jobs yet! Go to Home and click ⭐ to save jobs.")
    else:
        # Pipeline overview
        cols = st.columns(5)
        status_list = [
            (ApplicationStatus.INTERESTED, "⭐ Interested"),
            (ApplicationStatus.APPLIED, "📤 Applied"),
            (ApplicationStatus.INTERVIEW, "🎯 Interview"),
            (ApplicationStatus.OFFER, "🎉 Offer"),
            (ApplicationStatus.REJECTED, "❌ Rejected"),
        ]
        for i, (status, label) in enumerate(status_list):
            cols[i].metric(label, len(by_status.get(status, [])))

        st.markdown("---")

        # Kanban view
        st.markdown("### Active Pipeline")
        cols = st.columns(3)
        kanban_statuses = [
            (ApplicationStatus.INTERESTED, "⭐ Interested"),
            (ApplicationStatus.APPLIED, "📤 Applied"),
            (ApplicationStatus.INTERVIEW, "🎯 Interview"),
        ]
        for i, (status, label) in enumerate(kanban_statuses):
            with cols[i]:
                st.markdown(f"#### {label}")
                for app in by_status.get(status, []):
                    st.markdown(f"**{app.job.title}**")
                    st.caption(_get_clean_company(app.job.company))
                    if app.applied_date:
                        days = (datetime.utcnow() - app.applied_date).days
                        st.caption(f"📅 {days}d ago")

                    c1, c2 = st.columns(2)
                    with c1:
                        if status == ApplicationStatus.INTERESTED:
                            if st.button("📤", key=f"k_app_{app.id}", help="Applied"):
                                with get_db() as db:
                                    a = db.query(Application).filter(Application.id == app.id).first()
                                    if a:
                                        a.status = ApplicationStatus.APPLIED
                                        a.applied_date = datetime.utcnow()
                                st.rerun()
                        elif status == ApplicationStatus.APPLIED:
                            if st.button("🎯", key=f"k_int_{app.id}", help="Interview"):
                                with get_db() as db:
                                    a = db.query(Application).filter(Application.id == app.id).first()
                                    if a:
                                        a.status = ApplicationStatus.INTERVIEW
                                st.rerun()
                        elif status == ApplicationStatus.INTERVIEW:
                            if st.button("🎉", key=f"k_off_{app.id}", help="Offer"):
                                with get_db() as db:
                                    a = db.query(Application).filter(Application.id == app.id).first()
                                    if a:
                                        a.status = ApplicationStatus.OFFER
                                st.rerun()
                    with c2:
                        if st.button("❌", key=f"k_rej_{app.id}", help="Rejected"):
                            with get_db() as db:
                                a = db.query(Application).filter(Application.id == app.id).first()
                                if a:
                                    a.status = ApplicationStatus.REJECTED
                            st.rerun()
                    st.markdown("---")
                if not by_status.get(status):
                    st.caption("No applications")


# ============ STATISTICS ============
elif page == "📊 Statistics":
    st.title("📊 Statistics")
    st.caption("Your job search analytics")

    with get_db() as db:
        apps = db.query(Application).all()
        jobs_30d = db.query(Job).filter(Job.scraped_at >= datetime.utcnow() - timedelta(days=30)).count()

    pipeline = {}
    for app in apps:
        pipeline[app.status.value] = pipeline.get(app.status.value, 0) + 1

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Jobs (30d)", jobs_30d)
    col2.metric("Applied", pipeline.get("applied", 0))
    col3.metric("Interviews", pipeline.get("interview", 0))
    col4.metric("Offers", pipeline.get("offer", 0))

    st.markdown("---")

    # Recommendations
    st.markdown("### 💡 Recommended Actions")
    interested = pipeline.get("interested", 0)
    applied = pipeline.get("applied", 0)
    interviews = pipeline.get("interview", 0)

    if interested > 5 and applied == 0:
        st.error("🔴 **Start applying!** You have saved jobs but no applications yet.")
    elif applied > 0 and applied < 5:
        st.warning("🟡 **Apply more** - Aim for 5-10 applications per week.")
    elif applied >= 5 and interviews == 0:
        st.warning("🟡 **Review your CV** - Applications but no interviews yet.")
    elif interviews > 0:
        st.success("✅ **On track!** Keep applying while waiting for results.")
    else:
        st.info("Start by saving and applying to jobs on the Home page.")


# ============ SETTINGS ============
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")
    st.caption("Manage search keywords and preferences")

    st.markdown("### Search Keywords")
    with get_db() as db:
        keywords = db.query(SearchKeyword).all()

    if keywords:
        for kw in keywords:
            col1, col2 = st.columns([3, 1])
            with col1:
                status = "✅" if kw.is_active else "❌"
                st.write(f"{status} **{kw.keyword}** - {kw.jobs_found or 0} jobs found")
            with col2:
                if st.button("Toggle", key=f"toggle_{kw.id}"):
                    with get_db() as db:
                        k = db.query(SearchKeyword).filter(SearchKeyword.id == kw.id).first()
                        if k:
                            k.is_active = not k.is_active
                    st.rerun()
    else:
        st.info("No keywords configured. Add one below!")

    st.markdown("---")
    st.markdown("### Add Keyword")
    new_kw = st.text_input("New search keyword", placeholder="e.g., Python Developer")
    if st.button("Add Keyword") and new_kw:
        with get_db() as db:
            existing = db.query(SearchKeyword).filter(SearchKeyword.keyword == new_kw).first()
            if not existing:
                db.add(SearchKeyword(keyword=new_kw, is_active=True))
                st.success(f"Added: {new_kw}")
                st.rerun()
            else:
                st.warning("Keyword already exists")

    st.markdown("---")
    st.markdown("### Database")
    with get_db() as db:
        st.caption(f"Total jobs: {db.query(Job).count()}")
        st.caption(f"Total applications: {db.query(Application).count()}")
