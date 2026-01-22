"""
Modular AI-powered lexicon enrichment.

This script uses a two-phase approach:
1. Phase 1 (Basic): Enrich lemma, POS, translation, definition, difficulty, tags, examples
2. Phase 2 (POS-specific): Enrich conjugations/declensions for nouns, verbs, adjectives

Advantages:
- More cost-efficient (words without POS metadata skip Phase 2)
- Selective re-enrichment (re-run only Phase 2 for verbs if needed)
- Cleaner, more focused prompts

Usage:
    from scripts.enrichment.enrich_modular import enrich_basic, enrich_pos

    # Phase 1: Basic enrichment
    basic = enrich_basic("lopen", "to walk")

    # Phase 2: POS-specific enrichment (if pos in [noun, verb, adjective])
    if basic.pos == "verb":
        pos_meta = enrich_pos(basic.lemma, basic.pos, basic.translation)
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from core.schemas import (
    AIBasicEnrichment,
    AINounEnrichment,
    AIVerbEnrichment,
    AIAdjectiveEnrichment,
    PartOfSpeech,
    NounMetadata,
    VerbMetadata,
    AdjectiveMetadata,
)
from scripts.enrichment.constants import (
    N_EXAMPLES,
    SYSTEM_PROMPT_GENERAL,
    SYSTEM_PROMPT_NOUN,
    SYSTEM_PROMPT_VERB,
    SYSTEM_PROMPT_ADJECTIVE,
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


def enrich_basic(
    dutch_word: str,
    english_hint: Optional[str] = None,
    model: str = "gpt-4o-2024-08-06",
    return_usage: bool = False
) -> AIBasicEnrichment | tuple[AIBasicEnrichment, dict]:
    """
    Phase 1: Enrich basic word information.

    Returns lemma, POS, translation, definition, difficulty, tags, and general examples.
    Does NOT include POS-specific metadata.

    Args:
        dutch_word: The Dutch word to enrich
        english_hint: Optional English translation hint
        model: OpenAI model to use

    Returns:
        AIBasicEnrichment with basic word info

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """
    # Build the prompt
    prompt = f"""Analyze the Dutch word "{dutch_word}" """
    if english_hint:
        prompt += f"""(English: "{english_hint}") """

    prompt += "and provide basic linguistic metadata.\n\n"
    prompt += format_prompt(UNIVERSAL_INSTRUCTIONS, n_examples=N_EXAMPLES)

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
        response_format=AIBasicEnrichment,
    )

    # Extract the structured output
    enriched = completion.choices[0].message.parsed

    if enriched is None:
        raise ValueError(f"Failed to parse structured output for word: {dutch_word}")

    if return_usage:
        usage = {
            "prompt_tokens": completion.usage.prompt_tokens,
            "completion_tokens": completion.usage.completion_tokens,
            "total_tokens": completion.usage.total_tokens
        }
        return enriched, usage

    return enriched


def enrich_pos(
    lemma: str,
    pos: PartOfSpeech,
    translation: str,
    model: str = "gpt-4o-2024-08-06"
) -> NounMetadata | VerbMetadata | AdjectiveMetadata | None:
    """
    Phase 2: Enrich POS-specific metadata.

    Calls the appropriate enrichment function based on POS.
    Returns None for POS types that don't need specific metadata.

    Args:
        lemma: The Dutch lemma (from Phase 1)
        pos: Part of speech (from Phase 1)
        translation: English translation (from Phase 1)
        model: OpenAI model to use

    Returns:
        POS-specific metadata, or None if POS doesn't need enrichment

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """
    if pos == PartOfSpeech.NOUN:
        return enrich_noun(lemma, translation, model)
    elif pos == PartOfSpeech.VERB:
        return enrich_verb(lemma, translation, model)
    elif pos == PartOfSpeech.ADJECTIVE:
        return enrich_adjective(lemma, translation, model)
    else:
        # No POS-specific enrichment needed for other types
        return None


def enrich_noun(
    lemma: str,
    translation: str,
    model: str = "gpt-4o-2024-08-06"
) -> NounMetadata:
    """
    Phase 2: Enrich noun-specific metadata.

    Returns article, plural, diminutive, and examples.

    Args:
        lemma: The Dutch noun lemma
        translation: English translation (helps with context)
        model: OpenAI model to use

    Returns:
        NounMetadata with declension and examples

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """
    # Build the prompt
    prompt = f"""For the Dutch noun "{lemma}" (English: "{translation}"), provide complete noun metadata.\n\n"""
    prompt += format_prompt(NOUN_INSTRUCTIONS, n_examples=N_EXAMPLES)
    prompt += "\n\n" + COMPLETENESS_REMINDER

    client = get_client()

    # Call OpenAI with structured output
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT_NOUN
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=AINounEnrichment,
    )

    # Extract the structured output
    enriched = completion.choices[0].message.parsed

    if enriched is None or enriched.noun_meta is None:
        raise ValueError(f"Failed to parse noun metadata for: {lemma}")

    return enriched.noun_meta


def enrich_verb(
    lemma: str,
    translation: str,
    model: str = "gpt-4o-2024-08-06"
) -> VerbMetadata:
    """
    Phase 2: Enrich verb-specific metadata.

    Returns conjugation, prepositions, and examples.

    Args:
        lemma: The Dutch verb lemma
        translation: English translation (helps with context)
        model: OpenAI model to use

    Returns:
        VerbMetadata with conjugation and examples

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """
    # Build the prompt
    prompt = f"""For the Dutch verb "{lemma}" (English: "{translation}"), provide complete verb metadata.\n\n"""
    prompt += format_prompt(VERB_INSTRUCTIONS, n_examples=N_EXAMPLES)
    prompt += "\n\n" + COMPLETENESS_REMINDER

    client = get_client()

    # Call OpenAI with structured output
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT_VERB
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=AIVerbEnrichment,
    )

    # Extract the structured output
    enriched = completion.choices[0].message.parsed

    if enriched is None or enriched.verb_meta is None:
        raise ValueError(f"Failed to parse verb metadata for: {lemma}")

    return enriched.verb_meta


def enrich_adjective(
    lemma: str,
    translation: str,
    model: str = "gpt-4o-2024-08-06"
) -> AdjectiveMetadata:
    """
    Phase 2: Enrich adjective-specific metadata.

    Returns comparative, superlative, and examples.

    Args:
        lemma: The Dutch adjective lemma
        translation: English translation (helps with context)
        model: OpenAI model to use

    Returns:
        AdjectiveMetadata with comparison and examples

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """
    # Build the prompt
    prompt = f"""For the Dutch adjective "{lemma}" (English: "{translation}"), provide complete adjective metadata.\n\n"""
    prompt += format_prompt(ADJECTIVE_INSTRUCTIONS, n_examples=N_EXAMPLES)
    prompt += "\n\n" + COMPLETENESS_REMINDER

    client = get_client()

    # Call OpenAI with structured output
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT_ADJECTIVE
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=AIAdjectiveEnrichment,
    )

    # Extract the structured output
    enriched = completion.choices[0].message.parsed

    if enriched is None or enriched.adjective_meta is None:
        raise ValueError(f"Failed to parse adjective metadata for: {lemma}")

    return enriched.adjective_meta


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.enrichment.enrich_modular <dutch_word> [english_hint]")
        print("Example: python -m scripts.enrichment.enrich_modular lopen 'to walk'")
        sys.exit(1)

    word = sys.argv[1]
    hint = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Phase 1: Enriching basic info for '{word}'" + (f" ({hint})" if hint else ""))
    basic = enrich_basic(word, hint)

    print("\nBasic Enrichment Result:")
    print(f"  Lemma: {basic.lemma}")
    print(f"  POS: {basic.pos}")
    print(f"  Translation: {basic.translation}")
    print(f"  Difficulty: {basic.difficulty}")
    print(f"  Tags: {basic.tags}")
    print(f"  Examples: {len(basic.general_examples)}")

    # Check if we need Phase 2
    if basic.pos in [PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE]:
        print(f"\nPhase 2: Enriching {basic.pos} metadata...")
        pos_meta = enrich_pos(basic.lemma, basic.pos, basic.translation)

        if pos_meta:
            print(f"✓ Phase 2 complete")
            print(f"  Metadata type: {type(pos_meta).__name__}")
        else:
            print("  (no POS-specific metadata needed)")
    else:
        print(f"\n  POS '{basic.pos}' does not need Phase 2 enrichment")
