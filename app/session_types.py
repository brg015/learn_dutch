"""
Session item types used by the Streamlit controller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SessionItem:
    """
    A single study step within a session batch.
    """
    word: dict
    exercise_type: str
    tense_step: Optional[str] = None
    show_answer_on_load: bool = False
