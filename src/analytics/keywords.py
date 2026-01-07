"""Keyword analysis and recommendations."""

from datetime import datetime, timedelta

from ..database.db import get_db
from ..database.models import Job, SearchKeyword


def get_keyword_effectiveness() -> list[dict]:
    """Analyze effectiveness of search keywords.

    Returns:
        List of dictionaries with keyword effectiveness data
    """
    with get_db() as db:
        keywords = db.query(SearchKeyword).filter(SearchKeyword.is_active == True).all()

        results = []
        for kw in keywords:
            # Jobs found in total
            total_jobs = db.query(Job).filter(Job.search_keyword == kw.keyword).count()

            # Jobs found in last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_jobs = (
                db.query(Job)
                .filter(Job.search_keyword == kw.keyword)
                .filter(Job.scraped_at >= week_ago)
                .count()
            )

            # Unique companies
            unique_companies = (
                db.query(Job.company)
                .filter(Job.search_keyword == kw.keyword)
                .filter(Job.company.isnot(None))
                .distinct()
                .count()
            )

            results.append({
                "keyword": kw.keyword,
                "total_jobs": total_jobs,
                "recent_jobs": recent_jobs,
                "unique_companies": unique_companies,
                "weekly_rate": recent_jobs / 7 if recent_jobs > 0 else 0,
                "last_searched": kw.last_searched,
            })

        # Sort by recent jobs (most active keywords first)
        return sorted(results, key=lambda x: x["recent_jobs"], reverse=True)


def suggest_related_keywords(existing_keyword: str) -> list[str]:
    """Suggest related keywords based on job titles.

    Args:
        existing_keyword: A keyword that's already being used

    Returns:
        List of suggested related keywords
    """
    # Mapping of keywords to related terms (Norwegian job market specific)
    related_terms = {
        "python": ["django", "fastapi", "flask", "data scientist", "backend utvikler"],
        "utvikler": ["developer", "programmerer", "software engineer"],
        "backend": ["fullstack", "api", "server", "database"],
        "frontend": ["react", "vue", "angular", "ui/ux"],
        "data": ["analytics", "bi", "machine learning", "statistikk"],
        "junior": ["trainee", "graduate", "nyutdannet"],
        "konsulent": ["rådgiver", "consultant", "specialist"],
    }

    keyword_lower = existing_keyword.lower()
    suggestions = []

    for key, values in related_terms.items():
        if key in keyword_lower:
            suggestions.extend(values)
        for value in values:
            if value in keyword_lower:
                suggestions.append(key)
                suggestions.extend([v for v in values if v != value])

    # Remove duplicates and the original keyword
    suggestions = list(set(suggestions))
    if keyword_lower in suggestions:
        suggestions.remove(keyword_lower)

    return suggestions[:5]  # Return top 5 suggestions


def get_underperforming_keywords(threshold: int = 5) -> list[str]:
    """Find keywords that aren't finding many jobs.

    Args:
        threshold: Minimum jobs expected in last 7 days

    Returns:
        List of underperforming keyword names
    """
    effectiveness = get_keyword_effectiveness()
    return [
        kw["keyword"]
        for kw in effectiveness
        if kw["recent_jobs"] < threshold
    ]


def get_keyword_recommendations() -> list[dict]:
    """Get keyword recommendations based on analysis.

    Returns:
        List of recommendation dictionaries with action and reason
    """
    recommendations = []
    effectiveness = get_keyword_effectiveness()

    for kw_data in effectiveness:
        keyword = kw_data["keyword"]

        # Underperforming keyword
        if kw_data["recent_jobs"] < 3:
            suggestions = suggest_related_keywords(keyword)
            if suggestions:
                recommendations.append({
                    "keyword": keyword,
                    "action": "modify",
                    "reason": f"Only {kw_data['recent_jobs']} jobs this week",
                    "suggestions": suggestions,
                })

        # Well-performing keyword
        elif kw_data["recent_jobs"] > 20:
            recommendations.append({
                "keyword": keyword,
                "action": "specialize",
                "reason": f"High volume ({kw_data['recent_jobs']} jobs) - consider more specific terms",
                "suggestions": suggest_related_keywords(keyword),
            })

    return recommendations
