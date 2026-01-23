"""UI Components for Dutch Trainer"""

from app.ui.flashcard import render_flashcard
from app.ui.session_stats import render_session_stats, render_session_complete
from app.ui.feedback_buttons import render_feedback_buttons
from app.ui.details import render_word_details

__all__ = [
    "render_flashcard",
    "render_session_stats",
    "render_session_complete",
    "render_feedback_buttons",
    "render_word_details",
]
