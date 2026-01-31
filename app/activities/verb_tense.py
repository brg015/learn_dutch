"""
Verb Tense Activity

Learning mode: Practice verb conjugations (perfectum and past tense).
"""

import streamlit as st
from app.activities.base import AbstractActivity
from app.ui.flashcard import render_flashcard


class VerbTenseActivity(AbstractActivity):
    """
    Verb tense learning activity - practice perfectum and past tense conjugations.

    Sequential flow:
    1. Show infinitive → user provides perfectum (auxiliary + past participle)
    2. Show infinitive → user provides past tense (singular and plural)
    """

    def __init__(self, word: dict, tense_step: str):
        """
        Initialize verb tense activity.

        Args:
            word: Word dict with verb_meta
            tense_step: "perfectum" or "past_tense"
        """
        super().__init__(word)
        self.tense_step = tense_step
        self.verb_meta = word.get('verb_meta', {})

        # Validate verb metadata exists
        if not self.verb_meta:
            st.error(f"⚠️ Warning: Verb '{word.get('lemma')}' missing verb_meta. Please run Phase 2 enrichment.")

    def render_card_front(self) -> None:
        """Render infinitive and instruction on front of card."""
        word = self.word
        lemma = word.get("lemma", "")

        # For reflexive verbs, show full form (e.g., "zich schamen")
        if self.verb_meta.get("is_reflexive"):
            lemma_text = f"zich {lemma}"
        else:
            lemma_text = lemma

        render_flashcard(
            main_text=lemma_text,
            main_font_size="2.6em",
            subtitle_font_size="1.0em",
            bg_color="#f0f2f6"
        )

    def render_card_back(self) -> None:
        """Render correct answer and example on back of card."""
        word = self.word
        lemma = word.get("lemma", "")

        # For reflexive verbs, show full form
        if self.verb_meta.get("is_reflexive"):
            corner_text = f"zich {lemma}"
        else:
            corner_text = lemma

        # Build answer based on tense step
        if self.tense_step == "perfectum":
            answer_text, example_sentence = self._build_perfectum_answer()
        else:  # past_tense
            answer_text, example_sentence = self._build_past_answer()

        # Show example sentence as subtitle if available
        subtitle_text = ""
        if example_sentence:
            dutch = example_sentence.get("dutch", "")
            english = example_sentence.get("english", "")
            subtitle_text = f"<span style='color: #555;'>🇳🇱 {dutch}</span><br><span style='color: #777; font-size: 0.9em;'>🇬🇧 {english}</span>"

        render_flashcard(
            main_text=answer_text,
            subtitle=subtitle_text,
            corner_text=corner_text,
            main_font_size="2.2em",
            subtitle_font_size="1.0em",
            bg_color="#e8f4f8",
            wrap_text=True
        )

    def _build_perfectum_answer(self) -> tuple[str, dict | None]:
        """
        Build perfectum answer text and example sentence.

        Returns:
            Tuple of (answer_text, example_sentence_dict)
        """
        auxiliary = self.verb_meta.get("auxiliary", "?")
        past_participle = self.verb_meta.get("past_participle", "?")

        # Build answer (infinitive auxiliary + past participle)
        answer_text = f"{auxiliary} {past_participle}"

        # Add irregularity warning if applicable
        if self.verb_meta.get("is_irregular_participle"):
            answer_text += "<br><span style='font-size: 0.7em; color: #d9534f;'>⚠️ Irregular participle</span>"

        # Get example sentence from examples_perfect
        examples_perfect = self.verb_meta.get("examples_perfect", [])
        example = examples_perfect[0] if examples_perfect else None

        return answer_text, example

    def _build_past_answer(self) -> tuple[str, dict | None]:
        """
        Build past tense answer text and example sentence.

        Returns:
            Tuple of (answer_text, example_sentence_dict)
        """
        past_singular = self.verb_meta.get("past_singular", "?")
        past_plural = self.verb_meta.get("past_plural", "?")

        # Build answer (singular / plural)
        answer_text = f"{past_singular} / {past_plural}"

        # Add irregularity warning if applicable
        if self.verb_meta.get("is_irregular_past"):
            answer_text += "<br><span style='font-size: 0.7em; color: #d9534f;'>⚠️ Irregular past tense</span>"

        # Get example sentence from examples_past
        examples_past = self.verb_meta.get("examples_past", [])
        example = examples_past[0] if examples_past else None

        return answer_text, example


    def get_presentation_mode(self) -> str:
        """Return presentation mode identifier for analytics."""
        return f"verb_{self.tense_step}"  # "verb_perfectum" or "verb_past_tense"
