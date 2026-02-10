"""
Constants for analytics tracks and exercise-type mappings.
"""

from __future__ import annotations

from typing import Final


WORDS_EXERCISE_TYPES: Final[list[str]] = ["word_translation"]
VERB_TENSE_EXERCISE_TYPES: Final[list[str]] = ["verb_perfectum", "verb_past_tense"]
PREPOSITION_EXERCISE_TYPES: Final[list[str]] = ["word_preposition"]

TRACK_EXERCISE_TYPES: Final[dict[str, list[str]]] = {
    "words": WORDS_EXERCISE_TYPES,
    "verb_tenses": VERB_TENSE_EXERCISE_TYPES,
    "prepositions": PREPOSITION_EXERCISE_TYPES,
}

TRACK_LABELS: Final[dict[str, str]] = {
    "words": "Words",
    "verb_tenses": "Verb Tenses",
    "prepositions": "Prepositions",
}

