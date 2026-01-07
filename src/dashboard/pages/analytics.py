"""Analytics and insights page."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.keywords import get_keyword_effectiveness, get_keyword_recommendations
from src.analytics.stats import (
    get_application_pipeline,
    get_jobs_by_company,
    get_jobs_by_source,
    get_jobs_dataframe,
    get_jobs_over_time,
)


def render():
    """Render the analytics page."""
    st.title("📊 Statistics")
    st.caption("Track your job search progress and get recommendations")

    # Time period selector
    days = st.selectbox(
        "Analysis period",
        options=[7, 14, 30, 90],
        index=2,
        format_func=lambda x: f"Last {x} days",
    )

    # Overview metrics
    st.markdown("### Overview")

    df = get_jobs_dataframe(days)

    col1, col2, col3, col4 = st.columns(4)

    total_jobs = len(df)
    col1.metric("Total Jobs", total_jobs)

    unique_companies = df["company"].nunique() if not df.empty else 0
    col2.metric("Unique Companies", unique_companies)

    pipeline = get_application_pipeline()
    total_applied = sum(pipeline.get(s, 0) for s in ["applied", "interview", "offer"])
    col3.metric("Applications Sent", total_applied)

    interview_rate = (pipeline.get("interview", 0) + pipeline.get("offer", 0)) / total_applied * 100 if total_applied > 0 else 0
    col4.metric("Interview Rate", f"{interview_rate:.0f}%")

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Jobs by Source")
        source_data = get_jobs_by_source(days)
        if source_data:
            fig = px.pie(
                values=list(source_data.values()),
                names=list(source_data.keys()),
                hole=0.4,
            )
            fig.update_layout(showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")

    with col2:
        st.markdown("### Jobs Over Time")
        time_data = get_jobs_over_time(days)
        if not time_data.empty:
            fig = px.bar(time_data, x="date", y="count")
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Jobs Found",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")

    st.markdown("---")

    # Top Companies
    st.markdown("### Top Hiring Companies")
    company_data = get_jobs_by_company(days, top_n=10)
    if company_data:
        fig = px.bar(
            x=list(company_data.values()),
            y=list(company_data.keys()),
            orientation="h",
        )
        fig.update_layout(
            xaxis_title="Number of Jobs",
            yaxis_title="Company",
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No company data available")

    st.markdown("---")

    # Application Pipeline
    st.markdown("### Application Pipeline")
    pipeline = get_application_pipeline()

    if sum(pipeline.values()) > 0:
        # Create funnel chart
        stages = ["new", "interested", "applied", "interview", "offer"]
        values = [pipeline.get(s, 0) for s in stages]
        labels = ["New", "Interested", "Applied", "Interview", "Offer"]

        fig = go.Figure(go.Funnel(
            y=labels,
            x=values,
            textinfo="value+percent initial",
        ))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No application data yet. Start marking jobs as 'Interested' to track your pipeline.")

    st.markdown("---")

    # Keyword Analysis
    st.markdown("### Keyword Performance")

    keyword_data = get_keyword_effectiveness()
    if keyword_data:
        # Create comparison table
        st.dataframe(
            keyword_data,
            column_config={
                "keyword": "Search Keyword",
                "total_jobs": "Total Jobs",
                "recent_jobs": "This Week",
                "unique_companies": "Companies",
                "weekly_rate": st.column_config.NumberColumn("Daily Avg", format="%.1f"),
                "last_searched": st.column_config.DatetimeColumn("Last Searched"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Recommendations
        recommendations = get_keyword_recommendations()
        if recommendations:
            st.markdown("#### Recommendations")
            for rec in recommendations:
                if rec["action"] == "modify":
                    st.warning(f"🔄 **{rec['keyword']}**: {rec['reason']}")
                    if rec["suggestions"]:
                        st.caption(f"Try: {', '.join(rec['suggestions'])}")
                elif rec["action"] == "specialize":
                    st.info(f"🎯 **{rec['keyword']}**: {rec['reason']}")
                    if rec["suggestions"]:
                        st.caption(f"Consider: {', '.join(rec['suggestions'])}")
    else:
        st.info("Run a scrape to see keyword analytics")

    st.markdown("---")

    # Recommended Actions based on pipeline
    st.markdown("### 💡 Recommended Actions")

    pipeline = get_application_pipeline()
    interested = pipeline.get("interested", 0)
    applied = pipeline.get("applied", 0)
    interviews = pipeline.get("interview", 0)
    offers = pipeline.get("offer", 0)
    rejected = pipeline.get("rejected", 0)

    actions = []

    # Generate recommendations based on pipeline status
    if interested == 0 and applied == 0:
        actions.append({
            "priority": "high",
            "action": "Start saving jobs",
            "detail": "Browse jobs and click ⭐ to save interesting positions. Aim for 10-20 saved jobs to start."
        })
    elif interested > 5 and applied == 0:
        actions.append({
            "priority": "high",
            "action": "Start applying!",
            "detail": f"You have {interested} saved jobs but no applications. Pick your top 3 and apply today."
        })
    elif applied > 0 and applied < 5:
        actions.append({
            "priority": "medium",
            "action": "Increase application volume",
            "detail": f"Only {applied} applications sent. Aim for 5-10 per week for best results."
        })

    if applied >= 5 and interviews == 0:
        actions.append({
            "priority": "high",
            "action": "Review your CV and cover letter",
            "detail": f"{applied} applications but no interviews. Your application materials may need improvement."
        })
    elif applied >= 10 and interviews == 0:
        actions.append({
            "priority": "high",
            "action": "Get feedback on applications",
            "detail": "Consider having someone review your CV or try different job types."
        })

    if interviews > 0 and offers == 0 and rejected >= interviews:
        actions.append({
            "priority": "medium",
            "action": "Practice interview skills",
            "detail": "Interviews but no offers. Practice common questions and prepare better examples."
        })

    if rejected > applied * 0.8 and applied > 5:
        actions.append({
            "priority": "medium",
            "action": "Adjust your target roles",
            "detail": "High rejection rate. Consider if you are applying for roles that match your experience level."
        })

    if interested > 10:
        actions.append({
            "priority": "low",
            "action": "Review saved jobs",
            "detail": f"{interested} jobs saved. Go through them and apply to the best matches or remove outdated ones."
        })

    if not actions:
        if offers > 0:
            st.success("🎉 **Congratulations!** You have offers on the table. Good luck with your decision!")
        elif interviews > 0:
            st.info("✅ **On track!** You have interviews scheduled. Keep applying while you wait for results.")
        elif applied > 0:
            st.info("✅ **Good progress!** Keep applying and follow up on sent applications after 1 week.")
        else:
            st.info("Start by browsing jobs and saving ones that interest you.")
    else:
        for action in actions:
            if action["priority"] == "high":
                st.error(f"🔴 **{action['action']}** - {action['detail']}")
            elif action["priority"] == "medium":
                st.warning(f"🟡 **{action['action']}** - {action['detail']}")
            else:
                st.info(f"🔵 **{action['action']}** - {action['detail']}")
