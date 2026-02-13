"""
Session lifecycle helpers for Streamlit app.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import streamlit as st

from app.activity_registry import get_activity_spec
from app.session_requests import (
    request_key_for_mode,
    normalize_lexical_request,
    LexicalRequest,
)
from app.session_types import SessionItem
from core import fsrs
from core.session_builders.pool_utils import update_pool_state


KNOWN_POOL_ATTR_BY_EXERCISE_TYPE = {
    "word_translation": "word_pool_state",
    "word_preposition": "preposition_pool_state",
    "verb_perfectum": "verb_pool_state",
    "verb_past_tense": "verb_pool_state",
}


def _get_request_for_mode(mode: str) -> LexicalRequest:
    requests = st.session_state.lexical_requests
    request_key = request_key_for_mode(mode)
    request = normalize_lexical_request(
        requests.get(request_key),
        st.session_state.user_id,
        request_key,
    )
    requests[request_key] = request
    return request


def _get_pool_state(spec, request: LexicalRequest):
    if spec.pool_key == "word_pool":
        if st.session_state.word_pool_state is None:
            st.session_state.word_pool_state = spec.build_pool(request)
        return st.session_state.word_pool_state
    if spec.pool_key == "verb_pool":
        if st.session_state.verb_pool_state is None:
            st.session_state.verb_pool_state = spec.build_pool(request)
        return st.session_state.verb_pool_state
    if spec.pool_key == "preposition_pool":
        if st.session_state.preposition_pool_state is None:
            st.session_state.preposition_pool_state = spec.build_pool(request)
        return st.session_state.preposition_pool_state
    raise ValueError(f"Unknown pool key: {spec.pool_key}")


def start_new_session(mode: str) -> None:
    """
    Start a new learning session.
    """
    if st.session_state.user_id != getattr(st.session_state, "user_id_active", st.session_state.user_id):
        st.session_state.word_pool_state = None
        st.session_state.verb_pool_state = None
        st.session_state.preposition_pool_state = None
        st.session_state.lexical_requests = {}
        st.session_state.user_id_active = st.session_state.user_id

    spec = get_activity_spec(mode)
    request = _get_request_for_mode(mode)
    pool_state = _get_pool_state(spec, request)

    try:
        if mode == "verb_tenses":
            with st.spinner("Creating verb session..."):
                items, message = spec.build_items(pool_state, request)
        else:
            items, message = spec.build_items(pool_state, request)
    except Exception as exc:
        st.error(f"Error creating session: {exc}")
        import traceback
        st.code(traceback.format_exc())
        return

    if not items:
        st.error(message or "No items available.")
        return

    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.session_batch = items
    st.session_state.session_position = 0
    st.session_state.session_count = 0
    st.session_state.session_correct = 0
    st.session_state.learning_mode = mode
    st.session_state.review_events_buffer = []
    st.session_state.cards_buffer = []
    st.session_state.verb_response_buffer = {}

    load_next_item()


def load_next_item() -> None:
    """
    Load the next session item, or finish the session.
    """
    if st.session_state.session_position >= len(st.session_state.session_batch):
        flush_buffers()
        st.session_state.current_word = None
        st.session_state.activity = None
        return

    item: SessionItem = st.session_state.session_batch[st.session_state.session_position]

    st.session_state.current_word = item.word
    st.session_state.current_exercise_type = item.exercise_type
    st.session_state.current_tense_step = item.tense_step
    st.session_state.show_answer = item.show_answer_on_load
    st.session_state.start_time = datetime.now(timezone.utc)

    if "answer_choice" in st.session_state:
        st.session_state.pop("answer_choice", None)

    spec = get_activity_spec(st.session_state.learning_mode)
    st.session_state.activity = spec.activity_factory(item)


def _get_pool_state_for_exercise(exercise_type: str):
    pool_attr = KNOWN_POOL_ATTR_BY_EXERCISE_TYPE.get(exercise_type)
    if not pool_attr:
        return None
    return getattr(st.session_state, pool_attr, None)


def _is_known_no_score(exercise_type: str, word_id: str, card) -> bool:
    """
    True when this item comes from a KNOWN pool and should not update FSRS state.
    """
    if card is None:
        return False
    pool_state = _get_pool_state_for_exercise(exercise_type)
    return pool_state is not None and word_id in pool_state.known


def _build_known_no_score_event(card: fsrs.CardState, feedback_grade: fsrs.FeedbackGrade, latency_ms: int | None) -> dict:
    retrievability_before = None
    if card.last_ltm_timestamp is not None and card.review_count > 0:
        days_since_ltm = fsrs.get_days_since_ltm_review(card.last_ltm_timestamp)
        retrievability_before = fsrs.calculate_retrievability(card.stability, days_since_ltm)

    return {
        "word_id": card.word_id,
        "lemma": card.lemma,
        "pos": card.pos,
        "exercise_type": card.exercise_type,
        "timestamp": datetime.now(timezone.utc),
        "feedback_grade": feedback_grade,
        "latency_ms": latency_ms,
        "stability_before": card.stability,
        "difficulty_before": card.difficulty,
        "d_eff_before": card.d_eff,
        "retrievability_before": retrievability_before,
        "stability_after": card.stability,
        "difficulty_after": card.difficulty,
        "d_eff_after": card.d_eff,
        "is_ltm_event": 2,  # Known fallback no-score event
        "session_id": st.session_state.session_id,
        "session_position": st.session_state.session_position,
        "presentation_mode": st.session_state.activity.get_presentation_mode(),
        "user_id": st.session_state.user_id,
    }


def process_feedback(feedback_grade: fsrs.FeedbackGrade) -> None:
    """
    Process user feedback and move to next item.
    """
    if st.session_state.current_word:
        word = st.session_state.current_word
        exercise_type = st.session_state.current_exercise_type

        latency_ms = None
        if st.session_state.start_time:
            elapsed = datetime.now(timezone.utc) - st.session_state.start_time
            latency_ms = int(elapsed.total_seconds() * 1000)

        card = fsrs.load_card_state(st.session_state.user_id, word["word_id"], exercise_type)
        is_known_no_score = _is_known_no_score(exercise_type, word["word_id"], card)

        if card is None and not is_known_no_score:
            card = fsrs.CardState(
                user_id=st.session_state.user_id,
                word_id=word["word_id"],
                exercise_type=exercise_type,
                lemma=word["lemma"],
                pos=word["pos"],
                stability=fsrs.INITIAL_STABILITY,
                difficulty=fsrs.INITIAL_DIFFICULTY,
                d_eff=fsrs.INITIAL_DIFFICULTY,
                review_count=0,
                last_review_timestamp=datetime.now(timezone.utc),
                last_ltm_timestamp=None,
                ltm_review_date=None,
                stm_success_count_today=0
            )

        if is_known_no_score:
            event_data = _build_known_no_score_event(card, feedback_grade, latency_ms)
        else:
            updated_card, event_data = fsrs.process_review(card, feedback_grade)
            event_data["user_id"] = st.session_state.user_id
            event_data["latency_ms"] = latency_ms
            event_data["session_id"] = st.session_state.session_id
            event_data["session_position"] = st.session_state.session_position
            event_data["presentation_mode"] = st.session_state.activity.get_presentation_mode()
            st.session_state.cards_buffer.append(updated_card)

        st.session_state.review_events_buffer.append(event_data)

        if not is_known_no_score and exercise_type == "word_translation":
            if st.session_state.word_pool_state is not None:
                update_pool_state(
                    st.session_state.word_pool_state,
                    word["word_id"],
                    feedback_grade
                )
        elif not is_known_no_score and exercise_type in ("verb_perfectum", "verb_past_tense"):
            if st.session_state.verb_pool_state is not None:
                word_id = word["word_id"]
                buffer = st.session_state.verb_response_buffer
                buffer.setdefault(word_id, []).append(feedback_grade)

                if len(buffer[word_id]) >= 2:
                    grades = buffer.pop(word_id)

                    if fsrs.FeedbackGrade.AGAIN in grades:
                        combined = fsrs.FeedbackGrade.AGAIN
                    else:
                        in_stm = word_id in st.session_state.verb_pool_state.stm
                        if in_stm and all(g == fsrs.FeedbackGrade.EASY for g in grades):
                            combined = fsrs.FeedbackGrade.EASY
                        elif in_stm:
                            combined = fsrs.FeedbackGrade.HARD
                        else:
                            combined = fsrs.FeedbackGrade.MEDIUM

                    update_pool_state(
                        st.session_state.verb_pool_state,
                        word_id,
                        combined
                    )
        elif not is_known_no_score and exercise_type == "word_preposition":
            if st.session_state.preposition_pool_state is not None:
                update_pool_state(
                    st.session_state.preposition_pool_state,
                    word["word_id"],
                    feedback_grade
                )

        st.session_state.session_count += 1
        if feedback_grade != fsrs.FeedbackGrade.AGAIN:
            st.session_state.session_correct += 1

        st.session_state.session_position += 1

    load_next_item()
    st.rerun()


def flush_buffers() -> None:
    """
    Flush buffered cards and events to the database.
    """
    if st.session_state.cards_buffer:
        fsrs.batch_save_card_states(st.session_state.cards_buffer)
    if st.session_state.review_events_buffer:
        fsrs.batch_log_review_events(st.session_state.review_events_buffer)
    st.session_state.review_events_buffer = []
    st.session_state.cards_buffer = []


def end_session() -> None:
    """
    End the current session.
    """
    flush_buffers()
    st.session_state.current_word = None
    st.session_state.session_batch = []
    st.session_state.learning_mode = None
    st.session_state.activity = None
