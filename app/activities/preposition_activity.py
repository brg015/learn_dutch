"""
Preposition Activity

Practice fixed/prepositional usage by filling a missing preposition in context.
"""

from __future__ import annotations

import random

from app.activities.base import AbstractActivity
from app.ui.flashcard import render_flashcard
from app.ui.flashcard_style import PREPOSITION_BACK_STYLE, PREPOSITION_FRONT_STYLE
from core.preposition_drill import (
    PrepositionUsageOption,
    build_preposition_usages,
    emphasize_preposition,
)


class PrepositionActivity(AbstractActivity):
    """
    Preposition drill activity.

    For each card:
    - select one preposition usage
    - select one example sentence from that usage
    - show sentence with the selected preposition blanked
    """

    def __init__(self, word: dict):
        super().__init__(word)
        self.selected_usage, self.selected_example = self._select_prompt()

    def _select_prompt(self):
        usages = build_preposition_usages(self.word)
        if not usages:
            return None, None

        usage: PrepositionUsageOption = random.choice(usages)
        example = random.choice(usage.examples)
        return usage, example

    def _lemma_with_article(self) -> str:
        lemma_text = self.word.get("lemma", "")
        noun_meta = self.word.get("noun_meta") or {}
        if self.word.get("pos") == "noun" and noun_meta.get("article"):
            article = noun_meta["article"]
            lemma_text = f"{article} {lemma_text}"
        return lemma_text

    def render_card_front(self) -> None:
        if not self.selected_usage or not self.selected_example:
            render_flashcard(
                main_text="No preposition examples available",
                style=PREPOSITION_FRONT_STYLE,
                main_color="#999",
            )
            return

        render_flashcard(
            main_text=self.selected_example.blanked_dutch,
            corner_text=self._lemma_with_article(),
            style=PREPOSITION_FRONT_STYLE,
        )

    def render_card_back(self) -> None:
        if not self.selected_usage or not self.selected_example:
            render_flashcard(
                main_text="No preposition examples available",
                style=PREPOSITION_BACK_STYLE,
                main_color="#999",
            )
            return

        render_flashcard(
            main_text=(
                emphasize_preposition(
                    self.selected_example.dutch,
                    self.selected_usage.preposition,
                )
                or self.selected_example.dutch
            ),
            subtitle=self.selected_example.english,
            corner_text=self._lemma_with_article(),
            style=PREPOSITION_BACK_STYLE,
        )

    def get_presentation_mode(self) -> str:
        return "prepositions"
