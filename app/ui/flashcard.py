"""
Flashcard UI Component

Renders generalized flashcards with flexible styling.
"""

from __future__ import annotations

import streamlit as st
from app.ui.flashcard_style import (
    CARD_MIN_HEIGHT,
    CARD_PADDING,
    DEFAULT_FLASHCARD_STYLE,
    FlashcardStyle,
)


def render_flashcard(
    main_text: str,
    subtitle: str = "",
    corner_text: str = "",
    main_font_size: str | None = None,
    main_color: str | None = None,
    main_weight: str | None = None,
    subtitle_font_size: str | None = None,
    subtitle_color: str | None = None,
    subtitle_style: str | None = None,
    corner_font_size: str | None = None,
    corner_color: str | None = None,
    corner_style: str | None = None,
    wrap_text: bool | None = None,
    bg_color: str | None = None,
    style: FlashcardStyle | None = None,
) -> None:
    """
    Render a generalized flashcard with flexible styling.
    
    Args:
        main_text: Primary text (center, large)
        subtitle: Optional secondary text (below main, smaller)
        corner_text: Optional text in top-right corner
        main_font_size: CSS font size for main text (default: "3em")
        main_color: CSS color for main text (default: "#1f1f1f")
        main_weight: CSS font-weight for main text (default: "normal")
        subtitle_font_size: CSS font size for subtitle
        subtitle_color: CSS color for subtitle
        subtitle_style: CSS font-style for subtitle (e.g., "italic")
        corner_font_size: CSS font size for corner text
        corner_color: CSS color for corner text
        corner_style: CSS font-style for corner text
        wrap_text: If True, allow text wrapping; if False, white-space: nowrap
        bg_color: Background color of card (default: "#f0f2f6" for front, "#e8f4f8" for back)
        style: Optional style preset; explicit arguments override style values
    """
    resolved_style = style or DEFAULT_FLASHCARD_STYLE
    main_font_size = main_font_size or resolved_style.main_font_size
    main_color = main_color or resolved_style.main_color
    main_weight = main_weight or resolved_style.main_weight
    subtitle_font_size = subtitle_font_size or resolved_style.subtitle_font_size
    subtitle_color = subtitle_color or resolved_style.subtitle_color
    subtitle_style = subtitle_style or resolved_style.subtitle_style
    corner_font_size = corner_font_size or resolved_style.corner_font_size
    corner_color = corner_color or resolved_style.corner_color
    corner_style = corner_style or resolved_style.corner_style
    wrap_text = resolved_style.wrap_text if wrap_text is None else wrap_text
    bg_color = bg_color or resolved_style.bg_color

    # Build corner HTML if provided
    corner_html = ""
    if corner_text:
        corner_html = f'<div style="position: absolute; top: 15px; right: 20px; font-size: {corner_font_size}; color: {corner_color}; font-style: {corner_style};">{corner_text}</div>'
    
    # Build main text HTML
    white_space = "normal" if wrap_text else "nowrap"
    main_html = (
        f'<h1 style="font-size: {main_font_size}; color: {main_color}; '
        f'font-weight: {main_weight}; margin: 0; white-space: {white_space}; '
        'text-align: center; line-height: 1.4; max-width: 100%; '
        'overflow-wrap: anywhere; word-break: break-word;">'
        f"{main_text}</h1>"
    )
    
    # Build subtitle HTML if provided
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            f'<p style="font-size: {subtitle_font_size}; color: {subtitle_color}; '
            f'font-style: {subtitle_style}; margin: 15px 0 0 0; text-align: center; '
            'line-height: 1.4; max-width: 100%; overflow-wrap: anywhere; '
            f'word-break: break-word;">{subtitle}</p>'
        )
    
    # Combine into card HTML
    html = (
        f'<div style="background-color: {bg_color}; padding: {CARD_PADDING}; '
        'border-radius: 15px; text-align: center; box-shadow: 0 4px 6px '
        f'rgba(0, 0, 0, 0.1); min-height: {CARD_MIN_HEIGHT}; display: flex; '
        'flex-direction: column; align-items: center; justify-content: center; '
        f'position: relative;">{corner_html}{main_html}{subtitle_html}</div>'
    )
    
    st.markdown(html, unsafe_allow_html=True)
