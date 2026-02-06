"""
Lexicon selection requests used to build launch-scoped pools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class LexicalRequest:
    """
    Persistent selection settings for a mode's lexicon pool.
    """
    user_id: str
    mode: str
    user_tags: Optional[Tuple[str, ...]] = None
    pos: Optional[Tuple[str, ...]] = None
    only_enriched: bool = False
    override_gates: bool = False


def request_key_for_mode(mode: str) -> str:
    """
    Normalize modes that share a lexical request.
    """
    if mode == "sentences":
        return "words"
    return mode


def default_lexical_request(user_id: str, mode: str) -> LexicalRequest:
    """
    Build a default request for a given mode.
    """
    if mode == "verb_tenses":
        return LexicalRequest(
            user_id=user_id,
            mode=mode,
            pos=("verb",),
            only_enriched=True,
            override_gates=False
        )
    return LexicalRequest(user_id=user_id, mode=mode)
