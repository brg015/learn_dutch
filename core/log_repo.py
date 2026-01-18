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
from enum import Enum

# Configuration
DB_PATH = Path("logs/reviews.sqlite")


# ---- Enums ----

class FeedbackGrade(Enum):
    """User feedback grades for FSRS algorithm."""
    AGAIN = 1   # Completely forgot
    HARD = 2    # Remembered with difficulty
    MEDIUM = 3  # Remembered normally
    EASY = 4    # Remembered easily


# ---- Schema ----

def init_db(db_path: Path = DB_PATH) -> None:
    """
    Initialize the SQLite database with review_events and card_state tables.

    Creates the logs directory if it doesn't exist.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Append-only event log (immutable history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            lemma TEXT NOT NULL,
            pos TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            feedback_grade INTEGER NOT NULL,  -- FeedbackGrade enum value (1-4)
            latency_ms INTEGER,                -- Optional: time to answer in milliseconds
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Current FSRS state per card (mutable, updated after each review)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_state (
            lemma TEXT NOT NULL,
            pos TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            stability REAL NOT NULL,           -- S parameter (days)
            difficulty REAL NOT NULL,          -- D parameter (0-10 scale)
            last_review_timestamp TEXT NOT NULL,
            review_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (lemma, pos, exercise_type)
        )
    """)

    # Indexes for review_events
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_review_lemma_pos_exercise
        ON review_events(lemma, pos, exercise_type)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_review_timestamp
        ON review_events(timestamp DESC)
    """)

    # Index for card_state (for scheduling queries)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_card_last_review
        ON card_state(last_review_timestamp)
    """)

    conn.commit()
    conn.close()


# ---- FSRS Algorithm ----

# FSRS default parameters (based on FSRS-4.5 defaults)
DEFAULT_STABILITY = 1.0  # Initial stability in days
DEFAULT_DIFFICULTY = 5.0  # Initial difficulty (0-10 scale)
RETRIEVABILITY_THRESHOLD = 0.70  # Target recall probability

# FSRS weight parameters (simplified version)
# These control how S and D change based on feedback
W = {
    'stability_increase': {
        FeedbackGrade.AGAIN: 0.4,   # Failed recall reduces stability
        FeedbackGrade.HARD: 1.2,    # Hard recall slight increase
        FeedbackGrade.MEDIUM: 2.5,  # Medium recall good increase
        FeedbackGrade.EASY: 4.0,    # Easy recall large increase
    },
    'difficulty_change': {
        FeedbackGrade.AGAIN: 0.5,   # Failure increases difficulty
        FeedbackGrade.HARD: 0.2,    # Hard increases difficulty slightly
        FeedbackGrade.MEDIUM: -0.1, # Medium decreases difficulty slightly
        FeedbackGrade.EASY: -0.3,   # Easy decreases difficulty more
    }
}


def calculate_retrievability(
    stability: float,
    difficulty: float,
    days_since_review: float
) -> float:
    """
    Calculate current retrievability (probability of recall) for a card.

    Uses the FSRS forgetting curve formula:
    R = exp(ln(0.9) * days_since_review / stability)

    Args:
        stability: Current stability in days
        difficulty: Current difficulty (0-10)
        days_since_review: Days elapsed since last review

    Returns:
        Retrievability as probability (0.0 to 1.0)
    """
    import math

    if days_since_review <= 0:
        return 1.0  # Just reviewed

    # Forgetting curve: R = 0.9^(t/S)
    # Where t = days since review, S = stability
    return math.pow(0.9, days_since_review / stability)


def _update_card_state(
    cursor: sqlite3.Cursor,
    lemma: str,
    pos: str,
    exercise_type: str,
    feedback_grade: FeedbackGrade,
    timestamp: str
) -> None:
    """
    Update FSRS card state after a review (internal helper).

    Creates new card if first review, otherwise updates existing state.
    """
    import math

    # Check if card exists
    cursor.execute("""
        SELECT stability, difficulty, last_review_timestamp, review_count
        FROM card_state
        WHERE lemma = ? AND pos = ? AND exercise_type = ?
    """, (lemma, pos, exercise_type))

    row = cursor.fetchone()

    if row is None:
        # First review: initialize new card
        new_stability = DEFAULT_STABILITY * W['stability_increase'][feedback_grade]
        new_difficulty = DEFAULT_DIFFICULTY + W['difficulty_change'][feedback_grade]
        new_difficulty = max(1.0, min(10.0, new_difficulty))  # Clamp to [1, 10]

        cursor.execute("""
            INSERT INTO card_state (lemma, pos, exercise_type, stability, difficulty, last_review_timestamp, review_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (lemma, pos, exercise_type, new_stability, new_difficulty, timestamp))
    else:
        # Update existing card
        old_stability, old_difficulty, last_timestamp, review_count = row

        # Calculate days since last review
        last_dt = datetime.fromisoformat(last_timestamp)
        current_dt = datetime.fromisoformat(timestamp)
        days_elapsed = (current_dt - last_dt).total_seconds() / 86400.0

        # Calculate current retrievability before this review
        current_R = calculate_retrievability(old_stability, old_difficulty, days_elapsed)

        # Update stability based on feedback and current retrievability
        # Successful recall (MEDIUM/EASY) increases stability
        # Failed recall (AGAIN) decreases stability
        # The multiplier depends on how much was forgotten
        if feedback_grade == FeedbackGrade.AGAIN:
            # Failed: reduce stability
            new_stability = old_stability * W['stability_increase'][feedback_grade]
        else:
            # Successful: increase stability based on grade
            # If retrieved when R was low, bigger stability boost
            retrievability_factor = 1.0 + (1.0 - current_R)
            new_stability = old_stability * W['stability_increase'][feedback_grade] * retrievability_factor

        # Update difficulty
        new_difficulty = old_difficulty + W['difficulty_change'][feedback_grade]
        new_difficulty = max(1.0, min(10.0, new_difficulty))  # Clamp to [1, 10]

        # Ensure minimum stability
        new_stability = max(0.1, new_stability)

        cursor.execute("""
            UPDATE card_state
            SET stability = ?, difficulty = ?, last_review_timestamp = ?, review_count = ?
            WHERE lemma = ? AND pos = ? AND exercise_type = ?
        """, (new_stability, new_difficulty, timestamp, review_count + 1, lemma, pos, exercise_type))


# ---- Logging Functions ----

def log_review(
    lemma: str,
    pos: str,
    exercise_type: str,
    feedback_grade: FeedbackGrade,
    latency_ms: Optional[int] = None,
    db_path: Path = DB_PATH
) -> None:
    """
    Log a single review event and update FSRS card state.

    Args:
        lemma: The word lemma
        pos: Part of speech
        exercise_type: Type of exercise (e.g., "word_translation", "past_tense")
        feedback_grade: User's graded feedback (AGAIN/HARD/MEDIUM/EASY)
        latency_ms: Optional response time in milliseconds
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Append to immutable event log
    cursor.execute("""
        INSERT INTO review_events (timestamp, lemma, pos, exercise_type, feedback_grade, latency_ms)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        lemma,
        pos,
        exercise_type,
        feedback_grade.value,
        latency_ms
    ))

    # 2. Update or create card state
    _update_card_state(cursor, lemma, pos, exercise_type, feedback_grade, timestamp)

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


# ---- FSRS Card State Functions ----

def get_card_state(
    lemma: str,
    pos: str,
    exercise_type: str,
    db_path: Path = DB_PATH
) -> Optional[dict]:
    """
    Get current FSRS state for a specific card.

    Args:
        lemma: The word lemma
        pos: Part of speech
        exercise_type: Type of exercise
        db_path: Path to SQLite database

    Returns:
        Dict with stability, difficulty, last_review_timestamp, review_count, retrievability
        Returns None if card has never been reviewed
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT stability, difficulty, last_review_timestamp, review_count
        FROM card_state
        WHERE lemma = ? AND pos = ? AND exercise_type = ?
    """, (lemma, pos, exercise_type))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    stability, difficulty, last_timestamp, review_count = row

    # Calculate current retrievability
    last_dt = datetime.fromisoformat(last_timestamp)
    current_dt = datetime.now(timezone.utc)
    days_elapsed = (current_dt - last_dt).total_seconds() / 86400.0

    retrievability = calculate_retrievability(stability, difficulty, days_elapsed)

    return {
        'lemma': lemma,
        'pos': pos,
        'exercise_type': exercise_type,
        'stability': stability,
        'difficulty': difficulty,
        'last_review_timestamp': last_timestamp,
        'review_count': review_count,
        'retrievability': retrievability,
        'days_since_review': days_elapsed
    }


def get_due_cards(
    exercise_type: str = 'word_translation',
    threshold: float = RETRIEVABILITY_THRESHOLD,
    db_path: Path = DB_PATH
) -> list[dict]:
    """
    Get all cards that are due for review (retrievability below threshold).

    Cards are sorted by retrievability (most urgent first).

    Args:
        exercise_type: Type of exercise to filter by
        threshold: Retrievability threshold (default 0.70)
        db_path: Path to SQLite database

    Returns:
        List of card state dicts, sorted by retrievability ascending
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lemma, pos, stability, difficulty, last_review_timestamp, review_count
        FROM card_state
        WHERE exercise_type = ?
    """, (exercise_type,))

    rows = cursor.fetchall()
    conn.close()

    due_cards = []
    current_dt = datetime.now(timezone.utc)

    for lemma, pos, stability, difficulty, last_timestamp, review_count in rows:
        last_dt = datetime.fromisoformat(last_timestamp)
        days_elapsed = (current_dt - last_dt).total_seconds() / 86400.0

        retrievability = calculate_retrievability(stability, difficulty, days_elapsed)

        if retrievability <= threshold:
            due_cards.append({
                'lemma': lemma,
                'pos': pos,
                'exercise_type': exercise_type,
                'stability': stability,
                'difficulty': difficulty,
                'last_review_timestamp': last_timestamp,
                'review_count': review_count,
                'retrievability': retrievability,
                'days_since_review': days_elapsed
            })

    # Sort by retrievability (most at risk first)
    due_cards.sort(key=lambda x: x['retrievability'])

    return due_cards


def get_all_cards_with_state(
    exercise_type: str = 'word_translation',
    db_path: Path = DB_PATH
) -> list[dict]:
    """
    Get all cards with their current FSRS state and retrievability.

    Useful for analytics and debugging.

    Args:
        exercise_type: Type of exercise to filter by
        db_path: Path to SQLite database

    Returns:
        List of card state dicts with retrievability computed
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lemma, pos, stability, difficulty, last_review_timestamp, review_count
        FROM card_state
        WHERE exercise_type = ?
    """, (exercise_type,))

    rows = cursor.fetchall()
    conn.close()

    cards = []
    current_dt = datetime.now(timezone.utc)

    for lemma, pos, stability, difficulty, last_timestamp, review_count in rows:
        last_dt = datetime.fromisoformat(last_timestamp)
        days_elapsed = (current_dt - last_dt).total_seconds() / 86400.0

        retrievability = calculate_retrievability(stability, difficulty, days_elapsed)

        cards.append({
            'lemma': lemma,
            'pos': pos,
            'exercise_type': exercise_type,
            'stability': stability,
            'difficulty': difficulty,
            'last_review_timestamp': last_timestamp,
            'review_count': review_count,
            'retrievability': retrievability,
            'days_since_review': days_elapsed
        })

    return cards


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
            feedback_grade,
            latency_ms
        FROM review_events
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    events = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return events
