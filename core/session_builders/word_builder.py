"""
Scheduler - Three-Pool Session Creation

Creates study sessions from three distinct pools:
1. LTM pool: Cards with R < 0.70 (due for review)
2. STM pool: Cards marked AGAIN in last 0-1 calendar days
3. New pool: Cards never seen before

Session Logic:
- Fill LTM due up to LTM_FRACTION
- Top up from STM
- Top up from NEW
"""

from __future__ import annotations
import random
from typing import Optional

from core import fsrs, lexicon_repo
from core.session_builders.pool_utils import due_cards_from_snapshot, fill_in_order, sample_new_words
from core.session_builders.pool_types import PoolItem
from core.session_builders.stm_state import build_stm_set, build_stm_words, StmKey
from core.fsrs.constants import R_TARGET

# ---- Session Configuration ----
SESSION_SIZE = 20           # Words per session
LTM_FRACTION = 0.75         # Fraction of session from LTM pool (0-1)


def build_word_base_pool(
    user_id: str,
    exercise_type: str = "word_translation"
) -> dict:
    """
    Build the base pool snapshot for word sessions (one-time per launch).

    Returns:
        Dict with all_words and all_cards snapshots
    """
    all_words = lexicon_repo.get_all_words()
    all_cards = fsrs.get_all_cards_with_state(exercise_type, user_id)
    return {
        "all_words": all_words,
        "all_cards": all_cards,
    }


def build_word_pools(
    base_pool: dict,
    exercise_type: str,
    stm_set: set[StmKey],
    r_threshold: float = R_TARGET
) -> dict[str, list[PoolItem]]:
    """
    Build word pools from a base snapshot and STM set.
    """
    all_words = base_pool["all_words"]
    all_cards = base_pool["all_cards"]

    word_id_map = {w.get("word_id"): w for w in all_words if w.get("word_id")}

    # LTM pool (due cards)
    due_cards = due_cards_from_snapshot(all_cards, r_threshold=r_threshold)
    ltm_target = int(SESSION_SIZE * LTM_FRACTION)
    ltm_words: list[PoolItem] = []
    for card in due_cards:
        if len(ltm_words) >= ltm_target:
            break
        word = word_id_map.get(card.word_id)
        if word:
            ltm_words.append(PoolItem(word=word, status="ltm"))

    # STM pool (from stm_set, excluding LTM)
    stm_words = build_stm_words(
        stm_set,
        exercise_type,
        all_cards,
        lambda word_id: word_id_map.get(word_id)
    )
    ltm_ids = {item.word.get("word_id") for item in ltm_words if item.word.get("word_id")}
    stm_items = [
        PoolItem(word=w, status="stm")
        for w in stm_words
        if w.get("word_id") not in ltm_ids
    ]

    # NEW pool
    reviewed_word_ids = {c.word_id for c in all_cards if c.word_id}
    new_words = sample_new_words(all_words, reviewed_word_ids, SESSION_SIZE)
    new_items = [PoolItem(word=w, status="new") for w in new_words]

    return {
        "ltm": ltm_words,
        "stm": stm_items,
        "new": new_items,
    }


def create_session(
    exercise_type: str = "word_translation",
    user_id: str = "ben",
    stm_set: Optional[set[StmKey]] = None,
    base_pool: Optional[dict] = None
) -> list[dict]:
    """
    Create a study session using three-pool logic.

    Args:
        exercise_type: Type of exercise (default: "word_translation")
        user_id: User identifier for scoping review data
        stm_set: Optional STM set for this launch (word_id, exercise_type)
        base_pool: Optional base pool snapshot (all_words/all_cards)

    Returns:
        List of word dictionaries for the session (shuffled)
    """
    if base_pool is None:
        base_pool = build_word_base_pool(user_id, exercise_type)
    if stm_set is None:
        stm_set = build_stm_set(user_id, exercise_type)

    pools = build_word_pools(base_pool, exercise_type, stm_set)
    session_items = fill_in_order(pools, ["ltm", "stm", "new"], SESSION_SIZE)
    random.shuffle(session_items)
    return [item.word for item in session_items]
