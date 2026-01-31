"""
Shared prompt fragments and configuration for lexicon enrichment.

This module contains reusable prompt components used by both monolithic
and modular enrichment approaches, ensuring fair comparison and easier maintenance.
"""

# Configuration
N_EXAMPLES = 5  # Number of examples per form/tense

# ---- System Prompts ----

SYSTEM_PROMPT_GENERAL = "You are a Dutch linguistics expert who provides accurate, comprehensive word analysis."

SYSTEM_PROMPT_NOUN = "You are a Dutch linguistics expert specializing in noun declension."

SYSTEM_PROMPT_VERB = "You are a Dutch linguistics expert specializing in verb conjugation."

SYSTEM_PROMPT_ADJECTIVE = "You are a Dutch linguistics expert specializing in adjective comparison."

# ---- Shared Prompt Fragments ----

UNIVERSAL_INSTRUCTIONS = """Provide comprehensive linguistic metadata.

CRITICAL: The user may provide an inflected or conjugated form of the word (e.g., "liep", "mooier").
You MUST:
1. Identify the correct LEMMA (dictionary form: "lopen", "mooi")
2. Provide translation and definition FOR THE LEMMA, not the inflected form
   - Example: If user provides "liep", translate "lopen" as "to walk" (NOT "walked")
   - Example: If user provides "mooier", translate "mooi" as "beautiful" (NOT "more beautiful")

Instructions:
- Identify the correct part of speech (POS)
- Provide the SINGLE BEST, most common English translation FOR THE LEMMA (one clear answer for flashcards)
  * Choose the most natural, frequently used translation
  * Keep it concise - a single word or short phrase
  * Examples: "to walk" (not "to walk, to go"), "cozy" (not "cozy, nice, pleasant")
- Provide a clear definition FOR THE LEMMA (1-2 sentences) explaining meaning with context and nuance
  * Mention alternative translations if they're common (e.g., "can also mean 'nice' or 'pleasant'")
  * Explain WHEN and WHY to use this word
  * For uniquely Dutch concepts (like "gezellig"), provide cultural context
  * Help learners understand beyond literal translation
- Estimate CEFR difficulty level (A1-C2)
- Add up to 3 semantic tags representing the highest-level conceptual domains the word belongs to, avoiding synonyms and narrow subcategories
- Provide {n_examples} general example sentences in both Dutch and English

General Guidelines:
- For all examples, provide natural, practical sentences in both Dutch and English
- Keep examples simple and relevant to the word's difficulty level
- Prioritize common, everyday usage over literary or archaic forms
- Examples should sound like something a native speaker would actually say in conversation
- Avoid overly formal or textbook-sounding Dutch

Be accurate and comprehensive."""

NOUN_INSTRUCTIONS = """For this noun, provide complete metadata:

Required Fields:
- article (de/het) - REQUIRED, every noun has an article
  * This is critical for Dutch learners - never leave blank
- plural form - REQUIRED (even if rarely used, provide the correct form)
  * Common patterns: -en, -s, or irregular
- diminutive form - provide if it's commonly used
  * In Dutch, diminutives often change meaning/context (e.g., "biertje" is social/casual, not just small)
  * Only include if the diminutive is actually used in practice

Fixed Prepositions (Optional):
- Identify fixed prepositions for this noun (if any)
- Only include strongly conventional prepositions (e.g., "angst voor", "behoefte aan", "respect voor")
- Many nouns don't have fixed prepositions - return null if uncertain
- For each preposition, provide:
  * usage_frequency: "dominant" (most natural, 80%+), "common" (also used, 15-30%), "rare" (occasional but notable, <15%)
  * meaning_context: explanation if different prepositions change meaning
  * examples: {n_examples} bilingual sentences showing usage
    → Use contexts that make the preposition choice clear and natural
    → Prefer situations where this preposition is the most idiomatic choice
- Maximum 2 prepositions (most nouns have at most one)
- Order by frequency (dominant first)

Examples:
- {n_examples} examples in singular form (include the article, e.g., "de hond" not just "hond")
- {n_examples} examples in plural form

Guidelines:
- Articles (de/het) are CRITICAL for learners - always provide them
- Show natural usage in example sentences
- Include the article in all noun examples
- Be conservative with fixed prepositions - only include clear, conventional cases"""

VERB_INSTRUCTIONS = """For this verb, provide complete metadata:

Required Fields:
- past tense forms (singular and plural) - REQUIRED for all verbs
- past participle (voltooid deelwoord) - REQUIRED for all verbs
- auxiliary verb (hebben/zijn) - REQUIRED, specify which is used in perfect tense
- irregularity flags (REQUIRED - set to True/False, not None):
  * is_irregular_past: True if past tense doesn't follow regular -de/-te pattern
  * is_irregular_participle: True if participle doesn't follow regular ge-...-d/t pattern

Separable Verbs:
- whether it's separable and the prefix if applicable

Reflexive Verbs:
- whether it's reflexive (requires "zich" - e.g., "zich schamen", "zich vergissen")
- is_reflexive: True if the verb requires "zich"
- Note: The lemma should be WITHOUT "zich" (e.g., lemma="schamen" not "zich schamen")
- For reflexive verbs, examples should include "zich/je/me" as appropriate

Prepositional Verbs:
- Identify common prepositional verb uses (phrasal verbs where the preposition is part of the verb phrase)
- Examples: "denken aan" (to think of), "houden van" (to love), "wachten op" (to wait for)
- For each prepositional use, provide:
  * preposition: the preposition used (e.g., "aan", "op", "van")
  * meaning: English translation of the phrasal verb (e.g., "to think of", "to wait for")
  * case_note: grammatical notes if relevant (optional)
  * examples: {n_examples} bilingual example sentences showing this prepositional use
    → IMPORTANT: Use contexts that make the preposition choice clear and natural
    → Prefer situations where this preposition is the most idiomatic choice
    → Avoid generic contexts where multiple prepositions could work equally well
- Focus on high-frequency combinations (max 5-6)
- If no prepositions are typically used with this verb, leave the list empty
- These are verb-preposition chunks that learners should memorize as units

Examples in Different Tenses:
- For verbs WITHOUT prepositional uses:
  - Provide {n_examples} present tense examples
  - Provide {n_examples} past tense examples
  - Provide {n_examples} perfect tense examples
- For verbs WITH prepositional uses:
  - Prepositional examples are provided in the preposition_usage field
  - Still provide {n_examples} past and perfect examples (can include prepositions or not)

Guidelines:
- Prepositional verbs are multi-word verbs where the preposition fundamentally changes meaning
  * Example: "denken" (to think) vs "denken aan" (to think of) - different concepts
- These are essential for fluency - learners must know "houden van" means "to love"
- Examples should use natural, conversational Dutch (not formal or stilted)"""

ADJECTIVE_INSTRUCTIONS = """For this adjective, provide complete metadata:

Required Fields:
- comparative form (e.g., groot → groter, goed → beter, tevreden → meer tevreden) - REQUIRED
  * ALWAYS provide a form (required field, never leave blank)
  * Choose the MOST COMMONLY USED form if multiple options exist
    → If "meer [adjective]" is more common than "[adjective]er", use "meer [adjective]"
    → If the inflected form is more common, use that
  * Examples MUST use the same form you provide here (consistency is critical for learners)

- superlative form (e.g., groot → grootst, goed → best, tevreden → meest tevreden) - REQUIRED
  * ALWAYS provide a form (required field, never leave blank)
  * Choose the MOST COMMONLY USED form if multiple options exist
    → If "meest [adjective]" is more common than "[adjective]st", use "meest [adjective]"
    → If the inflected form is more common, use that
  * Examples MUST use the same form you provide here (consistency is critical for learners)

- Irregularity flags (REQUIRED for both comparative and superlative):
  * is_irregular_comparative: true if ANY of the following apply:
    → Completely different stem (goed → beter, veel → meer)
    → Uses "meer" instead of -er (tevreden → meer tevreden)
    → Unusual spelling changes (jong → jonger with single 'g')
  * is_irregular_superlative: true if ANY of the following apply:
    → Completely different stem (goed → best, veel → meest)
    → Uses "meest" instead of -st (tevreden → meest tevreden)
    → Unusual spelling changes

Fixed Prepositions (Optional):
- Identify fixed prepositions for this adjective (if any)
- Only include prepositions that are strongly conventional (not just possible)
- Examples: "bang voor" (afraid of), "trots op" (proud of), "goed in" (good at)
- For each preposition, provide:
  * usage_frequency: "dominant" (most natural, 80%+), "common" (also used, 15-30%), "rare" (occasional but notable, <15%)
  * meaning_context: explanation if different prepositions have different meanings (e.g., "bekend met" vs "bekend om")
  * examples: {n_examples} bilingual sentences showing usage
    → Use contexts that make the preposition choice clear and natural
    → Prefer situations where this preposition is the most idiomatic choice
- Maximum 3 prepositions (prioritize most useful for learners)
- Order by frequency (dominant first)
- If uncertain or the adjective doesn't have conventional fixed prepositions, return null

Examples:
- {n_examples} examples in base form showing natural usage
- {n_examples} examples in comparative form
- {n_examples} examples in superlative form

Guidelines:
- Show the adjective in natural context
- Use conversational Dutch, not formal or textbook language
- Be conservative with fixed prepositions - only include clear, conventional cases"""

# ---- Completeness Reminder ----

COMPLETENESS_REMINDER = """
IMPORTANT: Be thorough and complete. Fill in ALL required fields for the word's part of speech.
Do not leave fields blank unless they genuinely don't apply (e.g., diminutive for proper nouns).
For standard words, ALL metadata fields should have values."""


def format_prompt(base_instructions: str, **kwargs) -> str:
    """
    Format a prompt template with dynamic values.

    Args:
        base_instructions: The prompt template string
        **kwargs: Values to substitute (e.g., n_examples=2)

    Returns:
        Formatted prompt string
    """
    return base_instructions.format(**kwargs)
