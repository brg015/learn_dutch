"""
Metric computations for analytics dashboards.
"""

from __future__ import annotations

import pandas as pd


def build_day_index(events_df: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Build a dense UTC day index spanning the event range.
    """
    if events_df.empty:
        return pd.DatetimeIndex([], tz="UTC")
    start = events_df["day_utc"].min()
    end = events_df["day_utc"].max()
    return pd.date_range(start=start, end=end, freq="D", tz="UTC")


def zero_series(day_index: pd.DatetimeIndex, dtype: str = "float64") -> pd.Series:
    """
    Convenience zero-valued series aligned to day index.
    """
    return pd.Series(0, index=day_index, dtype=dtype)


def compute_studied_unique(events_df: pd.DataFrame) -> int:
    """
    Count unique studied word_ids in scoped events.
    """
    if events_df.empty:
        return 0
    return int(events_df["word_id"].nunique())


def compute_studied_cumulative(
    events_df: pd.DataFrame,
    day_index: pd.DatetimeIndex
) -> pd.Series:
    """
    Cumulative unique studied items by first-seen day.
    """
    if events_df.empty or len(day_index) == 0:
        return pd.Series(dtype="int64")

    first_seen = events_df.groupby("word_id")["timestamp"].min().dt.floor("D")
    counts = first_seen.value_counts().sort_index()
    return counts.reindex(day_index, fill_value=0).cumsum().astype("int64")


def compute_session_span_daily_hours(
    events_df: pd.DataFrame,
    exercise_types: list[str],
    day_index: pd.DatetimeIndex
) -> pd.Series:
    """
    Daily study time as sum of per-session span (last - first timestamp).
    """
    if events_df.empty or len(day_index) == 0:
        return pd.Series(dtype="float64")

    scoped = events_df[
        events_df["exercise_type"].isin(exercise_types)
        & events_df["session_id"].notna()
    ].copy()
    if scoped.empty:
        return zero_series(day_index, dtype="float64")

    spans = scoped.groupby("session_id").agg(
        session_start=("timestamp", "min"),
        session_end=("timestamp", "max"),
    )
    spans["span_hours"] = (
        spans["session_end"] - spans["session_start"]
    ).dt.total_seconds() / 3600.0
    spans["day_utc"] = spans["session_start"].dt.floor("D")

    daily = spans.groupby("day_utc")["span_hours"].sum()
    return daily.reindex(day_index, fill_value=0.0).astype("float64")


def compute_learned_count_single_track(snapshots_df: pd.DataFrame, r_target: float) -> int:
    """
    Learned count for a single-card track where learned == retrievability >= threshold.
    """
    if snapshots_df.empty:
        return 0
    return int((snapshots_df["retrievability"] >= r_target).sum())


def compute_learned_count_verb_tenses(
    perfectum_df: pd.DataFrame,
    past_df: pd.DataFrame,
    r_target: float
) -> int:
    """
    Learned count for verbs where both perfectum and past tense are above threshold.
    """
    if perfectum_df.empty and past_df.empty:
        return 0

    perf = perfectum_df.rename(columns={"retrievability": "r_perf"})
    past = past_df.rename(columns={"retrievability": "r_past"})
    merged = perf.merge(past, on="word_id", how="outer").fillna(0.0)
    return int(((merged["r_perf"] >= r_target) & (merged["r_past"] >= r_target)).sum())

