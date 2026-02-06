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
    tags: Optional[Tuple[str, ...]] = None
    override_gates: bool = False


def default_lexical_request(user_id: str, mode: str) -> LexicalRequest:
    """
    Build a default request for a given mode.
    """
    return LexicalRequest(user_id=user_id, mode=mode)
