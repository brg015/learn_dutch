"""
Scheduling - Main FSRS API for Review Management

This module ties together all FSRS components and provides the main API
for logging reviews and updating card state.

Main workflow:
1. User reviews a card
2. System determines if it's LTM or STM event
3. Apply appropriate update rules
4. Save state and log event
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from core.fsrs import memory_state, ltm_updates, stm_updates, persistence
from core.fsrs.constants import FeedbackGrade


def log_review(
    lemma: str,
    pos: str,
    exercise_type: str,
    feedback_grade: FeedbackGrade,
    latency_ms: Optional[int] = None,
    timestamp: Optional[datetime] = None
):
    """
    Log a review and update card state using FSRS algorithm.

    This is the main entry point for the FSRS system.

    Workflow:
    1. Load card state (or initialize new card)
    2. Determine if LTM or STM event
    3. Calculate retrievability
    4. Apply appropriate update rules
    5. Save state and log event

    Args:
        lemma: Word lemma
        pos: Part of speech
        exercise_type: Type of exercise
        feedback_grade: User feedback (AGAIN, HARD, MEDIUM, EASY)
        latency_ms: Response time in milliseconds (optional)
        timestamp: Review timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Load existing card state or initialize new card
    card = persistence.load_card_state(lemma, pos, exercise_type)

    if card is None:
        # New card - first review ever
        card = memory_state.initialize_new_card(lemma, pos, exercise_type)
        is_new_card = True
    else:
        is_new_card = False

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

    # Save updated state
    persistence.save_card_state(card)

    # Log event
    persistence.log_review_event(
        lemma=lemma,
        pos=pos,
        exercise_type=exercise_type,
        timestamp=timestamp,
        feedback_grade=feedback_grade,
        latency_ms=latency_ms,
        stability_before=stability_before,
        difficulty_before=difficulty_before,
        d_eff_before=d_eff_before,
        retrievability_before=retrievability_before,
        stability_after=card.stability,
        difficulty_after=card.difficulty,
        d_eff_after=card.d_eff,
        is_ltm_event=is_ltm
    )


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


# ---- Convenience functions for scheduler ----

def get_card_state(
    lemma: str,
    pos: str,
    exercise_type: str
) -> Optional[memory_state.CardState]:
    """
    Get current card state.

    Args:
        lemma: Word lemma
        pos: Part of speech
        exercise_type: Type of exercise

    Returns:
        CardState if card has been reviewed, None otherwise
    """
    return persistence.load_card_state(lemma, pos, exercise_type)


def get_due_cards(exercise_type: str) -> list[dict]:
    """
    Get all cards due for review (R < 0.70).

    Args:
        exercise_type: Type of exercise

    Returns:
        List of due cards sorted by urgency (lowest R first)
    """
    return persistence.get_due_cards(exercise_type)


def get_all_cards_with_state(exercise_type: str) -> list[dict]:
    """
    Get all reviewed cards with their current state.

    Args:
        exercise_type: Type of exercise

    Returns:
        List of all cards with state info
    """
    return persistence.get_all_cards_with_state(exercise_type)


def get_recent_events(limit: int = 10) -> list[dict]:
    """
    Get recent review events.

    Args:
        limit: Maximum number of events

    Returns:
        List of recent events (newest first)
    """
    return persistence.get_recent_events(limit)
