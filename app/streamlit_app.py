"""
Dutch Vocabulary Trainer - Main App

Clean, modularized Streamlit UI for the FSRS vocabulary learning system.
"""

import streamlit as st

from core import fsrs
from app.state import ensure_session_state, init_database
from app.session_controller import start_new_session, process_feedback, end_session
from app.ui import (
    render_session_stats,
    render_session_complete,
    render_feedback_buttons,
    render_word_details,
)


# ---- User Configuration ----

USER_OPTIONS = {
    "Ben": "ben",
    "Test": "test",
}


# ---- Page Setup ----

st.set_page_config(
    page_title="Dutch Vocabulary Trainer",
    page_icon="🇳🇱",
    layout="centered"
)


# ---- Database Initialization ----

init_database()


# ---- Session State Initialization ----

ensure_session_state(USER_OPTIONS)


# ---- UI Rendering ----

def render_test_mode_warning():
    """Show warning if in test mode."""
    if fsrs.is_test_mode():
        st.warning("⚠️ **TEST MODE** - Using test_learning_db (set TEST_MODE=false in .env for production)")


def render_intro_screen():
    """Render intro screen with mode selection."""
    st.markdown("<style>.stApp h1 { font-size: 1.6rem; }</style>", unsafe_allow_html=True)
    st.title("🇳🇱 Dutch Vocabulary Trainer")
    render_test_mode_warning()
    st.markdown("<br>" * 3, unsafe_allow_html=True)

    user_labels = list(USER_OPTIONS.keys())
    selected_label = st.selectbox(
        "User",
        user_labels,
        index=user_labels.index(st.session_state.user_label)
        if st.session_state.user_label in user_labels
        else 0
    )
    st.session_state.user_label = selected_label
    st.session_state.user_id = USER_OPTIONS[selected_label]
    st.markdown(f"**Welcome {selected_label}**")

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

    st.markdown("### 🔄 Verb Conjugation")
    st.markdown("Practice verb tenses (perfectum and past tense):")

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

    if st.button("Verb Tenses", type="secondary", use_container_width=True, help="Practice verb conjugations"):
        start_new_session("verb_tenses")
        st.rerun()


def render_active_session():
    """Render active learning session."""
    word = st.session_state.current_word
    activity = st.session_state.activity

    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.show_answer:
        # Show card front
        activity.render_card_front()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Reveal Answer", use_container_width=True, type="primary"):
            st.session_state.show_answer = True
            st.rerun()
    else:
        # Show card back
        activity.render_card_back()
        st.markdown("<br>", unsafe_allow_html=True)

        # Feedback buttons
        key_suffix = f"{st.session_state.learning_mode}_{st.session_state.session_position}"
        feedback = render_feedback_buttons(key_suffix=key_suffix)
        if feedback is not None:
            process_feedback(feedback)
            # Don't rerun here - Streamlit naturally reruns from button click

        st.markdown("<br>", unsafe_allow_html=True)
        render_word_details(word)

    if fsrs.is_test_mode():
        st.caption("TEST MODE - Using test_learning_db")


# ---- Main App ----

def main():
    """Main app entry point."""
    # Session stats and quit button
    quit_clicked = render_session_stats()
    if quit_clicked:
        end_session()
        st.rerun()

    # Main content
    if st.session_state.current_word is None:
        render_intro_screen()
    else:
        render_active_session()


if __name__ == "__main__":
    main()


