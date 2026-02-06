"""
Lexicon settings page rendering.
"""

from __future__ import annotations

from app.ui.lexicon_settings import render_lexicon_settings


def render_lexicon_page(user_options: dict[str, str]) -> None:
    render_lexicon_settings(user_options)
