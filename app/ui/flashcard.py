"""
Flashcard UI Component

Renders generalized flashcards with flexible styling.
"""

import streamlit as st


def render_flashcard(
    main_text: str,
    subtitle: str = "",
    corner_text: str = "",
    main_font_size: str = "3em",
    main_color: str = "#1f1f1f",
    main_weight: str = "normal",
    subtitle_font_size: str = "1.2em",
    subtitle_color: str = "#666",
    subtitle_style: str = "italic",
    corner_font_size: str = "0.9em",
    corner_color: str = "#666",
    corner_style: str = "italic",
    wrap_text: bool = False,
    bg_color: str = "#f0f2f6",
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
    """
    # Build corner HTML if provided
    corner_html = ""
    if corner_text:
        corner_html = f'<div style="position: absolute; top: 15px; right: 20px; font-size: {corner_font_size}; color: {corner_color}; font-style: {corner_style};">{corner_text}</div>'
    
    # Build main text HTML
    white_space = "normal" if wrap_text else "nowrap"
    main_html = f'<h1 style="font-size: {main_font_size}; color: {main_color}; font-weight: {main_weight}; margin: 0; white-space: {white_space}; text-align: center; line-height: 1.4;">{main_text}</h1>'
    
    # Build subtitle HTML if provided
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<p style="font-size: {subtitle_font_size}; color: {subtitle_color}; font-style: {subtitle_style}; margin: 15px 0 0 0; text-align: center; line-height: 1.4;">{subtitle}</p>'
    
    # Combine into card HTML
    html = f'<div style="background-color: {bg_color}; padding: 60px 40px; border-radius: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); min-height: 300px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative;">{corner_html}{main_html}{subtitle_html}</div>'
    
    st.markdown(html, unsafe_allow_html=True)
