"""
Test enrichment for a single word to see full AI output.

This helps debug why certain fields might be missing.

Usage:
    python -m scripts.maintenance.test_single_word tevreden "satisfied"
"""

import sys
import json

from scripts.enrichment.enrich_lexicon import enrich_word


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.maintenance.test_single_word <dutch_word> [english_hint]")
        print("Example: python -m scripts.maintenance.test_single_word tevreden satisfied")
        sys.exit(1)

    dutch = sys.argv[1]
    english = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Testing enrichment for: {dutch}" + (f" ({english})" if english else ""))
    print("=" * 80)
    print()

    try:
        result = enrich_word(dutch, english)

        # Print full JSON output
        print("FULL AI RESPONSE:")
        print("=" * 80)
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
        print("=" * 80)
        print()

        # Highlight specific fields
        print("KEY FIELDS:")
        print("-" * 80)
        print(f"Lemma:       {result.lemma}")
        print(f"POS:         {result.pos}")
        print(f"Translation: {result.translation}")
        print(f"Difficulty:  {result.difficulty}")
        print(f"Tags:        {result.tags}")
        print()

        # Check for POS-specific metadata
        if result.pos == "adjective" and result.adjective_meta:
            print("ADJECTIVE METADATA:")
            print("-" * 80)
            print(f"Comparative: {result.adjective_meta.comparative}")
            print(f"Superlative: {result.adjective_meta.superlative}")
            print(f"Examples:    {len(result.adjective_meta.examples_base)} base, "
                  f"{len(result.adjective_meta.examples_comparative)} comparative, "
                  f"{len(result.adjective_meta.examples_superlative)} superlative")
        elif result.pos == "verb" and result.verb_meta:
            print("VERB METADATA:")
            print("-" * 80)
            print(f"Past Singular:  {result.verb_meta.past_singular}")
            print(f"Past Plural:    {result.verb_meta.past_plural}")
            print(f"Participle:     {result.verb_meta.past_participle}")
            print(f"Auxiliary:      {result.verb_meta.auxiliary}")
            print(f"Reflexive:      {result.verb_meta.is_reflexive}")
            print(f"Irregular Past: {result.verb_meta.is_irregular_past}")
            print(f"Irregular Part: {result.verb_meta.is_irregular_participle}")
            if result.verb_meta.common_prepositions:
                print(f"Prepositions:   {', '.join(result.verb_meta.common_prepositions)}")
        elif result.pos == "noun" and result.noun_meta:
            print("NOUN METADATA:")
            print("-" * 80)
            print(f"Article:     {result.noun_meta.article}")
            print(f"Plural:      {result.noun_meta.plural}")
            print(f"Diminutive:  {result.noun_meta.diminutive}")

        print()
        print("✓ Enrichment test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
