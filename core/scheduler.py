"""
Word scheduler for selecting words to review.

MVP: Random selection from available words.
Future: Sophisticated spaced repetition algorithms (SM-2, adaptive scheduling).

The scheduler supports dynamic selection - pick one word at a time based on
current review history, or batch selection for performance optimization.
"""

from __future__ import annotations

from typing import Optional

from core import lexicon_repo, log_repo


def select_next_word(
    enriched_only: bool = True,
    tag: Optional[str] = None,
    exclude_recent: bool = False
) -> Optional[dict]:
    """
    Select the next word to review.

    This is the main interface for dynamic, one-at-a-time scheduling.
    After each review, call this again to get the next word.

    MVP implementation: Random selection.

    Future implementation will:
    - Calculate priority scores for all words
    - Consider accuracy, recency, exposure count, difficulty
    - Apply spaced repetition algorithms
    - Avoid showing the same word twice in a row

    Args:
        enriched_only: If True, only select from enriched words
        tag: Optional tag filter (user_tags or AI tags)
        exclude_recent: If True, exclude the most recently reviewed word

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

    # MVP: Random selection
    # Future: Replace with priority-based selection
    return lexicon_repo.get_random_word(
        enriched_only=enriched_only,
        tag=tag,
        exclude_lemmas=exclude_lemmas
    )


# ---- Future Scheduling Logic (Placeholder) ----

def calculate_priority(lemma: str, pos: str) -> float:
    """
    Calculate priority score for a word (higher = more urgent to review).

    Future implementation will use:
    - Accuracy (lower accuracy = higher priority)
    - Recency (longer time since last review = higher priority)
    - Exposure count (fewer exposures = higher priority)
    - Difficulty level (CEFR)
    - Forgetting curve modeling
    - n-words back / n-time back metrics

    Args:
        lemma: The word lemma
        pos: Part of speech

    Returns:
        Priority score (0.0 to 1.0, higher is more urgent)
    """
    # Placeholder: Always return 0.5 (equal priority)
    # When implementing: calculate based on review history

    # Example of what this might look like:
    # accuracy = log_repo.get_accuracy(lemma, pos)
    # last_review = log_repo.get_last_review_timestamp(lemma, pos)
    # exposure_count = log_repo.get_review_count(lemma, pos)
    #
    # # Calculate time since last review
    # if last_review:
    #     hours_since = (datetime.now(datetime.timezone.utc) - last_review).total_seconds() / 3600
    # else:
    #     hours_since = float('inf')  # Never reviewed
    #
    # # Priority formula (example - needs tuning)
    # priority = (
    #     (1 - accuracy) * 0.4 +                    # Lower accuracy = higher priority
    #     min(hours_since / 24, 1.0) * 0.3 +        # Longer time = higher priority
    #     (1.0 / (exposure_count + 1)) * 0.2 +      # Fewer exposures = higher priority
    #     0.1                                        # Base priority
    # )
    #
    # return min(priority, 1.0)

    return 0.5


def select_priority_based(
    enriched_only: bool = True,
    tag: Optional[str] = None,
    exclude_recent: bool = False
) -> Optional[dict]:
    """
    Select next word using priority scoring (future implementation).

    This will replace select_next_word() when priority algorithm is implemented.

    Args:
        enriched_only: If True, only select from enriched words
        tag: Optional tag filter
        exclude_recent: If True, exclude most recently reviewed word

    Returns:
        Highest priority word to review
    """
    # Get all available words
    available_words = lexicon_repo.get_all_words(
        enriched_only=enriched_only,
        tag=tag
    )

    if not available_words:
        return None

    # Filter out recent word if requested
    if exclude_recent:
        recent_events = log_repo.get_recent_events(limit=1)
        if recent_events:
            last = recent_events[0]
            available_words = [
                w for w in available_words
                if not (w["lemma"] == last["lemma"] and w["pos"] == last["pos"])
            ]

    # Calculate priorities and select highest
    # (Placeholder: just return a random one for now)
    if available_words:
        import random
        return random.choice(available_words)

    return None
