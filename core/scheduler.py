"""
Word scheduler for selecting words to review.

Uses FSRS (Free Spaced Repetition Scheduler) algorithm to prioritize words
based on forgetting curves and retrievability.

Sessions are pre-computed batches of words to review, mixing:
- Due cards (retrievability < 70%)
- New cards (never seen before)
- Practice cards (retrievability > 70%, for extra practice)
"""

from __future__ import annotations

from typing import Optional
import random

from core import lexicon_repo, log_repo


def select_next_word(
    enriched_only: bool = True,
    tag: Optional[str] = None,
    exclude_recent: bool = False,
    exercise_type: str = 'word_translation',
    max_new_cards: int = 10
) -> Optional[dict]:
    """
    Select the next word to review using FSRS scheduling.

    Priority order:
    1. Due cards (retrievability < 70%) - sorted by most urgent
    2. New cards (never seen before) - up to max_new_cards limit
    3. If no due or new cards, return None (study session complete)

    Args:
        enriched_only: If True, only select from enriched words
        tag: Optional tag filter (user_tags or AI tags)
        exclude_recent: If True, exclude the most recently reviewed word
        exercise_type: Type of exercise (default: 'word_translation')
        max_new_cards: Maximum number of new cards to introduce per session

    Returns:
        Lexicon entry dictionary, or None if no words available
    """
    exclude_lemmas = None

    if exclude_recent:
        # Get the most recent review event
        recent_events = log_repo.get_recent_events(limit=1)
        if recent_events:
            last_event = recent_events[0]
            exclude_lemmas = {(last_event["lemma"], last_event["pos"])}

    # 1. Check for due cards (retrievability below threshold)
    due_cards = log_repo.get_due_cards(exercise_type=exercise_type)

    if due_cards:
        # Filter by tag if specified
        if tag:
            due_cards = [
                card for card in due_cards
                if _word_matches_tag(card['lemma'], card['pos'], tag)
            ]

        # Exclude recent if requested
        if exclude_lemmas:
            due_cards = [
                card for card in due_cards
                if (card['lemma'], card['pos']) not in exclude_lemmas
            ]

        if due_cards:
            # Return most urgent (lowest retrievability)
            card = due_cards[0]
            return lexicon_repo.get_word(card['lemma'], card['pos'])

    # 2. Check for new cards (never reviewed for this exercise type)
    reviewed_set = _get_reviewed_cards_for_exercise(exercise_type)
    new_cards_seen_this_session = _count_new_cards_this_session(exercise_type)

    # Only introduce new cards if under the limit
    if new_cards_seen_this_session < max_new_cards:
        new_word = lexicon_repo.get_random_word(
            enriched_only=enriched_only,
            tag=tag,
            exclude_lemmas=reviewed_set | (exclude_lemmas or set())
        )
        if new_word:
            return new_word

    # 3. Fallback: If no due cards and hit new card limit,
    #    but user wants to study anyway, pick a random reviewed card
    #    This happens when all cards were just reviewed (R ≈ 100%)
    if reviewed_set:
        # Pick from cards we've seen before (for practice)
        word = lexicon_repo.get_random_word(
            enriched_only=enriched_only,
            tag=tag,
            exclude_lemmas=exclude_lemmas or set()
        )
        if word:
            return word

    # 4. Truly nothing available
    return None


def _word_matches_tag(lemma: str, pos: str, tag: str) -> bool:
    """Check if a word has a specific tag (helper)."""
    word = lexicon_repo.get_word(lemma, pos)
    if not word:
        return False

    user_tags = word.get('user_tags', [])
    ai_tags = word.get('tags', [])
    return tag in user_tags or tag in ai_tags


def _get_reviewed_cards_for_exercise(exercise_type: str) -> set[tuple[str, str]]:
    """Get all (lemma, pos) pairs reviewed for a specific exercise type."""
    all_cards = log_repo.get_all_cards_with_state(exercise_type=exercise_type)
    return {(card['lemma'], card['pos']) for card in all_cards}


def _count_new_cards_this_session(exercise_type: str) -> int:
    """
    Count how many new cards (review_count == 1) were introduced recently.

    For simplicity, we count cards with review_count == 1 from today.
    """
    from datetime import datetime, timezone, timedelta

    all_cards = log_repo.get_all_cards_with_state(exercise_type=exercise_type)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    new_today = 0
    for card in all_cards:
        if card['review_count'] == 1:
            # Check if first review was today
            last_review = datetime.fromisoformat(card['last_review_timestamp'])
            if last_review >= today_start:
                new_today += 1

    return new_today


# ---- Session Batching ----

def start_session(
    size: int = 20,
    exercise_type: str = 'word_translation',
    enriched_only: bool = True,
    tag: Optional[str] = None,
    max_new_cards: int = 5
) -> list[tuple[str, str]]:
    """
    Pre-compute a batch of words to review this session.

    The batch intelligently mixes:
    1. Due cards (retrievability < 70%) - most urgent first
    2. New cards (never seen) - up to max_new_cards per session
    3. Practice cards (R > 70%) - fill remainder, prioritize highest R

    Args:
        size: Number of words in the session batch (default: 20)
        exercise_type: Type of exercise (default: 'word_translation')
        enriched_only: If True, only select from enriched words
        tag: Optional tag filter
        max_new_cards: Maximum new cards to introduce per session (default: 5)

    Returns:
        List of (lemma, pos) tuples in optimal review order
    """
    batch = []
    reviewed_set = _get_reviewed_cards_for_exercise(exercise_type)

    # 1. Add all due cards (up to session size)
    due_cards = log_repo.get_due_cards(exercise_type=exercise_type)

    if tag:
        due_cards = [
            card for card in due_cards
            if _word_matches_tag(card['lemma'], card['pos'], tag)
        ]

    for card in due_cards[:size]:
        batch.append((card['lemma'], card['pos']))

    # 2. Add new cards (up to max_new_cards per session)
    remaining_space = size - len(batch)
    new_cards_budget = min(
        max_new_cards,      # Per-session limit (not per-day)
        remaining_space     # Don't exceed session size
    )

    if new_cards_budget > 0:
        # Get new words not yet reviewed
        attempts = 0
        max_attempts = new_cards_budget * 3  # Try 3x to avoid infinite loop

        while len(batch) < len(batch) + new_cards_budget and attempts < max_attempts:
            new_word = lexicon_repo.get_random_word(
                enriched_only=enriched_only,
                tag=tag,
                exclude_lemmas=reviewed_set | set(batch)
            )
            if new_word:
                batch.append((new_word['lemma'], new_word['pos']))
            else:
                break  # No more new words available
            attempts += 1

    # 3. Fill remainder with practice cards (high retrievability)
    remaining_space = size - len(batch)

    if remaining_space > 0:
        # Get all cards with state, filter out what's already in batch
        all_cards = log_repo.get_all_cards_with_state(exercise_type=exercise_type)

        if tag:
            all_cards = [
                card for card in all_cards
                if _word_matches_tag(card['lemma'], card['pos'], tag)
            ]

        # Filter out cards already in batch
        batch_set = set(batch)
        available_practice = [
            card for card in all_cards
            if (card['lemma'], card['pos']) not in batch_set
        ]

        # Sort by retrievability (highest first) for intelligent practice
        available_practice.sort(key=lambda c: c['retrievability'], reverse=True)

        # Mix: 70% from top quartile (easy refreshers), 30% from rest (variety)
        top_quartile_size = max(1, len(available_practice) // 4)
        top_cards = available_practice[:top_quartile_size]
        rest_cards = available_practice[top_quartile_size:]

        practice_picks = []
        top_count = int(remaining_space * 0.7)
        rest_count = remaining_space - top_count

        # Randomly sample from each group for variety
        if top_cards:
            practice_picks.extend(random.sample(top_cards, min(top_count, len(top_cards))))

        remaining_after_top = remaining_space - len(practice_picks)
        if rest_cards and remaining_after_top > 0:
            practice_picks.extend(random.sample(rest_cards, min(remaining_after_top, len(rest_cards))))

        for card in practice_picks:
            batch.append((card['lemma'], card['pos']))

    # If we still don't have enough, fill remainder with random words
    # This handles:
    # - First session (no reviewed cards): randomly pick new words to get started
    # - Established learner: pick any remaining words for variety
    if len(batch) < size:
        attempts = 0
        max_attempts = (size - len(batch)) * 3

        while len(batch) < size and attempts < max_attempts:
            word = lexicon_repo.get_random_word(
                enriched_only=enriched_only,
                tag=tag,
                exclude_lemmas=set(batch)
            )
            if word:
                batch.append((word['lemma'], word['pos']))
            else:
                break  # Truly no more words available
            attempts += 1

    return batch
