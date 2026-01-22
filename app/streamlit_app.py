"""
Dutch Vocabulary Trainer - Streamlit UI

Simple review session interface for learning Dutch vocabulary.
"""

import streamlit as st
import uuid
import random
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
if "learning_mode" not in st.session_state:
    st.session_state.learning_mode = None  # "words" or "sentences"
if "current_example" not in st.session_state:
    st.session_state.current_example = None  # Selected example for sentence mode


def start_new_session(mode: str):
    """Start a new session with a pre-computed batch of words.

    Args:
        mode: Learning mode - "words" or "sentences"
    """
    # Create session using three-pool scheduler
    batch = session_builder.create_session(
        exercise_type='word_translation',
        tag=None  # No tag filtering for now
    )

    # Generate unique session ID for analytics
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.session_batch = batch
    st.session_state.session_position = 0
    st.session_state.session_count = 0
    st.session_state.session_correct = 0
    st.session_state.learning_mode = mode

    # Load first word
    if batch:
        load_next_word()


def load_next_word():
    """Load the next word from the current session batch."""
    if st.session_state.session_position >= len(st.session_state.session_batch):
        # Session complete
        st.session_state.current_word = None
        st.session_state.current_example = None
        return

    # New scheduler returns word dicts directly, not tuples
    word = st.session_state.session_batch[st.session_state.session_position]

    st.session_state.current_word = word
    st.session_state.show_answer = False
    st.session_state.start_time = datetime.now(timezone.utc)

    # If sentence mode, select a random example
    if st.session_state.learning_mode == "sentences":
        examples = word.get('general_examples', [])
        if examples:
            st.session_state.current_example = random.choice(examples)
        else:
            # Fallback if no examples available
            st.session_state.current_example = None
    else:
        st.session_state.current_example = None


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
            session_position=st.session_state.session_position,
            presentation_mode=st.session_state.learning_mode  # "words" or "sentences"
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

# Test mode indicator (if enabled)
if fsrs.is_test_mode():
    st.warning("⚠️ **TEST MODE** - Using test_learning.db (set TEST_MODE=false in .env for production)")

st.title("🇳🇱 Dutch Vocabulary Trainer")

# Show session stats and quit button at the top
if st.session_state.session_batch:
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
            # Reset session
            st.session_state.current_word = None
            st.session_state.session_batch = []
            st.session_state.learning_mode = None
            st.rerun()

    st.divider()

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

    # Mode selection (always show on intro screen)
    st.markdown("### 📚 Word Learning")
    st.markdown("Choose how you'd like to practice:")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Only Words", type="primary", use_container_width=True, help="Practice individual words"):
            start_new_session("words")
            st.rerun()

    with col2:
        if st.button("Sentences", type="primary", use_container_width=True, help="Practice words in context"):
            start_new_session("sentences")
            st.rerun()
else:
    word = st.session_state.current_word

    # Get lemma with article for nouns
    lemma_text = word["lemma"]
    if word["pos"] == "noun" and word.get("noun_meta", {}).get("article"):
        article = word["noun_meta"]["article"]
        lemma_text = f"{article} {lemma_text}"

    # Flashcard styling
    st.markdown("<br>" * 2, unsafe_allow_html=True)  # Add top spacing

    if not st.session_state.show_answer:
        # FRONT OF CARD
        if st.session_state.learning_mode == "sentences" and st.session_state.current_example:
            # Sentence mode: Show sentence with lemma in corner
            sentence = st.session_state.current_example['dutch']
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
                    position: relative;
                ">
                    <div style="
                        position: absolute;
                        top: 15px;
                        right: 20px;
                        font-size: 0.75em;
                        color: #999;
                        font-style: italic;
                    ">
                        {lemma_text}
                    </div>
                    <h1 style="font-size: 2.2em; margin: 0; color: #1f1f1f; line-height: 1.4; word-wrap: break-word; max-width: 100%;">
                        {sentence}
                    </h1>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Word mode: Show word only
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
                        {lemma_text}
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
        # BACK OF CARD
        translation_text = word.get("translation", "No translation")

        if st.session_state.learning_mode == "sentences" and st.session_state.current_example:
            # Sentence mode: Translation + sentence translation below
            sentence_translation = st.session_state.current_example['english']
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
                    <h1 style="font-size: 3em; margin: 0 0 20px 0; color: #1f1f1f;">
                        {translation_text}
                    </h1>
                    <p style="font-size: 1.2em; margin: 0; color: #666; font-style: italic; line-height: 1.4;">
                        {sentence_translation}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Word mode: Translation with lemma in corner
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
                        {lemma_text}
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

        # Details section with tabs
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📖 Details"):
            # Check if word is enriched
            is_enriched = word.get('word_enrichment', {}).get('enriched', False)

            if not is_enriched:
                st.info("⚠️ This word hasn't been enriched yet. Run enrichment to see detailed information.")
                st.caption(f"**Part of Speech:** {word.get('pos', 'Unknown')}")
            else:
                # Create tabs: Definition, Examples, Grammar (if POS-enriched)
                has_pos_meta = (
                    (word.get('pos') == 'noun' and word.get('noun_meta')) or
                    (word.get('pos') == 'verb' and word.get('verb_meta')) or
                    (word.get('pos') == 'adjective' and word.get('adjective_meta'))
                )

                if has_pos_meta:
                    tab1, tab2, tab3 = st.tabs(["📖 Definition", "📝 Examples", "🔧 Grammar"])
                else:
                    tab1, tab2 = st.tabs(["📖 Definition", "📝 Examples"])
                    tab3 = None

                # Tab 1: Definition (most important!)
                with tab1:
                    # Definition
                    if word.get('definition'):
                        st.markdown(f"**{word['definition']}**")
                        st.markdown("")

                    # POS and CEFR
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"**Part of Speech:** {word.get('pos', 'Unknown').title()}")
                    with col2:
                        if word.get('difficulty'):
                            st.caption(f"**CEFR Level:** {word['difficulty']}")

                    # Tags (if any)
                    if word.get('tags'):
                        st.caption(f"**Topics:** {', '.join(word['tags'])}")

                # Tab 2: Examples (grouped by type)
                with tab2:
                    # General examples first
                    if word.get('general_examples'):
                        st.markdown("**General Usage**")
                        for ex in word['general_examples']:
                            st.caption(f"🇳🇱 {ex['dutch']}")
                            st.caption(f"🇬🇧 {ex['english']}")
                            st.markdown("")

                    # POS-specific examples
                    if word.get('pos') == 'verb' and word.get('verb_meta'):
                        verb_meta = word['verb_meta']

                        # Create subtabs for verb examples
                        verb_tabs = []
                        if verb_meta.get('examples_present'):
                            verb_tabs.append("Present")
                        if verb_meta.get('examples_past'):
                            verb_tabs.append("Past")
                        if verb_meta.get('examples_perfect'):
                            verb_tabs.append("Perfect")
                        if verb_meta.get('preposition_usage'):
                            verb_tabs.append("With Prepositions")

                        if verb_tabs:
                            subtabs = st.tabs(verb_tabs)
                            tab_idx = 0

                            if verb_meta.get('examples_present'):
                                with subtabs[tab_idx]:
                                    for ex in verb_meta['examples_present']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if verb_meta.get('examples_past'):
                                with subtabs[tab_idx]:
                                    for ex in verb_meta['examples_past']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if verb_meta.get('examples_perfect'):
                                with subtabs[tab_idx]:
                                    for ex in verb_meta['examples_perfect']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if verb_meta.get('preposition_usage'):
                                with subtabs[tab_idx]:
                                    for prep_usage in verb_meta['preposition_usage']:
                                        st.markdown(f"**{word['lemma']} {prep_usage['preposition']}** ({prep_usage['meaning']})")
                                        for ex in prep_usage.get('examples', []):
                                            st.caption(f"🇳🇱 {ex['dutch']}")
                                            st.caption(f"🇬🇧 {ex['english']}")
                                            st.markdown("")

                    elif word.get('pos') == 'noun' and word.get('noun_meta'):
                        noun_meta = word['noun_meta']

                        # Create subtabs for noun examples
                        noun_tabs = []
                        if noun_meta.get('examples_singular'):
                            noun_tabs.append("Singular")
                        if noun_meta.get('examples_plural'):
                            noun_tabs.append("Plural")
                        if noun_meta.get('fixed_prepositions'):
                            noun_tabs.append("With Prepositions")

                        if noun_tabs:
                            subtabs = st.tabs(noun_tabs)
                            tab_idx = 0

                            if noun_meta.get('examples_singular'):
                                with subtabs[tab_idx]:
                                    for ex in noun_meta['examples_singular']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if noun_meta.get('examples_plural'):
                                with subtabs[tab_idx]:
                                    for ex in noun_meta['examples_plural']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if noun_meta.get('fixed_prepositions'):
                                with subtabs[tab_idx]:
                                    for prep in noun_meta['fixed_prepositions']:
                                        freq = prep.get('usage_frequency', 'common')
                                        st.markdown(f"**{word['lemma']} {prep['preposition']}** ({freq})")
                                        if prep.get('meaning_context'):
                                            st.caption(prep['meaning_context'])
                                        for ex in prep.get('examples', []):
                                            st.caption(f"🇳🇱 {ex['dutch']}")
                                            st.caption(f"🇬🇧 {ex['english']}")
                                            st.markdown("")

                    elif word.get('pos') == 'adjective' and word.get('adjective_meta'):
                        adj_meta = word['adjective_meta']

                        # Create subtabs for adjective examples
                        adj_tabs = []
                        if adj_meta.get('examples_base'):
                            adj_tabs.append("Base")
                        if adj_meta.get('examples_comparative'):
                            adj_tabs.append("Comparative")
                        if adj_meta.get('examples_superlative'):
                            adj_tabs.append("Superlative")
                        if adj_meta.get('fixed_prepositions'):
                            adj_tabs.append("With Prepositions")

                        if adj_tabs:
                            subtabs = st.tabs(adj_tabs)
                            tab_idx = 0

                            if adj_meta.get('examples_base'):
                                with subtabs[tab_idx]:
                                    for ex in adj_meta['examples_base']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if adj_meta.get('examples_comparative'):
                                with subtabs[tab_idx]:
                                    for ex in adj_meta['examples_comparative']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if adj_meta.get('examples_superlative'):
                                with subtabs[tab_idx]:
                                    for ex in adj_meta['examples_superlative']:
                                        st.caption(f"🇳🇱 {ex['dutch']}")
                                        st.caption(f"🇬🇧 {ex['english']}")
                                        st.markdown("")
                                tab_idx += 1

                            if adj_meta.get('fixed_prepositions'):
                                with subtabs[tab_idx]:
                                    for prep in adj_meta['fixed_prepositions']:
                                        freq = prep.get('usage_frequency', 'common')
                                        st.markdown(f"**{word['lemma']} {prep['preposition']}** ({freq})")
                                        if prep.get('meaning_context'):
                                            st.caption(prep['meaning_context'])
                                        for ex in prep.get('examples', []):
                                            st.caption(f"🇳🇱 {ex['dutch']}")
                                            st.caption(f"🇬🇧 {ex['english']}")
                                            st.markdown("")

                # Tab 3: Grammar (POS-specific metadata)
                if tab3 is not None:
                    with tab3:
                        if word.get('pos') == 'noun' and word.get('noun_meta'):
                            noun_meta = word['noun_meta']
                            if noun_meta.get('article'):
                                st.markdown(f"**Article:** {noun_meta['article']}")
                            if noun_meta.get('plural'):
                                st.markdown(f"**Plural:** {noun_meta['plural']}")
                            if noun_meta.get('diminutive'):
                                st.markdown(f"**Diminutive:** {noun_meta['diminutive']}")

                        elif word.get('pos') == 'verb' and word.get('verb_meta'):
                            verb_meta = word['verb_meta']
                            if verb_meta.get('past_singular'):
                                st.markdown(f"**Past (singular):** {verb_meta['past_singular']}")
                            if verb_meta.get('past_plural'):
                                st.markdown(f"**Past (plural):** {verb_meta['past_plural']}")
                            if verb_meta.get('past_participle'):
                                st.markdown(f"**Past Participle:** {verb_meta['past_participle']}")
                            if verb_meta.get('auxiliary'):
                                st.markdown(f"**Auxiliary:** {verb_meta['auxiliary']}")
                            if verb_meta.get('is_separable'):
                                st.markdown(f"**Separable:** Yes")
                                if verb_meta.get('separable_prefix'):
                                    st.markdown(f"**Prefix:** {verb_meta['separable_prefix']}")
                            if verb_meta.get('is_reflexive'):
                                st.markdown(f"**Reflexive:** Yes (requires 'zich')")

                            # Irregularity flags
                            if verb_meta.get('is_irregular_past'):
                                st.caption("⚠️ Irregular past tense")
                            if verb_meta.get('is_irregular_participle'):
                                st.caption("⚠️ Irregular past participle")

                        elif word.get('pos') == 'adjective' and word.get('adjective_meta'):
                            adj_meta = word['adjective_meta']
                            if adj_meta.get('comparative'):
                                st.markdown(f"**Comparative:** {adj_meta['comparative']}")
                                if adj_meta.get('is_irregular_comparative'):
                                    st.caption("⚠️ Irregular comparative")
                            if adj_meta.get('superlative'):
                                st.markdown(f"**Superlative:** {adj_meta['superlative']}")
                                if adj_meta.get('is_irregular_superlative'):
                                    st.caption("⚠️ Irregular superlative")
