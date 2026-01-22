"""
Utility functions for comparing monolithic vs modular enrichment approaches.

This module provides functions to:
- Compare both approaches on multiple words
- Calculate actual costs from API token usage
- Save/load comparison results as pickle files
- Merge results from multiple test runs
"""

from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from scripts.enrichment.enrich_lexicon import enrich_word
from scripts.enrichment.enrich_modular import enrich_basic, enrich_pos
from scripts.enrichment.constants import (
    SYSTEM_PROMPT_NOUN,
    SYSTEM_PROMPT_VERB,
    SYSTEM_PROMPT_ADJECTIVE,
    NOUN_INSTRUCTIONS,
    VERB_INSTRUCTIONS,
    ADJECTIVE_INSTRUCTIONS,
    COMPLETENESS_REMINDER,
    format_prompt,
    N_EXAMPLES,
)
from core.schemas import PartOfSpeech
from scripts.enrichment.enrich_modular import get_client


# Pricing (as of Jan 2025)
COST_INPUT_PER_1M = 2.50
COST_OUTPUT_PER_1M = 10.00


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate actual cost from token counts."""
    input_cost = (input_tokens / 1_000_000) * COST_INPUT_PER_1M
    output_cost = (output_tokens / 1_000_000) * COST_OUTPUT_PER_1M
    return input_cost + output_cost


def enrich_modular_with_n_examples(
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
    from openai import OpenAI
    import os
    from dotenv import load_dotenv

    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Phase 1: Basic enrichment
    phase1_start = datetime.now()

    # Build Phase 1 prompt with custom n_examples
    from scripts.enrichment.constants import UNIVERSAL_INSTRUCTIONS, SYSTEM_PROMPT_GENERAL
    from core.schemas import AIBasicEnrichment

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

    # Phase 2: POS-specific (if needed)
    phase2_cost = 0.0
    phase2_duration = 0.0
    pos_metadata = None

    if basic_enriched.pos in [PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE]:
        phase2_start = datetime.now()

        if basic_enriched.pos == PartOfSpeech.NOUN:
            prompt = f"""For the Dutch noun "{basic_enriched.lemma}" (English: "{basic_enriched.translation}"), provide complete noun metadata.\n\n"""
            prompt += format_prompt(NOUN_INSTRUCTIONS, n_examples=n_examples) + "\n\n" + COMPLETENESS_REMINDER
            from core.schemas import AINounEnrichment
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_NOUN}, {"role": "user", "content": prompt}],
                response_format=AINounEnrichment,
            )
            pos_metadata = completion.choices[0].message.parsed.noun_meta

        elif basic_enriched.pos == PartOfSpeech.VERB:
            prompt = f"""For the Dutch verb "{basic_enriched.lemma}" (English: "{basic_enriched.translation}"), provide complete verb metadata.\n\n"""
            prompt += format_prompt(VERB_INSTRUCTIONS, n_examples=n_examples) + "\n\n" + COMPLETENESS_REMINDER
            from core.schemas import AIVerbEnrichment
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_VERB}, {"role": "user", "content": prompt}],
                response_format=AIVerbEnrichment,
            )
            pos_metadata = completion.choices[0].message.parsed.verb_meta

        elif basic_enriched.pos == PartOfSpeech.ADJECTIVE:
            prompt = f"""For the Dutch adjective "{basic_enriched.lemma}" (English: "{basic_enriched.translation}"), provide complete adjective metadata.\n\n"""
            prompt += format_prompt(ADJECTIVE_INSTRUCTIONS, n_examples=n_examples) + "\n\n" + COMPLETENESS_REMINDER
            from core.schemas import AIAdjectiveEnrichment
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_ADJECTIVE}, {"role": "user", "content": prompt}],
                response_format=AIAdjectiveEnrichment,
            )
            pos_metadata = completion.choices[0].message.parsed.adjective_meta

        phase2_duration = (datetime.now() - phase2_start).total_seconds()
        phase2_cost = calculate_cost(completion.usage.prompt_tokens, completion.usage.completion_tokens)

    total_cost = phase1_cost + phase2_cost
    total_duration = phase1_duration + phase2_duration

    enriched_data = {
        "lemma": basic_enriched.lemma,
        "pos": str(basic_enriched.pos),
        "translation": basic_enriched.translation,
        "difficulty": str(basic_enriched.difficulty),
        "pos_metadata": pos_metadata,
    }

    return enriched_data, total_cost, total_duration


def compare_example_counts(
    word_list: list[tuple[str, str]],
    example_counts: list[int],
    model: str = "gpt-4o-2024-08-06",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Compare modular enrichment costs across different N_EXAMPLES values.

    Args:
        word_list: List of (dutch_word, english_hint) tuples
        example_counts: List of N_EXAMPLES values to test (e.g., [1, 2, 3, 4])
        model: OpenAI model to use
        verbose: Print progress messages

    Returns:
        DataFrame with columns: dutch_word, english_hint, n_examples, cost, duration, pos
    """
    results = []

    for idx, (dutch_word, english_hint) in enumerate(word_list, 1):
        if verbose:
            print(f"[{idx}/{len(word_list)}] Processing: {dutch_word} ({english_hint})")

        for n_examples in example_counts:
            if verbose:
                print(f"  Testing with n_examples={n_examples}...")

            try:
                enriched_data, cost, duration = enrich_modular_with_n_examples(
                    dutch_word, english_hint, n_examples, model
                )

                results.append({
                    "dutch_word": dutch_word,
                    "english_hint": english_hint,
                    "lemma": enriched_data["lemma"],
                    "pos": enriched_data["pos"],
                    "n_examples": n_examples,
                    "cost": cost,
                    "duration": duration,
                    "model_used": model,
                    "timestamp": datetime.now().isoformat(),
                })

                if verbose:
                    print(f"    ✓ Cost: ${cost:.5f}, Duration: {duration:.2f}s")

            except Exception as e:
                if verbose:
                    print(f"    ✗ Error: {e}")
                results.append({
                    "dutch_word": dutch_word,
                    "english_hint": english_hint,
                    "lemma": None,
                    "pos": None,
                    "n_examples": n_examples,
                    "cost": None,
                    "duration": None,
                    "model_used": model,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                })

    return pd.DataFrame(results)


def compare_multiple_words(
    word_list: list[tuple[str, str]],
    model: str = "gpt-4o-2024-08-06",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Compare monolithic vs modular enrichment for multiple words.

    Args:
        word_list: List of (dutch_word, english_hint) tuples
        model: OpenAI model to use
        verbose: Print progress messages

    Returns:
        DataFrame with comparison results for each word
    """
    results = []

    for idx, (dutch_word, english_hint) in enumerate(word_list, 1):
        if verbose:
            print(f"[{idx}/{len(word_list)}] Processing: {dutch_word} ({english_hint})")

        try:
            # Monolithic approach
            if verbose:
                print("  Running monolithic...")
            mono_start = datetime.now()
            mono_result = enrich_word(dutch_word, english_hint, model=model, return_usage=True)
            mono_enriched, mono_usage = mono_result
            mono_duration = (datetime.now() - mono_start).total_seconds()
            mono_cost = calculate_cost(mono_usage["prompt_tokens"], mono_usage["completion_tokens"])

            # Modular approach - Phase 1
            if verbose:
                print("  Running modular (Phase 1)...")
            phase1_start = datetime.now()
            modular_basic, phase1_usage = enrich_basic(dutch_word, english_hint, model=model, return_usage=True)
            phase1_duration = (datetime.now() - phase1_start).total_seconds()
            phase1_cost = calculate_cost(phase1_usage["prompt_tokens"], phase1_usage["completion_tokens"])

            # Modular approach - Phase 2 (if needed)
            phase2_cost = 0.0
            phase2_duration = 0.0

            if modular_basic.pos in [PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE]:
                if verbose:
                    print(f"  Running modular (Phase 2 - {modular_basic.pos})...")
                phase2_start = datetime.now()

                # Build prompt and call API for Phase 2
                client = get_client()

                if modular_basic.pos == PartOfSpeech.NOUN:
                    prompt = f"""For the Dutch noun "{modular_basic.lemma}" (English: "{modular_basic.translation}"), provide complete noun metadata.\n\n"""
                    prompt += format_prompt(NOUN_INSTRUCTIONS, n_examples=N_EXAMPLES) + "\n\n" + COMPLETENESS_REMINDER
                    from core.schemas import AINounEnrichment
                    completion = client.beta.chat.completions.parse(
                        model=model,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT_NOUN}, {"role": "user", "content": prompt}],
                        response_format=AINounEnrichment,
                    )
                elif modular_basic.pos == PartOfSpeech.VERB:
                    prompt = f"""For the Dutch verb "{modular_basic.lemma}" (English: "{modular_basic.translation}"), provide complete verb metadata.\n\n"""
                    prompt += format_prompt(VERB_INSTRUCTIONS, n_examples=N_EXAMPLES) + "\n\n" + COMPLETENESS_REMINDER
                    from core.schemas import AIVerbEnrichment
                    completion = client.beta.chat.completions.parse(
                        model=model,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT_VERB}, {"role": "user", "content": prompt}],
                        response_format=AIVerbEnrichment,
                    )
                elif modular_basic.pos == PartOfSpeech.ADJECTIVE:
                    prompt = f"""For the Dutch adjective "{modular_basic.lemma}" (English: "{modular_basic.translation}"), provide complete adjective metadata.\n\n"""
                    prompt += format_prompt(ADJECTIVE_INSTRUCTIONS, n_examples=N_EXAMPLES) + "\n\n" + COMPLETENESS_REMINDER
                    from core.schemas import AIAdjectiveEnrichment
                    completion = client.beta.chat.completions.parse(
                        model=model,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT_ADJECTIVE}, {"role": "user", "content": prompt}],
                        response_format=AIAdjectiveEnrichment,
                    )

                phase2_cost = calculate_cost(completion.usage.prompt_tokens, completion.usage.completion_tokens)
                phase2_duration = (datetime.now() - phase2_start).total_seconds()

            modular_total_cost = phase1_cost + phase2_cost
            modular_total_duration = phase1_duration + phase2_duration

            # Consistency checks
            lemma_match = mono_enriched.lemma == modular_basic.lemma
            pos_match = mono_enriched.pos == modular_basic.pos
            translation_match = mono_enriched.translation == modular_basic.translation

            # Collect results
            results.append({
                "dutch_word": dutch_word,
                "english_hint": english_hint,
                "lemma": modular_basic.lemma,
                "pos": str(modular_basic.pos),
                "model_used": model,
                "monolithic_cost": mono_cost,
                "modular_cost": modular_total_cost,
                "cost_difference": modular_total_cost - mono_cost,
                "cost_savings_pct": ((mono_cost - modular_total_cost) / mono_cost) * 100,
                "monolithic_time": mono_duration,
                "modular_time": modular_total_duration,
                "time_difference": modular_total_duration - mono_duration,
                "lemma_match": lemma_match,
                "pos_match": pos_match,
                "translation_match": translation_match,
                "timestamp": datetime.now().isoformat(),
            })

            if verbose:
                print(f"  ✓ Complete - Mono: ${mono_cost:.5f}, Modular: ${modular_total_cost:.5f}\n")

        except Exception as e:
            if verbose:
                print(f"  ✗ Error: {e}\n")
            results.append({
                "dutch_word": dutch_word,
                "english_hint": english_hint,
                "lemma": None,
                "pos": None,
                "model_used": model,
                "monolithic_cost": None,
                "modular_cost": None,
                "cost_difference": None,
                "cost_savings_pct": None,
                "monolithic_time": None,
                "modular_time": None,
                "time_difference": None,
                "lemma_match": None,
                "pos_match": None,
                "translation_match": None,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            })

    return pd.DataFrame(results)


def save_results(df: pd.DataFrame, filepath: str | Path) -> None:
    """
    Save comparison results to a pickle file.

    Args:
        df: DataFrame with comparison results
        filepath: Path to save the pickle file
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'wb') as f:
        pickle.dump(df, f)

    print(f"Saved {len(df)} results to {filepath}")


def load_results(filepath: str | Path) -> pd.DataFrame:
    """
    Load comparison results from a pickle file.

    Args:
        filepath: Path to the pickle file

    Returns:
        DataFrame with comparison results
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Results file not found: {filepath}")

    with open(filepath, 'rb') as f:
        df = pickle.load(f)

    print(f"Loaded {len(df)} results from {filepath}")
    return df


def merge_results(df1: pd.DataFrame, df2: pd.DataFrame, drop_duplicates: bool = True) -> pd.DataFrame:
    """
    Merge two result DataFrames.

    Args:
        df1: First DataFrame
        df2: Second DataFrame
        drop_duplicates: If True, drop duplicate (dutch_word, english_hint, model_used) rows,
                        keeping the most recent timestamp

    Returns:
        Merged DataFrame
    """
    merged = pd.concat([df1, df2], ignore_index=True)

    if drop_duplicates:
        # Sort by timestamp (most recent first), then drop duplicates
        merged = merged.sort_values('timestamp', ascending=False)
        merged = merged.drop_duplicates(subset=['dutch_word', 'english_hint', 'model_used'], keep='first')
        merged = merged.sort_index().reset_index(drop=True)

    return merged


def load_or_create(filepath: str | Path) -> pd.DataFrame:
    """
    Load results if file exists, otherwise return empty DataFrame.

    Args:
        filepath: Path to the pickle file

    Returns:
        DataFrame with comparison results (empty if file doesn't exist)
    """
    filepath = Path(filepath)

    if filepath.exists():
        return load_results(filepath)
    else:
        print(f"No existing results found at {filepath}, starting fresh")
        return pd.DataFrame()
