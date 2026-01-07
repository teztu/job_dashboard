"""Job recommendation engine based on profile matching."""

from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload

from src.database.db import get_db
from src.database.models import ApplicationStatus, Job

# Your profile skills (extracted from CV)
PROFILE_SKILLS = {
    # Core skills (high weight)
    "python": 10,
    "sql": 8,
    "data": 7,
    "backend": 7,
    "api": 6,

    # Frameworks/tools
    "fastapi": 8,
    "pandas": 6,
    "machine learning": 8,
    "ml": 8,
    "sqlalchemy": 5,
    "streamlit": 5,

    # General IT
    "utvikler": 5,  # developer in Norwegian
    "developer": 5,
    "junior": 6,  # Good match for entry-level
    "analyst": 6,
    "analytiker": 6,

    # Languages
    "norwegian": 3,
    "english": 3,
}

# Negative keywords (jobs to avoid)
NEGATIVE_KEYWORDS = {
    "senior": -5,
    "lead": -3,
    "manager": -3,
    "10+ years": -8,
    "5+ years": -5,
}


def score_job(job: Job) -> int:
    """Score a job based on profile match.

    Higher score = better match.
    """
    score = 0

    # Combine title and description for matching
    text = f"{job.title or ''} {job.description or ''} {job.company or ''}".lower()

    # Check positive keywords
    for keyword, weight in PROFILE_SKILLS.items():
        if keyword.lower() in text:
            score += weight

    # Check negative keywords
    for keyword, weight in NEGATIVE_KEYWORDS.items():
        if keyword.lower() in text:
            score += weight  # weight is already negative

    # Bonus for Oslo location
    if job.location and "oslo" in job.location.lower():
        score += 3

    # Bonus for recent jobs (prefer fresh listings)
    if job.posted_date:
        days_old = (datetime.utcnow() - job.posted_date).days
        if days_old <= 3:
            score += 5
        elif days_old <= 7:
            score += 3
        elif days_old <= 14:
            score += 1

    return score


def get_daily_recommendation() -> dict | None:
    """Get the top recommended job for today.

    Returns dict with job info and match score, or None if no jobs.
    """
    with get_db() as db:
        # Get jobs from last 14 days that haven't been applied to
        since = datetime.utcnow() - timedelta(days=14)

        jobs = (
            db.query(Job)
            .options(joinedload(Job.application))
            .filter(Job.scraped_at >= since)
            .all()
        )

        # Filter out jobs already marked as interested/applied
        available_jobs = [
            j for j in jobs
            if not j.application or j.application.status == ApplicationStatus.NEW
        ]

        if not available_jobs:
            return None

        # Score all jobs
        scored_jobs = [(job, score_job(job)) for job in available_jobs]

        # Sort by score (highest first)
        scored_jobs.sort(key=lambda x: x[1], reverse=True)

        # Get top job
        top_job, top_score = scored_jobs[0]

        # Calculate match percentage (rough estimate)
        max_possible_score = sum(PROFILE_SKILLS.values()) + 8  # +8 for location and freshness
        match_pct = min(100, int((top_score / max_possible_score) * 100))

        return {
            "job": top_job,
            "score": top_score,
            "match_percentage": match_pct,
            "reasons": _get_match_reasons(top_job),
        }


def _get_match_reasons(job: Job) -> list[str]:
    """Get human-readable reasons why this job matches."""
    reasons = []
    text = f"{job.title or ''} {job.description or ''}".lower()

    if "python" in text:
        reasons.append("Python skills match")
    if "junior" in text or "entry" in text:
        reasons.append("Entry-level position")
    if "data" in text:
        reasons.append("Data-related role")
    if "backend" in text or "api" in text:
        reasons.append("Backend/API development")
    if "machine learning" in text or "ml" in text:
        reasons.append("Machine Learning focus")
    if job.location and "oslo" in job.location.lower():
        reasons.append("Located in Oslo")

    return reasons[:3]  # Return top 3 reasons


def get_top_recommendations(n: int = 5) -> list[dict]:
    """Get top N recommended jobs."""
    with get_db() as db:
        since = datetime.utcnow() - timedelta(days=14)

        jobs = (
            db.query(Job)
            .options(joinedload(Job.application))
            .filter(Job.scraped_at >= since)
            .all()
        )

        available_jobs = [
            j for j in jobs
            if not j.application or j.application.status == ApplicationStatus.NEW
        ]

        if not available_jobs:
            return []

        scored_jobs = [(job, score_job(job)) for job in available_jobs]
        scored_jobs.sort(key=lambda x: x[1], reverse=True)

        max_possible = sum(PROFILE_SKILLS.values()) + 8

        return [
            {
                "job": job,
                "score": score,
                "match_percentage": min(100, int((score / max_possible) * 100)),
                "reasons": _get_match_reasons(job),
            }
            for job, score in scored_jobs[:n]
        ]
