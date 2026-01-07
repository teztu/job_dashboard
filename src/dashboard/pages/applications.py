"""Application tracking page - Kanban style board."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import datetime

import streamlit as st

from sqlalchemy.orm import joinedload

from src.database.db import get_db
from src.database.models import Job, Application, ApplicationStatus


def render():
    """Render the applications page."""
    st.title("📋 My Applications")
    st.caption("Track your job applications from interested to offer")

    # Get all jobs with applications
    with get_db() as db:
        applications = (
            db.query(Application).options(joinedload(Application.job))
            .order_by(Application.updated_at.desc())
            .all()
        )

        # Group by status
        by_status = {}
        for status in ApplicationStatus:
            by_status[status] = [a for a in applications if a.status == status]

    # Check if empty
    if len(applications) == 0:
        st.info("""
        **No saved jobs yet!**

        Go to **Browse Jobs** and click the **⭐ Interested** button to save jobs you want to apply for.

        Your saved jobs will appear here so you can track your application progress.
        """)
        return

    # Pipeline stats
    st.markdown("### Pipeline Overview")
    cols = st.columns(len(ApplicationStatus))

    status_labels = {
        ApplicationStatus.NEW: ("🆕", "New"),
        ApplicationStatus.INTERESTED: ("⭐", "Interested"),
        ApplicationStatus.APPLIED: ("📤", "Applied"),
        ApplicationStatus.INTERVIEW: ("🎯", "Interview"),
        ApplicationStatus.OFFER: ("🎉", "Offer"),
        ApplicationStatus.REJECTED: ("❌", "Rejected"),
        ApplicationStatus.WITHDRAWN: ("↩️", "Withdrawn"),
    }

    for i, status in enumerate(ApplicationStatus):
        emoji, label = status_labels[status]
        count = len(by_status[status])
        cols[i].metric(f"{emoji} {label}", count)

    st.markdown("---")

    # Kanban board - show main stages
    st.markdown("### Active Applications")

    # Filter to show only active statuses
    active_statuses = [
        ApplicationStatus.INTERESTED,
        ApplicationStatus.APPLIED,
        ApplicationStatus.INTERVIEW,
    ]

    cols = st.columns(len(active_statuses))

    for i, status in enumerate(active_statuses):
        emoji, label = status_labels[status]
        apps = by_status[status]

        with cols[i]:
            st.markdown(f"#### {emoji} {label} ({len(apps)})")

            for app in apps:
                with st.container():
                    st.markdown(f"**{app.job.title}**")
                    st.caption(app.job.company if app.job.company else "Company not listed")

                    if app.applied_date:
                        days_ago = (datetime.utcnow() - app.applied_date).days
                        st.caption(f"Applied {days_ago} days ago")

                    # Action buttons
                    col1, col2 = st.columns(2)

                    with col1:
                        if status == ApplicationStatus.INTERESTED:
                            if st.button("📤", key=f"to_app_{app.id}", help="Mark as Applied"):
                                _update_status(app.id, ApplicationStatus.APPLIED)
                                st.rerun()
                        elif status == ApplicationStatus.APPLIED:
                            if st.button("🎯", key=f"to_int_{app.id}", help="Got Interview"):
                                _update_status(app.id, ApplicationStatus.INTERVIEW)
                                st.rerun()
                        elif status == ApplicationStatus.INTERVIEW:
                            if st.button("🎉", key=f"to_off_{app.id}", help="Got Offer"):
                                _update_status(app.id, ApplicationStatus.OFFER)
                                st.rerun()

                    with col2:
                        if st.button("❌", key=f"to_rej_{app.id}", help="Rejected"):
                            _update_status(app.id, ApplicationStatus.REJECTED)
                            st.rerun()

                    st.markdown("---")

            if not apps:
                st.info("No applications")

    # Notes section
    st.markdown("---")
    st.markdown("### Application Notes")

    # Select an application to add notes
    all_active = []
    for status in active_statuses:
        all_active.extend(by_status[status])

    if all_active:
        selected_app = st.selectbox(
            "Select application",
            options=all_active,
            format_func=lambda a: f"{a.job.title} @ {a.job.company or 'Unknown'}",
        )

        if selected_app:
            st.markdown(f"**{selected_app.job.title}** at {selected_app.job.company}")

            # Display existing notes
            if selected_app.notes:
                st.text_area("Existing Notes", selected_app.notes, disabled=True, height=150)

            # Add new note
            new_note = st.text_input("Add note")
            if st.button("Add Note") and new_note:
                _add_note(selected_app.id, new_note)
                st.success("Note added!")
                st.rerun()
    else:
        st.info("Mark some jobs as 'Interested' to start tracking them here.")


def _update_status(app_id: int, status: ApplicationStatus):
    """Update application status."""
    with get_db() as db:
        app = db.query(Application).filter(Application.id == app_id).first()
        if app:
            app.status = status
            app.updated_at = datetime.utcnow()
            if status == ApplicationStatus.APPLIED and not app.applied_date:
                app.applied_date = datetime.utcnow()


def _add_note(app_id: int, note: str):
    """Add a note to an application."""
    with get_db() as db:
        app = db.query(Application).filter(Application.id == app_id).first()
        if app:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            new_note = f"[{timestamp}] {note}"
            if app.notes:
                app.notes = app.notes + chr(10) + chr(10) + new_note
            else:
                app.notes = new_note
