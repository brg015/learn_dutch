"""
Types for analytics dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


AnalyticsTrack = Literal["words", "verb_tenses", "prepositions"]


@dataclass(frozen=True)
class TrackDashboardData:
    """
    Precomputed metrics and series for one analytics track.
    """
    track: AnalyticsTrack
    label: str
    studied_unique_current: int
    learned_current: int
    studied_cumulative_daily: pd.Series
    study_span_daily_hours: pd.Series
    study_span_cumulative_hours: pd.Series

