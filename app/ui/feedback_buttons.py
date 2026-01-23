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

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        if st.button("❌ Again", use_container_width=True, help="Completely forgot"):
            return fsrs.FeedbackGrade.AGAIN

    with row1_col2:
        if st.button("😰 Hard", use_container_width=True, help="Remembered with difficulty"):
            return fsrs.FeedbackGrade.HARD

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        if st.button("👍 Medium", use_container_width=True, help="Remembered normally"):
            return fsrs.FeedbackGrade.MEDIUM

    with row2_col2:
        if st.button("✨ Easy", use_container_width=True, help="Remembered easily"):
            return fsrs.FeedbackGrade.EASY

    return None

