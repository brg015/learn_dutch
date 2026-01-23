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

    # Process a review (algorithm only, no DB calls)
    card, event_data = fsrs.process_review(card, feedback_grade)

    # Get due cards
    due_cards = fsrs.get_due_cards("word_translation")
"""

# Core scheduler API (algorithm logic)
from core.fsrs.scheduler import process_review

# Database API
from core.fsrs.database import (
    init_db,
    reset_db,
    is_test_mode,
    load_card_state,
    save_card_state,
    batch_save_card_states,
    batch_log_review_events,
    get_card_state,
    get_due_cards,
    get_all_cards_with_state,
    get_recent_events
)

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
    # Core algorithm
    "process_review",
    
    # Database operations
    "init_db",
    "reset_db",
    "is_test_mode",
    "load_card_state",
    "save_card_state",
    "batch_save_card_states",
    "batch_log_review_events",
    "get_card_state",
    "get_due_cards",
    "get_all_cards_with_state",
    "get_recent_events",

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
