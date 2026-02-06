"""
Pool utilities for session builders.

These helpers provide shared, minimal primitives for building and reasoning
about session pools without enforcing a single scheduling policy.
"""

from __future__ import annotations

from core.fsrs.constants import FeedbackGrade
from core.session_builders.pool_types import PoolState


def update_pool_state(
    pool_state: PoolState,
    word_id: str,
    feedback_grade: FeedbackGrade
) -> None:
    """
    Update pool membership based on feedback.
    """
    if word_id not in pool_state.word_map:
        return

    if feedback_grade == FeedbackGrade.AGAIN:
        pool_state.move_to(word_id, "stm")
        pool_state.ltm_scores.pop(word_id, None)
        return

    if word_id in pool_state.stm:
        if feedback_grade == FeedbackGrade.EASY:
            pool_state.move_to(word_id, "known")
        return

    if word_id in pool_state.ltm or word_id in pool_state.new:
        pool_state.move_to(word_id, "known")
        pool_state.ltm_scores.pop(word_id, None)
