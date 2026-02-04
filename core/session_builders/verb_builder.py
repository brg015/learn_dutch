"""
Verb Tense Session Builder - Three-Pool Logic

Creates verb conjugation study sessions from multiple pools:
1. LTM pool: Verbs due if either tense is below threshold
2. STM pool: Verbs recently missed (today/yesterday)
3. New pool: Verbs with no conjugation state yet (meaning known)

Session Logic:
- Due if R_perfectum < 0.70 OR R_past < 0.70
- Filter: only verbs where user knows the meaning (toggleable threshold)
- Returns triplets: (word_dict, "perfectum", "past_tense")
"""

from __future__ import annotations
import random
from typing import Optional

from core import fsrs, lexicon_repo
from core.session_builders.stm_state import StmKey
from core.session_builders.pool_utils import fill_in_order
from core.session_builders.pool_types import PoolItem
from core.fsrs.constants import R_TARGET, VERB_FILTER_THRESHOLD, VERB_SESSION_SIZE
from core.fsrs.memory_state import CardStateSnapshot


def create_verb_tense_session(
    user_id: str,
    r_threshold: float = R_TARGET,
    filter_known: bool = True,
    stm_set_perfectum: Optional[set[StmKey]] = None,
    stm_set_past: Optional[set[StmKey]] = None,
    base_pool: Optional[dict] = None
) -> tuple[list[tuple[dict, str, str]], str]:
    """
    Create a verb tense study session using three-pool logic.

    Args:
        user_id: User identifier for scoping review data
        r_threshold: Retrievability threshold for "due" (default: 0.70)
        filter_known: If True, filter to verbs where user knows the meaning
        stm_set_perfectum: Optional STM set for verb_perfectum
        stm_set_past: Optional STM set for verb_past_tense

    Returns:
        Tuple of (triplets, message):
        - triplets: List of (word_dict, "perfectum", "past_tense") tuples
        - message: Empty string if success, error message if no verbs available
    """
    if base_pool is None:
        base_pool = build_verb_base_pool(user_id)

    all_verbs = base_pool["all_verbs"]
    meaning_map = base_pool["meaning_map"]
    perfectum_map = base_pool["perfectum_map"]
    past_map = base_pool["past_map"]

    if not all_verbs:
        return [], "No enriched verbs found. Please run Phase 2 enrichment on some verbs first."

    # 2. Apply filtering (toggleable based on "known" threshold)
    if filter_known and VERB_FILTER_THRESHOLD > 0.0:
        filtered_verbs = _filter_known_verbs(all_verbs, meaning_map)
        if not filtered_verbs:
            return [], f"No verbs where meaning recall >= {VERB_FILTER_THRESHOLD:.0%}. Learn more verb meanings first!"
    else:
        filtered_verbs = all_verbs

    # 3. Build pools (categorize verbs by due status)
    pools = _build_verb_pools(
        filtered_verbs,
        r_threshold,
        meaning_map,
        perfectum_map,
        past_map,
        stm_set_perfectum or set(),
        stm_set_past or set()
    )
    # 4. Fill session (priority: ltm -> stm -> new)
    session_items = fill_in_order(pools, ["ltm", "stm", "new"], VERB_SESSION_SIZE)

    if not session_items:
        return [], "No verbs available. Learn more verb meanings to practice conjugation!"

    # 5. Prepare triplets and shuffle
    session_verbs = [item.word for item in session_items]
    triplets = _prepare_triplets(session_verbs)

    return triplets, ""


def build_verb_base_pool(user_id: str) -> dict:
    """
    Build the base pool snapshot for verb sessions (one-time per launch).

    Returns:
        Dict with all_verbs and card-state maps
    """
    all_verbs = lexicon_repo.get_enriched_verbs()
    meaning_cards = fsrs.get_all_cards_with_state("word_translation", user_id)
    perfectum_cards = fsrs.get_all_cards_with_state("verb_perfectum", user_id)
    past_cards = fsrs.get_all_cards_with_state("verb_past_tense", user_id)

    return {
        "all_verbs": all_verbs,
        "meaning_map": {c.word_id: c for c in meaning_cards if c.word_id},
        "perfectum_map": {c.word_id: c for c in perfectum_cards if c.word_id},
        "past_map": {c.word_id: c for c in past_cards if c.word_id},
    }


def _filter_known_verbs(verbs: list[dict], meaning_map: dict[str, CardStateSnapshot]) -> list[dict]:
    """
    Filter to verbs where user "knows" the meaning (R >= threshold).

    Args:
        verbs: List of verb dictionaries
        meaning_map: Snapshot map of meaning card states

    Returns:
        Filtered list of verbs
    """
    known_verbs = []

    for verb in verbs:
        # Check if user knows the base meaning (word_translation exercise)
        translation_state = meaning_map.get(verb.get("word_id"))

        if translation_state and translation_state.retrievability >= VERB_FILTER_THRESHOLD:
            known_verbs.append(verb)
        # Note: If no translation_state, verb is excluded (must learn meaning first)

    return known_verbs


def _build_verb_pools(
    verbs: list[dict],
    r_threshold: float,
    meaning_map: dict[str, CardStateSnapshot],
    perfectum_map: dict[str, CardStateSnapshot],
    past_map: dict[str, CardStateSnapshot],
    stm_set_perfectum: set[StmKey],
    stm_set_past: set[StmKey]
) -> dict[str, list[PoolItem]]:
    """
    Build categorized verb pools based on due status.

    Args:
        verbs: List of verb dictionaries
        r_threshold: Retrievability threshold for "due"
        meaning_map: Snapshot map of meaning card states
        perfectum_map: Snapshot map of perfectum card states
        past_map: Snapshot map of past tense card states
        stm_set_perfectum: STM set for perfectum
        stm_set_past: STM set for past tense

    Returns:
        Dictionary with pools:
        - 'ltm': Due if either tense is below threshold
        - 'stm': Recently missed (today/yesterday)
        - 'new': No conjugation state yet (but knows meaning)
    """
    pools: dict[str, list[PoolItem]] = {
        "ltm": [],
        "stm": [],
        "new": [],
    }

    verb_ids = {v.get("word_id") for v in verbs if v.get("word_id")}

    ltm_ids = {
        vid for vid in verb_ids
        if (
            (perfectum_map.get(vid) and perfectum_map[vid].retrievability < r_threshold)
            or (past_map.get(vid) and past_map[vid].retrievability < r_threshold)
        )
    }

    new_ids = {
        vid for vid in verb_ids
        if vid not in perfectum_map and vid not in past_map
    }

    stm_ids = {
        word_id for (word_id, ex_type) in (stm_set_perfectum | stm_set_past)
        if ex_type in ("verb_perfectum", "verb_past_tense")
    }

    for verb in verbs:
        word_id = verb.get("word_id")
        if not word_id:
            continue

        if word_id in ltm_ids:
            pools["ltm"].append(PoolItem(word=verb, status="ltm"))
        elif word_id in new_ids:
            pools["new"].append(PoolItem(word=verb, status="new"))
        if word_id in stm_ids:
            pools["stm"].append(PoolItem(word=verb, status="stm"))

    # De-dupe STM against LTM/NEW to keep pools unique
    ltm_ids = {v.word.get("word_id") for v in pools["ltm"] if v.word.get("word_id")}
    new_ids = {v.word.get("word_id") for v in pools["new"] if v.word.get("word_id")}
    pools["stm"] = [
        v for v in pools["stm"]
        if v.word.get("word_id") not in ltm_ids and v.word.get("word_id") not in new_ids
    ]
    return pools


def _prepare_triplets(verbs: list[dict]) -> list[tuple[dict, str, str]]:
    """
    Prepare triplets and shuffle.

    Each triplet: (word_dict, "perfectum", "past_tense")

    Args:
        verbs: List of verb dictionaries

    Returns:
        List of triplets, shuffled at the verb level
    """
    # Shuffle verbs (but preserve triplet structure)
    random.shuffle(verbs)

    # Create triplets
    triplets = [(verb, "perfectum", "past_tense") for verb in verbs]

    return triplets
