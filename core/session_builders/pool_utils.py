"""
Pool utilities for session builders.

These helpers provide shared, minimal primitives for building and reasoning
about session pools without enforcing a single scheduling policy.
"""

from __future__ import annotations
import random
from typing import TypeVar


T = TypeVar("T")


def fill_in_order(
    pools: dict[str, list[T]],
    order: list[str],
    target_size: int
) -> list[T]:
    """
    Fill a session by walking pools in order until target_size is reached.
    """
    session: list[T] = []
    for name in order:
        for item in pools.get(name, []):
            if len(session) >= target_size:
                return session
            session.append(item)
    return session


def due_cards_from_snapshot(
    all_cards: list,
    r_threshold: float
) -> list:
    """
    Filter and sort due cards from a snapshot (no DB calls).
    """
    due_cards = [c for c in all_cards if c.retrievability < r_threshold]
    due_cards.sort(key=lambda c: c.retrievability)
    return due_cards


def sample_new_words(
    all_words: list[dict],
    reviewed_word_ids: set[str],
    count: int
) -> list[dict]:
    """
    Sample words that are not yet reviewed.
    """
    if count <= 0:
        return []

    new_words = [w for w in all_words if w.get("word_id") not in reviewed_word_ids]
    if not new_words:
        return []
    sample_size = min(count, len(new_words))
    return random.sample(new_words, sample_size)
