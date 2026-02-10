"""
Analytics page rendering.
"""

from __future__ import annotations

import streamlit as st

from core import fsrs
from core.analytics import TRACK_LABELS, build_track_dashboard
from core.analytics.types import AnalyticsTrack


TRACK_ORDER: list[AnalyticsTrack] = ["words", "verb_tenses", "prepositions"]
TRACK_LABEL_TO_KEY: dict[str, AnalyticsTrack] = {
    TRACK_LABELS[track]: track
    for track in TRACK_ORDER
}


@st.cache_data(show_spinner=False)
def _cached_dashboard(user_id: str, track: str):
    return build_track_dashboard(user_id=user_id, track=track)


def render_analytics_page(user_options: dict[str, str]) -> None:
    del user_options  # reserved for future sign-in integration

    st.subheader("Learning Analytics")
    st.caption(f"User: {st.session_state.user_label} ({st.session_state.user_id})")

    labels = [TRACK_LABELS[track] for track in TRACK_ORDER]
    selected_label = st.radio(
        "Card Track",
        labels,
        horizontal=True,
    )
    selected_track = TRACK_LABEL_TO_KEY[selected_label]

    if st.button("Refresh Analytics", use_container_width=False):
        _cached_dashboard.clear()
        st.rerun()

    dashboard = _cached_dashboard(st.session_state.user_id, selected_track)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Studied Items (Unique)", f"{dashboard.studied_unique_current:,}")
    with col2:
        if selected_track == "verb_tenses":
            learned_help = f"Verbs with both perfectum and past tense retrievability >= {fsrs.R_TARGET:.2f}"
        else:
            learned_help = f"Cards with retrievability >= {fsrs.R_TARGET:.2f}"
        st.metric("Learned Items (Current)", f"{dashboard.learned_current:,}", help=learned_help)

    st.markdown("### Studied Items Over Time")
    if dashboard.studied_cumulative_daily.empty:
        st.info("No study events yet for this track.")
    else:
        studied_df = dashboard.studied_cumulative_daily.rename("studied_cumulative").to_frame()
        st.line_chart(studied_df)

    st.markdown("### Study Time")
    if dashboard.study_span_daily_hours.empty:
        st.info("No session-span data yet for this track.")
    else:
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            st.caption("Daily session span (hours)")
            st.bar_chart(dashboard.study_span_daily_hours.rename("daily_hours").to_frame())
        with time_col2:
            st.caption("Cumulative session span (hours)")
            st.line_chart(dashboard.study_span_cumulative_hours.rename("cumulative_hours").to_frame())
