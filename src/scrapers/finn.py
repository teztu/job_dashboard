"""Scraper for Finn.no job listings."""

import logging
import re
from collections.abc import Generator
from datetime import datetime
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ..database.models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class FinnScraper(BaseScraper):
    """Scraper for Finn.no job listings."""

    BASE_URL = "https://www.finn.no"
    SEARCH_URL = "https://www.finn.no/job/fulltime/search.html"

    # Location codes for major Norwegian cities
    LOCATION_CODES = {
        "oslo": "0.20001",
        "bergen": "0.20003",
        "trondheim": "0.20012",
        "stavanger": "0.20011",
        "tromsø": "0.20016",
        "kristiansand": "0.20009",
        "drammen": "0.20002",
    }

    @property
    def source_name(self) -> str:
        return "finn"

    def _get_location_code(self) -> str | None:
        """Get Finn.no location code for the configured location."""
        location_lower = self.location.lower()
        return self.LOCATION_CODES.get(location_lower)

    def _build_search_url(self, keyword: str, page: int = 1) -> str:
        """Build the search URL with parameters."""
        params = {
            "q": keyword,
            "sort": "PUBLISHED_DESC",  # Sort by newest first
        }

        # Add location filter if available
        location_code = self._get_location_code()
        if location_code:
            params["location"] = location_code

        # Add pagination
        if page > 1:
            params["page"] = page

        return f"{self.SEARCH_URL}?{urlencode(params)}"

    def _parse_job_listing(self, article: BeautifulSoup) -> Job | None:
        """Parse a single job listing from search results."""
        try:
            # Find the link element
            link_elem = article.find("a", class_=re.compile(r"sf-search-ad-link|job-ad-link"))
            if not link_elem:
                link_elem = article.find("a", href=re.compile(r"/job/fulltime/ad\.html"))
            if not link_elem:
                return None

            # Get URL and ID
            url = link_elem.get("href", "")
            if url.startswith("/"):
                url = self.BASE_URL + url

            # Extract job ID from URL
            source_id = None
            id_match = re.search(r"finnkode=(\d+)", url)
            if id_match:
                source_id = id_match.group(1)

            # Get title
            title_elem = article.find("h2") or article.find("h3") or link_elem
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Get company
            company = None
            company_elem = article.find("span", class_=re.compile(r"text-gray|job-ad-company"))
            if company_elem:
                company = company_elem.get_text(strip=True)
            else:
                # Try to find in the structure
                detail_elems = article.find_all("span")
                # Strings to exclude from company names
                excluded = ["dag", "time", "uke", "oslo", "bergen", "favoritt", "legg til",
                           "lagre", "saved", "sist", "publisert", "stillinger"]
                for elem in detail_elems:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 2 and not any(x in text.lower() for x in excluded):
                        company = text
                        break

            # Final validation - reject if it is still garbage
            if company and any(x in company.lower() for x in ["favoritt", "legg til", "lagre"]):
                company = None

            # Get location
            location = None
            location_elem = article.find("span", class_=re.compile(r"location|place"))
            if location_elem:
                location = location_elem.get_text(strip=True)
            else:
                # Look for Oslo, Bergen, etc. in text
                for city in ["Oslo", "Bergen", "Trondheim", "Stavanger", "Tromsø"]:
                    if city in article.get_text():
                        location = city
                        break

            # Get posted date (relative like "2 dager siden")
            posted_date = None
            time_elem = article.find("time") or article.find(string=re.compile(r"dag|time|uke"))
            if time_elem:
                date_text = time_elem.get_text(strip=True) if hasattr(time_elem, "get_text") else str(time_elem)
                posted_date = self._parse_relative_date(date_text)

            return Job(
                title=title,
                company=company,
                location=location or self.location,
                url=url,
                source="finn",
                source_id=source_id,
                posted_date=posted_date,
                scraped_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.warning(f"Failed to parse job listing: {e}")
            return None

    def _parse_relative_date(self, text: str) -> datetime | None:
        """Parse Norwegian relative date strings like '2 dager siden'."""
        from datetime import timedelta

        text = text.lower().strip()
        now = datetime.utcnow()

        try:
            if "i dag" in text or "nettopp" in text:
                return now
            elif "i går" in text:
                return now - timedelta(days=1)

            # Match patterns like "2 dager siden", "1 uke siden"
            match = re.search(r"(\d+)\s*(dag|time|uke|måned)", text)
            if match:
                num = int(match.group(1))
                unit = match.group(2)

                if unit == "time":
                    return now - timedelta(hours=num)
                elif unit == "dag":
                    return now - timedelta(days=num)
                elif unit == "uke":
                    return now - timedelta(weeks=num)
                elif unit == "måned":
                    return now - timedelta(days=num * 30)

        except Exception:
            pass

        return None

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """Get total number of pages from pagination."""
        try:
            # Look for pagination element
            pagination = soup.find("nav", class_=re.compile(r"pagination"))
            if pagination:
                page_links = pagination.find_all("a")
                pages = []
                for link in page_links:
                    text = link.get_text(strip=True)
                    if text.isdigit():
                        pages.append(int(text))
                if pages:
                    return max(pages)
        except Exception:
            pass
        return 1

    def search(self, keyword: str, max_pages: int = 5) -> Generator[Job, None, None]:
        """Search for jobs on Finn.no.

        Args:
            keyword: Search term
            max_pages: Maximum number of pages to scrape (default 5)

        Yields:
            Job objects
        """
        logger.info(f"Searching Finn.no for '{keyword}' in {self.location}")

        page = 1
        total_pages = 1

        while page <= min(max_pages, total_pages):
            url = self._build_search_url(keyword, page)
            logger.debug(f"Fetching page {page}: {url}")

            response = self._get(url)
            if not response:
                break

            soup = BeautifulSoup(response.text, "lxml")

            # Get total pages on first request
            if page == 1:
                total_pages = self._get_total_pages(soup)
                logger.info(f"Found {total_pages} pages of results")

            # Find job listings
            # Finn.no uses different structures, try multiple selectors
            articles = soup.find_all("article", class_=re.compile(r"ad-card|job-ad|result-item"))
            if not articles:
                articles = soup.find_all("article")
            if not articles:
                # Try finding by data attribute or other means
                articles = soup.select("[data-testid='ad-card']")

            logger.debug(f"Found {len(articles)} job listings on page {page}")

            for article in articles:
                job = self._parse_job_listing(article)
                if job and job.url:
                    yield job

            page += 1

    def get_job_details(self, job: Job) -> Job:
        """Fetch additional details for a job by visiting its page.

        Args:
            job: Job object with URL

        Returns:
            Job object with additional details filled in
        """
        if not job.url:
            return job

        response = self._get(job.url)
        if not response:
            return job

        soup = BeautifulSoup(response.text, "lxml")

        # Get full description
        desc_elem = soup.find("div", class_=re.compile(r"description|job-description"))
        if desc_elem:
            job.description = desc_elem.get_text(strip=True)

        # Get deadline
        deadline_elem = soup.find(string=re.compile(r"søknadsfrist|deadline", re.I))
        if deadline_elem:
            parent = deadline_elem.parent
            if parent:
                parent.get_text(strip=True)
                # Try to parse date - could be various formats
                # This is simplified, real implementation would need more parsing

        return job
