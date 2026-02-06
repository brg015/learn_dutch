"""
Simple page router for Streamlit tabs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.pages.study import render_study_page
from app.pages.lexicon import render_lexicon_page


@dataclass(frozen=True)
class AppPage:
    title: str
    render: Callable[[dict[str, str]], None]


PAGES = [
    AppPage(title="Study", render=render_study_page),
    AppPage(title="Lexicon", render=render_lexicon_page),
]
