"""Job market statistics and analytics."""

from collections import Counter
from datetime import datetime, timedelta

import pandas as pd

from ..database.db import get_db
from ..database.models import Application, ApplicationStatus, Job, SearchKeyword


def get_jobs_dataframe(days: int | None = None) -> pd.DataFrame:
    """Get jobs as a pandas DataFrame.

    Args:
        days: If specified, only return jobs from the last N days

    Returns:
        DataFrame with job data
    """
    with get_db() as db:
        query = db.query(Job)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Job.scraped_at >= since)

        jobs = query.all()

        data = []
        for job in jobs:
            data.append({
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "source": job.source,
                "url": job.url,
                "posted_date": job.posted_date,
                "scraped_at": job.scraped_at,
                "search_keyword": job.search_keyword,
                "has_application": job.application is not None,
                "application_status": job.application.status.value if job.application else None,
            })

        return pd.DataFrame(data)


def get_jobs_by_source(days: int | None = None) -> dict[str, int]:
    """Get job counts by source.

    Args:
        days: If specified, only count jobs from the last N days

    Returns:
        Dictionary mapping source name to job count
    """
    df = get_jobs_dataframe(days)
    if df.empty:
        return {}
    return df["source"].value_counts().to_dict()


def get_jobs_by_company(days: int | None = None, top_n: int = 10) -> dict[str, int]:
    """Get top companies by job count.

    Args:
        days: If specified, only count jobs from the last N days
        top_n: Number of top companies to return

    Returns:
        Dictionary mapping company name to job count
    """
    df = get_jobs_dataframe(days)
    if df.empty:
        return {}

    # Filter out unknown companies
    df = df[df["company"].notna() & (df["company"] != "")]
    return df["company"].value_counts().head(top_n).to_dict()


def get_jobs_over_time(days: int = 30) -> pd.DataFrame:
    """Get daily job counts over time.

    Args:
        days: Number of days to look back

    Returns:
        DataFrame with date and job count columns
    """
    df = get_jobs_dataframe(days)
    if df.empty:
        return pd.DataFrame(columns=["date", "count"])

    df["date"] = pd.to_datetime(df["scraped_at"]).dt.date
    daily_counts = df.groupby("date").size().reset_index(name="count")
    return daily_counts


def get_keyword_stats() -> list[dict]:
    """Get statistics for all search keywords.

    Returns:
        List of dictionaries with keyword statistics
    """
    with get_db() as db:
        keywords = db.query(SearchKeyword).filter(SearchKeyword.is_active == True).all()

        stats = []
        for kw in keywords:
            # Count jobs found with this keyword
            jobs_count = db.query(Job).filter(Job.search_keyword == kw.keyword).count()

            # Count applications for jobs found with this keyword
            applications = (
                db.query(Application)
                .join(Job)
                .filter(Job.search_keyword == kw.keyword)
            )

            applied_count = applications.filter(
                Application.status.in_([
                    ApplicationStatus.APPLIED,
                    ApplicationStatus.INTERVIEW,
                    ApplicationStatus.OFFER,
                ])
            ).count()

            interview_count = applications.filter(
                Application.status.in_([
                    ApplicationStatus.INTERVIEW,
                    ApplicationStatus.OFFER,
                ])
            ).count()

            stats.append({
                "keyword": kw.keyword,
                "jobs_found": jobs_count,
                "applications_sent": applied_count,
                "interviews": interview_count,
                "last_searched": kw.last_searched,
                "success_rate": interview_count / applied_count if applied_count > 0 else 0,
            })

        return sorted(stats, key=lambda x: x["jobs_found"], reverse=True)


def get_application_pipeline() -> dict[str, int]:
    """Get application counts by status.

    Returns:
        Dictionary mapping status to count
    """
    with get_db() as db:
        pipeline = {}
        for status in ApplicationStatus:
            count = db.query(Application).filter(Application.status == status).count()
            pipeline[status.value] = count
        return pipeline


def get_common_skills(days: int | None = None, top_n: int = 20) -> dict[str, int]:
    """Extract common skills/keywords from job descriptions.

    Args:
        days: If specified, only analyze jobs from the last N days
        top_n: Number of top skills to return

    Returns:
        Dictionary mapping skill to frequency
    """
    df = get_jobs_dataframe(days)
    if df.empty:
        return {}

    # Common tech skills to look for
    skills_to_find = [
        "python", "java", "javascript", "typescript", "react", "node",
        "sql", "postgresql", "mongodb", "aws", "azure", "docker",
        "kubernetes", "git", "agile", "scrum", "api", "rest",
        "machine learning", "data science", "devops", "ci/cd",
        "fastapi", "django", "flask", "pandas", "numpy",
    ]

    # Note: This is a simplified version. Real implementation would use NLP
    # For now, we just count keyword occurrences in titles

    skill_counts = Counter()
    for title in df["title"].dropna():
        title_lower = title.lower()
        for skill in skills_to_find:
            if skill in title_lower:
                skill_counts[skill] += 1

    return dict(skill_counts.most_common(top_n))
