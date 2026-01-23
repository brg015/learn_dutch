"""
Word Activity

Learning mode: Practice individual words.
"""

from app.activities.base import AbstractActivity
from app.ui.flashcard import render_flashcard


class WordActivity(AbstractActivity):
    """
    Word learning activity - practice individual words.
    
    Renders word on front, translation on back.
    """

    def render_card_front(self) -> None:
        """Render word on front of card."""
        word = self.word
        render_flashcard(
            main_text=word["lemma"],
            main_font_size="3.5em",
            bg_color="#f0f2f6"
        )

    def render_card_back(self) -> None:
        """Render translation on back of card."""
        word = self.word
        translation_text = word.get("translation", "No translation")
        
        # Get lemma with article for nouns
        lemma_text = word["lemma"]
        if word["pos"] == "noun" and word.get("noun_meta", {}).get("article"):
            article = word["noun_meta"]["article"]
            lemma_text = f"{article} {lemma_text}"
        
        render_flashcard(
            main_text=translation_text,
            corner_text=lemma_text,
            bg_color="#e8f4f8"
        )

    def get_presentation_mode(self) -> str:
        """Return presentation mode."""
        return "words"
