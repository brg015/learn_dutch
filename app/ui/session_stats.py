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
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        total = len(st.session_state.session_batch)
        current = st.session_state.session_position
        st.metric("Progress", f"{current}/{total}")
    
    with col2:
        st.metric("Reviewed", st.session_state.session_count)
    
    with col3:
        if st.session_state.session_count > 0:
            accuracy = st.session_state.session_correct / st.session_state.session_count * 100
            st.metric("Accuracy", f"{accuracy:.0f}%")
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)  # Align with metrics
        if st.button("❌", help="Quit session", use_container_width=True):
            return True
    
    st.divider()
    return False


def render_session_complete():
    """Render session completion message."""
    if st.session_state.session_count > 0:
        st.success(f"🎉 Session complete! You reviewed {st.session_state.session_count} words.")
        if st.session_state.session_count > 0:
            accuracy = st.session_state.session_correct / st.session_state.session_count * 100
            st.info(f"Accuracy: {accuracy:.1f}%")
