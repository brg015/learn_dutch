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
- Provide accurate English translation(s)
- Estimate CEFR difficulty level (A1-C2)
- Add relevant semantic tags (max 5)
- Fill in POS-specific metadata based on the word type:

  For NOUNS:
  - article (de/het)
  - plural form
  - diminutive form (if common)
  - examples in singular and plural forms

  For VERBS:
  - past tense forms (singular and plural)
  - past participle (voltooid deelwoord)
  - auxiliary verb (hebben/zijn)
  - whether it's separable and the prefix if applicable
  - irregularity flags:
    * is_irregular_past: True if past tense doesn't follow regular -de/-te pattern
    * is_irregular_participle: True if participle doesn't follow regular ge-...-d/t pattern
  - common prepositions used with the verb (e.g., denken aan, wachten op)
  - examples in present, past, and perfect tenses
  - examples should demonstrate prepositional usage where relevant

  For ADJECTIVES:
  - comparative form
  - superlative form
  - examples in base, comparative, and superlative forms

- For all examples, provide natural, practical sentences in both Dutch and English
- Keep examples simple and relevant to the word's difficulty level
- Prioritize common, everyday usage over literary or archaic forms

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
