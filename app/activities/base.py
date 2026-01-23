"""
Abstract Base Activity

Defines the interface for learning activities (words, sentences, etc).
"""

from abc import ABC, abstractmethod
import streamlit as st


class AbstractActivity(ABC):
    """
    Abstract base class for learning activities.
    
    Subclasses should implement:
    - render_card_front()
    - render_card_back()
    - get_presentation_mode()
    """

    def __init__(self, word: dict):
        """
        Initialize activity.
        
        Args:
            word: Word dict with all metadata
        """
        self.word = word

    @abstractmethod
    def render_card_front(self) -> None:
        """Render the front side of the flashcard."""
        pass

    @abstractmethod
    def render_card_back(self) -> None:
        """Render the back side of the flashcard."""
        pass

    @abstractmethod
    def get_presentation_mode(self) -> str:
        """Return the presentation mode identifier (e.g., 'words', 'sentences')."""
        pass
