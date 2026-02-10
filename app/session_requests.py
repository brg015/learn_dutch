"""
Lexicon selection requests used to build launch-scoped pools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from core.fsrs.constants import LTM_SESSION_FRACTION


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
    ltm_fraction: float = LTM_SESSION_FRACTION


def _clamp_fraction(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_lexical_request(
    request: object | None,
    user_id: str,
    mode: str
) -> LexicalRequest:
    """
    Normalize request objects to the latest LexicalRequest schema.
    """
    if request is None:
        return default_lexical_request(user_id, mode)

    request_user_id = getattr(request, "user_id", user_id)
    request_mode = getattr(request, "mode", mode)
    if request_user_id != user_id or request_mode != mode:
        return default_lexical_request(user_id, mode)

    return LexicalRequest(
        user_id=request_user_id,
        mode=request_mode,
        user_tags=getattr(request, "user_tags", None),
        pos=getattr(request, "pos", None),
        only_enriched=bool(getattr(request, "only_enriched", False)),
        override_gates=bool(getattr(request, "override_gates", False)),
        ltm_fraction=_clamp_fraction(getattr(request, "ltm_fraction", LTM_SESSION_FRACTION)),
    )


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
    if mode == "prepositions":
        return LexicalRequest(
            user_id=user_id,
            mode=mode,
            only_enriched=True,
        )
    return LexicalRequest(user_id=user_id, mode=mode)
