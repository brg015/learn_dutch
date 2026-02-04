"""
Migrate timestamp columns from text to timestamptz.

This script is idempotent: it only alters columns that are currently text-like.

Usage:
  python scripts/migrate_timestamps_to_datetime.py

Requires DATABASE_URL (and optionally TEST_MODE) in the environment.
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from core.fsrs.database import get_engine


def _is_text_column(inspector, table_name: str, column_name: str) -> bool:
    for col in inspector.get_columns(table_name):
        if col["name"] == column_name:
            col_type = str(col["type"]).upper()
            return "CHAR" in col_type or "TEXT" in col_type
    return False


def _alter_column(conn, table_name: str, column_name: str, using_sql: str) -> None:
    conn.execute(
        text(
            f'ALTER TABLE {table_name} '
            f'ALTER COLUMN "{column_name}" TYPE TIMESTAMPTZ USING {using_sql}'
        )
    )


def main() -> None:
    engine = get_engine()
    inspector = inspect(engine)

    with engine.begin() as conn:
        if _is_text_column(inspector, "card_state", "last_review_timestamp"):
            _alter_column(conn, "card_state", "last_review_timestamp", 'last_review_timestamp::timestamptz')

        if _is_text_column(inspector, "card_state", "last_ltm_timestamp"):
            _alter_column(conn, "card_state", "last_ltm_timestamp", "NULLIF(last_ltm_timestamp,'')::timestamptz")

        if _is_text_column(inspector, "review_events", "timestamp"):
            _alter_column(conn, "review_events", "timestamp", '"timestamp"::timestamptz')


if __name__ == "__main__":
    main()
