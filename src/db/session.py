"""
Database engine and session management.

Supports PostgreSQL in production (via DATABASE_URL) and falls back to a
local SQLite file for development, per Core Rule #6 in the project guide.
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.config import settings
from src.db.models import Base
from src.db.migrations import run_migrations


def _make_engine(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        # Needed because Streamlit can access the session from more than
        # one thread across reruns.
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, connect_args=connect_args)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create tables if they don't exist yet, then apply lightweight migrations."""
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)


def get_db():
    """FastAPI-style generator dependency, kept for reuse in scripts/tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context-manager form of get_db for scripts and tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
