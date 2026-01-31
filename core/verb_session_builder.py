"""
Verb Tense Session Builder - Multi-Pool with OR Logic

Creates verb conjugation study sessions from multiple pools:
1. Pool A: Due verbs (both tenses need review, R < 0.70)
2. Pool B: Due verbs (one tense needs review)
3. Pool C: New verbs (learned from word_translation)
4. Pool D: STM verbs (recently missed, today/yesterday)
5. Pool E: Known conjugates (practice mode, R >= 0.70)
6. Pool F: Brand new words (not learned meaning yet) - shows message

Session Logic:
- OR scheduling: verb is due if R_perfectum < 0.70 OR R_past < 0.70
- Filter: only verbs where user "knows" the meaning (toggleable threshold)
- Returns triplets: (word_dict, "perfectum", "past_tense")
"""

from __future__ import annotations
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from core import fsrs, lexicon_repo
from core.fsrs.constants import FeedbackGrade, R_TARGET, VERB_FILTER_THRESHOLD, VERB_SESSION_SIZE
from core.fsrs.memory_state import calculate_retrievability


def create_verb_tense_session(
    user_id: str,
    r_threshold: float = R_TARGET,
    filter_known: bool = True
) -> tuple[list[tuple[dict, str, str]], str]:
    """
    Create a verb tense study session using multi-pool OR logic.

    Args:
        user_id: User identifier for scoping review data
        r_threshold: Retrievability threshold for "due" (default: 0.70)
        filter_known: If True, filter to verbs where user knows the meaning

    Returns:
        Tuple of (triplets, message):
        - triplets: List of (word_dict, "perfectum", "past_tense") tuples
        - message: Empty string if success, error message if no verbs available
    """
    print(f"[VERB SESSION] Starting session creation for user: {user_id}")

    # 1. Get all enriched verbs (Phase 2 enrichment with verb_meta)
    all_verbs = _get_enriched_verbs()
    print(f"[VERB SESSION] Found {len(all_verbs)} enriched verbs")

    if not all_verbs:
        return [], "No enriched verbs found. Please run Phase 2 enrichment on some verbs first."

    # 2. Apply filtering (toggleable based on "known" threshold)
    if filter_known and VERB_FILTER_THRESHOLD > 0.0:
        print(f"[VERB SESSION] Filtering by known threshold: {VERB_FILTER_THRESHOLD}")
        filtered_verbs = _filter_known_verbs(all_verbs, user_id)
        print(f"[VERB SESSION] {len(filtered_verbs)} verbs passed filter")
        if not filtered_verbs:
            return [], f"No verbs where meaning recall >= {VERB_FILTER_THRESHOLD:.0%}. Learn more verb meanings first!"
    else:
        # Testing mode: include all enriched verbs
        print(f"[VERB SESSION] Skipping filter (threshold = {VERB_FILTER_THRESHOLD})")
        filtered_verbs = all_verbs

    # 3. Build pools (categorize verbs by due status)
    print(f"[VERB SESSION] Building pools from {len(filtered_verbs)} verbs")
    pools = _build_verb_pools(filtered_verbs, user_id, r_threshold)
    print(f"[VERB SESSION] Pool sizes - due_both: {len(pools['due_both'])}, due_one: {len(pools['due_one'])}, new: {len(pools['new'])}, stm: {len(pools['stm'])}, known: {len(pools['known'])}")

    # 4. Fill session (priority: A → B → C → D → E)
    session_verbs = _fill_session(pools, VERB_SESSION_SIZE)
    print(f"[VERB SESSION] Session filled with {len(session_verbs)} verbs")

    if not session_verbs:
        return [], "No verbs available. Learn more verb meanings to practice conjugation!"

    # 5. Prepare triplets and shuffle
    triplets = _prepare_triplets(session_verbs)
    print(f"[VERB SESSION] Created {len(triplets)} triplets ({len(triplets)*2} total exercises)")

    return triplets, ""


def _get_enriched_verbs() -> list[dict]:
    """
    Get all verbs with Phase 2 enrichment (verb_meta populated).

    Returns:
        List of word dictionaries
    """
    # Query MongoDB for verbs with verb_meta
    all_words = lexicon_repo.get_all_words()

    enriched_verbs = [
        word for word in all_words
        if word.get("pos") == "verb" and word.get("verb_meta") is not None
    ]

    return enriched_verbs


def _filter_known_verbs(verbs: list[dict], user_id: str) -> list[dict]:
    """
    Filter to verbs where user "knows" the meaning (R >= threshold).

    Args:
        verbs: List of verb dictionaries
        user_id: User identifier

    Returns:
        Filtered list of verbs
    """
    known_verbs = []

    for verb in verbs:
        # Check if user knows the base meaning (word_translation exercise)
        translation_state = fsrs.get_card_state(
            user_id=user_id,
            word_id=verb.get("word_id"),
            exercise_type="word_translation"
        )

        if translation_state:
            # Calculate retrievability
            days_since_ltm = fsrs.get_days_since_ltm_review(translation_state.last_ltm_timestamp)
            R = calculate_retrievability(translation_state.stability, days_since_ltm)

            if R >= VERB_FILTER_THRESHOLD:
                known_verbs.append(verb)
        # Note: If no translation_state, verb is excluded (must learn meaning first)

    return known_verbs


def _build_verb_pools(
    verbs: list[dict],
    user_id: str,
    r_threshold: float
) -> dict[str, list]:
    """
    Build categorized verb pools based on due status.

    Args:
        verbs: List of verb dictionaries
        user_id: User identifier
        r_threshold: Retrievability threshold for "due"

    Returns:
        Dictionary with pools:
        - 'due_both': Both tenses need review
        - 'due_one': One tense needs review
        - 'new': No conjugation state yet (but knows meaning)
        - 'stm': Recently missed (today/yesterday)
        - 'known': Both tenses mastered (R >= threshold)
    """
    pools = {
        'due_both': [],
        'due_one': [],
        'new': [],
        'stm': [],
        'known': []
    }

    print(f"[VERB SESSION] Processing {len(verbs)} verbs for pool categorization...")

    # Early exit optimization: if we have enough verbs in high-priority pools, stop processing
    target_count = VERB_SESSION_SIZE * 2  # Aim for 2x session size to have options

    for idx, verb in enumerate(verbs):
        # Progress logging every 50 verbs
        if idx % 50 == 0:
            print(f"[VERB SESSION] Processed {idx}/{len(verbs)} verbs...")

        # Early exit if we have enough high-priority verbs
        if len(pools['due_both']) + len(pools['due_one']) + len(pools['new']) >= target_count:
            print(f"[VERB SESSION] Early exit: Have {len(pools['due_both']) + len(pools['due_one']) + len(pools['new'])} verbs in priority pools (target: {target_count})")
            break

        # Get card states for both tenses
        perfectum_state = fsrs.get_card_state(
            user_id=user_id,
            word_id=verb.get("word_id"),
            exercise_type="verb_perfectum"
        )
        past_state = fsrs.get_card_state(
            user_id=user_id,
            word_id=verb.get("word_id"),
            exercise_type="verb_past_tense"
        )

        # Calculate retrievability for each tense
        if perfectum_state:
            days_since_perfectum = fsrs.get_days_since_ltm_review(perfectum_state.last_ltm_timestamp)
            R_perfectum = calculate_retrievability(perfectum_state.stability, days_since_perfectum)
        else:
            R_perfectum = 0.0  # No state = needs learning

        if past_state:
            days_since_past = fsrs.get_days_since_ltm_review(past_state.last_ltm_timestamp)
            R_past = calculate_retrievability(past_state.stability, days_since_past)
        else:
            R_past = 0.0  # No state = needs learning

        # Categorize based on retrievability
        perfectum_due = R_perfectum < r_threshold
        past_due = R_past < r_threshold

        # Pool A: Both tenses due
        if perfectum_due and past_due:
            pools['due_both'].append((verb, R_perfectum, R_past))

        # Pool B: One tense due (XOR)
        elif perfectum_due or past_due:
            pools['due_one'].append((verb, R_perfectum, R_past))

        # Pool E: Known (both tenses mastered)
        elif perfectum_state and past_state:
            pools['known'].append((verb, R_perfectum, R_past))

        # Pool C: New (no conjugation state yet, but knows meaning)
        elif not perfectum_state and not past_state:
            pools['new'].append(verb)

        # Pool D: STM (check if recently reviewed and failed)
        if _is_recent_stm(perfectum_state) or _is_recent_stm(past_state):
            # Only add if still due (R < threshold)
            if perfectum_due or past_due:
                # Avoid duplicates from due pools
                if not (perfectum_due and past_due) and not (perfectum_due or past_due):
                    pools['stm'].append(verb)

    print(f"[VERB SESSION] Finished processing all {len(verbs)} verbs")
    return pools


def _is_recent_stm(card_state) -> bool:
    """
    Check if card has recent STM activity (today/yesterday).

    Args:
        card_state: CardState object or None

    Returns:
        True if reviewed within STM_MAX_AGE_DAYS, False otherwise
    """
    if not card_state or not card_state.last_review_timestamp:
        return False

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    return card_state.last_review_timestamp >= yesterday_start


def _fill_session(pools: dict[str, list], session_size: int) -> list[dict]:
    """
    Fill session from pools in priority order.

    Priority: due_both → due_one → new → stm → known

    Args:
        pools: Dictionary of categorized verb pools
        session_size: Target number of verbs

    Returns:
        List of verb dictionaries for the session
    """
    session_verbs = []

    # Priority A: Due (both tenses)
    for verb, _, _ in pools['due_both']:
        if len(session_verbs) >= session_size:
            break
        session_verbs.append(verb)

    # Priority B: Due (one tense)
    if len(session_verbs) < session_size:
        for verb, _, _ in pools['due_one']:
            if len(session_verbs) >= session_size:
                break
            session_verbs.append(verb)

    # Priority C: New (but knows meaning)
    if len(session_verbs) < session_size:
        for verb in pools['new']:
            if len(session_verbs) >= session_size:
                break
            session_verbs.append(verb)

    # Priority D: STM (recently missed)
    if len(session_verbs) < session_size:
        for verb in pools['stm']:
            if len(session_verbs) >= session_size:
                break
            # Avoid duplicates
            if verb not in session_verbs:
                session_verbs.append(verb)

    # Priority E: Known (practice mode)
    if len(session_verbs) < session_size:
        for verb, _, _ in pools['known']:
            if len(session_verbs) >= session_size:
                break
            session_verbs.append(verb)

    return session_verbs


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
