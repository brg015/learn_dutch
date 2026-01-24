"""
Session Statistics UI

Renders progress metrics and controls.
"""

import streamlit as st


def render_session_stats() -> bool:
    """
    Render session progress metrics and exit button.
    
    Returns:
        True if quit button was clicked, False otherwise
    """
    if not st.session_state.session_batch or st.session_state.current_word is None:
        return False
    
    col1, col2 = st.columns([4, 1])

    with col1:
        total = len(st.session_state.session_batch)
        current = st.session_state.session_position
        st.markdown(
            f"<div style='font-size:0.9rem;color:#666;'>{current}/{total}</div>",
            unsafe_allow_html=True
        )

    with col2:
        if st.button("×", help="Quit session"):
            return True

    st.markdown("<hr style='margin: 0.2rem 0;'>", unsafe_allow_html=True)
    return False


def render_session_complete():
    """Render session completion message."""
    if st.session_state.session_count > 0:
        st.success(f"🎉 Session complete! You reviewed {st.session_state.session_count} words.")
        if st.session_state.session_count > 0:
            accuracy = st.session_state.session_correct / st.session_state.session_count * 100
            st.info(f"Accuracy: {accuracy:.1f}%")

