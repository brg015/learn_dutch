"""
Dutch Vocabulary Trainer - Streamlit UI

Simple review session interface for learning Dutch vocabulary.
"""

import streamlit as st
import uuid
from datetime import datetime, timezone

from core import session_builder, fsrs, lexicon_repo

# Initialize database
fsrs.init_db()

# Cache database counts to avoid repeated MongoDB queries
@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_word_counts():
    """Get total and enriched word counts (cached)."""
    return {
        "total": lexicon_repo.count_words(enriched_only=False),
        "enriched": lexicon_repo.count_words(enriched_only=True)
    }

# Page config
st.set_page_config(
    page_title="Dutch Vocabulary Trainer",
    page_icon="🇳🇱",
    layout="centered"
)

# Session state initialization
if "current_word" not in st.session_state:
    st.session_state.current_word = None
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False
if "session_batch" not in st.session_state:
    st.session_state.session_batch = []  # List of word dicts
if "session_position" not in st.session_state:
    st.session_state.session_position = 0
if "session_count" not in st.session_state:
    st.session_state.session_count = 0
if "session_correct" not in st.session_state:
    st.session_state.session_correct = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None


def start_new_session():
    """Start a new session with a pre-computed batch of words."""
    # Get filter settings
    tag_filter = st.session_state.get("tag_filter")
    if tag_filter == "All":
        tag_filter = None

    # Create session using new three-pool scheduler
    batch = session_builder.create_session(
        exercise_type='word_translation',
        tag=tag_filter
    )

    # Generate unique session ID for analytics
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.session_batch = batch
    st.session_state.session_position = 0
    st.session_state.session_count = 0
    st.session_state.session_correct = 0

    # Load first word
    if batch:
        load_next_word()


def load_next_word():
    """Load the next word from the current session batch."""
    if st.session_state.session_position >= len(st.session_state.session_batch):
        # Session complete
        st.session_state.current_word = None
        return

    # New scheduler returns word dicts directly, not tuples
    word = st.session_state.session_batch[st.session_state.session_position]

    st.session_state.current_word = word
    st.session_state.show_answer = False
    st.session_state.start_time = datetime.now(timezone.utc)


def log_and_next(feedback_grade: fsrs.FeedbackGrade):
    """Log the current review result and move to next word in session."""
    if st.session_state.current_word:
        word = st.session_state.current_word

        # Calculate latency
        latency_ms = None
        if st.session_state.start_time:
            elapsed = datetime.now(timezone.utc) - st.session_state.start_time
            latency_ms = int(elapsed.total_seconds() * 1000)

        # Log the review with session context
        fsrs.log_review(
            word_id=word["word_id"],
            lemma=word["lemma"],
            pos=word["pos"],
            exercise_type="word_translation",  # MVP: only Dutch→English
            feedback_grade=feedback_grade,
            latency_ms=latency_ms,
            session_id=st.session_state.session_id,
            session_position=st.session_state.session_position
        )

        # Update session stats (count anything other than AGAIN as correct)
        st.session_state.session_count += 1
        if feedback_grade != fsrs.FeedbackGrade.AGAIN:
            st.session_state.session_correct += 1

        # Move to next word in batch
        st.session_state.session_position += 1

    # Load next word from batch
    load_next_word()


# ---- UI Layout ----

st.title("🇳🇱 Dutch Vocabulary Trainer")

# Sidebar: Filters and stats
with st.sidebar:
    st.header("Settings")

    # Tag filter (only editable between sessions)
    all_tags = ["All"] + lexicon_repo.get_all_tags()
    st.selectbox(
        "Filter by tag:",
        options=all_tags,
        key="tag_filter",
        disabled=st.session_state.current_word is not None
    )

    st.divider()

    # Session stats
    st.header("Session Stats")
    if st.session_state.session_batch:
        # Show progress
        total = len(st.session_state.session_batch)
        current = st.session_state.session_position
        st.progress(current / total if total > 0 else 0)
        st.caption(f"Progress: {current}/{total} words")

    st.metric("Words reviewed", st.session_state.session_count)
    if st.session_state.session_count > 0:
        accuracy = st.session_state.session_correct / st.session_state.session_count * 100
        st.metric("Accuracy", f"{accuracy:.1f}%")

    st.divider()

    # Database stats
    st.header("Lexicon Stats")
    counts = get_word_counts()
    st.metric("Total words", counts["total"])
    st.metric("Enriched words", counts["enriched"])

    if counts["enriched"] == 0:
        st.warning("⚠️ No enriched words yet. Using basic word pairs.")
        st.caption("Run: `py -m scripts.enrich_and_update --batch-size 10`")

# Main content area
if st.session_state.current_word is None:
    # Session not started or session complete
    st.markdown("<br>" * 3, unsafe_allow_html=True)  # Add spacing

    if st.session_state.session_count > 0:
        # Session just finished
        st.success(f"🎉 Session complete! You reviewed {st.session_state.session_count} words.")
        if st.session_state.session_count > 0:
            accuracy = st.session_state.session_correct / st.session_state.session_count * 100
            st.info(f"Accuracy: {accuracy:.1f}%")

        if st.button("Start New Session", type="primary", use_container_width=True):
            start_new_session()
            st.rerun()
    else:
        # First session
        if st.button("Start Session", type="primary", use_container_width=True):
            start_new_session()
            st.rerun()
else:
    word = st.session_state.current_word

    # Prepare display text (with article for nouns if enriched)
    display_text = word["lemma"]
    if word["pos"] == "noun" and word.get("noun_meta", {}).get("article"):
        article = word["noun_meta"]["article"]
        display_text = f"{article} {display_text}"

    # Flashcard styling
    st.markdown("<br>" * 2, unsafe_allow_html=True)  # Add top spacing

    if not st.session_state.show_answer:
        # FRONT OF CARD: Dutch word only
        st.markdown(
            f"""
            <div style="
                background-color: #f0f2f6;
                padding: 60px 40px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                min-height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <h1 style="font-size: 3.5em; margin: 0; color: #1f1f1f;">
                    {display_text}
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Reveal Answer", use_container_width=True, type="primary"):
            st.session_state.show_answer = True
            st.rerun()

    else:
        # BACK OF CARD: English translation with Dutch in corner
        # Handle both new (translation string) and old (translations list) schema
        if word.get("translation"):
            translation_text = word["translation"]
        elif word.get("translations"):
            translation_text = ', '.join(word["translations"])
        else:
            translation_text = "No translation"

        st.markdown(
            f"""
            <div style="
                background-color: #e8f4f8;
                padding: 60px 40px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                min-height: 300px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                position: relative;
            ">
                <div style="
                    position: absolute;
                    top: 15px;
                    right: 20px;
                    font-size: 0.9em;
                    color: #666;
                    font-style: italic;
                ">
                    {display_text}
                </div>
                <h1 style="font-size: 3em; margin: 0; color: #1f1f1f;">
                    {translation_text}
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        # User feedback buttons (graded)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**How well did you remember this word?**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("❌ Again", use_container_width=True, help="Completely forgot"):
                log_and_next(fsrs.FeedbackGrade.AGAIN)
                st.rerun()

        with col2:
            if st.button("😰 Hard", use_container_width=True, help="Remembered with difficulty"):
                log_and_next(fsrs.FeedbackGrade.HARD)
                st.rerun()

        with col3:
            if st.button("👍 Medium", use_container_width=True, help="Remembered normally"):
                log_and_next(fsrs.FeedbackGrade.MEDIUM)
                st.rerun()

        with col4:
            if st.button("✨ Easy", use_container_width=True, help="Remembered easily"):
                log_and_next(fsrs.FeedbackGrade.EASY)
                st.rerun()

        # Tell me more section
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📖 Tell me more"):
            # Entry type and POS
            st.markdown(f"**Type:** {word.get('entry_type', 'word')}")
            if word.get('pos'):
                st.markdown(f"**Part of Speech:** {word['pos']}")
            if word.get('difficulty'):
                st.markdown(f"**Difficulty:** {word['difficulty']}")

            # POS-specific metadata
            if word.get('pos') == 'noun' and word.get('noun_meta'):
                with st.expander("🏷️ Noun Details"):
                    noun_meta = word['noun_meta']
                    if noun_meta.get('article'):
                        st.write(f"**Article:** {noun_meta['article']}")
                    if noun_meta.get('plural'):
                        st.write(f"**Plural:** {noun_meta['plural']}")
                    if noun_meta.get('diminutive'):
                        st.write(f"**Diminutive:** {noun_meta['diminutive']}")

                    # Noun examples
                    if noun_meta.get('examples_singular'):
                        st.markdown("**Singular Examples:**")
                        for ex in noun_meta['examples_singular']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")
                    if noun_meta.get('examples_plural'):
                        st.markdown("**Plural Examples:**")
                        for ex in noun_meta['examples_plural']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")

            elif word.get('pos') == 'verb' and word.get('verb_meta'):
                with st.expander("⚡ Verb Details"):
                    verb_meta = word['verb_meta']
                    if verb_meta.get('past_singular'):
                        st.write(f"**Past (singular):** {verb_meta['past_singular']}")
                    if verb_meta.get('past_plural'):
                        st.write(f"**Past (plural):** {verb_meta['past_plural']}")
                    if verb_meta.get('past_participle'):
                        st.write(f"**Past Participle:** {verb_meta['past_participle']}")
                    if verb_meta.get('auxiliary'):
                        st.write(f"**Auxiliary:** {verb_meta['auxiliary']}")
                    if verb_meta.get('separable'):
                        st.write(f"**Separable:** Yes")
                        if verb_meta.get('separable_prefix'):
                            st.write(f"**Prefix:** {verb_meta['separable_prefix']}")
                    if verb_meta.get('common_prepositions'):
                        st.write(f"**Common Prepositions:** {', '.join(verb_meta['common_prepositions'])}")

                    # Verb examples
                    if verb_meta.get('examples_present'):
                        st.markdown("**Present Tense Examples:**")
                        for ex in verb_meta['examples_present']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")
                    if verb_meta.get('examples_past'):
                        st.markdown("**Past Tense Examples:**")
                        for ex in verb_meta['examples_past']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")
                    if verb_meta.get('examples_perfect'):
                        st.markdown("**Perfect Tense Examples:**")
                        for ex in verb_meta['examples_perfect']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")

            elif word.get('pos') == 'adjective' and word.get('adjective_meta'):
                with st.expander("✨ Adjective Details"):
                    adj_meta = word['adjective_meta']
                    if adj_meta.get('comparative'):
                        st.write(f"**Comparative:** {adj_meta['comparative']}")
                    if adj_meta.get('superlative'):
                        st.write(f"**Superlative:** {adj_meta['superlative']}")

                    # Adjective examples
                    if adj_meta.get('examples_base'):
                        st.markdown("**Base Examples:**")
                        for ex in adj_meta['examples_base']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")
                    if adj_meta.get('examples_comparative'):
                        st.markdown("**Comparative Examples:**")
                        for ex in adj_meta['examples_comparative']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")
                    if adj_meta.get('examples_superlative'):
                        st.markdown("**Superlative Examples:**")
                        for ex in adj_meta['examples_superlative']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")

            # General examples (for other POS types)
            if word.get('general_examples'):
                with st.expander("💬 Examples"):
                    for ex in word['general_examples']:
                        st.caption(f"🇳🇱 {ex['dutch']}")
                        st.caption(f"🇬🇧 {ex['english']}")
                        st.markdown("")

            # If no enriched data
            if not word.get('enrichment', {}).get('enriched'):
                st.info("This word hasn't been enriched yet. Run enrichment to see detailed information.")
