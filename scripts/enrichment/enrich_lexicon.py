"""
AI-powered lexicon enrichment script (monolithic approach).

This script uses OpenAI's structured outputs to enrich Dutch words with
comprehensive linguistic metadata in a single API call.

Usage:
    from scripts.enrichment.enrich_lexicon import enrich_word
    result = enrich_word("lopen", "to walk")
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from core.schemas import AIEnrichedEntry
from scripts.enrichment.constants import (
    N_EXAMPLES,
    SYSTEM_PROMPT_GENERAL,
    UNIVERSAL_INSTRUCTIONS,
    NOUN_INSTRUCTIONS,
    VERB_INSTRUCTIONS,
    ADJECTIVE_INSTRUCTIONS,
    COMPLETENESS_REMINDER,
    format_prompt,
)

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
    model: str = "gpt-4o-2024-08-06",
    return_usage: bool = False
) -> AIEnrichedEntry | tuple[AIEnrichedEntry, dict]:
    """
    Use OpenAI's structured outputs to enrich a Dutch word with linguistic metadata.

    Args:
        dutch_word: The Dutch word to enrich (lemma form)
        english_hint: Optional English translation hint to help the AI
        model: OpenAI model to use (must support structured outputs)
        return_usage: If True, return tuple of (enriched_entry, usage_dict)

    Returns:
        AIEnrichedEntry with all linguistic metadata filled in, or
        tuple of (AIEnrichedEntry, usage_dict) if return_usage=True

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """

    # Build the prompt using shared constants
    prompt = f"""Analyze the Dutch word "{dutch_word}" """
    if english_hint:
        prompt += f"""(English: "{english_hint}") """

    prompt += "and provide comprehensive linguistic metadata.\n\n"

    # Add universal instructions
    prompt += format_prompt(UNIVERSAL_INSTRUCTIONS, n_examples=N_EXAMPLES)
    prompt += "\n\nFill in POS-specific metadata based on the word type:\n\n"

    # Add POS-specific instructions
    prompt += "For NOUNS:\n"
    prompt += format_prompt(NOUN_INSTRUCTIONS, n_examples=N_EXAMPLES)
    prompt += "\n\n"

    prompt += "For VERBS:\n"
    prompt += format_prompt(VERB_INSTRUCTIONS, n_examples=N_EXAMPLES)
    prompt += "\n\n"

    prompt += "For ADJECTIVES:\n"
    prompt += format_prompt(ADJECTIVE_INSTRUCTIONS, n_examples=N_EXAMPLES)
    prompt += "\n\n"

    # Add completeness reminder
    prompt += COMPLETENESS_REMINDER

    client = get_client()

    # Call OpenAI with structured output
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT_GENERAL
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

    if return_usage:
        usage = {
            "prompt_tokens": completion.usage.prompt_tokens,
            "completion_tokens": completion.usage.completion_tokens,
            "total_tokens": completion.usage.total_tokens
        }
        return enriched_entry, usage

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
