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
    if not st.session_state.session_batch:
        return False
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 0.8])

    with col1:
        total = len(st.session_state.session_batch)
        current = st.session_state.session_position
        st.caption("Progress")
        st.markdown(f"**{current}/{total}**")

    with col2:
        st.caption("Reviewed")
        st.markdown(f"**{st.session_state.session_count}**")

    with col3:
        st.caption("Accuracy")
        if st.session_state.session_count > 0:
            accuracy = st.session_state.session_correct / st.session_state.session_count * 100
            st.markdown(f"**{accuracy:.0f}%**")
        else:
            st.markdown("**-**")

    with col4:
        if st.button("X", help="Quit session"):
            return True

    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
    return False


def render_session_complete():
    """Render session completion message."""
    if st.session_state.session_count > 0:
        st.success(f"🎉 Session complete! You reviewed {st.session_state.session_count} words.")
        if st.session_state.session_count > 0:
            accuracy = st.session_state.session_correct / st.session_state.session_count * 100
            st.info(f"Accuracy: {accuracy:.1f}%")

