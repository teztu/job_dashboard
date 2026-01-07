"""Settings page."""

import os

import streamlit as st

from ...database.db import get_db, init_db
from ...database.models import SearchKeyword


def render():
    """Render the settings page."""
    st.title("⚙️ Settings")

    # Search Keywords
    st.markdown("### Search Keywords")
    st.markdown("Configure the keywords used to search for jobs.")

    with get_db() as db:
        keywords = db.query(SearchKeyword).all()

        if keywords:
            st.markdown("**Current Keywords:**")
            for kw in keywords:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(kw.keyword)
                with col2:
                    st.caption(f"{kw.jobs_found} jobs")
                with col3:
                    if st.button("🗑️", key=f"del_{kw.id}", help="Delete"):
                        db.delete(kw)
                        st.rerun()
        else:
            st.info("No keywords configured. Add some below!")

    # Add new keyword
    st.markdown("**Add Keyword:**")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_keyword = st.text_input("New keyword", placeholder="e.g., Python utvikler", label_visibility="collapsed")
    with col2:
        if st.button("Add", use_container_width=True):
            if new_keyword:
                with get_db() as db:
                    existing = db.query(SearchKeyword).filter(SearchKeyword.keyword == new_keyword).first()
                    if not existing:
                        db.add(SearchKeyword(keyword=new_keyword))
                        st.success(f"Added: {new_keyword}")
                        st.rerun()
                    else:
                        st.warning("Keyword already exists")

    st.markdown("---")

    # Location
    st.markdown("### Search Location")
    current_location = os.getenv("SEARCH_LOCATION", "Oslo")
    st.info(f"Current location: **{current_location}**")
    st.caption("Edit the `.env` file to change the search location")

    st.markdown("---")

    # Email Notifications
    st.markdown("### Email Notifications")

    smtp_configured = bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))

    if smtp_configured:
        st.success("✅ Email notifications are configured")
        notification_email = os.getenv("NOTIFICATION_EMAIL", "Not set")
        st.caption(f"Sending to: {notification_email}")
    else:
        st.warning("⚠️ Email notifications not configured")
        st.caption("Edit the `.env` file to configure SMTP settings")

        with st.expander("How to configure email"):
            st.markdown("""
            1. Copy `.env.example` to `.env`
            2. Fill in your SMTP settings:
               - **SMTP_HOST**: Your email provider's SMTP server (e.g., smtp.gmail.com)
               - **SMTP_PORT**: Usually 587 for TLS
               - **SMTP_USER**: Your email address
               - **SMTP_PASSWORD**: Your app password (not your regular password)
               - **NOTIFICATION_EMAIL**: Where to send notifications

            **For Gmail:**
            - Enable 2-factor authentication
            - Generate an App Password at https://myaccount.google.com/apppasswords
            - Use the App Password as SMTP_PASSWORD
            """)

    st.markdown("---")

    # Database
    st.markdown("### Database")

    with get_db() as db:
        from ...database.models import Job, Application, ScrapingLog

        job_count = db.query(Job).count()
        app_count = db.query(Application).count()
        log_count = db.query(ScrapingLog).count()

    col1, col2, col3 = st.columns(3)
    col1.metric("Jobs", job_count)
    col2.metric("Applications", app_count)
    col3.metric("Scraping Logs", log_count)

    if st.button("🗑️ Clear All Data", type="secondary"):
        if st.checkbox("I understand this will delete all data"):
            from ...database.db import drop_db

            drop_db()
            init_db()
            st.success("Database cleared!")
            st.rerun()

    st.markdown("---")

    # About
    st.markdown("### About")
    st.markdown("""
    **Job Hunter** is an AI-powered job hunting assistant for the Norwegian job market.

    - Automatically scrapes Finn.no and Arbeidsplassen.no
    - Tracks your job applications
    - Provides analytics and insights

    Built with [Claude Code](https://claude.com/claude-code)
    """)
