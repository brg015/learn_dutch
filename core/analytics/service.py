"""
Service layer to assemble analytics dashboards by track.
"""

from __future__ import annotations

import pandas as pd

from core import fsrs
from core.analytics.constants import (
    TRACK_EXERCISE_TYPES,
    TRACK_LABELS,
)
from core.analytics.metrics import (
    build_day_index,
    compute_learned_count_single_track,
    compute_learned_count_verb_tenses,
    compute_session_span_daily_hours,
    compute_studied_cumulative,
    compute_studied_unique,
)
from core.analytics.queries import (
    load_card_snapshots_df,
    load_review_events_df,
)
from core.analytics.types import AnalyticsTrack, TrackDashboardData


def _learned_current(user_id: str, track: AnalyticsTrack) -> int:
    if track == "words":
        word_df = load_card_snapshots_df(user_id, "word_translation")
        return compute_learned_count_single_track(word_df, fsrs.R_TARGET)

    if track == "prepositions":
        prep_df = load_card_snapshots_df(user_id, "word_preposition")
        return compute_learned_count_single_track(prep_df, fsrs.R_TARGET)

    perfectum_df = load_card_snapshots_df(user_id, "verb_perfectum")
    past_df = load_card_snapshots_df(user_id, "verb_past_tense")
    return compute_learned_count_verb_tenses(perfectum_df, past_df, fsrs.R_TARGET)


def build_track_dashboard(user_id: str, track: AnalyticsTrack) -> TrackDashboardData:
    """
    Build all KPI values and series needed by the analytics page for a track.
    """
    exercise_types = TRACK_EXERCISE_TYPES[track]
    events_df = load_review_events_df(user_id=user_id, exercise_types=exercise_types)
    day_index = build_day_index(events_df)

    studied_unique = compute_studied_unique(events_df)
    studied_cumulative = compute_studied_cumulative(events_df, day_index)
    study_daily = compute_session_span_daily_hours(events_df, exercise_types, day_index)
    study_cumulative = study_daily.cumsum() if not study_daily.empty else pd.Series(dtype="float64")
    learned_current = _learned_current(user_id=user_id, track=track)

    return TrackDashboardData(
        track=track,
        label=TRACK_LABELS[track],
        studied_unique_current=studied_unique,
        learned_current=learned_current,
        studied_cumulative_daily=studied_cumulative,
        study_span_daily_hours=study_daily,
        study_span_cumulative_hours=study_cumulative,
    )

