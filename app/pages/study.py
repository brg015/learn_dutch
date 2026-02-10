"""
Study page rendering.
"""

from __future__ import annotations

import streamlit as st

from app.session_controller import start_new_session, process_feedback
from app.ui import (
    render_session_complete,
    render_feedback_buttons,
    render_word_details,
)
from core import fsrs


def render_study_page(user_options: dict[str, str]) -> None:
    """
    Render the study flow (intro or active session).
    """
    if st.session_state.current_word is None:
        _render_intro_screen(user_options)
    else:
        _render_active_session()


def _render_intro_screen(user_options: dict[str, str]) -> None:
    st.markdown("<style>.stApp h1 { font-size: 1.6rem; }</style>", unsafe_allow_html=True)
    st.title("🇳🇱 Dutch Vocabulary Trainer")
    if fsrs.is_test_mode():
        st.warning("⚠️ **TEST MODE** - Using test_learning_db (set TEST_MODE=false in .env for production)")
    st.markdown("<br>" * 3, unsafe_allow_html=True)
    st.markdown(f"**Welcome {st.session_state.user_label}**")

    if st.session_state.session_count > 0:
        render_session_complete()

    st.markdown("### 📚 Word Learning")
    st.markdown("Choose how you'd like to practice:")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Only Words", type="primary", use_container_width=True, help="Practice individual words"):
            start_new_session("words")
            st.rerun()

    with col2:
        if st.button("Sentences", type="primary", use_container_width=True, help="Practice words in context"):
            start_new_session("sentences")
            st.rerun()

    st.markdown("### Grammar & Usage")
    st.markdown("Practice conjugation and usage patterns:")

    st.markdown(
        """
        <style>
        div[data-testid="baseButton-secondary"] > button,
        button[kind="secondary"] {
            background: #2563eb;
            color: #ffffff;
            border: 1px solid #1d4ed8;
        }
        div[data-testid="baseButton-secondary"] > button:hover,
        button[kind="secondary"]:hover {
            background: #1d4ed8;
            color: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    col_grammar_1, col_grammar_2 = st.columns(2)

    with col_grammar_1:
        if st.button("Verb Tenses", type="secondary", use_container_width=True, help="Practice verb conjugations"):
            start_new_session("verb_tenses")
            st.rerun()

    with col_grammar_2:
        if st.button("Prepositions", type="secondary", use_container_width=True, help="Practice fixed preposition usage"):
            start_new_session("prepositions")
            st.rerun()

def _render_active_session() -> None:
    word = st.session_state.current_word
    activity = st.session_state.activity

    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.show_answer:
        activity.render_card_front()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Reveal Answer", use_container_width=True, type="primary"):
            st.session_state.show_answer = True
            st.rerun()
    else:
        activity.render_card_back()
        st.markdown("<br>", unsafe_allow_html=True)

        key_suffix = f"{st.session_state.learning_mode}_{st.session_state.session_position}"
        feedback = render_feedback_buttons(key_suffix=key_suffix)
        if feedback is not None:
            process_feedback(feedback)

        st.markdown("<br>", unsafe_allow_html=True)
        render_word_details(word)

    if fsrs.is_test_mode():
        st.caption("TEST MODE - Using test_learning_db")

