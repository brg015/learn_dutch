"""
Dutch Vocabulary Trainer - Main App

Clean, modularized Streamlit UI for the FSRS vocabulary learning system.
"""

import streamlit as st

from core import fsrs
from app.state import ensure_session_state, init_database
from app.session_controller import end_session
from app.ui import render_session_stats
from app.router import PAGES


# ---- User Configuration ----

USER_OPTIONS = {
    "Ben": "ben",
    "Test": "test",
}


# ---- Page Setup ----

st.set_page_config(
    page_title="Dutch Vocabulary Trainer",
    page_icon="🇳🇱",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ---- Database Initialization ----

init_database()


# ---- Session State Initialization ----

ensure_session_state(USER_OPTIONS)


# ---- Main App ----

def _render_user_entry_screen() -> None:
    """
    Render a simple per-launch user selection screen.
    """
    st.title("🇳🇱 Dutch Vocabulary Trainer")
    st.markdown("### Select User")
    labels = list(USER_OPTIONS.keys())
    selected_label = st.radio(
        "Who is studying?",
        labels,
        index=labels.index(st.session_state.user_label)
        if st.session_state.user_label in labels
        else 0,
        horizontal=True,
    )
    if st.button("Enter App", type="primary", use_container_width=True):
        st.session_state.user_label = selected_label
        st.session_state.user_id = USER_OPTIONS[selected_label]
        st.session_state.user_id_active = st.session_state.user_id

        # Reset launch-scoped pools/requests to avoid stale cross-user state.
        st.session_state.word_pool_state = None
        st.session_state.verb_pool_state = None
        st.session_state.preposition_pool_state = None
        st.session_state.lexical_requests = {}

        st.session_state.user_selected = True
        st.rerun()


def main():
    """Main app entry point."""
    if not st.session_state.user_selected:
        _render_user_entry_screen()
        return

    # Session stats and quit button
    quit_clicked = render_session_stats()
    if quit_clicked:
        end_session()
        st.rerun()

    if st.session_state.current_word is None:
        tabs = st.tabs([page.title for page in PAGES])
        for tab, page in zip(tabs, PAGES):
            with tab:
                page.render(USER_OPTIONS)
    else:
        PAGES[0].render(USER_OPTIONS)


if __name__ == "__main__":
    main()


