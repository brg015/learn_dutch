"""
Dutch Vocabulary Trainer - Main App

Clean, modularized Streamlit UI for the FSRS vocabulary learning system.
"""

import streamlit as st
import uuid
from datetime import datetime, timezone

from core import session_builder, fsrs
from core import verb_session_builder
from app.activities import WordActivity, SentenceActivity, VerbTenseActivity
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

@st.cache_resource
def _init_database():
    """Initialize database schema if needed (runs once per session)."""
    fsrs.init_db()


_init_database()


# ---- Session State Initialization ----

def _init_session_state():
    """Initialize all session state variables."""
    if "user_id" not in st.session_state:
        default_user_id = fsrs.get_default_user_id()
        st.session_state.user_id = default_user_id
        st.session_state.user_label = next(
            (label for label, uid in USER_OPTIONS.items() if uid == default_user_id),
            "Ben"
        )
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


_init_session_state()


# ---- Session Management ----

def start_new_session(mode: str):
    """
    Start a new learning session.

    Args:
        mode: Learning mode ("words", "sentences", or "verb_tenses")
    """
    if mode == "verb_tenses":
        # Create verb tense session (returns triplets)
        try:
            print("[STREAMLIT] Starting verb session creation...")
            with st.spinner("Creating verb session..."):
                triplets, message = verb_session_builder.create_verb_tense_session(
                    user_id=st.session_state.user_id,
                    r_threshold=fsrs.R_TARGET,
                    filter_known=True
                )
            print(f"[STREAMLIT] Session creation complete. Got {len(triplets)} triplets")

            if not triplets:
                st.error(message)
                return  # Don't create session, but allow rerun
        except Exception as e:
            st.error(f"Error creating verb session: {e}")
            import traceback
            st.code(traceback.format_exc())
            return  # Don't create session, but allow rerun

        # Flatten triplets into sequential exercises
        # Each triplet: (word_dict, "perfectum", "past_tense")
        batch = []
        for word, _, _ in triplets:
            batch.append((word, "perfectum"))
            batch.append((word, "past_tense"))
    else:
        # Word translation session (words or sentences mode)
        batch = session_builder.create_session(
            exercise_type='word_translation',
            tag=None,
            user_id=st.session_state.user_id
        )

    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.session_batch = batch
    st.session_state.session_position = 0
    st.session_state.session_count = 0
    st.session_state.session_correct = 0
    st.session_state.learning_mode = mode
    st.session_state.review_events_buffer = []
    st.session_state.cards_buffer = []

    load_next_word()


def load_next_word():
    """Load the next word from the session batch."""
    if st.session_state.session_position >= len(st.session_state.session_batch):
        # Session complete
        flush_buffers()
        st.session_state.current_word = None
        st.session_state.activity = None
        return

    # Handle different batch formats based on mode
    if st.session_state.learning_mode == "verb_tenses":
        # Batch contains tuples: (word_dict, tense_step)
        word, tense_step = st.session_state.session_batch[st.session_state.session_position]
        st.session_state.current_tense_step = tense_step
        st.session_state.current_exercise_type = f"verb_{tense_step}"
    else:
        # Batch contains word dicts
        word = st.session_state.session_batch[st.session_state.session_position]
        st.session_state.current_exercise_type = "word_translation"
        st.session_state.current_tense_step = None

    st.session_state.current_word = word
    st.session_state.show_answer = False
    st.session_state.start_time = datetime.now(timezone.utc)
    if "answer_choice" in st.session_state:
        st.session_state.pop("answer_choice", None)
    if st.session_state.learning_mode == "verb_tenses":
        st.session_state.show_answer = st.session_state.current_tense_step == "past_tense"

    # Create activity based on mode
    if st.session_state.learning_mode == "words":
        st.session_state.activity = WordActivity(word)
    elif st.session_state.learning_mode == "sentences":
        st.session_state.activity = SentenceActivity(word)
    elif st.session_state.learning_mode == "verb_tenses":
        st.session_state.activity = VerbTenseActivity(word, st.session_state.current_tense_step)


def process_feedback(feedback_grade: fsrs.FeedbackGrade):
    """
    Process user feedback and move to next word.

    Args:
        feedback_grade: User's grade feedback
    """
    if st.session_state.current_word:
        word = st.session_state.current_word
        exercise_type = st.session_state.current_exercise_type

        # Calculate latency
        latency_ms = None
        if st.session_state.start_time:
            elapsed = datetime.now(timezone.utc) - st.session_state.start_time
            latency_ms = int(elapsed.total_seconds() * 1000)

        # Load or initialize card state (use current exercise_type)
        card = fsrs.load_card_state(st.session_state.user_id, word["word_id"], exercise_type)
        if card is None:
            card = fsrs.CardState(
                user_id=st.session_state.user_id,
                word_id=word["word_id"],
                exercise_type=exercise_type,
                lemma=word["lemma"],
                pos=word["pos"],
                stability=4.0,
                difficulty=5.0,
                d_eff=5.0,
                review_count=0,
                last_review_timestamp=datetime.now(timezone.utc),
                last_ltm_timestamp=None,
                ltm_review_date=None,
                stm_success_count_today=0
            )

        # Process review
        updated_card, event_data = fsrs.process_review(card, feedback_grade)
        event_data['user_id'] = st.session_state.user_id
        event_data['latency_ms'] = latency_ms
        event_data['session_id'] = st.session_state.session_id
        event_data['session_position'] = st.session_state.session_position
        event_data['presentation_mode'] = st.session_state.activity.get_presentation_mode()

        # Buffer for batch write
        st.session_state.cards_buffer.append(updated_card)
        st.session_state.review_events_buffer.append(event_data)

        # Update session stats
        st.session_state.session_count += 1
        if feedback_grade != fsrs.FeedbackGrade.AGAIN:
            st.session_state.session_correct += 1

        st.session_state.session_position += 1

    load_next_word()
    st.rerun()


def flush_buffers():
    """Flush buffered cards and events to database."""
    if st.session_state.cards_buffer:
        fsrs.batch_save_card_states(st.session_state.cards_buffer)
    if st.session_state.review_events_buffer:
        fsrs.batch_log_review_events(st.session_state.review_events_buffer)
    st.session_state.review_events_buffer = []
    st.session_state.cards_buffer = []


def end_session():
    """End the current session."""
    flush_buffers()
    st.session_state.current_word = None
    st.session_state.session_batch = []
    st.session_state.learning_mode = None
    st.session_state.activity = None


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


