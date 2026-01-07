"""Database connection and utilities."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "jobs.db"


def get_database_url() -> str:
    """Get database URL from environment or use default SQLite."""
    return os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


# Create engine lazily
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            echo=os.getenv("DEBUG", "").lower() == "true",
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,  # Allow accessing loaded attributes after session closes
        )
    return _SessionLocal


def init_db() -> None:
    """Initialize the database, creating all tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables (use with caution!)."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get a database session as a context manager.

    Usage:
        with get_db() as db:
            jobs = db.query(Job).all()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session (manual management required).

    Remember to call session.close() when done!

    Usage:
        db = get_db_session()
        try:
            jobs = db.query(Job).all()
            db.commit()
        finally:
            db.close()
    """
    SessionLocal = get_session_factory()
    return SessionLocal()
