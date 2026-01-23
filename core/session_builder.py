"""
Scheduler - Three-Pool Session Creation

Creates study sessions from three distinct pools:
1. LTM pool: Cards with R < 0.70 (due for review)
2. STM pool: Cards marked AGAIN in last 0-1 calendar days
3. New pool: Cards never seen before

Session Logic:
- First session of day: LTM_FRACTION from LTM pool + NEW_FRACTION from new pool
  - If LTM insufficient, fill remainder with new cards
  - If no LTM history exists, b=1.0 (all new)
- Subsequent sessions: Priority order LTM > STM > New, all shuffled
"""

from __future__ import annotations
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from core import fsrs, lexicon_repo
from core.fsrs.constants import FeedbackGrade, R_TARGET

# ---- Session Configuration ----
SESSION_SIZE = 20           # Words per session
LTM_FRACTION = 0.75         # Fraction of first session from LTM pool (0-1)
NEW_FRACTION = 0.25         # Fraction of first session from new cards (0-1)
STM_MAX_AGE_DAYS = 1        # Max age for STM pool (0-1 days: today or yesterday)

assert abs(LTM_FRACTION + NEW_FRACTION - 1.0) < 0.001, "LTM_FRACTION + NEW_FRACTION must equal 1.0"


def create_session(
    exercise_type: str = "word_translation",
    tag: Optional[str] = None,
    user_id: str = "ben"
) -> list[dict]:
    """
    Create a study session using three-pool logic.

    Args:
        exercise_type: Type of exercise (default: "word_translation")
        tag: Optional tag filter for new cards
        user_id: User identifier for scoping review data

    Returns:
        List of word dictionaries for the session (shuffled)
    """
    # Determine if this is the first session today
    if _is_first_session_today(user_id):
        return _create_first_session(exercise_type, tag, user_id)
    else:
        return _create_subsequent_session(exercise_type, tag, user_id)


def _is_first_session_today(user_id: str) -> bool:
    """
    Check if this is the first session of the day.

    Logic: If any review event exists today, it's not the first session.
    """
    from core.fsrs.database import get_session
    from core.fsrs.models import ReviewEvent as ReviewEventModel
    from sqlalchemy import func

    session = get_session()
    try:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        count = session.query(func.count(ReviewEventModel.id)).filter(
            ReviewEventModel.user_id == user_id,
            ReviewEventModel.timestamp >= today_start.isoformat()
        ).scalar()
        
        return count == 0
    finally:
        session.close()


def _create_first_session(exercise_type: str, tag: Optional[str], user_id: str) -> list[dict]:
    """
    Create first session of the day.

    Logic:
    1. Get due cards (R < 0.70) from LTM pool
    2. If no LTM cards exist at all, use 100% new cards
    3. Otherwise, draw LTM_FRACTION from due cards (or all available if fewer)
    4. Fill remainder with new cards
    5. Shuffle final batch

    Args:
        exercise_type: Type of exercise
        tag: Optional tag filter for new cards
        user_id: User identifier for scoping review data

    Returns:
        Shuffled session batch
    """
    # Check if any LTM history exists
    all_cards = fsrs.get_all_cards_with_state(exercise_type, user_id)
    has_ltm_history = len(all_cards) > 0

    if not has_ltm_history:
        # No history: all new cards
        new_cards = _sample_new_cards(SESSION_SIZE, exercise_type, tag, user_id)
        random.shuffle(new_cards)
        return new_cards

    # Get due cards (R < R_TARGET)
    due_cards = fsrs.get_due_cards(exercise_type, user_id, r_threshold=R_TARGET)

    # Calculate target counts
    ltm_target = int(SESSION_SIZE * LTM_FRACTION)
    new_target = int(SESSION_SIZE * NEW_FRACTION)

    # Draw from LTM (or all available if fewer)
    ltm_count = min(ltm_target, len(due_cards))
    ltm_batch = due_cards[:ltm_count]

    # Fill remainder with new cards
    new_count = SESSION_SIZE - ltm_count
    new_batch = _sample_new_cards(new_count, exercise_type, tag, user_id)

    # Convert LTM cards to word dicts
    ltm_words = []
    for card in ltm_batch:
        # Use word_id if available, otherwise fall back to lemma/pos
        if "word_id" in card:
            word = lexicon_repo.get_word_by_id(card["word_id"])
        else:
            word = lexicon_repo.get_word_by_lemma_pos(card["lemma"], card["pos"])

        if word:
            ltm_words.append(word)

    # Combine and shuffle
    session = ltm_words + new_batch
    random.shuffle(session)

    return session


def _create_subsequent_session(exercise_type: str, tag: Optional[str], user_id: str) -> list[dict]:
    """
    Create subsequent session (not first of day).

    Logic:
    1. Priority order: LTM > STM > New
    2. Draw from each pool until SESSION_SIZE is reached
    3. Shuffle final batch

    Args:
        exercise_type: Type of exercise
        tag: Optional tag filter for new cards
        user_id: User identifier for scoping review data

    Returns:
        Shuffled session batch
    """
    session = []

    # 1. Draw from LTM pool (R < R_TARGET)
    due_cards = fsrs.get_due_cards(exercise_type, user_id, r_threshold=R_TARGET)
    ltm_count = min(len(due_cards), SESSION_SIZE)

    for card in due_cards[:ltm_count]:
        # Use word_id if available, otherwise fall back to lemma/pos
        if "word_id" in card:
            word = lexicon_repo.get_word_by_id(card["word_id"])
        else:
            word = lexicon_repo.get_word_by_lemma_pos(card["lemma"], card["pos"])

        if word:
            session.append(word)

    # 2. If not full, draw from STM pool (recent AGAIN)
    if len(session) < SESSION_SIZE:
        stm_pool = _get_stm_pool(exercise_type, user_id)
        stm_count = min(len(stm_pool), SESSION_SIZE - len(session))

        for card_info in stm_pool[:stm_count]:
            # STM pool only has lemma/pos, look up by those
            word = lexicon_repo.get_word_by_lemma_pos(card_info["lemma"], card_info["pos"])
            if word:
                session.append(word)

    # 3. If still not full, draw from new cards
    if len(session) < SESSION_SIZE:
        new_count = SESSION_SIZE - len(session)
        new_batch = _sample_new_cards(new_count, exercise_type, tag, user_id)
        session.extend(new_batch)

    # Shuffle and return
    random.shuffle(session)
    return session


def _get_stm_pool(exercise_type: str, user_id: str) -> list[dict]:
    """
    Get STM pool: cards marked AGAIN in last 0-1 calendar days.

    Logic:
    1. Query review_events for AGAIN feedback in today or yesterday
    2. Exclude cards where last review was EASY (they exit STM pool)
    3. Sort by most recent failure first (same-day failures prioritized)

    Args:
        exercise_type: Type of exercise
        user_id: User identifier for scoping review data

    Returns:
        List of card info dicts (lemma, pos, last_again_timestamp)
    """
    from core.fsrs.database import get_session
    from core.fsrs.models import ReviewEvent as ReviewEventModel
    from sqlalchemy import func, and_

    session = get_session()
    try:
        # Get start of today and yesterday (calendar days, not 48-hour window)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        # Find cards marked AGAIN in today or yesterday
        again_events = session.query(
            ReviewEventModel.lemma,
            ReviewEventModel.pos,
            func.max(ReviewEventModel.timestamp).label('last_again_timestamp')
        ).filter(
            and_(
                ReviewEventModel.user_id == user_id,
                ReviewEventModel.exercise_type == exercise_type,
                ReviewEventModel.feedback_grade == int(FeedbackGrade.AGAIN),
                ReviewEventModel.timestamp >= yesterday_start.isoformat()
            )
        ).group_by(ReviewEventModel.lemma, ReviewEventModel.pos).all()

        # Filter out cards where last review (any feedback) was EASY
        stm_pool = []
        for lemma, pos, last_again_timestamp in again_events:
            # Get last review event for this card
            last_review = session.query(ReviewEventModel.feedback_grade).filter(
                and_(
                    ReviewEventModel.user_id == user_id,
                    ReviewEventModel.lemma == lemma,
                    ReviewEventModel.pos == pos,
                    ReviewEventModel.exercise_type == exercise_type
                )
            ).order_by(ReviewEventModel.timestamp.desc()).first()

            # If last review was not EASY, card stays in STM pool
            if last_review and last_review.feedback_grade != int(FeedbackGrade.EASY):
                stm_pool.append({
                    "lemma": lemma,
                    "pos": pos,
                    "last_again_timestamp": last_again_timestamp
                })

        # Sort by most recent failure (same-day failures first)
        stm_pool.sort(key=lambda x: x["last_again_timestamp"], reverse=True)

        return stm_pool
    finally:
        session.close()


def _sample_new_cards(
    count: int,
    exercise_type: str,
    tag: Optional[str],
    user_id: str
) -> list[dict]:
    """
    Sample new cards (never reviewed before).

    Args:
        count: Number of cards to sample
        exercise_type: Type of exercise
        tag: Optional tag filter
        user_id: User identifier for scoping review data

    Returns:
        List of word dictionaries
    """
    if count <= 0:
        return []

    # Get all reviewed cards for this exercise type
    reviewed_cards = fsrs.get_all_cards_with_state(exercise_type, user_id)
    reviewed_set = {(card["lemma"], card["pos"]) for card in reviewed_cards}

    # Get all words from lexicon
    all_words = lexicon_repo.get_all_words()

    # Filter to new cards (not reviewed)
    new_words = [
        word for word in all_words
        if (word["lemma"], word["pos"]) not in reviewed_set
    ]

    # Apply tag filter if specified
    if tag:
        new_words = [word for word in new_words if _word_matches_tag(word, tag)]

    # Sample without replacement
    sample_size = min(count, len(new_words))
    return random.sample(new_words, sample_size)


def _word_matches_tag(word: dict, tag: str) -> bool:
    """
    Check if word matches tag filter.

    Args:
        word: Word dictionary
        tag: Tag to match

    Returns:
        True if word has the tag, False otherwise
    """
    word_tags = word.get("tags", [])
    if isinstance(word_tags, str):
        word_tags = [word_tags]
    return tag in word_tags
