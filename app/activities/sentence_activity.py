"""
Sentence Activity

Learning mode: Practice words in sentence context.
"""

import random
from app.activities.base import AbstractActivity
from app.ui.flashcard import render_flashcard
from app.ui.flashcard_style import SENTENCE_BACK_STYLE, SENTENCE_FRONT_STYLE


class SentenceActivity(AbstractActivity):
    """
    Sentence learning activity - practice words in context.
    
    Renders word in a sentence on front, translations on back.
    """

    def __init__(self, word: dict):
        """
        Initialize sentence activity.
        
        Args:
            word: Word dict with general_examples containing sentences
        """
        super().__init__(word)
        self.example = self._select_example()

    def _select_example(self) -> dict:
        """Select a random example sentence for this word."""
        examples = self.word.get('general_examples', [])
        if examples:
            return random.choice(examples)
        return None

    def render_card_front(self) -> None:
        """Render sentence on front of card."""
        if self.example is None:
            render_flashcard(
                main_text="No example sentences available",
                style=SENTENCE_FRONT_STYLE,
                main_color="#999",
            )
            return
        
        sentence = self.example['dutch']
        
        # Get lemma with article for nouns
        lemma_text = self.word["lemma"]
        if self.word["pos"] == "noun" and self.word.get("noun_meta", {}).get("article"):
            article = self.word["noun_meta"]["article"]
            lemma_text = f"{article} {lemma_text}"
        
        render_flashcard(
            main_text=sentence,
            corner_text=lemma_text,
            style=SENTENCE_FRONT_STYLE,
        )

    def render_card_back(self) -> None:
        """Render translations on back of card."""
        if self.example is None:
            render_flashcard(
                main_text="No example sentences available",
                style=SENTENCE_BACK_STYLE,
                main_color="#999",
            )
            return
        
        translation = self.word.get("translation", "No translation")
        sentence_translation = self.example['english']
        
        # Get lemma with article for nouns
        lemma_text = self.word["lemma"]
        if self.word["pos"] == "noun" and self.word.get("noun_meta", {}).get("article"):
            article = self.word["noun_meta"]["article"]
            lemma_text = f"{article} {lemma_text}"
        
        render_flashcard(
            main_text=translation,
            subtitle=sentence_translation,
            corner_text=lemma_text,
            style=SENTENCE_BACK_STYLE,
        )

    def get_presentation_mode(self) -> str:
        """Return presentation mode."""
        return "sentences"

    def get_current_example(self) -> dict:
        """Get the currently displayed example."""
        return self.example
