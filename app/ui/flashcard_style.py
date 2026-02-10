"""
Flashcard style presets and constants.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---- Shared Card Layout ----

CARD_PADDING = "35px 24px"
CARD_MIN_HEIGHT = "210px"
FRONT_BG_COLOR = "#f0f2f6"
BACK_BG_COLOR = "#e8f4f8"


# ---- Shared Typography Defaults ----

DEFAULT_MAIN_FONT_SIZE = "3em"
DEFAULT_MAIN_COLOR = "#1f1f1f"
DEFAULT_MAIN_WEIGHT = "normal"
DEFAULT_SUBTITLE_FONT_SIZE = "1.2em"
DEFAULT_SUBTITLE_COLOR = "#666"
DEFAULT_SUBTITLE_STYLE = "italic"
DEFAULT_CORNER_FONT_SIZE = "0.9em"
DEFAULT_CORNER_COLOR = "#666"
DEFAULT_CORNER_STYLE = "italic"


@dataclass(frozen=True)
class FlashcardStyle:
    """
    Visual style preset for flashcards.
    """
    main_font_size: str = DEFAULT_MAIN_FONT_SIZE
    main_color: str = DEFAULT_MAIN_COLOR
    main_weight: str = DEFAULT_MAIN_WEIGHT
    subtitle_font_size: str = DEFAULT_SUBTITLE_FONT_SIZE
    subtitle_color: str = DEFAULT_SUBTITLE_COLOR
    subtitle_style: str = DEFAULT_SUBTITLE_STYLE
    corner_font_size: str = DEFAULT_CORNER_FONT_SIZE
    corner_color: str = DEFAULT_CORNER_COLOR
    corner_style: str = DEFAULT_CORNER_STYLE
    wrap_text: bool = False
    bg_color: str = FRONT_BG_COLOR


DEFAULT_FLASHCARD_STYLE = FlashcardStyle()


# ---- Activity Presets ----

WORD_FRONT_STYLE = FlashcardStyle(
    main_font_size="2.5em",
    bg_color=FRONT_BG_COLOR,
)

WORD_BACK_STYLE = FlashcardStyle(
    bg_color=BACK_BG_COLOR,
)

SENTENCE_FRONT_STYLE = FlashcardStyle(
    main_font_size="1.6em",
    corner_font_size="0.85em",
    wrap_text=True,
    bg_color=FRONT_BG_COLOR,
)

SENTENCE_BACK_STYLE = FlashcardStyle(
    main_font_size="2.0em",
    subtitle_font_size="1.0em",
    wrap_text=True,
    bg_color=BACK_BG_COLOR,
)

VERB_FRONT_STYLE = FlashcardStyle(
    main_font_size="2.6em",
    subtitle_font_size="1.0em",
    bg_color=FRONT_BG_COLOR,
)

VERB_BACK_STYLE = FlashcardStyle(
    main_font_size="2.2em",
    subtitle_font_size="1.0em",
    subtitle_style="normal",
    wrap_text=True,
    bg_color=BACK_BG_COLOR,
)

PREPOSITION_FRONT_STYLE = FlashcardStyle(
    main_font_size="1.7em",
    corner_font_size="0.85em",
    wrap_text=True,
    bg_color=FRONT_BG_COLOR,
)

PREPOSITION_BACK_STYLE = FlashcardStyle(
    main_font_size="1.6em",
    subtitle_font_size="1.0em",
    subtitle_style="normal",
    wrap_text=True,
    bg_color=BACK_BG_COLOR,
)
