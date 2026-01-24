"""
Feedback Button UI

Renders grading buttons for user feedback.
"""

import streamlit as st
from core import fsrs


def render_feedback_buttons() -> fsrs.FeedbackGrade:
    """
    Render feedback grading buttons.
    
    Returns:
        FeedbackGrade selected by user, or None if no button clicked
    """
    st.markdown("**How well did you remember this word?**")

    st.markdown(
        """
        <style>
        .stRadio div[role="radiogroup"] {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        .stRadio label {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 0.55rem 0.6rem;
            text-align: center;
            background: #f9fafb;
        }
        .stRadio label:hover {
            border-color: #bbb;
            background: #f3f4f6;
        }
        .stRadio label div {
            justify-content: center;
            font-weight: 600;
            color: #111;
        }
        .stRadio input {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    choice = st.radio(
        "Answer",
        ["❌ Again", "😰 Hard", "👍 Medium", "✨ Easy"],
        index=None,
        key="answer_choice",
        label_visibility="collapsed"
    )

    if choice is None:
        return None
    if choice.startswith("❌"):
        return fsrs.FeedbackGrade.AGAIN
    if choice.startswith("😰"):
        return fsrs.FeedbackGrade.HARD
    if choice.startswith("👍"):
        return fsrs.FeedbackGrade.MEDIUM
    return fsrs.FeedbackGrade.EASY

