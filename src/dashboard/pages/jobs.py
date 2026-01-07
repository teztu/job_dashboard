"""Jobs browser page."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from sqlalchemy.orm import joinedload

from src.database.db import get_db
from src.database.models import Job, Application, ApplicationStatus


def render():
    """Render the jobs page."""
    st.title("🔍 Job Browser")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

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
        )

    with col3:
        keyword_filter = st.text_input("Search keyword", placeholder="e.g., Python")

    with col4:
        status_filter = st.selectbox(
            "Application Status",
            options=["All", "Not Applied", "Interested", "Applied", "Interview"],
        )

    # Query jobs
    with get_db() as db:
        query = db.query(Job).options(joinedload(Job.application))

        # Apply filters
        since = datetime.utcnow() - timedelta(days=days_filter)
        query = query.filter(Job.scraped_at >= since)

        if source_filter != "All":
            query = query.filter(Job.source == source_filter)

        if keyword_filter:
            query = query.filter(
                (Job.title.ilike(f"%{keyword_filter}%")) |
                (Job.company.ilike(f"%{keyword_filter}%")) |
                (Job.search_keyword.ilike(f"%{keyword_filter}%"))
            )

        # Order by newest first
        jobs = query.order_by(Job.scraped_at.desc()).all()

        # Filter by application status
        if status_filter == "Not Applied":
            jobs = [j for j in jobs if not j.application or j.application.status == ApplicationStatus.NEW]
        elif status_filter == "Interested":
            jobs = [j for j in jobs if j.application and j.application.status == ApplicationStatus.INTERESTED]
        elif status_filter == "Applied":
            jobs = [j for j in jobs if j.application and j.application.status == ApplicationStatus.APPLIED]
        elif status_filter == "Interview":
            jobs = [j for j in jobs if j.application and j.application.status == ApplicationStatus.INTERVIEW]

    # Stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jobs", len(jobs))

    new_today = len([j for j in jobs if j.scraped_at and j.scraped_at.date() == datetime.utcnow().date()])
    col2.metric("New Today", new_today)

    applied = len([j for j in jobs if j.application and j.application.status != ApplicationStatus.NEW])
    col3.metric("With Status", applied)

    st.markdown("---")

    # Display jobs
    if not jobs:
        st.info("No jobs found matching your criteria. Try adjusting the filters or running a scrape.")
        return

    for job in jobs:
        with st.container():
            # Job card
            col1, col2 = st.columns([4, 1])

            with col1:
                # Status badge
                status_badge = ""
                if job.application:
                    status_colors = {
                        ApplicationStatus.NEW: "🆕",
                        ApplicationStatus.INTERESTED: "⭐",
                        ApplicationStatus.APPLIED: "📤",
                        ApplicationStatus.INTERVIEW: "🎯",
                        ApplicationStatus.OFFER: "🎉",
                        ApplicationStatus.REJECTED: "❌",
                        ApplicationStatus.WITHDRAWN: "↩️",
                    }
                    status_badge = status_colors.get(job.application.status, "")

                st.markdown(f"### {status_badge} {job.title}")
                st.markdown(f"**{job.company or 'Unknown Company'}** • {job.location or 'Unknown Location'}")

                if job.posted_date:
                    st.caption(f"Posted: {job.posted_date.strftime('%Y-%m-%d')} • Source: {job.source}")
                else:
                    st.caption(f"Scraped: {job.scraped_at.strftime('%Y-%m-%d %H:%M')} • Source: {job.source}")

            with col2:
                st.link_button("View Job", job.url, use_container_width=True)

                # Quick status buttons
                current_status = job.application.status if job.application else None

                if current_status != ApplicationStatus.INTERESTED:
                    if st.button("⭐ Interested", key=f"int_{job.id}", use_container_width=True):
                        _update_status(job.id, ApplicationStatus.INTERESTED)
                        st.rerun()

                if current_status != ApplicationStatus.APPLIED:
                    if st.button("📤 Applied", key=f"app_{job.id}", use_container_width=True):
                        _update_status(job.id, ApplicationStatus.APPLIED)
                        st.rerun()

            st.markdown("---")


def _update_status(job_id: int, status: ApplicationStatus):
    """Update application status for a job."""
    with get_db() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            if not job.application:
                job.application = Application(job_id=job_id)
                db.add(job.application)

            job.application.status = status
            if status == ApplicationStatus.APPLIED:
                job.application.applied_date = datetime.utcnow()
