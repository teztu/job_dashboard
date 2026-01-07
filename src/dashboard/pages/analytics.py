"""Analytics and insights page."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.analytics.stats import (
    get_jobs_dataframe,
    get_jobs_by_source,
    get_jobs_by_company,
    get_jobs_over_time,
    get_keyword_stats,
    get_application_pipeline,
)
from src.analytics.keywords import get_keyword_effectiveness, get_keyword_recommendations


def render():
    """Render the analytics page."""
    st.title("📊 Analytics & Insights")

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
