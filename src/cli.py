"""Command-line interface for Job Hunter."""

import logging
import os
import sys
from datetime import datetime, timedelta

import click
from dotenv import load_dotenv

from .database.db import get_db, init_db
from .database.models import Application, ApplicationStatus, Job, SearchKeyword
from .scrapers import ArbeidsplassenScraper, FinnScraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_keywords() -> list[str]:
    """Get search keywords from environment or defaults."""
    keywords_str = os.getenv(
        "SEARCH_KEYWORDS",
        "Junior utvikler,Python utvikler,Backend utvikler,Dataanalytiker"
    )
    return [k.strip() for k in keywords_str.split(",") if k.strip()]


def get_location() -> str:
    """Get search location from environment or default."""
    return os.getenv("SEARCH_LOCATION", "Oslo")


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def main(debug: bool):
    """Job Hunter - Norwegian job scraping and tracking tool."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)


@main.command()
@click.option("--all", "scrape_all", is_flag=True, help="Scrape all configured sites")
@click.option("--site", type=click.Choice(["finn", "arbeidsplassen"]), help="Scrape specific site")
@click.option("--keyword", "-k", multiple=True, help="Search keywords (can specify multiple)")
def scrape(scrape_all: bool, site: str, keyword: tuple):
    """Scrape job listings from Norwegian job sites."""
    # Initialize database
    init_db()

    location = get_location()
    keywords = list(keyword) if keyword else get_keywords()

    click.echo(f"Searching in {location} for: {', '.join(keywords)}")

    total_found = 0
    total_new = 0

    scrapers = []
    if scrape_all or site == "finn" or not site:
        scrapers.append(("Finn.no", FinnScraper(location)))
    if scrape_all or site == "arbeidsplassen":
        scrapers.append(("Arbeidsplassen.no", ArbeidsplassenScraper(location)))

    for name, scraper in scrapers:
        click.echo(f"\n--- Scraping {name} ---")
        with scraper:
            for kw in keywords:
                try:
                    found, new = scraper.scrape_and_save(kw)
                    total_found += found
                    total_new += new
                    click.echo(f"  '{kw}': {found} found, {new} new")
                except Exception as e:
                    click.echo(f"  '{kw}': Error - {e}", err=True)

    click.echo(f"\n=== Total: {total_found} jobs found, {total_new} new ===")

    # Update keyword statistics
    with get_db() as db:
        for kw in keywords:
            keyword_record = db.query(SearchKeyword).filter(SearchKeyword.keyword == kw).first()
            if not keyword_record:
                keyword_record = SearchKeyword(keyword=kw)
                db.add(keyword_record)

            jobs_count = db.query(Job).filter(Job.search_keyword == kw).count()
            keyword_record.jobs_found = jobs_count
            keyword_record.last_searched = datetime.utcnow()


@main.command("list")
@click.option("--days", "-d", default=7, help="Show jobs from last N days")
@click.option("--source", "-s", help="Filter by source (finn, arbeidsplassen)")
@click.option("--keyword", "-k", help="Filter by search keyword")
@click.option("--limit", "-n", default=20, help="Maximum number of jobs to show")
def list_jobs(days: int, source: str, keyword: str, limit: int):
    """List recently scraped jobs."""
    init_db()

    with get_db() as db:
        query = db.query(Job)

        # Apply filters
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Job.scraped_at >= since)
        if source:
            query = query.filter(Job.source == source)
        if keyword:
            query = query.filter(Job.search_keyword.ilike(f"%{keyword}%"))

        # Order by newest first
        query = query.order_by(Job.scraped_at.desc())

        jobs = query.limit(limit).all()

        if not jobs:
            click.echo("No jobs found matching your criteria.")
            return

        click.echo(f"\n{'=' * 60}")
        click.echo(f"Recent Jobs (last {days} days)")
        click.echo(f"{'=' * 60}\n")

        for job in jobs:
            status = ""
            if job.application:
                status = f" [{job.application.status.value.upper()}]"

            click.echo(f"[{job.source}] {job.title}{status}")
            if job.company:
                click.echo(f"  Company: {job.company}")
            if job.location:
                click.echo(f"  Location: {job.location}")
            click.echo(f"  URL: {job.url}")
            if job.posted_date:
                click.echo(f"  Posted: {job.posted_date.strftime('%Y-%m-%d')}")
            click.echo()


@main.command()
def stats():
    """Show job hunting statistics."""
    init_db()

    with get_db() as db:
        # Total jobs
        total_jobs = db.query(Job).count()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        jobs_today = db.query(Job).filter(Job.scraped_at >= today).count()

        # Jobs by source
        sources = {}
        for source in ["finn", "arbeidsplassen"]:
            sources[source] = db.query(Job).filter(Job.source == source).count()

        # Application stats
        app_stats = {}
        for status in ApplicationStatus:
            count = db.query(Application).filter(Application.status == status).count()
            if count > 0:
                app_stats[status.value] = count

        # Keywords
        keywords = db.query(SearchKeyword).filter(SearchKeyword.is_active == True).all()

        click.echo("\n" + "=" * 50)
        click.echo("JOB HUNTER STATISTICS")
        click.echo("=" * 50)

        click.echo(f"\nTotal Jobs: {total_jobs}")
        click.echo(f"New Today: {jobs_today}")

        click.echo("\nJobs by Source:")
        for source, count in sources.items():
            click.echo(f"  {source}: {count}")

        if app_stats:
            click.echo("\nApplication Pipeline:")
            for status, count in app_stats.items():
                click.echo(f"  {status}: {count}")

        if keywords:
            click.echo("\nSearch Keywords:")
            for kw in keywords:
                click.echo(f"  '{kw.keyword}': {kw.jobs_found} jobs")

        click.echo()


@main.command()
@click.argument("job_id", type=int)
@click.option("--status", "-s", type=click.Choice([s.value for s in ApplicationStatus]))
@click.option("--notes", "-n", help="Add notes")
def apply(job_id: int, status: str, notes: str):
    """Update application status for a job."""
    init_db()

    with get_db() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            click.echo(f"Job ID {job_id} not found.", err=True)
            return

        if not job.application:
            job.application = Application(job_id=job_id)
            db.add(job.application)

        if status:
            job.application.status = ApplicationStatus(status)
            if status == "applied":
                job.application.applied_date = datetime.utcnow()

        if notes:
            if job.application.notes:
                job.application.notes += f"\n\n[{datetime.utcnow().strftime('%Y-%m-%d')}] {notes}"
            else:
                job.application.notes = f"[{datetime.utcnow().strftime('%Y-%m-%d')}] {notes}"

        click.echo(f"Updated job: {job.title}")
        click.echo(f"Status: {job.application.status.value}")


@main.command()
def dashboard():
    """Launch the Streamlit dashboard."""
    import subprocess

    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
    click.echo("Launching dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])


@main.command()
def notify():
    """Send email notification with new jobs."""
    from .notifications.email import send_daily_digest

    init_db()
    try:
        send_daily_digest()
        click.echo("Email notification sent!")
    except Exception as e:
        click.echo(f"Failed to send notification: {e}", err=True)


@main.command("init-db")
def init_database():
    """Initialize the database."""
    init_db()
    click.echo("Database initialized!")


if __name__ == "__main__":
    main()
