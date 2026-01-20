"""
FSRS - Free Spaced Repetition Scheduler

Main API for the vocabulary learning system.

This module implements a principled spaced repetition algorithm with:
- Long-Term Memory (LTM) updates for spaced retrieval
- Short-Term Memory (STM) practice for fluency repair
- Exponential forgetting curve: R = exp(-Δt/S)
- Interpretable memory state (Stability, Difficulty, Retrievability)

Quick start:
    from core import fsrs

    # Initialize database
    fsrs.init_db()

    # Log a review
    fsrs.log_review(
        lemma="verrekijker",
        pos="noun",
        exercise_type="word_translation",
        feedback_grade=fsrs.FeedbackGrade.MEDIUM
    )

    # Get due cards
    due_cards = fsrs.get_due_cards("word_translation")
"""

# Main scheduling API
from core.fsrs.review_logger import (
    log_review,
    get_card_state,
    get_due_cards,
    get_all_cards_with_state,
    get_recent_events
)

# Database initialization
from core.fsrs.persistence import init_db

# Constants and parameters
from core.fsrs.constants import (
    FeedbackGrade,
    R_TARGET,
    S_MIN,
    D_MIN,
    D_MAX,
    K,
    K_FAIL,
    ALPHA,
    ETA,
    BASE_GAIN,
    U_RATING
)

# Memory state (for advanced usage)
from core.fsrs.memory_state import (
    CardState,
    calculate_retrievability,
    get_days_since_ltm_review,
    is_ltm_event
)


__all__ = [
    # Main API
    "log_review",
    "get_card_state",
    "get_due_cards",
    "get_all_cards_with_state",
    "get_recent_events",
    "init_db",

    # Enums
    "FeedbackGrade",

    # Memory state
    "CardState",
    "calculate_retrievability",
    "get_days_since_ltm_review",
    "is_ltm_event",

    # Parameters
    "R_TARGET",
    "S_MIN",
    "D_MIN",
    "D_MAX",
    "K",
    "K_FAIL",
    "ALPHA",
    "ETA",
    "BASE_GAIN",
    "U_RATING",
]
