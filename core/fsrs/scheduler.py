"""
Scheduler - FSRS Algorithm Logic

Pure FSRS scheduling and state updates (no database calls).

Main workflow:
1. Load card state (caller's responsibility)
2. Determine if LTM or STM event
3. Calculate retrievability
4. Apply appropriate update rules
5. Return updated card + event data dict

This module handles ONLY the algorithm logic.
Database I/O is handled by the database module.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Tuple

from core.fsrs import memory_state, ltm_updates, stm_updates
from core.fsrs.constants import FeedbackGrade


def process_review(
    card: memory_state.CardState,
    feedback_grade: FeedbackGrade,
    timestamp: Optional[datetime] = None
) -> Tuple[memory_state.CardState, dict]:
    """
    Process a review and return updated card state + event data.
    
    This is the core FSRS algorithm. No database calls.
    Caller is responsible for:
    1. Loading the card
    2. Saving the card after review
    3. Persisting the event
    
    Args:
        card: CardState to update (may be new or existing)
        feedback_grade: User feedback (AGAIN, HARD, MEDIUM, EASY)
        timestamp: Review timestamp (defaults to now)
        
    Returns:
        Tuple of (updated_card, event_data_dict)
        event_data_dict is ready to pass to database.batch_log_review_events()
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Detect if this is a new card
    is_new_card = card.review_count == 0

    # Save state before update (for logging)
    stability_before = card.stability if not is_new_card else None
    difficulty_before = card.difficulty if not is_new_card else None
    d_eff_before = card.d_eff if not is_new_card else None

    # Determine if this is LTM or STM event
    is_ltm = memory_state.is_ltm_event(card.last_ltm_timestamp, timestamp)

    # Calculate retrievability before update
    if is_new_card:
        retrievability_before = None
    else:
        days_since_ltm = memory_state.get_days_since_ltm_review(card.last_ltm_timestamp)
        retrievability_before = memory_state.calculate_retrievability(
            card.stability,
            days_since_ltm
        )

    # Apply appropriate update rules
    if is_ltm:
        _apply_ltm_update(card, feedback_grade, retrievability_before, timestamp)
    else:
        _apply_stm_update(card, feedback_grade, timestamp)

    # Increment review count
    card.review_count += 1

    # Build event data dict (ready to persist)
    event_data = {
        'word_id': card.word_id,
        'lemma': card.lemma,
        'pos': card.pos,
        'exercise_type': card.exercise_type,
        'timestamp': timestamp,
        'feedback_grade': feedback_grade,
        'latency_ms': None,  # Will be set by caller if needed
        'stability_before': stability_before,
        'difficulty_before': difficulty_before,
        'd_eff_before': d_eff_before,
        'retrievability_before': retrievability_before,
        'stability_after': card.stability,
        'difficulty_after': card.difficulty,
        'd_eff_after': card.d_eff,
        'is_ltm_event': is_ltm,
        'session_id': None,  # Will be set by caller if needed
        'session_position': None,  # Will be set by caller if needed
        'presentation_mode': None  # Will be set by caller if needed
    }

    return card, event_data


def _apply_ltm_update(
    card: memory_state.CardState,
    feedback_grade: FeedbackGrade,
    retrievability: Optional[float],
    timestamp: datetime
):
    """
    Apply LTM update rules to card state (modifies in place).

    LTM updates:
    - Update stability (S)
    - Update difficulty (D)
    - Compute D_floor for STM
    - Reset D_eff to new D
    - Reset STM success count
    - Update LTM timestamp

    Args:
        card: CardState to update (modified in place)
        feedback_grade: User feedback
        retrievability: Current retrievability (None for new cards)
        timestamp: Review timestamp
    """
    # For new cards, use initial retrievability of 1.0
    is_new = retrievability is None
    if is_new:
        retrievability = 1.0

    # Apply LTM update formulas
    new_stability, new_difficulty, d_floor = ltm_updates.apply_ltm_update(
        stability=card.stability,
        difficulty=card.difficulty,
        d_eff=card.d_eff,
        retrievability=retrievability,
        feedback_grade=feedback_grade,
        is_new_card=is_new
    )

    # Update card state
    card.stability = new_stability
    card.difficulty = new_difficulty
    card.d_eff = new_difficulty  # Reset D_eff to new D after LTM event
    card.last_review_timestamp = timestamp
    card.last_ltm_timestamp = timestamp
    card.ltm_review_date = timestamp.date().isoformat()
    card.stm_success_count_today = 0  # Reset STM count


def _apply_stm_update(
    card: memory_state.CardState,
    feedback_grade: FeedbackGrade,
    timestamp: datetime
):
    """
    Apply STM update rules to card state (modifies in place).

    STM updates:
    - Update D_eff (if successful)
    - Increment STM success count (if successful)
    - Update last review timestamp (but NOT last_ltm_timestamp)

    STM does NOT update S or D.

    Args:
        card: CardState to update (modified in place)
        feedback_grade: User feedback
        timestamp: Review timestamp
    """
    # Only update D_eff for successful retrievals
    if stm_updates.should_update_d_eff(feedback_grade):
        # Compute D_floor from current state
        days_since_ltm = memory_state.get_days_since_ltm_review(card.last_ltm_timestamp)
        retrievability = memory_state.calculate_retrievability(card.stability, days_since_ltm)
        d_floor = ltm_updates.compute_d_floor(card.difficulty, retrievability)

        # Update D_eff with diminishing returns
        new_d_eff = stm_updates.apply_stm_success_update(
            d_eff=card.d_eff,
            d_floor=d_floor,
            stm_success_count=card.stm_success_count_today
        )

        card.d_eff = new_d_eff
        card.stm_success_count_today += 1

    # Update timestamp (but not LTM timestamp)
    card.last_review_timestamp = timestamp
