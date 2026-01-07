"""Base scraper class for job sites."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generator, Optional

import requests
from ratelimit import limits, sleep_and_retry

from ..database.db import get_db
from ..database.models import Job, ScrapingLog

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for job scrapers.

    All scrapers should inherit from this class and implement:
    - source_name: Name of the job source (e.g., 'finn', 'arbeidsplassen')
    - search(): Generator that yields Job objects
    """

    # Rate limiting: 1 request per second by default
    CALLS_PER_PERIOD = 1
    PERIOD_SECONDS = 1

    # Request settings
    TIMEOUT = 30
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, location: str = "Oslo"):
        """Initialize scraper with search location."""
        self.location = location
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "no,en;q=0.9",
        })

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this source (e.g., 'finn')."""
        pass

    @abstractmethod
    def search(self, keyword: str) -> Generator[Job, None, None]:
        """Search for jobs matching the keyword.

        Args:
            keyword: Search term to look for

        Yields:
            Job objects (not yet saved to database)
        """
        pass

    @sleep_and_retry
    @limits(calls=CALLS_PER_PERIOD, period=PERIOD_SECONDS)
    def _rate_limited_get(self, url: str, **kwargs) -> requests.Response:
        """Make a rate-limited GET request."""
        return self.session.get(url, timeout=self.TIMEOUT, **kwargs)

    def _get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a GET request with error handling."""
        try:
            response = self._rate_limited_get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def scrape_and_save(self, keyword: str) -> tuple[int, int]:
        """Scrape jobs and save to database.

        Args:
            keyword: Search term to look for

        Returns:
            Tuple of (total_jobs_found, new_jobs_saved)
        """
        log = ScrapingLog(
            source=self.source_name,
            keyword=keyword,
            started_at=datetime.utcnow(),
        )

        jobs_found = 0
        jobs_new = 0

        try:
            with get_db() as db:
                # Add the log entry
                db.add(log)

                for job in self.search(keyword):
                    jobs_found += 1

                    # Check if job already exists (by source_id or URL)
                    existing = None
                    if job.source_id:
                        existing = (
                            db.query(Job)
                            .filter(Job.source == job.source, Job.source_id == job.source_id)
                            .first()
                        )
                    if not existing:
                        existing = db.query(Job).filter(Job.url == job.url).first()

                    if existing:
                        logger.debug(f"Job already exists: {job.title}")
                        continue

                    # Save new job
                    job.search_keyword = keyword
                    db.add(job)
                    jobs_new += 1
                    logger.info(f"New job: {job.title} at {job.company}")

                # Update log
                log.finished_at = datetime.utcnow()
                log.jobs_found = jobs_found
                log.jobs_new = jobs_new
                log.success = True

                logger.info(
                    f"Scraped {self.source_name} for '{keyword}': "
                    f"{jobs_found} found, {jobs_new} new"
                )

        except Exception as e:
            log.success = False
            log.error_message = str(e)
            logger.error(f"Scraping failed: {e}")
            raise

        return jobs_found, jobs_new

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
