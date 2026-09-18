"""
Lightweight, additive schema migrations.

`Base.metadata.create_all()` (called in `init_db`) already creates any
brand-new table, so the only thing this module needs to handle is adding
columns to tables that may already exist from an earlier version of the
app (e.g. `sale_time`, `post_time`, `platform` were added after the first
release). Each migration is a no-op if the column already exists, so this
is safe to run on every startup.

If you add a new nullable column to an existing table in the future, add
one more guarded `ADD COLUMN` block here and document it in
PROJECT_GUIDE.md under "Migrations".
"""
from __future__ import annotations

from sqlalchemy import text, inspect


def _add_column_if_missing(conn, inspector, table: str, column: str, sqlite_ddl: str, other_ddl: str) -> None:
    existing_columns = [col["name"] for col in inspector.get_columns(table)]
    if column in existing_columns:
        return
    try:
        if "sqlite" in str(conn.engine.url):
            conn.execute(text(sqlite_ddl))
        else:
            conn.execute(text(other_ddl))
        conn.commit()
    except Exception:
        # Column may have been added concurrently, or the table may not
        # exist yet on a brand-new database (create_all handles that case).
        pass


def run_migrations(engine) -> None:
    inspector = inspect(engine)
    if "media_posts" not in inspector.get_table_names() or "sales" not in inspector.get_table_names():
        return

    with engine.connect() as conn:
        _add_column_if_missing(
            conn, inspector, "media_posts", "post_time",
            "ALTER TABLE media_posts ADD COLUMN post_time TEXT",
            "ALTER TABLE media_posts ADD COLUMN IF NOT EXISTS post_time TIME",
        )
        _add_column_if_missing(
            conn, inspector, "media_posts", "platform",
            "ALTER TABLE media_posts ADD COLUMN platform TEXT DEFAULT 'instagram'",
            "ALTER TABLE media_posts ADD COLUMN IF NOT EXISTS platform VARCHAR(50) DEFAULT 'instagram'",
        )
        _add_column_if_missing(
            conn, inspector, "sales", "sale_time",
            "ALTER TABLE sales ADD COLUMN sale_time TEXT",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS sale_time TIME",
        )
