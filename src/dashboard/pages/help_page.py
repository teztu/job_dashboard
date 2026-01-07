"""Help page with FAQ and Getting Started guide."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st


def render():
    """Render the help page."""
    st.title("❓ Help & Getting Started")
    
    # Getting Started
    st.markdown("## 🚀 How to Use Job Hunter")
    
    with st.expander("**Step 1: Browse Jobs**", expanded=True):
        st.markdown("""
        The **Browse Jobs** page shows all scraped job listings from Finn.no and Arbeidsplassen.no.
        
        - Use filters to narrow down by time period, source, or keywords
        - **Top 5 Recommended** jobs are shown based on your profile match
        - Click **⭐ Interested** to save jobs you want to apply for
        - Click **📤 Applied** after you have applied
        """)
    
    with st.expander("**Step 2: Track Applications**"):
        st.markdown("""
        The **My Applications** page shows all jobs you have saved or applied to.
        
        **Status Pipeline:**
        - ⭐ **Interested** - Jobs you want to apply for
        - 📤 **Applied** - Jobs you have applied to (with date)
        - 🎯 **Interview** - You got an interview!
        - 🎉 **Offer** - You received an offer
        - ❌ **Rejected** - Application was rejected
        
        Move jobs through stages by clicking the status buttons.
        Add notes to track follow-ups and interview details.
        """)
    
    with st.expander("**Step 3: Analyze Your Search**"):
        st.markdown("""
        The **Statistics** page shows insights about your job search:
        
        - **Application funnel** - See conversion rates at each stage
        - **Weekly activity** - Track how many jobs you are applying to
        - **Top companies** - See who is hiring most
        - **Recommendations** - Get tips to improve your job search
        """)
    
    with st.expander("**Step 4: Configure Settings**"):
        st.markdown("""
        In **Settings** you can:
        
        - Add or remove search keywords
        - View database statistics
        - Configure email notifications (coming soon)
        """)
    
    st.markdown("---")
    
    # FAQ
    st.markdown("## ❓ Frequently Asked Questions")
    
    with st.expander("How do I get new jobs?"):
        st.markdown("""
        Run the scraper from command line:
        Searching in Oslo for: Junior utvikler, Python utvikler, Backend utvikler, Dataanalytiker

--- Scraping Finn.no ---
  'Junior utvikler': 51 found, 8 new
  'Python utvikler': 51 found, 1 new
  'Backend utvikler': 51 found, 1 new
  'Dataanalytiker': 51 found, 1 new

--- Scraping Arbeidsplassen.no ---
  'Junior utvikler': 18 found, 0 new
  'Python utvikler': 112 found, 0 new
  'Backend utvikler': 121 found, 0 new
  'Dataanalytiker': 23 found, 0 new

=== Total: 478 jobs found, 11 new ===
        
        Or set up GitHub Actions for automatic daily scraping.
        """)
    
    with st.expander("Why are some companies showing as 'Not listed'?"):
        st.markdown("""
        Some job listings do not include the company name directly.
        This can happen when:
        - The company uses a recruitment agency
        - The listing is anonymous
        - The scraper could not extract the company name
        
        Click "View" to see the full job listing with company details.
        """)
    
    with st.expander("How does the job matching work?"):
        st.markdown("""
        Jobs are scored based on keyword matching against your profile:
        
        **High match keywords:**
        - Python, SQL, Data, Backend, API, FastAPI
        - Machine Learning, Junior, Developer
        
        **Bonus points:**
        - Oslo location
        - Recently posted jobs
        
        **Lower priority:**
        - Senior/Lead positions (you are looking for junior roles)
        
        The match percentage shows how well a job fits your profile.
        """)
    
    with st.expander("How do I track my application progress?"):
        st.markdown("""
        1. Find a job in **Browse Jobs**
        2. Click **⭐ Interested** to save it
        3. Go to **My Applications** to see your saved jobs
        4. After applying, click **📤** to mark as Applied
        5. Update status as you progress (Interview, Offer, etc.)
        6. Add notes to track important details
        """)
    
    with st.expander("What should I do if I am not getting interviews?"):
        st.markdown("""
        Check the **Statistics** page for recommendations. Common tips:
        
        1. **Apply to more jobs** - Aim for 5-10 applications per week
        2. **Tailor your CV** - Customize for each application
        3. **Expand keywords** - Try different job titles
        4. **Follow up** - Send a follow-up email after 1 week
        5. **Check requirements** - Make sure you meet key qualifications
        """)
    
    st.markdown("---")
    
    # Quick tips
    st.markdown("## 💡 Pro Tips")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **🎯 Daily Routine**
        
        1. Check "Today is Top Pick" in sidebar
        2. Review new jobs (filter by Last 1 day)
        3. Save interesting jobs
        4. Apply to 2-3 saved jobs
        5. Update application statuses
        """)
    
    with col2:
        st.info("""
        **📊 Track Your Progress**
        
        - Aim for 5+ applications per week
        - 10% interview rate is normal
        - Follow up after 1 week silence
        - Keep notes on each application
        """)
