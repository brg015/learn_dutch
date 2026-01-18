"""
SQLite repository for review logs.

Tracks all learning events in an append-only log.
Metrics (accuracy, exposure count, recency) are computed at query time.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Configuration
DB_PATH = Path("logs/reviews.sqlite")


# ---- Schema ----

def init_db(db_path: Path = DB_PATH) -> None:
    """
    Initialize the SQLite database with the review_events table.

    Creates the logs directory if it doesn't exist.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            lemma TEXT NOT NULL,
            pos TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            remembered INTEGER NOT NULL,  -- 0 or 1 (SQLite boolean)
            latency_ms INTEGER,           -- Optional: time to answer in milliseconds
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Index for fast lookups by lemma+pos
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_lemma_pos
        ON review_events(lemma, pos)
    """)

    # Index for timestamp-based queries (recency)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON review_events(timestamp DESC)
    """)

    conn.commit()
    conn.close()


# ---- Logging Functions ----

def log_review(
    lemma: str,
    pos: str,
    exercise_type: str,
    remembered: bool,
    latency_ms: Optional[int] = None,
    db_path: Path = DB_PATH
) -> None:
    """
    Log a single review event.

    Args:
        lemma: The word lemma
        pos: Part of speech
        exercise_type: Type of exercise (e.g., "word_translation", "past_tense")
        remembered: Whether the user remembered the answer
        latency_ms: Optional response time in milliseconds
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO review_events (timestamp, lemma, pos, exercise_type, remembered, latency_ms)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        lemma,
        pos,
        exercise_type,
        1 if remembered else 0,
        latency_ms
    ))

    conn.commit()
    conn.close()


# ---- Query Functions (for scheduler) ----

def get_review_count(lemma: str, pos: str, db_path: Path = DB_PATH) -> int:
    """
    Get the total number of times a word has been reviewed.

    Args:
        lemma: The word lemma
        pos: Part of speech
        db_path: Path to SQLite database

    Returns:
        Total number of review events for this word
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM review_events
        WHERE lemma = ? AND pos = ?
    """, (lemma, pos))

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_last_review_timestamp(lemma: str, pos: str, db_path: Path = DB_PATH) -> Optional[datetime]:
    """
    Get the timestamp of the last review for a word.

    Args:
        lemma: The word lemma
        pos: Part of speech
        db_path: Path to SQLite database

    Returns:
        Datetime of last review, or None if never reviewed
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp
        FROM review_events
        WHERE lemma = ? AND pos = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (lemma, pos))

    row = cursor.fetchone()
    conn.close()

    if row:
        return datetime.fromisoformat(row[0])
    return None


def get_unique_lemmas_since(
    lemma: str,
    pos: str,
    db_path: Path = DB_PATH
) -> int:
    """
    Count unique lemmas reviewed since the last time this word appeared.

    This is the "n-words back" metric.

    Args:
        lemma: The word lemma
        pos: Part of speech
        db_path: Path to SQLite database

    Returns:
        Number of unique lemmas reviewed since last seeing this word (0 if never seen)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get timestamp of last review for this word
    cursor.execute("""
        SELECT timestamp
        FROM review_events
        WHERE lemma = ? AND pos = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (lemma, pos))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return 0  # Never reviewed

    last_timestamp = row[0]

    # Count unique lemmas reviewed after that timestamp
    cursor.execute("""
        SELECT COUNT(DISTINCT lemma)
        FROM review_events
        WHERE timestamp > ?
    """, (last_timestamp,))

    count = cursor.fetchone()[0]
    conn.close()

    return count


def get_accuracy(lemma: str, pos: str, db_path: Path = DB_PATH) -> float:
    """
    Calculate accuracy (% remembered) for a word.

    Args:
        lemma: The word lemma
        pos: Part of speech
        db_path: Path to SQLite database

    Returns:
        Accuracy as a float between 0.0 and 1.0 (returns 0.0 if never reviewed)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(remembered) as correct
        FROM review_events
        WHERE lemma = ? AND pos = ?
    """, (lemma, pos))

    row = cursor.fetchone()
    conn.close()

    total, correct = row

    if total == 0:
        return 0.0

    return correct / total


def get_all_reviewed_lemmas(db_path: Path = DB_PATH) -> set[tuple[str, str]]:
    """
    Get all (lemma, pos) pairs that have been reviewed at least once.

    Args:
        db_path: Path to SQLite database

    Returns:
        Set of (lemma, pos) tuples
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT lemma, pos
        FROM review_events
    """)

    reviewed = set(cursor.fetchall())
    conn.close()

    return reviewed


# ---- Utility Functions ----

def get_recent_events(limit: int = 10, db_path: Path = DB_PATH) -> list[dict]:
    """
    Get the most recent review events.

    Useful for displaying recent activity in the UI.

    Args:
        limit: Maximum number of events to return
        db_path: Path to SQLite database

    Returns:
        List of event dictionaries, most recent first
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            timestamp,
            lemma,
            pos,
            exercise_type,
            remembered,
            latency_ms
        FROM review_events
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    events = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return events
