"""
Verb Tense Session Builder - Pool State

Creates verb conjugation study sessions from launch-scoped pools:
1. LTM pool: Verbs due if either tense is below threshold
2. STM pool: Verbs recently missed (today/yesterday)
3. New pool: Verbs with no conjugation state yet (meaning known)
4. Known pool: Verbs with both tenses above threshold
"""

from __future__ import annotations
import random
from typing import Optional, Sequence

from core import fsrs, lexicon_repo
from core.session_builders.pool_types import PoolState
from core.session_builders.stm_state import build_stm_set
from core.fsrs.constants import (
    LTM_SESSION_FRACTION,
    R_TARGET,
    VERB_FILTER_THRESHOLD,
    VERB_SESSION_SIZE,
)


def build_verb_pool_state(
    user_id: str,
    r_threshold: float = R_TARGET,
    filter_known: bool = True,
    user_tags: Optional[Sequence[str]] = None,
    pos: Optional[Sequence[str]] = None
) -> PoolState:
    """
    Build launch-scoped pool state for verb sessions.
    """
    if pos is not None and "verb" not in pos:
        return PoolState(
            word_map={},
            ltm=set(),
            stm=set(),
            new=set(),
            known=set(),
            ltm_scores={}
        )

    all_verbs = lexicon_repo.get_enriched_verbs(
        user_tags=user_tags if user_tags else None
    )
    word_map = {w.get("word_id"): w for w in all_verbs if w.get("word_id")}

    meaning_cards = fsrs.get_all_cards_with_state("word_translation", user_id)
    perfectum_cards = fsrs.get_all_cards_with_state("verb_perfectum", user_id)
    past_cards = fsrs.get_all_cards_with_state("verb_past_tense", user_id)

    meaning_map = {c.word_id: c for c in meaning_cards if c.word_id}
    perfectum_map = {c.word_id: c for c in perfectum_cards if c.word_id}
    past_map = {c.word_id: c for c in past_cards if c.word_id}

    if filter_known and VERB_FILTER_THRESHOLD > 0.0:
        word_map = {
            word_id: word
            for word_id, word in word_map.items()
            if word_id in meaning_map and meaning_map[word_id].retrievability >= VERB_FILTER_THRESHOLD
        }

    verb_ids = set(word_map.keys())

    ltm: set[str] = set()
    known: set[str] = set()
    new: set[str] = set()
    ltm_scores: dict[str, float] = {}

    for word_id in verb_ids:
        perfectum_state = perfectum_map.get(word_id)
        past_state = past_map.get(word_id)

        if not perfectum_state and not past_state:
            new.add(word_id)
            continue

        r_perfectum = perfectum_state.retrievability if perfectum_state else 0.0
        r_past = past_state.retrievability if past_state else 0.0

        if r_perfectum < r_threshold or r_past < r_threshold:
            ltm.add(word_id)
            ltm_scores[word_id] = min(r_perfectum, r_past)
        else:
            known.add(word_id)

    stm_set_perfectum = build_stm_set(user_id, "verb_perfectum")
    stm_set_past = build_stm_set(user_id, "verb_past_tense")
    stm_ids = {
        word_id for (word_id, ex_type) in (stm_set_perfectum | stm_set_past)
        if word_id in word_map and ex_type in ("verb_perfectum", "verb_past_tense")
    }

    for word_id in stm_ids:
        ltm.discard(word_id)
        new.discard(word_id)
        known.discard(word_id)
        ltm_scores.pop(word_id, None)

    return PoolState(
        word_map=word_map,
        ltm=ltm,
        stm=set(stm_ids),
        new=new,
        known=known,
        ltm_scores=ltm_scores
    )


def create_verb_tense_session(
    pool_state: PoolState,
    session_size: int = VERB_SESSION_SIZE,
    ltm_fraction: float = LTM_SESSION_FRACTION
) -> tuple[list[tuple[dict, str, str]], str]:
    """
    Create a verb tense study session using pool state.
    """
    ltm_target = int(session_size * ltm_fraction)
    ltm_ids = sorted(
        pool_state.ltm,
        key=lambda word_id: pool_state.ltm_scores.get(word_id, 1.0)
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

    if not session_ids:
        return [], "No verbs available. Learn more verb meanings to practice conjugation!"

    session_verbs = [pool_state.word_map[word_id] for word_id in session_ids if word_id in pool_state.word_map]
    random.shuffle(session_verbs)
    triplets = [(verb, "perfectum", "past_tense") for verb in session_verbs]

    return triplets, ""
