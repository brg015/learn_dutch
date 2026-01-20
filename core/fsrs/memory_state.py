"""
Memory State - FSRS Card State and Retrievability

Defines the core memory state variables and derived quantities for FSRS.

Key concepts:
- Stability (S): How slowly memory decays (in days)
- Difficulty (D): How hard the card is to learn (1-10 scale)
- Retrievability (R): Probability of successful recall at time t
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import math


@dataclass
class CardState:
    """
    Memory state for a single card.

    A card is defined as: (lemma, pos, exercise_type)
    """
    lemma: str
    pos: str
    exercise_type: str

    # Long-term memory parameters (persistent)
    stability: float  # S, in days
    difficulty: float  # D, range 1-10

    # Effective difficulty (used for next LTM update, reset after)
    d_eff: float  # D_eff, modified by STM practice

    # Review tracking
    review_count: int  # Total number of reviews (LTM + STM)
    last_review_timestamp: datetime  # Most recent review (any type)
    last_ltm_timestamp: Optional[datetime]  # Most recent LTM review
    ltm_review_date: Optional[str]  # Date of last LTM review (YYYY-MM-DD)

    # Short-term memory tracking (reset daily after LTM event)
    stm_success_count_today: int  # Number of STM successes since last LTM

    def __post_init__(self):
        """Ensure D_eff is initialized if not set."""
        if self.d_eff is None:
            self.d_eff = self.difficulty


def calculate_retrievability(
    stability: float,
    days_since_ltm_review: float
) -> float:
    """
    Calculate retrievability using exponential decay.

    Formula: R = exp(-Δt / S)

    Where:
    - Δt = time since last LTM review (in days)
    - S = stability (in days)

    Interpretation:
    - Immediately after review: R ≈ 1.0 (100% recall probability)
    - As time passes: R decays smoothly
    - When R drops below threshold (e.g. 0.70), card becomes "due"

    Args:
        stability: Current stability in days
        days_since_ltm_review: Time since last LTM review in days

    Returns:
        Retrievability between 0 and 1
    """
    if days_since_ltm_review <= 0:
        return 1.0

    # R = exp(-Δt / S)
    return math.exp(-days_since_ltm_review / stability)


def get_days_since_ltm_review(last_ltm_timestamp: Optional[datetime]) -> float:
    """
    Calculate days since last LTM review.

    Args:
        last_ltm_timestamp: Timestamp of last LTM review, or None for new cards

    Returns:
        Days since LTM review (0 if never reviewed)
    """
    if last_ltm_timestamp is None:
        return 0.0

    now = datetime.now(timezone.utc)
    delta = now - last_ltm_timestamp
    return delta.total_seconds() / 86400.0  # Convert to days


def is_ltm_event(
    last_ltm_timestamp: Optional[datetime],
    current_timestamp: datetime
) -> bool:
    """
    Determine if this review is an LTM event.

    LTM event = first review of the day for this card.

    Logic:
    - If never reviewed before (last_ltm_timestamp is None) -> LTM
    - If last LTM review was on a different day -> LTM
    - If last LTM review was today -> STM

    Args:
        last_ltm_timestamp: Timestamp of last LTM review
        current_timestamp: Timestamp of current review

    Returns:
        True if this is an LTM event, False if STM
    """
    if last_ltm_timestamp is None:
        # First review ever -> LTM
        return True

    # Compare dates (ignoring time)
    last_date = last_ltm_timestamp.date()
    current_date = current_timestamp.date()

    # Different day -> LTM
    return last_date != current_date


def initialize_new_card(
    lemma: str,
    pos: str,
    exercise_type: str,
    initial_stability: float = 0.5,
    initial_difficulty: float = 5.0
) -> CardState:
    """
    Initialize state for a new card (never seen before).

    Args:
        lemma: Word lemma
        pos: Part of speech
        exercise_type: Type of exercise
        initial_stability: Starting stability (default: 0.5 days)
        initial_difficulty: Starting difficulty (default: 5.0, middle of 1-10 scale)

    Returns:
        New CardState initialized with defaults
    """
    now = datetime.now(timezone.utc)

    return CardState(
        lemma=lemma,
        pos=pos,
        exercise_type=exercise_type,
        stability=initial_stability,
        difficulty=initial_difficulty,
        d_eff=initial_difficulty,
        review_count=0,
        last_review_timestamp=now,
        last_ltm_timestamp=None,
        ltm_review_date=None,
        stm_success_count_today=0
    )
