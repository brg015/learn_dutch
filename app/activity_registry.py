"""
Activity registry for Streamlit session handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from app.activities import WordActivity, SentenceActivity, VerbTenseActivity
from app.session_requests import LexicalRequest
from app.session_types import SessionItem
from core import fsrs
from core.session_builders import (
    build_word_pool_state,
    build_verb_pool_state,
    create_word_session,
    create_verb_tense_session,
)
from core.session_builders.pool_types import PoolState


@dataclass(frozen=True)
class ActivitySpec:
    """
    Activity configuration and builders.
    """
    mode: str
    label: str
    description: str
    pool_key: str
    build_pool: Callable[[LexicalRequest], PoolState]
    build_items: Callable[[PoolState], tuple[list[SessionItem], Optional[str]]]
    activity_factory: Callable[[SessionItem], object]


def _build_word_pool(request: LexicalRequest) -> PoolState:
    return build_word_pool_state(request.user_id, "word_translation")


def _build_word_items(pool_state: PoolState) -> tuple[list[SessionItem], Optional[str]]:
    words = create_word_session(pool_state)
    items = [
        SessionItem(word=word, exercise_type="word_translation")
        for word in words
    ]
    return items, None


def _build_verb_pool(request: LexicalRequest) -> PoolState:
    return build_verb_pool_state(
        request.user_id,
        r_threshold=fsrs.R_TARGET,
        filter_known=not request.override_gates
    )


def _build_verb_items(pool_state: PoolState) -> tuple[list[SessionItem], Optional[str]]:
    triplets, message = create_verb_tense_session(
        pool_state=pool_state,
        session_size=fsrs.VERB_SESSION_SIZE
    )
    if not triplets:
        return [], message

    items: list[SessionItem] = []
    for word, _, _ in triplets:
        items.append(
            SessionItem(
                word=word,
                exercise_type="verb_perfectum",
                tense_step="perfectum",
                show_answer_on_load=False
            )
        )
        items.append(
            SessionItem(
                word=word,
                exercise_type="verb_past_tense",
                tense_step="past_tense",
                show_answer_on_load=True
            )
        )

    return items, None


ACTIVITY_SPECS: dict[str, ActivitySpec] = {
    "words": ActivitySpec(
        mode="words",
        label="Only Words",
        description="Practice individual words",
        pool_key="word_pool",
        build_pool=_build_word_pool,
        build_items=_build_word_items,
        activity_factory=lambda item: WordActivity(item.word),
    ),
    "sentences": ActivitySpec(
        mode="sentences",
        label="Sentences",
        description="Practice words in context",
        pool_key="word_pool",
        build_pool=_build_word_pool,
        build_items=_build_word_items,
        activity_factory=lambda item: SentenceActivity(item.word),
    ),
    "verb_tenses": ActivitySpec(
        mode="verb_tenses",
        label="Verb Tenses",
        description="Practice verb conjugations",
        pool_key="verb_pool",
        build_pool=_build_verb_pool,
        build_items=_build_verb_items,
        activity_factory=lambda item: VerbTenseActivity(item.word, item.tense_step),
    ),
}


def get_activity_spec(mode: str) -> ActivitySpec:
    return ACTIVITY_SPECS[mode]
