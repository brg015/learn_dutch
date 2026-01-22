"""
Persistence Layer - Database I/O for FSRS

Handles all database operations for card state and review events.

Schema:
- card_state: Persistent memory state for each card
- review_events: Log of all review attempts
"""

from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

from core.fsrs.memory_state import CardState
from core.fsrs.constants import FeedbackGrade


# Database path configuration
DB_DIR = Path(__file__).parent.parent.parent / "logs"

def get_db_path() -> Path:
    """
    Get the database path based on TEST_MODE environment variable.

    Returns:
        Path to learning.db (production) or test_learning.db (test mode)
    """
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    db_name = "test_learning.db" if test_mode else "learning.db"
    return DB_DIR / db_name


def is_test_mode() -> bool:
    """Check if running in test mode."""
    return os.getenv("TEST_MODE", "false").lower() == "true"


def get_connection() -> sqlite3.Connection:
    """Get database connection with row factory."""
    DB_DIR.mkdir(exist_ok=True)
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def reset_db():
    """
    DANGEROUS: Delete all data and recreate tables.

    Only use this for testing or when you want to start fresh.
    All review history will be lost!
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Drop old tables
    cursor.execute("DROP TABLE IF EXISTS review_events")
    cursor.execute("DROP TABLE IF EXISTS card_state")

    conn.commit()
    conn.close()

    # Now create fresh tables
    init_db()


def init_db():
    """
    Initialize database schema if tables don't exist.

    Safe to call multiple times - only creates tables if they don't exist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create card_state table with new schema (IF NOT EXISTS)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_state (
            word_id TEXT NOT NULL,
            exercise_type TEXT NOT NULL,

            -- Keep lemma/pos for readability and backward compat
            lemma TEXT NOT NULL,
            pos TEXT NOT NULL,

            -- Long-term memory parameters
            stability REAL NOT NULL,
            difficulty REAL NOT NULL,

            -- Effective difficulty (for next LTM update)
            d_eff REAL NOT NULL,

            -- Review tracking
            review_count INTEGER NOT NULL,
            last_review_timestamp TEXT NOT NULL,
            last_ltm_timestamp TEXT,
            ltm_review_date TEXT,

            -- Short-term memory tracking (reset after LTM)
            stm_success_count_today INTEGER NOT NULL DEFAULT 0,

            -- Metadata
            d_floor REAL,  -- Floor difficulty from last LTM update

            PRIMARY KEY (word_id, exercise_type)
        )
    """)

    # Create review_events table (IF NOT EXISTS)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id TEXT NOT NULL,
            exercise_type TEXT NOT NULL,

            -- Keep lemma/pos for readability and analytics
            lemma TEXT NOT NULL,
            pos TEXT NOT NULL,

            timestamp TEXT NOT NULL,
            feedback_grade INTEGER NOT NULL,
            latency_ms INTEGER,

            -- State before review
            stability_before REAL,
            difficulty_before REAL,
            d_eff_before REAL,
            retrievability_before REAL,

            -- State after review
            stability_after REAL NOT NULL,
            difficulty_after REAL NOT NULL,
            d_eff_after REAL NOT NULL,

            -- Event type
            is_ltm_event INTEGER NOT NULL,  -- 1 for LTM, 0 for STM

            -- Session context (optional, for analytics)
            session_id TEXT,
            session_position INTEGER,

            FOREIGN KEY (word_id, exercise_type)
                REFERENCES card_state (word_id, exercise_type)
        )
    """)

    # Indexes for performance (IF NOT EXISTS)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_review_events_card
        ON review_events (word_id, exercise_type)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_card_state_lemma_pos
        ON card_state (lemma, pos)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_review_events_timestamp
        ON review_events (timestamp)
    """)

    conn.commit()
    conn.close()


def load_card_state(
    word_id: str,
    exercise_type: str
) -> Optional[CardState]:
    """
    Load card state from database.

    Args:
        word_id: Unique word identifier
        exercise_type: Type of exercise

    Returns:
        CardState if found, None if new card
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM card_state
        WHERE word_id = ? AND exercise_type = ?
    """, (word_id, exercise_type))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    # Parse timestamps
    last_review_ts = datetime.fromisoformat(row["last_review_timestamp"])
    last_ltm_ts = (
        datetime.fromisoformat(row["last_ltm_timestamp"])
        if row["last_ltm_timestamp"]
        else None
    )

    return CardState(
        word_id=row["word_id"],
        exercise_type=row["exercise_type"],
        lemma=row["lemma"],
        pos=row["pos"],
        stability=row["stability"],
        difficulty=row["difficulty"],
        d_eff=row["d_eff"],
        review_count=row["review_count"],
        last_review_timestamp=last_review_ts,
        last_ltm_timestamp=last_ltm_ts,
        ltm_review_date=row["ltm_review_date"],
        stm_success_count_today=row["stm_success_count_today"]
    )


def save_card_state(card: CardState):
    """
    Save card state to database (insert or update).

    Args:
        card: CardState to save
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO card_state (
            word_id, exercise_type,
            lemma, pos,
            stability, difficulty, d_eff,
            review_count, last_review_timestamp, last_ltm_timestamp, ltm_review_date,
            stm_success_count_today
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        card.word_id,
        card.exercise_type,
        card.lemma,
        card.pos,
        card.stability,
        card.difficulty,
        card.d_eff,
        card.review_count,
        card.last_review_timestamp.isoformat(),
        card.last_ltm_timestamp.isoformat() if card.last_ltm_timestamp else None,
        card.ltm_review_date,
        card.stm_success_count_today
    ))

    conn.commit()
    conn.close()


def log_review_event(
    word_id: str,
    lemma: str,
    pos: str,
    exercise_type: str,
    timestamp: datetime,
    feedback_grade: FeedbackGrade,
    latency_ms: Optional[int],
    stability_before: Optional[float],
    difficulty_before: Optional[float],
    d_eff_before: Optional[float],
    retrievability_before: Optional[float],
    stability_after: float,
    difficulty_after: float,
    d_eff_after: float,
    is_ltm_event: bool,
    session_id: Optional[str] = None,
    session_position: Optional[int] = None
):
    """
    Log a review event to the database.

    Args:
        word_id: Unique word identifier
        lemma: Word lemma (for readability/analytics)
        pos: Part of speech (for readability/analytics)
        exercise_type: Type of exercise
        timestamp: Review timestamp
        feedback_grade: User feedback
        latency_ms: Response time in milliseconds
        stability_before: Stability before update (None for new cards)
        difficulty_before: Difficulty before update (None for new cards)
        d_eff_before: D_eff before update (None for new cards)
        retrievability_before: R before update (None for new cards)
        stability_after: Stability after update
        difficulty_after: Difficulty after update
        d_eff_after: D_eff after update
        is_ltm_event: True for LTM event, False for STM
        session_id: Optional session identifier (for analytics)
        session_position: Optional position in session (0-indexed, for analytics)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO review_events (
            word_id, exercise_type, lemma, pos,
            timestamp, feedback_grade, latency_ms,
            stability_before, difficulty_before, d_eff_before, retrievability_before,
            stability_after, difficulty_after, d_eff_after,
            is_ltm_event, session_id, session_position
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        word_id, exercise_type, lemma, pos,
        timestamp.isoformat(),
        int(feedback_grade),
        latency_ms,
        stability_before,
        difficulty_before,
        d_eff_before,
        retrievability_before,
        stability_after,
        difficulty_after,
        d_eff_after,
        1 if is_ltm_event else 0,
        session_id,
        session_position
    ))

    conn.commit()
    conn.close()


def get_all_cards_with_state(exercise_type: str) -> list[dict]:
    """
    Get all cards with their current state and retrievability.

    Args:
        exercise_type: Type of exercise to filter by

    Returns:
        List of dicts with card info and computed retrievability
    """
    from core.fsrs.memory_state import calculate_retrievability, get_days_since_ltm_review

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM card_state
        WHERE exercise_type = ?
        ORDER BY last_review_timestamp DESC
    """, (exercise_type,))

    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        last_ltm_ts = (
            datetime.fromisoformat(row["last_ltm_timestamp"])
            if row["last_ltm_timestamp"]
            else None
        )

        days_since = get_days_since_ltm_review(last_ltm_ts)
        retrievability = calculate_retrievability(row["stability"], days_since)

        result.append({
            "word_id": row["word_id"],
            "lemma": row["lemma"],
            "pos": row["pos"],
            "exercise_type": row["exercise_type"],
            "stability": row["stability"],
            "difficulty": row["difficulty"],
            "d_eff": row["d_eff"],
            "retrievability": retrievability,
            "review_count": row["review_count"],
            "last_review_timestamp": row["last_review_timestamp"],
            "last_ltm_timestamp": row["last_ltm_timestamp"],
            "stm_success_count_today": row["stm_success_count_today"]
        })

    return result


def get_due_cards(exercise_type: str, r_threshold: float = 0.70) -> list[dict]:
    """
    Get cards with retrievability below threshold (due for review).

    Args:
        exercise_type: Type of exercise to filter by
        r_threshold: Retrievability threshold (default: 0.70)

    Returns:
        List of due cards, sorted by retrievability (most urgent first)
    """
    all_cards = get_all_cards_with_state(exercise_type)

    # Filter by threshold
    due_cards = [c for c in all_cards if c["retrievability"] < r_threshold]

    # Sort by retrievability (lowest first = most urgent)
    due_cards.sort(key=lambda c: c["retrievability"])

    return due_cards


def get_recent_events(limit: int = 10) -> list[dict]:
    """
    Get recent review events.

    Args:
        limit: Maximum number of events to return

    Returns:
        List of recent events (newest first)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM review_events
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
