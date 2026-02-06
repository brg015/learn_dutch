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

from core import fsrs, lexicon_repo
from core.session_builders.pool_types import PoolState
from core.session_builders.stm_state import build_stm_set
from core.fsrs.constants import R_TARGET

# ---- Session Configuration ----
SESSION_SIZE = 20           # Words per session
LTM_FRACTION = 0.75         # Fraction of session from LTM pool (0-1)


def build_word_pool_state(
    user_id: str,
    exercise_type: str = "word_translation"
) -> PoolState:
    """
    Build launch-scoped pool state for word sessions.
    """
    all_words = lexicon_repo.get_all_words()
    word_map = {w.get("word_id"): w for w in all_words if w.get("word_id")}

    snapshots = fsrs.get_all_cards_with_state(exercise_type, user_id)
    r_by_id = {snap.word_id: snap.retrievability for snap in snapshots}

    ltm: set[str] = set()
    known: set[str] = set()
    new: set[str] = set(word_map.keys())

    for word_id, r_value in r_by_id.items():
        if word_id not in word_map:
            continue
        new.discard(word_id)
        if r_value < R_TARGET:
            ltm.add(word_id)
        else:
            known.add(word_id)

    stm_set = build_stm_set(user_id, exercise_type)
    stm_ids = {
        word_id for (word_id, ex_type) in stm_set
        if ex_type == exercise_type and word_id in word_map
    }

    for word_id in stm_ids:
        ltm.discard(word_id)
        new.discard(word_id)
        known.discard(word_id)

    ltm_scores = {word_id: r_by_id[word_id] for word_id in ltm if word_id in r_by_id}

    return PoolState(
        word_map=word_map,
        ltm=ltm,
        stm=set(stm_ids),
        new=new,
        known=known,
        ltm_scores=ltm_scores
    )


def create_session(
    pool_state: PoolState,
    session_size: int = SESSION_SIZE,
    ltm_fraction: float = LTM_FRACTION
) -> list[dict]:
    """
    Create a study session using three-pool logic.

    Args:
        pool_state: Launch-scoped pool state
        session_size: Number of words in the session
        ltm_fraction: Fraction of session pulled from LTM

    Returns:
        List of word dictionaries for the session (shuffled)
    """
    ltm_target = int(session_size * ltm_fraction)
    ltm_ids = sorted(
        pool_state.ltm,
        key=lambda word_id: pool_state.ltm_scores.get(word_id, 1.0)
    )
    session_ids = list(ltm_ids[:ltm_target])

    if len(session_ids) < session_size:
        stm_ids = list(pool_state.stm)
        random.shuffle(stm_ids)
        for word_id in stm_ids:
            if len(session_ids) >= session_size:
                break
            session_ids.append(word_id)

    if len(session_ids) < session_size:
        remaining = session_size - len(session_ids)
        new_ids = list(pool_state.new)
        if new_ids:
            session_ids.extend(random.sample(new_ids, min(remaining, len(new_ids))))

    words = [pool_state.word_map[word_id] for word_id in session_ids if word_id in pool_state.word_map]
    random.shuffle(words)
    return words
