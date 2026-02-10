"""
Utilities for preposition drill prompt construction.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class PrepositionExample:
    """
    A single example sentence for a preposition usage.
    """
    dutch: str
    english: str
    blanked_dutch: str


@dataclass(frozen=True)
class PrepositionUsageOption:
    """
    One preposition usage with one or more blankable example sentences.
    """
    preposition: str
    examples: list[PrepositionExample]
    meaning: Optional[str] = None


def _preposition_pattern(preposition: str) -> Optional[str]:
    """
    Build a regex pattern that matches the preposition as standalone token(s).
    """
    preposition = (preposition or "").strip()
    if not preposition:
        return None
    tokens = preposition.split()
    if not tokens:
        return None
    return r"(?<!\w)" + r"\s+".join(re.escape(token) for token in tokens) + r"(?!\w)"


def blank_preposition(sentence: str, preposition: str) -> Optional[str]:
    """
    Replace all standalone occurrences of `preposition` in `sentence` with "____".

    Returns:
        Blanked sentence, or None if no replacement was made.
    """
    sentence = (sentence or "").strip()
    if not sentence:
        return None

    pattern = _preposition_pattern(preposition)
    if pattern is None:
        return None

    blanked, n_replacements = re.subn(pattern, "____", sentence, flags=re.IGNORECASE)
    if n_replacements == 0:
        return None
    return blanked


def emphasize_preposition(sentence: str, preposition: str) -> Optional[str]:
    """
    Wrap all standalone occurrences of `preposition` in <strong>..</strong>.
    """
    sentence = (sentence or "").strip()
    if not sentence:
        return None

    pattern = _preposition_pattern(preposition)
    if pattern is None:
        return None

    emphasized, n_replacements = re.subn(
        pattern,
        lambda match: f"<strong>{match.group(0)}</strong>",
        sentence,
        flags=re.IGNORECASE,
    )
    if n_replacements == 0:
        return None
    return emphasized


def _build_usage_from_examples(
    preposition: str,
    examples: list[dict],
    meaning: Optional[str] = None
) -> Optional[PrepositionUsageOption]:
    """
    Build a usage option if at least one example can be blanked.
    """
    preposition = (preposition or "").strip()
    if not preposition:
        return None

    parsed_examples: list[PrepositionExample] = []
    for example in examples or []:
        dutch = (example.get("dutch") or "").strip()
        english = (example.get("english") or "").strip()
        if not dutch or not english:
            continue

        blanked = blank_preposition(dutch, preposition)
        if blanked is None:
            continue

        parsed_examples.append(
            PrepositionExample(
                dutch=dutch,
                english=english,
                blanked_dutch=blanked,
            )
        )

    if not parsed_examples:
        return None

    return PrepositionUsageOption(
        preposition=preposition,
        examples=parsed_examples,
        meaning=meaning,
    )


def build_preposition_usages(word: dict) -> list[PrepositionUsageOption]:
    """
    Extract preposition usages from POS-specific metadata for drill prompts.

    Sources:
    - verb_meta.preposition_usage[*]
    - noun_meta.fixed_prepositions[*]
    - adjective_meta.fixed_prepositions[*]
    """
    usages: list[PrepositionUsageOption] = []

    verb_meta = word.get("verb_meta") or {}
    for usage in verb_meta.get("preposition_usage") or []:
        built = _build_usage_from_examples(
            preposition=usage.get("preposition", ""),
            examples=usage.get("examples") or [],
            meaning=usage.get("meaning"),
        )
        if built:
            usages.append(built)

    noun_meta = word.get("noun_meta") or {}
    for usage in noun_meta.get("fixed_prepositions") or []:
        built = _build_usage_from_examples(
            preposition=usage.get("preposition", ""),
            examples=usage.get("examples") or [],
            meaning=usage.get("meaning_context"),
        )
        if built:
            usages.append(built)

    adjective_meta = word.get("adjective_meta") or {}
    for usage in adjective_meta.get("fixed_prepositions") or []:
        built = _build_usage_from_examples(
            preposition=usage.get("preposition", ""),
            examples=usage.get("examples") or [],
            meaning=usage.get("meaning_context"),
        )
        if built:
            usages.append(built)

    return usages
