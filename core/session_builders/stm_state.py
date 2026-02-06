"""
Short-term memory (STM) state helpers.

STM is modeled as a launch-scoped set of (word_id, exercise_type) keys,
initialized from recent AGAIN events. Session updates are applied to pool state.
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
