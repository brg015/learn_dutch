"""
Lexicon settings UI for building LexicalRequest filters.
"""

from __future__ import annotations

from typing import Optional, Sequence

import streamlit as st

from app.session_requests import LexicalRequest, request_key_for_mode
from core.session_builders import build_word_pool_state, build_verb_pool_state
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
    request = requests.get(request_key)
    if request is None or request.user_id != st.session_state.user_id:
        from app.session_requests import default_lexical_request
        request = default_lexical_request(st.session_state.user_id, request_key)
        requests[request_key] = request
    return request


def _apply_request(request_key: str, request: LexicalRequest) -> None:
    st.session_state.lexical_requests[request_key] = request
    if request_key == "verb_tenses":
        st.session_state.verb_pool_state = None
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
    st.subheader("Lexicon Settings")

    user_labels = list(user_options.keys())
    selected_label = st.selectbox(
        "User",
        user_labels,
        index=user_labels.index(st.session_state.user_label)
        if st.session_state.user_label in user_labels
        else 0
    )
    st.session_state.user_label = selected_label
    st.session_state.user_id = user_options[selected_label]

    activity_choices = {
        "Word activities (words + sentences)": "words",
        "Verb conjugation": "verb_tenses",
    }
    selected_activity = st.selectbox(
        "Apply filters to",
        list(activity_choices.keys())
    )
    request_key = request_key_for_mode(activity_choices[selected_activity])
    apply_all = st.checkbox("Apply to all activities", value=False)

    current_request = _current_request_for_key(request_key)

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

    if request_key == "verb_tenses" and not apply_all:
        st.info("Verb sessions force POS=verb and enriched-only.")
        pos_selection = ("verb",)
        only_enriched = True
        allow_override = st.checkbox(
            "Allow verbs without known meaning",
            value=current_request.override_gates
        )
    else:
        if request_key == "verb_tenses":
            st.info("Verb sessions only use POS=verb; excluding verbs yields an empty verb pool.")
        pos_selection = st.multiselect(
            "Parts of speech",
            options=pos_options,
            default=list(current_request.pos or [])
        )
        only_enriched = st.checkbox(
            "Only enriched",
            value=current_request.only_enriched
        )
        allow_override = False

    preview_counts = None
    preview_counts_words = None
    preview_counts_verbs = None
    if st.button("Preview pools"):
        if apply_all:
            word_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="words",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=False
            )
            verb_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="verb_tenses",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=True,
                override_gates=allow_override
            )
            preview_counts_words = _preview_pool_counts("words", word_request)
            preview_counts_verbs = _preview_pool_counts("verb_tenses", verb_request)
        else:
            preview_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode=request_key,
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=allow_override
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
                override_gates=False
            )
            verb_request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode="verb_tenses",
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=True,
                override_gates=allow_override
            )
            _apply_request("words", word_request)
            _apply_request("verb_tenses", verb_request)
        else:
            request = LexicalRequest(
                user_id=st.session_state.user_id,
                mode=request_key,
                user_tags=tuple(selected_tags) if selected_tags else None,
                pos=tuple(pos_selection) if pos_selection else None,
                only_enriched=only_enriched,
                override_gates=allow_override
            )
            _apply_request(request_key, request)

        st.success("Lexicon filters applied.")

    if st.button("Reset to defaults"):
        if apply_all:
            from app.session_requests import default_lexical_request
            _apply_request("words", default_lexical_request(st.session_state.user_id, "words"))
            _apply_request("verb_tenses", default_lexical_request(st.session_state.user_id, "verb_tenses"))
        else:
            from app.session_requests import default_lexical_request
            _apply_request(request_key, default_lexical_request(st.session_state.user_id, request_key))
        st.success("Lexicon filters reset.")
