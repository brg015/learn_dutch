"""
Streamlit session state and database initialization helpers.
"""

from __future__ import annotations

import streamlit as st

from core import fsrs


def init_database() -> None:
    """
    Initialize database schema (cached per Streamlit session).
    """
    @st.cache_resource
    def _init_database() -> None:
        fsrs.init_db()

    _init_database()


def ensure_session_state(user_options: dict[str, str]) -> None:
    """
    Populate Streamlit session_state with defaults.
    """
    if "user_id" not in st.session_state:
        default_user_id = fsrs.get_default_user_id()
        st.session_state.user_id = default_user_id
        st.session_state.user_label = next(
            (label for label, uid in user_options.items() if uid == default_user_id),
            "Ben"
        )
    if "user_selected" not in st.session_state:
        st.session_state.user_selected = False
    if "current_word" not in st.session_state:
        st.session_state.current_word = None
    if "show_answer" not in st.session_state:
        st.session_state.show_answer = False
    if "session_batch" not in st.session_state:
        st.session_state.session_batch = []
    if "session_position" not in st.session_state:
        st.session_state.session_position = 0
    if "session_count" not in st.session_state:
        st.session_state.session_count = 0
    if "session_correct" not in st.session_state:
        st.session_state.session_correct = 0
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "learning_mode" not in st.session_state:
        st.session_state.learning_mode = None
    if "activity" not in st.session_state:
        st.session_state.activity = None
    if "review_events_buffer" not in st.session_state:
        st.session_state.review_events_buffer = []
    if "cards_buffer" not in st.session_state:
        st.session_state.cards_buffer = []
    if "current_exercise_type" not in st.session_state:
        st.session_state.current_exercise_type = "word_translation"
    if "current_tense_step" not in st.session_state:
        st.session_state.current_tense_step = None
    if "user_id_active" not in st.session_state:
        st.session_state.user_id_active = st.session_state.user_id
    if "word_pool_state" not in st.session_state:
        st.session_state.word_pool_state = None
    if "verb_pool_state" not in st.session_state:
        st.session_state.verb_pool_state = None
    if "preposition_pool_state" not in st.session_state:
        st.session_state.preposition_pool_state = None
    if "verb_response_buffer" not in st.session_state:
        st.session_state.verb_response_buffer = {}
    if "lexical_requests" not in st.session_state:
        st.session_state.lexical_requests = {}
