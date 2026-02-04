"""
Short-term memory (STM) state helpers.

STM is modeled as a launch-scoped dynamic set of (word_id, exercise_type) keys,
initialized from recent AGAIN events and updated during a session.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Set, Tuple

from core.fsrs.database import get_session
from core.fsrs.models import ReviewEvent as ReviewEventModel
from core.fsrs.constants import FeedbackGrade


StmKey = Tuple[str, str]


def build_stm_set(user_id: str, exercise_type: str) -> Set[StmKey]:
    """
    Build initial STM set from recent AGAIN events (today/yesterday).
    """
    session = get_session()
    try:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        events = session.query(
            ReviewEventModel.word_id,
            ReviewEventModel.exercise_type,
            ReviewEventModel.feedback_grade,
        ).filter(
            ReviewEventModel.user_id == user_id,
            ReviewEventModel.exercise_type == exercise_type,
            ReviewEventModel.timestamp >= yesterday_start,
            ReviewEventModel.feedback_grade == int(FeedbackGrade.AGAIN),
        ).all()

        return {(e.word_id, e.exercise_type) for e in events}
    finally:
        session.close()


def build_stm_words(
    stm_set: Set[StmKey],
    exercise_type: str,
    all_cards: list,
    lookup_word: callable
) -> list[dict]:
    """
    Convert STM set into word dictionaries for a given exercise type.

    Args:
        stm_set: Set of (word_id, exercise_type)
        exercise_type: Exercise type to filter
        all_cards: Snapshot of card states for this exercise
        lookup_word: Callable(word_id) -> word dict or None

    Returns:
        List of word dictionaries
    """
    card_map = {c.word_id: c for c in all_cards if c.word_id}
    stm_words = []
    for word_id, ex_type in stm_set:
        if ex_type != exercise_type:
            continue
        if word_id not in card_map:
            continue
        word = lookup_word(word_id)
        if word:
            stm_words.append(word)
    return stm_words


def update_stm_set(
    stm_set: Set[StmKey],
    word_id: str,
    exercise_type: str,
    feedback_grade: FeedbackGrade
) -> None:
    """
    Update STM set after a review.

    Rules:
    - AGAIN: add to STM
    - EASY: remove from STM
    - HARD/MEDIUM: keep if already present
    """
    key = (word_id, exercise_type)
    if feedback_grade == FeedbackGrade.AGAIN:
        stm_set.add(key)
    elif feedback_grade == FeedbackGrade.EASY:
        stm_set.discard(key)
