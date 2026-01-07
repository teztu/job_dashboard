"""Tests for database models and utilities."""

from datetime import datetime

import pytest

from src.database.db import drop_db, get_db, init_db
from src.database.models import Application, ApplicationStatus, Job, SearchKeyword


@pytest.fixture(autouse=True)
def setup_db():
    """Set up a fresh database for each test."""
    import os
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    # Re-initialize the database module
    from src.database import db
    db._engine = None
    db._SessionLocal = None

    init_db()
    yield
    drop_db()


class TestJobModel:
    """Tests for the Job model."""

    def test_create_job(self):
        """Test creating a job."""
        with get_db() as db:
            job = Job(
                title="Python Developer",
                company="Test Company",
                location="Oslo",
                url="https://example.com/job/1",
                source="finn",
                source_id="12345",
            )
            db.add(job)
            db.flush()

            assert job.id is not None
            assert job.title == "Python Developer"
            assert job.source == "finn"

    def test_job_is_new(self):
        """Test the is_new property."""
        with get_db() as db:
            job = Job(
                title="New Job",
                url="https://example.com/job/2",
                source="finn",
                scraped_at=datetime.utcnow(),
            )
            db.add(job)
            db.flush()

            assert job.is_new is True


class TestApplicationModel:
    """Tests for the Application model."""

    def test_create_application(self):
        """Test creating an application."""
        with get_db() as db:
            job = Job(
                title="Test Job",
                url="https://example.com/job/3",
                source="finn",
            )
            db.add(job)
            db.flush()

            application = Application(
                job_id=job.id,
                status=ApplicationStatus.INTERESTED,
            )
            db.add(application)
            db.flush()

            assert application.id is not None
            assert application.status == ApplicationStatus.INTERESTED

    def test_application_status_update(self):
        """Test updating application status."""
        with get_db() as db:
            job = Job(
                title="Test Job",
                url="https://example.com/job/4",
                source="finn",
            )
            db.add(job)
            db.flush()

            application = Application(job_id=job.id)
            db.add(application)
            db.flush()

            assert application.status == ApplicationStatus.NEW

            application.status = ApplicationStatus.APPLIED
            application.applied_date = datetime.utcnow()
            db.flush()

            assert application.status == ApplicationStatus.APPLIED
            assert application.applied_date is not None


class TestSearchKeyword:
    """Tests for the SearchKeyword model."""

    def test_create_keyword(self):
        """Test creating a search keyword."""
        with get_db() as db:
            keyword = SearchKeyword(
                keyword="Python utvikler",
                jobs_found=10,
            )
            db.add(keyword)
            db.flush()

            assert keyword.id is not None
            assert keyword.keyword == "Python utvikler"

    def test_success_rate(self):
        """Test the success_rate property."""
        keyword = SearchKeyword(
            keyword="Test",
            applications_sent=10,
            interviews_received=2,
        )
        assert keyword.success_rate == 0.2

        keyword_no_apps = SearchKeyword(
            keyword="Test2",
            applications_sent=0,
        )
        assert keyword_no_apps.success_rate is None
