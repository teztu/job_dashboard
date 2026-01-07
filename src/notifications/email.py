"""Email notification module."""

import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ..database.db import get_db
from ..database.models import Job

logger = logging.getLogger(__name__)


def get_email_config() -> dict:
    """Get email configuration from environment."""
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "recipient": os.getenv("NOTIFICATION_EMAIL"),
    }


def is_email_configured() -> bool:
    """Check if email is properly configured."""
    config = get_email_config()
    return all([config["user"], config["password"], config["recipient"]])


def send_email(subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
    """Send an email notification.

    Args:
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body (optional, generated from HTML if not provided)

    Returns:
        True if email was sent successfully
    """
    config = get_email_config()

    if not is_email_configured():
        logger.warning("Email not configured. Set SMTP_USER, SMTP_PASSWORD, and NOTIFICATION_EMAIL.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["user"]
        msg["To"] = config["recipient"]

        # Plain text version
        if not body_text:
            # Simple HTML to text conversion
            import re
            body_text = re.sub(r"<[^>]+>", "", body_html)
            body_text = body_text.replace("&nbsp;", " ")

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls()
            server.login(config["user"], config["password"])
            server.send_message(msg)

        logger.info(f"Email sent: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_daily_digest() -> bool:
    """Send daily digest of new jobs.

    Returns:
        True if email was sent successfully
    """
    if not is_email_configured():
        logger.warning("Email not configured, skipping daily digest")
        return False

    # Get jobs from the last 24 hours
    since = datetime.utcnow() - timedelta(days=1)

    with get_db() as db:
        new_jobs = (
            db.query(Job)
            .filter(Job.scraped_at >= since)
            .order_by(Job.scraped_at.desc())
            .all()
        )

    if not new_jobs:
        logger.info("No new jobs to report")
        return True

    # Build email content
    subject = f"Job Hunter: {len(new_jobs)} new jobs found"

    # Group by source
    jobs_by_source = {}
    for job in new_jobs:
        if job.source not in jobs_by_source:
            jobs_by_source[job.source] = []
        jobs_by_source[job.source].append(job)

    # Build HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .job {{ border-left: 3px solid #2563eb; padding-left: 15px; margin: 15px 0; }}
            .job-title {{ font-weight: bold; font-size: 16px; margin-bottom: 5px; }}
            .job-company {{ color: #666; }}
            .job-link {{ color: #2563eb; }}
            .source {{ background: #f3f4f6; padding: 10px; margin-top: 20px; }}
            .footer {{ text-align: center; color: #666; padding: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Job Hunter Daily Digest</h1>
            <p>{len(new_jobs)} new jobs found</p>
        </div>
        <div class="content">
    """

    for source, jobs in jobs_by_source.items():
        source_name = source.capitalize()
        html += f'<div class="source"><h2>{source_name} ({len(jobs)} jobs)</h2></div>'

        for job in jobs[:10]:  # Limit to 10 per source
            html += f"""
            <div class="job">
                <div class="job-title">{job.title}</div>
                <div class="job-company">{job.company or 'Unknown company'} - {job.location or 'Unknown location'}</div>
                <a class="job-link" href="{job.url}">View Job</a>
            </div>
            """

        if len(jobs) > 10:
            html += f'<p>... and {len(jobs) - 10} more jobs</p>'

    html += """
        </div>
        <div class="footer">
            <p>Job Hunter - Built with Claude Code</p>
            <p>Launch your dashboard to see all jobs and track applications.</p>
        </div>
    </body>
    </html>
    """

    return send_email(subject, html)
