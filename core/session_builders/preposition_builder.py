"""
Preposition Drill Session Builder.

Creates sessions for preposition usage recall:
1. LTM pool: Cards with R < R_TARGET
2. STM pool: Cards marked AGAIN recently
3. New pool: Cards not yet reviewed in this exercise type
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from core import fsrs, lexicon_repo
from core.preposition_drill import build_preposition_usages
from core.session_builders.pool_types import PoolState
from core.session_builders.stm_state import build_stm_set
from core.fsrs.constants import (
    LTM_SESSION_FRACTION,
    PREPOSITION_FILTER_THRESHOLD,
    PREPOSITION_SESSION_SIZE,
    R_TARGET,
)


def build_preposition_pool_state(
    user_id: str,
    user_tags: Optional[Sequence[str]] = None,
    pos: Optional[Sequence[str]] = None,
    enriched_only: bool = False,
    r_threshold: float = PREPOSITION_FILTER_THRESHOLD,
    filter_known: bool = True,
) -> PoolState:
    """
    Build launch-scoped pool state for preposition drill sessions.
    """
    all_words = lexicon_repo.get_all_words(
        enriched_only=enriched_only,
        user_tags=user_tags,
        pos=pos,
    )

    # Only keep POS where preposition metadata is expected.
    candidate_words = [
        word
        for word in all_words
        if (word.get("pos") in {"verb", "noun", "adjective"})
    ]

    # Eligibility: at least one usable preposition usage with blankable examples.
    eligible_words = [word for word in candidate_words if build_preposition_usages(word)]
    word_map = {w.get("word_id"): w for w in eligible_words if w.get("word_id")}

    meaning_cards = fsrs.get_all_cards_with_state("word_translation", user_id)
    meaning_map = {card.word_id: card for card in meaning_cards if card.word_id}

    if filter_known and r_threshold > 0.0:
        word_map = {
            word_id: word
            for word_id, word in word_map.items()
            if word_id in meaning_map and meaning_map[word_id].retrievability >= r_threshold
        }

    exercise_type = "word_preposition"
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
        ltm_scores=ltm_scores,
    )


def create_preposition_session(
    pool_state: PoolState,
    session_size: int = PREPOSITION_SESSION_SIZE,
    ltm_fraction: float = LTM_SESSION_FRACTION,
) -> list[dict]:
    """
    Create preposition drill session using three-pool logic plus LTM fallback.
    """
    ltm_target = int(session_size * ltm_fraction)
    ltm_ids = sorted(
        pool_state.ltm,
        key=lambda word_id: pool_state.ltm_scores.get(word_id, 1.0),
    )
    session_ids = list(ltm_ids[:ltm_target])
    selected_ids = set(session_ids)

    if len(session_ids) < session_size:
        stm_ids = list(pool_state.stm)
        random.shuffle(stm_ids)
        for word_id in stm_ids:
            if len(session_ids) >= session_size:
                break
            if word_id in selected_ids:
                continue
            session_ids.append(word_id)
            selected_ids.add(word_id)

    if len(session_ids) < session_size:
        remaining = session_size - len(session_ids)
        new_ids = list(pool_state.new)
        if new_ids:
            sampled_new = random.sample(new_ids, min(remaining, len(new_ids)))
            session_ids.extend(sampled_new)
            selected_ids.update(sampled_new)

    if len(session_ids) < session_size:
        remaining = session_size - len(session_ids)
        remaining_ltm_ids = [word_id for word_id in ltm_ids if word_id not in selected_ids]
        if remaining_ltm_ids:
            sampled_ltm = remaining_ltm_ids[:remaining]
            session_ids.extend(sampled_ltm)
            selected_ids.update(sampled_ltm)

    if len(session_ids) < session_size:
        remaining = session_size - len(session_ids)
        known_ids = [word_id for word_id in pool_state.known if word_id not in selected_ids]
        if known_ids:
            sampled_known = random.sample(known_ids, min(remaining, len(known_ids)))
            session_ids.extend(sampled_known)
            selected_ids.update(sampled_known)

    words = [pool_state.word_map[word_id] for word_id in session_ids if word_id in pool_state.word_map]
    random.shuffle(words)
    return words
