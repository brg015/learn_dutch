"""
Test enrichment for a single word to see full AI output (modular approach).

This helps debug why certain fields might be missing.
Uses the two-phase modular enrichment (Phase 1: basic, Phase 2: POS-specific).

Usage:
    python -m scripts.maintenance.test_single_word tevreden "satisfied"
"""

import sys
import json

from scripts.enrichment.enrich_modular import enrich_basic, enrich_pos
from core.schemas import PartOfSpeech


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.maintenance.test_single_word <dutch_word> [english_hint]")
        print("Example: python -m scripts.maintenance.test_single_word tevreden satisfied")
        sys.exit(1)

    dutch = sys.argv[1]
    english = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Testing modular enrichment for: {dutch}" + (f" ({english})" if english else ""))
    print("=" * 80)
    print()

    try:
        # Phase 1: Basic enrichment
        print("PHASE 1: Basic enrichment...")
        print("-" * 80)
        basic_enriched = enrich_basic(dutch, english)

        print(json.dumps(basic_enriched.model_dump(), indent=2, ensure_ascii=False))
        print()
        print(f"✓ Phase 1 complete - Lemma: {basic_enriched.lemma}, POS: {basic_enriched.pos}")
        print()

        # Phase 2: POS-specific enrichment (if applicable)
        pos_metadata = None

        if basic_enriched.pos in [PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE]:
            print(f"PHASE 2: {basic_enriched.pos} enrichment...")
            print("-" * 80)
            pos_metadata = enrich_pos(basic_enriched.lemma, basic_enriched.pos, basic_enriched.translation)

            print(json.dumps(pos_metadata.model_dump(), indent=2, ensure_ascii=False))
            print()
            print(f"✓ Phase 2 complete")
            print()
        else:
            print(f"→ Phase 2 skipped (POS '{basic_enriched.pos}' doesn't need it)")
            print()

        # Highlight specific fields
        print("KEY FIELDS (Phase 1):")
        print("-" * 80)
        print(f"Lemma:       {basic_enriched.lemma}")
        print(f"POS:         {basic_enriched.pos}")
        print(f"Translation: {basic_enriched.translation}")
        print(f"Definition:  {basic_enriched.definition}")
        print(f"Difficulty:  {basic_enriched.difficulty}")
        print(f"Tags:        {basic_enriched.tags}")
        print(f"Examples:    {len(basic_enriched.general_examples)}")
        print()

        # Check for POS-specific metadata
        if pos_metadata:
            if basic_enriched.pos == PartOfSpeech.ADJECTIVE:
                print("ADJECTIVE METADATA (Phase 2):")
                print("-" * 80)
                adj_meta = pos_metadata.adjective_meta
                print(f"Comparative: {adj_meta.comparative}")
                print(f"Superlative: {adj_meta.superlative}")
                print(f"Irregular Comparative: {adj_meta.is_irregular_comparative}")
                print(f"Irregular Superlative: {adj_meta.is_irregular_superlative}")
                if adj_meta.fixed_prepositions:
                    print(f"Fixed Prepositions: {len(adj_meta.fixed_prepositions)}")
                    for prep in adj_meta.fixed_prepositions:
                        print(f"  - {prep.preposition} ({prep.usage_frequency}): {prep.meaning_context or 'N/A'}")
                print(f"Examples:    {len(adj_meta.examples_base)} base, "
                      f"{len(adj_meta.examples_comparative)} comparative, "
                      f"{len(adj_meta.examples_superlative)} superlative")
            elif basic_enriched.pos == PartOfSpeech.VERB:
                print("VERB METADATA (Phase 2):")
                print("-" * 80)
                verb_meta = pos_metadata.verb_meta
                print(f"Past Singular:  {verb_meta.past_singular}")
                print(f"Past Plural:    {verb_meta.past_plural}")
                print(f"Participle:     {verb_meta.past_participle}")
                print(f"Auxiliary:      {verb_meta.auxiliary}")
                print(f"Separable:      {verb_meta.separable}")
                if verb_meta.separable:
                    print(f"Prefix:         {verb_meta.separable_prefix}")
                print(f"Reflexive:      {verb_meta.is_reflexive}")
                print(f"Irregular Past: {verb_meta.is_irregular_past}")
                print(f"Irregular Part: {verb_meta.is_irregular_participle}")
                if verb_meta.preposition_usage:
                    print(f"Prepositional Uses: {len(verb_meta.preposition_usage)}")
                    for prep_use in verb_meta.preposition_usage:
                        print(f"  - {prep_use.preposition}: {prep_use.meaning}")
                        print(f"    Examples: {len(prep_use.examples)}")
            elif basic_enriched.pos == PartOfSpeech.NOUN:
                print("NOUN METADATA (Phase 2):")
                print("-" * 80)
                noun_meta = pos_metadata.noun_meta
                print(f"Article:     {noun_meta.article}")
                print(f"Plural:      {noun_meta.plural}")
                print(f"Diminutive:  {noun_meta.diminutive}")
                if noun_meta.fixed_prepositions:
                    print(f"Fixed Prepositions: {len(noun_meta.fixed_prepositions)}")
                    for prep in noun_meta.fixed_prepositions:
                        print(f"  - {prep.preposition} ({prep.usage_frequency}): {prep.meaning_context or 'N/A'}")
                print(f"Examples:    {len(noun_meta.examples_singular)} singular, "
                      f"{len(noun_meta.examples_plural)} plural")

        print()
        print("✓ Enrichment test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
