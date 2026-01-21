"""
AI-powered lexicon enrichment script.

This script uses OpenAI's structured outputs to enrich Dutch words with
comprehensive linguistic metadata for the MongoDB lexicon.

Usage:
    from scripts.enrich_lexicon import enrich_word
    result = enrich_word("lopen", "to walk")
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from core.schemas import AIEnrichedEntry

# Load environment variables
load_dotenv()

# Initialize OpenAI client (module-level, reused across calls)
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create the OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        _client = OpenAI(api_key=api_key)
    return _client


def enrich_word(
    dutch_word: str,
    english_hint: Optional[str] = None,
    model: str = "gpt-4o-2024-08-06"
) -> AIEnrichedEntry:
    """
    Use OpenAI's structured outputs to enrich a Dutch word with linguistic metadata.

    Args:
        dutch_word: The Dutch word to enrich (lemma form)
        english_hint: Optional English translation hint to help the AI
        model: OpenAI model to use (must support structured outputs)

    Returns:
        AIEnrichedEntry with all linguistic metadata filled in

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """

    # Build the prompt
    prompt = f"""You are a Dutch linguistics expert. Analyze the Dutch word "{dutch_word}" """
    if english_hint:
        prompt += f"""(English: "{english_hint}") """

    prompt += """and provide comprehensive linguistic metadata.

Instructions:
- Identify the correct part of speech (POS)
- Provide the SINGLE BEST, most common English translation (one clear answer for flashcards)
  * Choose the most natural, frequently used translation
  * Keep it concise - a single word or short phrase
  * Examples: "to walk" (not "to walk, to go"), "cozy" (not "cozy, nice, pleasant")
- Provide a clear definition (1-2 sentences) explaining meaning with context and nuance
  * Mention alternative translations if they're common (e.g., "can also mean 'nice' or 'pleasant'")
  * Explain WHEN and WHY to use this word
  * For uniquely Dutch concepts (like "gezellig"), provide cultural context
  * Help learners understand beyond literal translation
- Estimate CEFR difficulty level (A1-C2)
- Add relevant semantic tags (max 5)
- Fill in POS-specific metadata based on the word type:

IMPORTANT: Be thorough and complete. Fill in ALL required fields for the word's part of speech.
Do not leave fields blank unless they genuinely don't apply (e.g., diminutive for proper nouns).
For standard words, ALL metadata fields should have values.

  For NOUNS:
  - article (de/het) - REQUIRED, every noun has an article
    * This is critical for Dutch learners - never leave blank
  - plural form - REQUIRED (even if rarely used, provide the correct form)
    * Common patterns: -en, -s, or irregular
  - diminutive form - provide if it's commonly used
    * In Dutch, diminutives often change meaning/context (e.g., "biertje" is social/casual, not just small)
    * Only include if the diminutive is actually used in practice
  - examples in singular and plural forms (2 examples each showing natural usage)
    * Include the article in the examples (e.g., "de hond" not just "hond")

  For VERBS:
  - past tense forms (singular and plural) - REQUIRED for all verbs
  - past participle (voltooid deelwoord) - REQUIRED for all verbs
  - auxiliary verb (hebben/zijn) - REQUIRED, specify which is used in perfect tense
  - whether it's separable and the prefix if applicable
    * For separable verbs, examples MUST show the verb both together and separated
    * Example: "opstaan" → "Ik sta om 7 uur op" (showing separation)
  - whether it's reflexive (requires "zich" - e.g., "zich schamen", "zich vergissen")
    * is_reflexive: True if the verb requires "zich"
    * Note: The lemma should be WITHOUT "zich" (e.g., lemma="schamen" not "zich schamen")
  - irregularity flags (REQUIRED - set to True/False, not None):
    * is_irregular_past: True if past tense doesn't follow regular -de/-te pattern
    * is_irregular_participle: True if participle doesn't follow regular ge-...-d/t pattern
  - common prepositions used with the verb (e.g., denken aan, wachten op)
    * Provide ALL common prepositions that naturally pair with this verb
    * These are essential for fluency - don't skip them
    * If no prepositions are typically used, leave the list empty
  - preposition_examples: If the verb has common prepositions, provide examples GROUPED by preposition
    * CRITICAL: Use the "preposition_examples" field (a list of objects, one per preposition)
    * Provide exactly 2 examples for EACH preposition
    * Example structure for "praten":
      [
        {
          "preposition": "met",
          "examples": [
            {"dutch": "Ik praat met mijn vriend", "english": "I'm talking with my friend"},
            {"dutch": "Ze praat altijd met haar moeder", "english": "She always talks with her mother"}
          ]
        },
        {
          "preposition": "over",
          "examples": [
            {"dutch": "We praten over het weer", "english": "We're talking about the weather"},
            {"dutch": "Hij praat graag over politiek", "english": "He likes talking about politics"}
          ]
        },
        {
          "preposition": "tegen",
          "examples": [
            {"dutch": "Praat niet zo tegen mij!", "english": "Don't talk to me like that!"},
            {"dutch": "Ze praat altijd tegen de hond", "english": "She always talks to the dog"}
          ]
        }
      ]
    * The meaning changes significantly with each preposition - this grouped format helps learners understand each variant
  - examples in present, past, and perfect tenses
    * For verbs WITH prepositions:
      - Fill preposition_examples (grouped by preposition, 2 per preposition)
      - ALSO provide 2 examples_present (can be any 2 from the preposition examples)
      - Provide 2 past examples
      - Provide 2 perfect examples
    * For verbs WITHOUT prepositions:
      - Leave preposition_examples EMPTY
      - Provide 2 present examples
      - Provide 2 past examples
      - Provide 2 perfect examples
  - for reflexive verbs, examples should include "zich/je/me" as appropriate
  - examples should use natural, conversational Dutch (not formal or stilted)

  For ADJECTIVES:
  - comparative form (e.g., groot → groter)
    * For regular adjectives, add -er/-st
    * For irregular ones, provide the correct form (e.g., goed → beter, veel → meer)
    * For adjectives that use "meer/meest" (more/most), still provide both forms if possible
      (e.g., tevreden can be "tevredener" or "meer tevreden" - provide "tevredener" as comparative)
    * ALWAYS provide a value - don't leave blank
  - superlative form (e.g., groot → grootst)
    * ALWAYS provide a value - don't leave blank
  - examples in base, comparative, and superlative forms showing natural usage

- For all examples, provide natural, practical sentences in both Dutch and English
- Keep examples simple and relevant to the word's difficulty level
- Prioritize common, everyday usage over literary or archaic forms
- Examples should sound like something a native speaker would actually say in conversation
- Avoid overly formal or textbook-sounding Dutch

DUTCH-SPECIFIC REMINDERS:
- Articles (de/het) are CRITICAL for learners - always provide them
- Verb + preposition combinations change the meaning significantly
  * Example: "praten met" = talk with, "praten over" = talk about, "praten tegen" = talk to/against
  * Use the "preposition_examples" field (a dictionary) to group examples by preposition
  * Each preposition gets exactly 2 example sentences
  * This structured format is the most important part of verb learning - don't shortcut it
- Separable verbs must show separation in examples (e.g., "Ik bel je later op" not just "opbellen")

Be accurate and comprehensive."""

    client = get_client()

    # Call OpenAI with structured output
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a Dutch linguistics expert who provides accurate, comprehensive word analysis."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=AIEnrichedEntry,
    )

    # Extract the structured output
    enriched_entry = completion.choices[0].message.parsed

    if enriched_entry is None:
        raise ValueError(f"Failed to parse structured output for word: {dutch_word}")

    return enriched_entry


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.enrich_lexicon <dutch_word> [english_hint]")
        print("Example: python -m scripts.enrich_lexicon lopen 'to walk'")
        sys.exit(1)

    word = sys.argv[1]
    hint = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Enriching: {word}" + (f" ({hint})" if hint else ""))
    result = enrich_word(word, hint)
    print("\nResult:")
    print(result.model_dump_json(indent=2))
