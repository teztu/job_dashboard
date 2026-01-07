"""Tests for job scrapers."""


from src.scrapers.arbeidsplassen import ArbeidsplassenScraper
from src.scrapers.finn import FinnScraper


class TestFinnScraper:
    """Tests for FinnScraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = FinnScraper("Oslo")
        assert scraper.source_name == "finn"

    def test_build_search_url(self):
        """Test URL building."""
        scraper = FinnScraper("Oslo")
        url = scraper._build_search_url("python", page=1)

        assert "finn.no" in url
        assert "q=python" in url
        assert "location" in url  # Oslo should be included

    def test_parse_relative_date(self):
        """Test parsing Norwegian relative dates."""
        scraper = FinnScraper("Oslo")

        # Test "i dag"
        result = scraper._parse_relative_date("i dag")
        assert result is not None

        # Test "2 dager siden"
        result = scraper._parse_relative_date("2 dager siden")
        assert result is not None

    def test_location_code_lookup(self):
        """Test location code lookup."""
        scraper = FinnScraper("Oslo")
        assert scraper._get_location_code() is not None

        scraper_bergen = FinnScraper("Bergen")
        assert scraper_bergen._get_location_code() is not None


class TestArbeidsplassenScraper:
    """Tests for ArbeidsplassenScraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = ArbeidsplassenScraper("Oslo")
        assert scraper.source_name == "arbeidsplassen"

    def test_build_search_url(self):
        """Test URL building."""
        scraper = ArbeidsplassenScraper("Oslo")
        url = scraper._build_search_url("backend", page=0)

        assert "arbeidsplassen.nav.no" in url
        assert "q=backend" in url

    def test_parse_job_listing(self):
        """Test parsing a job listing from JSON."""
        scraper = ArbeidsplassenScraper("Oslo")

        mock_item = {
            "uuid": "test-uuid-123",
            "title": "Python Developer",
            "employer": {"name": "Test Company"},
            "workplace": {"city": "Oslo"},
            "published": "2024-01-15T10:00:00Z",
        }

        job = scraper._parse_job_listing(mock_item)

        assert job is not None
        assert job.title == "Python Developer"
        assert job.company == "Test Company"
        assert job.source_id == "test-uuid-123"


class TestBaseScraper:
    """Tests for base scraper functionality."""

    def test_user_agent_set(self):
        """Test that user agent is set."""
        scraper = FinnScraper("Oslo")
        assert "Mozilla" in scraper.session.headers["User-Agent"]

    def test_context_manager(self):
        """Test context manager protocol."""
        with FinnScraper("Oslo") as scraper:
            assert scraper is not None
        # Session should be closed after exiting context
