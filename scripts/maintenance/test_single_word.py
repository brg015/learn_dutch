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
from core.schemas import PartOfSpeech, AIEnrichedEntry


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
        noun_meta = None
        verb_meta = None
        adjective_meta = None

        if basic_enriched.pos in [PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE]:
            print(f"PHASE 2: {basic_enriched.pos} enrichment...")
            print("-" * 80)
            pos_metadata = enrich_pos(basic_enriched.lemma, basic_enriched.pos, basic_enriched.translation)

            print(json.dumps(pos_metadata.model_dump(), indent=2, ensure_ascii=False))
            print()
            print(f"✓ Phase 2 complete")
            print()

            # Assign to correct field
            if basic_enriched.pos == PartOfSpeech.NOUN:
                noun_meta = pos_metadata
            elif basic_enriched.pos == PartOfSpeech.VERB:
                verb_meta = pos_metadata
            elif basic_enriched.pos == PartOfSpeech.ADJECTIVE:
                adjective_meta = pos_metadata
        else:
            print(f"→ Phase 2 skipped (POS '{basic_enriched.pos}' doesn't need it)")
            print()

        # Combine into full AIEnrichedEntry format
        result = AIEnrichedEntry(
            lemma=basic_enriched.lemma,
            pos=basic_enriched.pos,
            sense=basic_enriched.sense,
            translation=basic_enriched.translation,
            definition=basic_enriched.definition,
            difficulty=basic_enriched.difficulty,
            tags=basic_enriched.tags,
            general_examples=basic_enriched.general_examples,
            noun_meta=noun_meta,
            verb_meta=verb_meta,
            adjective_meta=adjective_meta,
        )

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
            if result.adjective_meta.fixed_prepositions:
                print(f"Fixed Prepositions: {len(result.adjective_meta.fixed_prepositions)}")
                for prep in result.adjective_meta.fixed_prepositions:
                    print(f"  - {prep.preposition} ({prep.usage_frequency})")
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
            if result.verb_meta.preposition_usage:
                print(f"Prepositional Uses: {len(result.verb_meta.preposition_usage)}")
                for prep_use in result.verb_meta.preposition_usage:
                    print(f"  - {prep_use.preposition}: {prep_use.meaning}")
        elif result.pos == "noun" and result.noun_meta:
            print("NOUN METADATA:")
            print("-" * 80)
            print(f"Article:     {result.noun_meta.article}")
            print(f"Plural:      {result.noun_meta.plural}")
            print(f"Diminutive:  {result.noun_meta.diminutive}")
            if result.noun_meta.fixed_prepositions:
                print(f"Fixed Prepositions: {len(result.noun_meta.fixed_prepositions)}")
                for prep in result.noun_meta.fixed_prepositions:
                    print(f"  - {prep.preposition} ({prep.usage_frequency})")

        print()
        print("✓ Enrichment test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
