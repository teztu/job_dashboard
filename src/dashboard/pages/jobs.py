"""Jobs browser page."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta

import streamlit as st
from sqlalchemy.orm import joinedload

from src.analytics.recommendations import get_top_recommendations
from src.database.db import get_db
from src.database.models import Application, ApplicationStatus, Job


def _get_suggested_keywords():
    """Get keyword suggestions based on jobs user has applied to."""
    from collections import Counter
    with get_db() as db:
        # Get jobs user has shown interest in
        apps = db.query(Application).options(joinedload(Application.job)).filter(
            Application.status.in_([
                ApplicationStatus.INTERESTED,
                ApplicationStatus.APPLIED,
                ApplicationStatus.INTERVIEW,
                ApplicationStatus.OFFER
            ])
        ).all()

        if not apps:
            return []

        # Extract words from job titles
        words = []
        stopwords = {"and", "or", "the", "a", "an", "in", "at", "for", "to", "of", "med", "og", "i", "-", "/"}
        for app in apps:
            title_words = app.job.title.lower().split()
            for word in title_words:
                word = word.strip(".,()[]:-/")
                if len(word) > 2 and word not in stopwords:
                    words.append(word)

        # Get most common words not in current search keywords
        current_keywords = {"python", "junior", "utvikler", "developer", "backend", "data", "ml", "machine", "learning"}
        counter = Counter(words)
        suggestions = []
        for word, count in counter.most_common(10):
            if word not in current_keywords and count >= 2:
                suggestions.append(word.title())

        return suggestions[:5]


def _get_clean_company(company):
    """Get clean company name, filtering out garbage data."""
    if not company:
        return "Company not available"

    # Filter out known garbage strings from scraping
    garbage = ["favoritt", "legg til", "lagre", "saved", "publisert"]
    if any(g in company.lower() for g in garbage):
        return "Company not available"

    return company


def render():
    """Render the jobs page."""
    st.title("🔍 Job Browser")

    # Daily Recommendations
    with st.expander("💡 **Top 5 Recommended Jobs for You** - Based on your profile", expanded=True):
        recs = get_top_recommendations(5)
        if recs:
            for i, rec in enumerate(recs):
                job = rec["job"]
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    reasons = " • ".join(rec["reasons"]) if rec["reasons"] else "Good match"
                    company = _get_clean_company(job.company)
                    st.markdown(f"**{i+1}. {job.title}** @ {company}")
                    st.caption(f"{rec['match_percentage']}% match - {reasons}")

                with col2:
                    if st.button("⭐", key=f"rec_int_{job.id}", help="Mark Interested", use_container_width=True):
                        _update_status(job.id, ApplicationStatus.INTERESTED)
                        st.rerun()

                with col3:
                    st.link_button("View", job.url, use_container_width=True)
        else:
            st.info("No recommendations available. Run a scrape to find jobs!")

    st.markdown("")

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
            format_func=lambda x: {"All": "All Sources", "finn": "🔵 Finn.no", "arbeidsplassen": "🟢 NAV"}.get(x, x),
        )

    with col3:
        keyword_filter = st.text_input("Search keyword", placeholder="e.g., Python")

    with col4:
        status_filter = st.selectbox(
            "Application Status",
            options=["All", "Not Applied", "Interested", "Applied", "Interview"],
        )

    # Suggested keywords based on applied jobs
    suggested = _get_suggested_keywords()
    if suggested:
        st.markdown("**💡 Suggested keywords** (based on your interests):")
        cols = st.columns(len(suggested))
        for i, kw in enumerate(suggested):
            with cols[i]:
                if st.button(kw, key=f"sugg_{kw}", use_container_width=True):
                    st.session_state["keyword_filter"] = kw
                    st.rerun()

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

                # Source icon
                source_icon = "🔵" if job.source == "finn" else "🟢"

                st.markdown(f"### {status_badge} {job.title}")
                company = _get_clean_company(job.company)
                st.markdown(f"**{company}** • {job.location or 'Oslo'}")

                if job.posted_date:
                    st.caption(f"Posted: {job.posted_date.strftime('%Y-%m-%d')} • {source_icon} {job.source.title()}")
                else:
                    st.caption(f"Scraped: {job.scraped_at.strftime('%Y-%m-%d %H:%M')} • {source_icon} {job.source.title()}")

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
