"""SQLAlchemy database models for Job Hunter."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ApplicationStatus(str, Enum):
    """Status of a job application."""
    NEW = "new"
    INTERESTED = "interested"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Job(Base):
    """A job listing scraped from a job site."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Job details
    title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Salary info (when available)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_text = Column(String(255), nullable=True)  # Original salary text

    # Source info
    source = Column(String(50), nullable=False)  # finn, arbeidsplassen, linkedin
    source_id = Column(String(255), nullable=True)  # ID on the source site
    url = Column(String(1000), nullable=False)

    # Dates
    posted_date = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Search metadata
    search_keyword = Column(String(255), nullable=True)  # Which keyword found this job

    # Relationships
    application = relationship("Application", back_populates="job", uselist=False)

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"

    @property
    def is_new(self) -> bool:
        """Check if job was scraped in the last 24 hours."""
        if not self.scraped_at:
            return False
        return (datetime.utcnow() - self.scraped_at).days < 1


class Application(Base):
    """Tracks your application status for a job."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), unique=True, nullable=False)

    # Status tracking
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.NEW, nullable=False)

    # Dates
    applied_date = Column(DateTime, nullable=True)
    interview_date = Column(DateTime, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="application")

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, job_id={self.job_id}, status='{self.status.value}')>"


class SearchKeyword(Base):
    """Tracks search keywords and their effectiveness."""

    __tablename__ = "search_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), unique=True, nullable=False)

    # Statistics
    jobs_found = Column(Integer, default=0)
    last_searched = Column(DateTime, nullable=True)

    # Effectiveness tracking (for future AI features)
    applications_sent = Column(Integer, default=0)
    interviews_received = Column(Integer, default=0)

    # Active flag
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<SearchKeyword(keyword='{self.keyword}', jobs_found={self.jobs_found})>"

    @property
    def success_rate(self) -> Optional[float]:
        """Calculate interview success rate."""
        if self.applications_sent == 0:
            return None
        return self.interviews_received / self.applications_sent


class ScrapingLog(Base):
    """Log of scraping runs for debugging and statistics."""

    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    source = Column(String(50), nullable=False)
    keyword = Column(String(255), nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    jobs_found = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)

    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ScrapingLog(source='{self.source}', jobs_found={self.jobs_found})>"
