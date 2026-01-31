"""
Word Details UI

Renders word enrichment details, examples, and grammar.
"""

import streamlit as st


def render_word_details(word: dict):
    """
    Render word details expander with tabs for definition, examples, grammar.
    
    Args:
        word: Word dict with enrichment data
    """
    with st.expander("📖 Details"):
        is_enriched = word.get('word_enrichment', {}).get('enriched', False)

        if not is_enriched:
            st.info("⚠️ This word hasn't been enriched yet. Run enrichment to see detailed information.")
            st.caption(f"**Part of Speech:** {word.get('pos', 'Unknown')}")
        else:
            _render_enriched_details(word)


def _render_enriched_details(word: dict):
    """Render tabs for enriched word details."""
    # Determine if POS metadata exists
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

    # Tab 1: Definition
    with tab1:
        if word.get('definition'):
            st.markdown(f"**{word['definition']}**")
            st.markdown("")

        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"**Part of Speech:** {word.get('pos', 'Unknown').title()}")
        with col2:
            if word.get('difficulty'):
                st.caption(f"**CEFR Level:** {word['difficulty']}")

        if word.get('tags'):
            st.caption(f"**Topics:** {', '.join(word['tags'])}")

    # Tab 2: Examples
    with tab2:
        _render_examples(word)

    # Tab 3: Grammar (if applicable)
    if tab3 is not None:
        with tab3:
            _render_grammar(word)


def _render_examples(word: dict):
    """Render examples section."""
    # General examples
    if word.get('general_examples'):
        st.markdown("**General Usage**")
        for ex in word['general_examples']:
            st.caption(f"🇳🇱 {ex['dutch']}")
            st.caption(f"🇬🇧 {ex['english']}")
            st.markdown("")

    # POS-specific examples
    pos = word.get('pos')
    
    if pos == 'verb' and word.get('verb_meta'):
        _render_verb_examples(word['verb_meta'], word['lemma'])
    elif pos == 'noun' and word.get('noun_meta'):
        _render_noun_examples(word['noun_meta'], word['lemma'])
    elif pos == 'adjective' and word.get('adjective_meta'):
        _render_adjective_examples(word['adjective_meta'], word['lemma'])


def _render_verb_examples(verb_meta: dict, lemma: str):
    """Render verb-specific examples."""
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
                    st.markdown(f"**{lemma} {prep_usage['preposition']}** ({prep_usage['meaning']})")
                    for ex in prep_usage.get('examples', []):
                        st.caption(f"🇳🇱 {ex['dutch']}")
                        st.caption(f"🇬🇧 {ex['english']}")
                        st.markdown("")


def _render_noun_examples(noun_meta: dict, lemma: str):
    """Render noun-specific examples."""
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
                    st.markdown(f"**{lemma} {prep['preposition']}** ({freq})")
                    if prep.get('meaning_context'):
                        st.caption(prep['meaning_context'])
                    for ex in prep.get('examples', []):
                        st.caption(f"🇳🇱 {ex['dutch']}")
                        st.caption(f"🇬🇧 {ex['english']}")
                        st.markdown("")


def _render_adjective_examples(adj_meta: dict, lemma: str):
    """Render adjective-specific examples."""
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
                    st.markdown(f"**{lemma} {prep['preposition']}** ({freq})")
                    if prep.get('meaning_context'):
                        st.caption(prep['meaning_context'])
                    for ex in prep.get('examples', []):
                        st.caption(f"🇳🇱 {ex['dutch']}")
                        st.caption(f"🇬🇧 {ex['english']}")
                        st.markdown("")


def _render_grammar(word: dict):
    """Render grammar section based on POS."""
    pos = word.get('pos')
    
    if pos == 'noun' and word.get('noun_meta'):
        noun_meta = word['noun_meta']
        if noun_meta.get('article'):
            st.markdown(f"**Article:** {noun_meta['article']}")
        if noun_meta.get('plural'):
            st.markdown(f"**Plural:** {noun_meta['plural']}")
        if noun_meta.get('diminutive'):
            st.markdown(f"**Diminutive:** {noun_meta['diminutive']}")

    elif pos == 'verb' and word.get('verb_meta'):
        verb_meta = word['verb_meta']
        if verb_meta.get('past_singular'):
            st.markdown(f"**Past (singular):** {verb_meta['past_singular']}")
        if verb_meta.get('past_plural'):
            st.markdown(f"**Past (plural):** {verb_meta['past_plural']}")
        if verb_meta.get('past_participle'):
            st.markdown(f"**Past Participle:** {verb_meta['past_participle']}")
        if verb_meta.get('auxiliary'):
            st.markdown(f"**Auxiliary:** {verb_meta['auxiliary']}")
        if verb_meta.get('separable'):
            st.markdown(f"**Separable:** Yes")
            if verb_meta.get('separable_prefix'):
                st.markdown(f"**Prefix:** {verb_meta['separable_prefix']}")
        if verb_meta.get('is_reflexive'):
            st.markdown(f"**Reflexive:** Yes (requires 'zich')")

        if verb_meta.get('is_irregular_past'):
            st.caption("⚠️ Irregular past tense")
        if verb_meta.get('is_irregular_participle'):
            st.caption("⚠️ Irregular past participle")

    elif pos == 'adjective' and word.get('adjective_meta'):
        adj_meta = word['adjective_meta']
        if adj_meta.get('comparative'):
            st.markdown(f"**Comparative:** {adj_meta['comparative']}")
        if adj_meta.get('superlative'):
            st.markdown(f"**Superlative:** {adj_meta['superlative']}")
