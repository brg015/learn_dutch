"""
Check enrichment results in MongoDB.

This script displays enriched words with their metadata to verify
AI enrichment quality before scaling up batch processing.

Usage:
    # Check all enriched words
    python -m scripts.maintenance.check_enrichment

    # Check specific number of words
    python -m scripts.maintenance.check_enrichment --limit 5

    # Check specific word
    python -m scripts.maintenance.check_enrichment --lemma "lopen"
"""

import argparse
from typing import Optional

from core import lexicon_repo


def format_examples(examples: list, indent: str = "      ") -> str:
    """Format bilingual examples for display."""
    if not examples:
        return f"{indent}(no examples)"

    lines = []
    for i, ex in enumerate(examples, 1):
        lines.append(f"{indent}{i}. NL: {ex.get('dutch', 'N/A')}")
        lines.append(f"{indent}   EN: {ex.get('english', 'N/A')}")
    return "\n".join(lines)


def display_word(word: dict) -> None:
    """Display a single enriched word with all metadata."""
    print("=" * 80)
    print(f"LEMMA: {word.get('lemma', 'N/A')}")
    print(f"POS: {word.get('pos', 'N/A')}")
    if word.get('sense'):
        print(f"SENSE: {word['sense']}")
    print("-" * 80)

    # Translation and definition
    print(f"TRANSLATION: {word.get('translation', 'N/A')}")
    if word.get('definition'):
        print(f"DEFINITION: {word['definition']}")

    # Metadata
    print(f"DIFFICULTY: {word.get('difficulty', 'unknown')}")
    tags = word.get('tags', [])
    if tags:
        print(f"TAGS: {', '.join(tags)}")

    # POS-specific metadata
    pos = word.get('pos')

    if pos == 'noun' and word.get('noun_meta'):
        meta = word['noun_meta']
        print("\n  NOUN METADATA:")
        print(f"    Article: {meta.get('article', 'N/A')}")
        print(f"    Plural: {meta.get('plural', 'N/A')}")
        if meta.get('diminutive'):
            print(f"    Diminutive: {meta['diminutive']}")

        if meta.get('examples_singular'):
            print("\n    Examples (Singular):")
            print(format_examples(meta['examples_singular']))
        if meta.get('examples_plural'):
            print("\n    Examples (Plural):")
            print(format_examples(meta['examples_plural']))

    elif pos == 'verb' and word.get('verb_meta'):
        meta = word['verb_meta']
        print("\n  VERB METADATA:")
        print(f"    Past Singular: {meta.get('past_singular', 'N/A')}")
        print(f"    Past Plural: {meta.get('past_plural', 'N/A')}")
        print(f"    Past Participle: {meta.get('past_participle', 'N/A')}")
        print(f"    Auxiliary: {meta.get('auxiliary', 'N/A')}")

        if meta.get('is_reflexive'):
            print(f"    Reflexive: Yes (zich {word.get('lemma')})")

        if meta.get('separable'):
            print(f"    Separable: Yes")
            if meta.get('separable_prefix'):
                print(f"    Prefix: {meta['separable_prefix']}")

        # Irregularity flags
        if meta.get('is_irregular_past'):
            print("    ⚠ Irregular past tense")
        if meta.get('is_irregular_participle'):
            print("    ⚠ Irregular participle")

        # Prepositions
        if meta.get('common_prepositions'):
            print(f"    Prepositions: {', '.join(meta['common_prepositions'])}")

        # Preposition-grouped examples (new format - list of objects)
        if meta.get('preposition_examples'):
            print("\n    Examples by Preposition:")
            for prep_obj in meta['preposition_examples']:
                prep = prep_obj.get('preposition', 'N/A')
                examples = prep_obj.get('examples', [])
                print(f"\n      [{prep}]")
                for i, ex in enumerate(examples, 1):
                    print(f"        {i}. NL: {ex.get('dutch', 'N/A')}")
                    print(f"           EN: {ex.get('english', 'N/A')}")

        # Regular tense examples
        if meta.get('examples_present'):
            print("\n    Examples (Present):")
            print(format_examples(meta['examples_present']))
        if meta.get('examples_past'):
            print("\n    Examples (Past):")
            print(format_examples(meta['examples_past']))
        if meta.get('examples_perfect'):
            print("\n    Examples (Perfect):")
            print(format_examples(meta['examples_perfect']))

    elif pos == 'adjective' and word.get('adjective_meta'):
        meta = word['adjective_meta']
        print("\n  ADJECTIVE METADATA:")
        print(f"    Comparative: {meta.get('comparative', 'N/A')}")
        print(f"    Superlative: {meta.get('superlative', 'N/A')}")

        # Irregularity flags
        if meta.get('is_irregular_comparative'):
            print("    ⚠ Irregular comparative")
        if meta.get('is_irregular_superlative'):
            print("    ⚠ Irregular superlative")

        if meta.get('examples_base'):
            print("\n    Examples (Base):")
            print(format_examples(meta['examples_base']))
        if meta.get('examples_comparative'):
            print("\n    Examples (Comparative):")
            print(format_examples(meta['examples_comparative']))
        if meta.get('examples_superlative'):
            print("\n    Examples (Superlative):")
            print(format_examples(meta['examples_superlative']))

    elif word.get('general_examples'):
        print("\n  EXAMPLES:")
        print(format_examples(word['general_examples'], indent="    "))

    # Enrichment metadata
    word_enrich = word.get('word_enrichment', {})
    pos_enrich = word.get('pos_enrichment', {})

    if word_enrich.get('enriched') or pos_enrich.get('enriched'):
        print(f"\n  ENRICHMENT:")

        if word_enrich.get('enriched'):
            print(f"    Phase 1 (Word): ✓")
            print(f"      Model: {word_enrich.get('model_used', 'N/A')}")
            print(f"      Version: {word_enrich.get('version', 1)}")
            if word_enrich.get('lemma_normalized'):
                print(f"      ⚠ Lemma normalized from: {word.get('import_data', {}).get('imported_word', 'N/A')}")
            if word_enrich.get('approved'):
                print(f"      ✓ Approved")

        if pos_enrich.get('enriched'):
            print(f"    Phase 2 (POS): ✓")
            print(f"      Model: {pos_enrich.get('model_used', 'N/A')}")
            print(f"      Version: {pos_enrich.get('version', 1)}")
            if pos_enrich.get('approved'):
                print(f"      ✓ Approved")

    print("=" * 80)
    print()


def main():
    parser = argparse.ArgumentParser(description="Check enrichment results in MongoDB")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of words to display (default: all)"
    )
    parser.add_argument(
        "--lemma",
        type=str,
        default=None,
        help="Check specific lemma (e.g., 'lopen')"
    )
    parser.add_argument(
        "--pos",
        type=str,
        default=None,
        help="Filter by part of speech (noun, verb, adjective, etc.)"
    )

    args = parser.parse_args()

    # Build query
    query = {"word_enrichment.enriched": True}
    if args.lemma:
        query["lemma"] = args.lemma
    if args.pos:
        query["pos"] = args.pos

    # Fetch words
    collection = lexicon_repo.get_collection()
    words = list(collection.find(query).sort("lemma", 1))

    if not words:
        print("No enriched words found.")
        if args.lemma:
            print(f"(lemma: {args.lemma})")
        if args.pos:
            print(f"(pos: {args.pos})")
        return

    # Apply limit
    if args.limit:
        words = words[:args.limit]

    # Display summary
    print(f"\nFound {len(words)} enriched word(s)")
    if args.limit and len(words) < args.limit:
        print(f"(showing all {len(words)})")
    elif args.limit:
        print(f"(showing first {args.limit})")
    print()

    # Display each word
    for word in words:
        display_word(word)


if __name__ == "__main__":
    main()
