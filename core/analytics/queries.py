"""
Data-loading helpers for analytics.
"""

from __future__ import annotations

import pandas as pd

from core import fsrs


def load_review_events_df(user_id: str, exercise_types: list[str]) -> pd.DataFrame:
    """
    Load review events for a user and selected exercise types into a dataframe.
    """
    rows = fsrs.get_review_events(user_id=user_id, exercise_types=exercise_types)
    if not rows:
        return pd.DataFrame(
            columns=["word_id", "exercise_type", "timestamp", "session_id", "day_utc"]
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=["word_id", "exercise_type", "timestamp", "session_id", "day_utc"]
        )

    df = df[["word_id", "exercise_type", "timestamp", "session_id"]].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["word_id", "timestamp"])
    df["day_utc"] = df["timestamp"].dt.floor("D")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def load_card_snapshots_df(user_id: str, exercise_type: str) -> pd.DataFrame:
    """
    Load current card-state snapshots for a user/exercise type.
    """
    snapshots = fsrs.get_all_cards_with_state(exercise_type, user_id)
    if not snapshots:
        return pd.DataFrame(columns=["word_id", "retrievability"])

    return pd.DataFrame(
        [{"word_id": s.word_id, "retrievability": s.retrievability} for s in snapshots]
    )

