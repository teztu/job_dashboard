"""Scraper for Arbeidsplassen.no (NAV) job listings."""

import logging
import re
from collections.abc import Generator
from datetime import datetime
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ..database.models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class ArbeidsplassenScraper(BaseScraper):
    """Scraper for Arbeidsplassen.no (NAV's job portal)."""

    BASE_URL = "https://arbeidsplassen.nav.no"
    SEARCH_URL = "https://arbeidsplassen.nav.no/stillinger"
    API_URL = "https://arbeidsplassen.nav.no/stillinger/api/search"

    # County codes for major Norwegian cities
    COUNTY_CODES = {
        "oslo": "03",
        "bergen": "46",  # Vestland
        "trondheim": "50",  # Trøndelag
        "stavanger": "11",  # Rogaland
        "tromsø": "54",  # Troms og Finnmark
        "kristiansand": "42",  # Agder
    }

    @property
    def source_name(self) -> str:
        return "arbeidsplassen"

    def _get_county_code(self) -> str | None:
        """Get county code for the configured location."""
        location_lower = self.location.lower()
        return self.COUNTY_CODES.get(location_lower)

    def _build_search_url(self, keyword: str, page: int = 0) -> str:
        """Build the search URL with parameters."""
        params = {
            "q": keyword,
            "from": page * 25,  # Results per page
            "size": 25,
        }

        # Add location filter
        county_code = self._get_county_code()
        if county_code:
            params["counties"] = county_code

        return f"{self.SEARCH_URL}?{urlencode(params)}"

    def _parse_job_listing(self, item: dict) -> Job | None:
        """Parse a job from the search results JSON."""
        try:
            # Extract basic info
            uuid = item.get("uuid", "")
            title = item.get("title", "Unknown")
            employer = item.get("employer", {})
            company = employer.get("name") if isinstance(employer, dict) else None

            # Location
            location = None
            workplace = item.get("workplace", {})
            if isinstance(workplace, dict):
                location = workplace.get("city") or workplace.get("municipal")
            if not location:
                location = self.location

            # URL
            url = f"{self.BASE_URL}/stillinger/stilling/{uuid}"

            # Dates
            published = item.get("published")
            expires = item.get("expires")

            posted_date = None
            deadline = None

            if published:
                try:
                    posted_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except Exception:
                    pass

            if expires:
                try:
                    deadline = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                except Exception:
                    pass

            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                source="arbeidsplassen",
                source_id=uuid,
                posted_date=posted_date,
                deadline=deadline,
                scraped_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.warning(f"Failed to parse job listing: {e}")
            return None

    def _parse_html_listing(self, article: BeautifulSoup) -> Job | None:
        """Parse a job from HTML search results (fallback)."""
        try:
            # Find link
            link = article.find("a", href=re.compile(r"/stillinger/stilling/"))
            if not link:
                return None

            url = link.get("href", "")
            if url.startswith("/"):
                url = self.BASE_URL + url

            # Extract UUID from URL
            source_id = None
            match = re.search(r"/stilling/([a-f0-9-]+)", url)
            if match:
                source_id = match.group(1)

            # Title
            title_elem = article.find("h2") or article.find("h3") or link
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Company - usually in a specific element
            company = None
            company_elem = article.find(class_=re.compile(r"employer|company"))
            if company_elem:
                company = company_elem.get_text(strip=True)

            # Location
            location = None
            location_elem = article.find(class_=re.compile(r"location|place|workplace"))
            if location_elem:
                location = location_elem.get_text(strip=True)

            return Job(
                title=title,
                company=company,
                location=location or self.location,
                url=url,
                source="arbeidsplassen",
                source_id=source_id,
                scraped_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.warning(f"Failed to parse HTML job listing: {e}")
            return None

    def search(self, keyword: str, max_pages: int = 5) -> Generator[Job, None, None]:
        """Search for jobs on Arbeidsplassen.no.

        Args:
            keyword: Search term
            max_pages: Maximum number of pages to scrape (default 5)

        Yields:
            Job objects
        """
        logger.info(f"Searching Arbeidsplassen.no for '{keyword}' in {self.location}")

        for page in range(max_pages):
            url = self._build_search_url(keyword, page)
            logger.debug(f"Fetching page {page + 1}: {url}")

            response = self._get(url)
            if not response:
                break

            # Try to parse as JSON first (if using API)
            try:
                data = response.json()
                if "content" in data:
                    items = data.get("content", [])
                    if not items:
                        logger.debug("No more results")
                        break

                    for item in items:
                        job = self._parse_job_listing(item)
                        if job:
                            yield job

                    # Check if there are more pages
                    total_elements = data.get("totalElements", 0)
                    if (page + 1) * 25 >= total_elements:
                        break

                    continue

            except Exception:
                pass

            # Fallback: Parse HTML
            soup = BeautifulSoup(response.text, "lxml")

            # Find job cards
            articles = soup.find_all("article") or soup.find_all(
                class_=re.compile(r"job-card|result-item|stilling")
            )

            if not articles:
                logger.debug("No job listings found on page")
                break

            for article in articles:
                job = self._parse_html_listing(article)
                if job:
                    yield job

    def get_job_details(self, job: Job) -> Job:
        """Fetch additional details for a job.

        Args:
            job: Job object with URL

        Returns:
            Job object with additional details
        """
        if not job.url:
            return job

        response = self._get(job.url)
        if not response:
            return job

        soup = BeautifulSoup(response.text, "lxml")

        # Get full description
        desc_elem = soup.find("div", class_=re.compile(r"description|job-description|stillingsbeskrivelse"))
        if desc_elem:
            job.description = desc_elem.get_text(strip=True)

        return job
