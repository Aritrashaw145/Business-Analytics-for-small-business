"""
Central configuration for the Business Analytics Dashboard.

All environment-dependent values (database connection, session secret,
model storage location) are read here once so the rest of the codebase
never touches `os.environ` directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    session_secret: str
    model_dir: str
    demo_email: str
    demo_password: str
    min_training_days: int
    min_training_posts: int
    prediction_evaluation_window_days: int


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # SQLite fallback for local development. Stored at the project root
    # so it survives restarts of the Streamlit process.
    return "sqlite:///business_analytics.db"


def load_settings() -> Settings:
    return Settings(
        database_url=_get_database_url(),
        session_secret=os.environ.get("SESSION_SECRET", "dev-session-secret-change-me"),
        model_dir=os.environ.get("MODEL_DIR", "models"),
        demo_email=os.environ.get("DEMO_EMAIL", "demo@example.com"),
        demo_password=os.environ.get("DEMO_PASSWORD", "demo123"),
        min_training_days=int(os.environ.get("MIN_TRAINING_DAYS", "7")),
        min_training_posts=int(os.environ.get("MIN_TRAINING_POSTS", "3")),
        prediction_evaluation_window_days=int(
            os.environ.get("PREDICTION_EVAL_WINDOW_DAYS", "3")
        ),
    )


settings = load_settings()
