"""
Test enrichment costs across different N_EXAMPLES values.

This script enriches the same words with different example counts to compare
API costs and help determine the optimal N_EXAMPLES value.

Usage:
    python -m scripts.maintenance.test_example_counts
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from scripts.enrichment.constants import (
    SYSTEM_PROMPT_NOUN,
    SYSTEM_PROMPT_VERB,
    SYSTEM_PROMPT_ADJECTIVE,
    NOUN_INSTRUCTIONS,
    VERB_INSTRUCTIONS,
    ADJECTIVE_INSTRUCTIONS,
    COMPLETENESS_REMINDER,
    format_prompt,
    SYSTEM_PROMPT_GENERAL,
    UNIVERSAL_INSTRUCTIONS,
)
from core.schemas import AIBasicEnrichment, AINounEnrichment, AIVerbEnrichment, AIAdjectiveEnrichment, PartOfSpeech

load_dotenv()


# Pricing (as of Jan 2025)
COST_INPUT_PER_1M = 2.50
COST_OUTPUT_PER_1M = 10.00


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate actual cost from token counts."""
    input_cost = (input_tokens / 1_000_000) * COST_INPUT_PER_1M
    output_cost = (output_tokens / 1_000_000) * COST_OUTPUT_PER_1M
    return input_cost + output_cost


def enrich_with_n_examples(
    dutch_word: str,
    english_hint: str,
    n_examples: int,
    model: str = "gpt-4o-2024-08-06"
) -> tuple[dict, float, float]:
    """
    Enrich a word using modular approach with custom number of examples.

    Args:
        dutch_word: Dutch word to enrich
        english_hint: English translation hint
        n_examples: Number of examples to request
        model: OpenAI model to use

    Returns:
        Tuple of (enriched_data, total_cost, total_duration)
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Phase 1: Basic enrichment
    phase1_start = datetime.now()

    prompt = f"""Analyze the Dutch word "{dutch_word}" """
    if english_hint:
        prompt += f"""(English: "{english_hint}") """
    prompt += "and provide basic linguistic metadata.\n\n"
    prompt += format_prompt(UNIVERSAL_INSTRUCTIONS, n_examples=n_examples)

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_GENERAL},
            {"role": "user", "content": prompt}
        ],
        response_format=AIBasicEnrichment,
    )

    basic_enriched = completion.choices[0].message.parsed
    phase1_duration = (datetime.now() - phase1_start).total_seconds()
    phase1_cost = calculate_cost(completion.usage.prompt_tokens, completion.usage.completion_tokens)
    phase1_tokens = {"input": completion.usage.prompt_tokens, "output": completion.usage.completion_tokens}

    # Phase 2: POS-specific (if needed)
    phase2_cost = 0.0
    phase2_duration = 0.0
    phase2_tokens = {"input": 0, "output": 0}
    pos_metadata = None

    if basic_enriched.pos in [PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE]:
        phase2_start = datetime.now()

        if basic_enriched.pos == PartOfSpeech.NOUN:
            prompt = f"""For the Dutch noun "{basic_enriched.lemma}" (English: "{basic_enriched.translation}"), provide complete noun metadata.\n\n"""
            prompt += format_prompt(NOUN_INSTRUCTIONS, n_examples=n_examples) + "\n\n" + COMPLETENESS_REMINDER
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_NOUN}, {"role": "user", "content": prompt}],
                response_format=AINounEnrichment,
            )
            pos_metadata = completion.choices[0].message.parsed.noun_meta

        elif basic_enriched.pos == PartOfSpeech.VERB:
            prompt = f"""For the Dutch verb "{basic_enriched.lemma}" (English: "{basic_enriched.translation}"), provide complete verb metadata.\n\n"""
            prompt += format_prompt(VERB_INSTRUCTIONS, n_examples=n_examples) + "\n\n" + COMPLETENESS_REMINDER
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_VERB}, {"role": "user", "content": prompt}],
                response_format=AIVerbEnrichment,
            )
            pos_metadata = completion.choices[0].message.parsed.verb_meta

        elif basic_enriched.pos == PartOfSpeech.ADJECTIVE:
            prompt = f"""For the Dutch adjective "{basic_enriched.lemma}" (English: "{basic_enriched.translation}"), provide complete adjective metadata.\n\n"""
            prompt += format_prompt(ADJECTIVE_INSTRUCTIONS, n_examples=n_examples) + "\n\n" + COMPLETENESS_REMINDER
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_ADJECTIVE}, {"role": "user", "content": prompt}],
                response_format=AIAdjectiveEnrichment,
            )
            pos_metadata = completion.choices[0].message.parsed.adjective_meta

        phase2_duration = (datetime.now() - phase2_start).total_seconds()
        phase2_cost = calculate_cost(completion.usage.prompt_tokens, completion.usage.completion_tokens)
        phase2_tokens = {"input": completion.usage.prompt_tokens, "output": completion.usage.completion_tokens}

    total_cost = phase1_cost + phase2_cost
    total_duration = phase1_duration + phase2_duration

    return {
        "lemma": basic_enriched.lemma,
        "pos": str(basic_enriched.pos),
        "translation": basic_enriched.translation,
        "phase1_cost": phase1_cost,
        "phase1_tokens": phase1_tokens,
        "phase2_cost": phase2_cost,
        "phase2_tokens": phase2_tokens,
        "total_cost": total_cost,
        "total_duration": total_duration,
    }, total_cost, total_duration


def test_example_counts():
    """Test different N_EXAMPLES values on sample words."""

    # Test words covering different POS types
    test_words = [
        ("lopen", "to walk", "verb"),
        ("hond", "dog", "noun"),
        ("groot", "big", "adjective"),
    ]

    # Test different example counts
    example_counts = [1, 2, 3, 5]

    print("=" * 80)
    print("TESTING EXAMPLE COUNTS: Cost & Token Comparison")
    print("=" * 80)
    print()

    results = []

    for dutch, english, expected_pos in test_words:
        print(f"\n{'='*80}")
        print(f"Word: {dutch} ({english}) - Expected POS: {expected_pos}")
        print(f"{'='*80}\n")

        for n in example_counts:
            print(f"  Testing n_examples={n}...", end=" ", flush=True)

            try:
                result, cost, duration = enrich_with_n_examples(dutch, english, n)
                results.append({
                    "word": dutch,
                    "pos": result["pos"],
                    "n_examples": n,
                    "phase1_cost": result["phase1_cost"],
                    "phase1_input": result["phase1_tokens"]["input"],
                    "phase1_output": result["phase1_tokens"]["output"],
                    "phase2_cost": result["phase2_cost"],
                    "phase2_input": result["phase2_tokens"]["input"],
                    "phase2_output": result["phase2_tokens"]["output"],
                    "total_cost": cost,
                    "duration": duration,
                })

                print(f"✓ Cost: ${cost:.5f}, Duration: {duration:.2f}s")
                print(f"     Phase 1: ${result['phase1_cost']:.5f} ({result['phase1_tokens']['input']} in, {result['phase1_tokens']['output']} out)")
                print(f"     Phase 2: ${result['phase2_cost']:.5f} ({result['phase2_tokens']['input']} in, {result['phase2_tokens']['output']} out)")

            except Exception as e:
                print(f"✗ Error: {e}")

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY TABLE")
    print(f"{'='*80}\n")

    print(f"{'Word':<10} {'POS':<10} {'N':<3} {'Phase1':<12} {'Phase2':<12} {'Total Cost':<12} {'Time(s)':<8}")
    print("-" * 80)

    for r in results:
        print(f"{r['word']:<10} {r['pos']:<10} {r['n_examples']:<3} "
              f"${r['phase1_cost']:<11.5f} ${r['phase2_cost']:<11.5f} "
              f"${r['total_cost']:<11.5f} {r['duration']:<8.2f}")

    # Cost analysis
    print(f"\n{'='*80}")
    print("COST ANALYSIS BY N_EXAMPLES")
    print(f"{'='*80}\n")

    for n in example_counts:
        n_results = [r for r in results if r["n_examples"] == n]
        avg_cost = sum(r["total_cost"] for r in n_results) / len(n_results)
        avg_p1 = sum(r["phase1_cost"] for r in n_results) / len(n_results)
        avg_p2 = sum(r["phase2_cost"] for r in n_results) / len(n_results)

        print(f"N={n}:")
        print(f"  Average total cost: ${avg_cost:.5f}")
        print(f"  Average Phase 1:    ${avg_p1:.5f}")
        print(f"  Average Phase 2:    ${avg_p2:.5f}")
        print()

    # Cost per 100 words
    print(f"{'='*80}")
    print("PROJECTED COST FOR 100 WORDS")
    print(f"{'='*80}\n")

    for n in example_counts:
        n_results = [r for r in results if r["n_examples"] == n]
        avg_cost = sum(r["total_cost"] for r in n_results) / len(n_results)
        cost_per_100 = avg_cost * 100

        print(f"N={n}: ${cost_per_100:.2f} per 100 words")


def main():
    test_example_counts()


if __name__ == "__main__":
    main()
