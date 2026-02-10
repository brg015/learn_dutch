"""
Lexicon settings UI for building LexicalRequest filters.
"""

from __future__ import annotations

from typing import Optional, Sequence

import streamlit as st

from app.session_requests import (
    LexicalRequest,
    normalize_lexical_request,
    request_key_for_mode,
)
from core.session_builders import (
    build_word_pool_state,
    build_verb_pool_state,
    build_preposition_pool_state,
)
from core import fsrs
from core import lexicon_repo


def _get_tag_options(min_count: int) -> list[str]:
    tag_counts = lexicon_repo.get_user_tag_counts(min_count=min_count)
    return [item["tag"] for item in tag_counts]


def _get_pos_options(min_count: int = 1) -> list[str]:
    collection = lexicon_repo.get_collection()
    pipeline = [
        {"$group": {"_id": "$pos", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": min_count}}},
        {"$sort": {"count": -1}},
    ]
    return [item["_id"] for item in collection.aggregate(pipeline) if item["_id"]]


@st.cache_data(show_spinner=False)
def _cached_tag_options(min_count: int) -> list[str]:
    return _get_tag_options(min_count)


@st.cache_data(show_spinner=False)
def _cached_pos_options(min_count: int = 1) -> list[str]:
    return _get_pos_options(min_count)


def _current_request_for_key(request_key: str) -> LexicalRequest:
    requests = st.session_state.lexical_requests
    request = normalize_lexical_request(
        requests.get(request_key),
        st.session_state.user_id,
        request_key,
    )
    requests[request_key] = request
    return request


def _apply_request(request_key: str, request: LexicalRequest) -> None:
    st.session_state.lexical_requests[request_key] = request
    if request_key == "verb_tenses":
        st.session_state.verb_pool_state = None
    elif request_key == "prepositions":
        st.session_state.preposition_pool_state = None
    elif request_key == "words":
        st.session_state.word_pool_state = None


def _preview_pool_counts(request_key: str, request: LexicalRequest) -> Optional[dict]:
    if request_key == "verb_tenses":
        pool_state = build_verb_pool_state(
            request.user_id,
            r_threshold=fsrs.R_TARGET,
            filter_known=not request.override_gates,
            user_tags=request.user_tags,
            pos=request.pos
        )
    elif request_key == "prepositions":
        pool_state = build_preposition_pool_state(
            user_id=request.user_id,
            user_tags=request.user_tags,
            pos=request.pos,
            enriched_only=request.only_enriched,
            r_threshold=fsrs.PREPOSITION_FILTER_THRESHOLD,
            filter_known=not request.override_gates,
        )
    else:
        pool_state = build_word_pool_state(
            request.user_id,
            "word_translation",
            user_tags=request.user_tags,
            pos=request.pos,
            enriched_only=request.only_enriched
        )
    return {
        "ltm": len(pool_state.ltm),
        "stm": len(pool_state.stm),
        "new": len(pool_state.new),
        "known": len(pool_state.known),
        "total": len(pool_state.word_map),
    }


def render_lexicon_settings(user_options: dict[str, str]) -> None:
    """
    Render lexicon settings UI.
    """
    del user_options  # user is selected once on app entry
    st.subheader("Lexicon Settings")
    st.caption(f"User: {st.session_state.user_label} ({st.session_state.user_id})")

    activity_choices = {
        "Word activities (words + sentences)": "words",
        "Grammar: Verb Tenses": "verb_tenses",
        "Preposition Usage (verbs, nouns, adjectives)": "prepositions",
    }
    selected_activity = st.selectbox(
        "Apply filters to",
        list(activity_choices.keys())
    )
    request_key = request_key_for_mode(activity_choices[selected_activity])
    apply_all = st.checkbox("Apply to all activities", value=False)

    current_request = _current_request_for_key(request_key)
    ltm_fraction = st.slider(
        "LTM Session Fraction",
        min_value=0.0,
        max_value=1.0,
        value=float(current_request.ltm_fraction),
        step=0.05,
        help="Portion of each session reserved for due LTM items before filling from STM, then NEW.",
    )

    min_count = st.number_input(
        "Minimum tag count",
        min_value=1,
        max_value=1000,
        value=20,
        step=1
    )
    tag_options = _cached_tag_options(int(min_count))
    selected_tags = st.multiselect(
        "User tags (OR)",
        options=tag_options,
        default=list(current_request.user_tags or [])
    )

    pos_options = _cached_pos_options()
    pos_selection: Sequence[str] = current_request.pos or ()

    allow_override_verbs = False
    allow_override_prepositions = False

    if apply_all:
        pos_selection = st.multiselect(
            "Parts of speech",
            options=pos_options,
            default=list(current_request.pos or [])
        )
        only_enriched = True
        verb_request_current = _current_request_for_key("verb_tenses")
        preposition_request_current = _current_request_for_key("prepositions")
        allow_override_verbs = st.checkbox(
            "Allow verbs without known meaning (Verb Tenses)",
            value=verb_request_current.override_gates,
        )
        allow_override_prepositions = st.checkbox(
            "Allow words without known meaning (Prepositions)",
            value=preposition_request_current.override_gates,
        )
        allow_override = False
    elif request_key == "verb_tenses":
        st.info("Verb sessions force POS=verb and enriched-only.")
        pos_selection = ("verb",)
        only_enriched = True
        allow_override_verbs = st.checkbox(
            "Allow verbs without known meaning",
            value=current_request.override_gates
        )
        allow_override = allow_override_verbs
    else:
        if request_key == "prepositions":
            st.info("Preposition sessions include verbs, nouns, and adjectives with usage examples.")
        pos_selection = st.multiselect(
            "Parts of speech",
            options=pos_options,
            default=list(current_request.pos or [])
        )
        only_enriched = True
        if request_key == "prepositions":
            allow_override_prepositions = st.checkbox(
                "Allow words without known meaning",
                value=current_request.override_gates
            )
            allow_override = allow_override_prepositions
        else:
            allow_override = False

    preview_counts = None
    preview_counts_words = None
    preview_counts_verbs = None
    preview_counts_prepositions = None
    if st.button("Preview pools"):
        if apply_all:
            word_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="words",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=False,
                ltm_fraction=ltm_fraction,
            )
            verb_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="verb_tenses",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=True,
                override_gates=allow_override_verbs,
                ltm_fraction=ltm_fraction,
            )
            preposition_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="prepositions",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=allow_override_prepositions,
                ltm_fraction=ltm_fraction,
            )
            preview_counts_words = _preview_pool_counts("words", word_request)
            preview_counts_verbs = _preview_pool_counts("verb_tenses", verb_request)
            preview_counts_prepositions = _preview_pool_counts("prepositions", preposition_request)
        else:
            preview_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode=request_key,
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=allow_override,
                ltm_fraction=ltm_fraction,
            )
            preview_counts = _preview_pool_counts(request_key, preview_request)

    if preview_counts_words:
        st.caption(
            "Words: "
            f"Total {preview_counts_words['total']} | "
            f"LTM {preview_counts_words['ltm']} | "
            f"STM {preview_counts_words['stm']} | "
            f"NEW {preview_counts_words['new']} | "
            f"KNOWN {preview_counts_words['known']}"
        )
    if preview_counts_verbs:
        st.caption(
            "Verbs: "
            f"Total {preview_counts_verbs['total']} | "
            f"LTM {preview_counts_verbs['ltm']} | "
            f"STM {preview_counts_verbs['stm']} | "
            f"NEW {preview_counts_verbs['new']} | "
            f"KNOWN {preview_counts_verbs['known']}"
        )
    if preview_counts_prepositions:
        st.caption(
            "Prepositions: "
            f"Total {preview_counts_prepositions['total']} | "
            f"LTM {preview_counts_prepositions['ltm']} | "
            f"STM {preview_counts_prepositions['stm']} | "
            f"NEW {preview_counts_prepositions['new']} | "
            f"KNOWN {preview_counts_prepositions['known']}"
        )
    if preview_counts:
        st.caption(
            f"Total {preview_counts['total']} | "
            f"LTM {preview_counts['ltm']} | "
            f"STM {preview_counts['stm']} | "
            f"NEW {preview_counts['new']} | "
            f"KNOWN {preview_counts['known']}"
        )

    if st.button("Apply filters"):
        if apply_all:
            word_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="words",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=False,
                ltm_fraction=ltm_fraction,
            )
            verb_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="verb_tenses",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=True,
                override_gates=allow_override_verbs,
                ltm_fraction=ltm_fraction,
            )
            preposition_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="prepositions",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=allow_override_prepositions,
                ltm_fraction=ltm_fraction,
            )
            _apply_request("words", word_request)
            _apply_request("verb_tenses", verb_request)
            _apply_request("prepositions", preposition_request)
        else:
            request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode=request_key,
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=allow_override,
                ltm_fraction=ltm_fraction,
            )
            _apply_request(request_key, request)

        st.success("Lexicon filters applied.")

    if st.button("Reset to defaults"):
        if apply_all:
            from app.session_requests import default_lexical_request
            _apply_request("words", default_lexical_request(st.session_state.user_id, "words"))
            _apply_request("verb_tenses", default_lexical_request(st.session_state.user_id, "verb_tenses"))
            _apply_request("prepositions", default_lexical_request(st.session_state.user_id, "prepositions"))
        else:
            from app.session_requests import default_lexical_request
            _apply_request(request_key, default_lexical_request(st.session_state.user_id, request_key))
        st.success("Lexicon filters reset.")
