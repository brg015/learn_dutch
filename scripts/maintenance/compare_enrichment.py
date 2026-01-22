"""
Compare monolithic vs modular enrichment approaches.

This script enriches the same words using both approaches and displays
the results side-by-side for comparison of quality, cost, and completeness.

Usage:
    python -m scripts.maintenance.compare_enrichment <dutch_word> [english_hint]

Example:
    python -m scripts.maintenance.compare_enrichment lopen "to walk"
    python -m scripts.maintenance.compare_enrichment praten "to talk"
"""

import sys
import json
from datetime import datetime

from scripts.enrichment.enrich_lexicon import enrich_word as enrich_monolithic
from scripts.enrichment.enrich_modular import enrich_basic, enrich_pos


def format_metadata(data: dict, indent: int = 2) -> str:
    """Format metadata dict for display."""
    return json.dumps(data, indent=indent, ensure_ascii=False)


def compare_enrichment(dutch: str, english: str = None):
    """
    Enrich the same word using both approaches and compare results.

    Args:
        dutch: Dutch word to enrich
        english: Optional English translation hint
    """
    print("=" * 80)
    print(f"COMPARISON: {dutch}" + (f" ({english})" if english else ""))
    print("=" * 80)
    print()

    # ---- Monolithic Approach ----
    print("APPROACH 1: MONOLITHIC (Single API Call)")
    print("-" * 80)

    monolithic_start = datetime.now()
    try:
        monolithic_result = enrich_monolithic(dutch, english)
        monolithic_duration = (datetime.now() - monolithic_start).total_seconds()

        print(f"✓ Enrichment completed in {monolithic_duration:.2f}s")
        print()
        print("Basic Info:")
        print(f"  Lemma:       {monolithic_result.lemma}")
        print(f"  POS:         {monolithic_result.pos}")
        print(f"  Translation: {monolithic_result.translation}")
        print(f"  Difficulty:  {monolithic_result.difficulty}")
        print(f"  Tags:        {monolithic_result.tags}")
        print(f"  Sense:       {monolithic_result.sense or 'None'}")
        print()

        # POS-specific metadata
        if monolithic_result.noun_meta:
            print("Noun Metadata:")
            print(format_metadata(monolithic_result.noun_meta.model_dump()))
        elif monolithic_result.verb_meta:
            print("Verb Metadata:")
            print(format_metadata(monolithic_result.verb_meta.model_dump()))
        elif monolithic_result.adjective_meta:
            print("Adjective Metadata:")
            print(format_metadata(monolithic_result.adjective_meta.model_dump()))

        print()
        print(f"General Examples: {len(monolithic_result.general_examples)}")
        for i, ex in enumerate(monolithic_result.general_examples, 1):
            print(f"  {i}. NL: {ex.dutch}")
            print(f"     EN: {ex.english}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print()

    # ---- Modular Approach ----
    print("APPROACH 2: MODULAR (Two-Phase)")
    print("-" * 80)

    # Phase 1
    print("Phase 1: Basic Enrichment")
    phase1_start = datetime.now()
    try:
        modular_basic = enrich_basic(dutch, english)
        phase1_duration = (datetime.now() - phase1_start).total_seconds()

        print(f"✓ Phase 1 completed in {phase1_duration:.2f}s")
        print()
        print("Basic Info:")
        print(f"  Lemma:       {modular_basic.lemma}")
        print(f"  POS:         {modular_basic.pos}")
        print(f"  Translation: {modular_basic.translation}")
        print(f"  Difficulty:  {modular_basic.difficulty}")
        print(f"  Tags:        {modular_basic.tags}")
        print(f"  Sense:       {modular_basic.sense or 'None'}")
        print()
        print(f"General Examples: {len(modular_basic.general_examples)}")
        for i, ex in enumerate(modular_basic.general_examples, 1):
            print(f"  {i}. NL: {ex.dutch}")
            print(f"     EN: {ex.english}")
        print()

    except Exception as e:
        print(f"✗ Phase 1 Error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Phase 2
    print("Phase 2: POS-Specific Enrichment")
    phase2_start = datetime.now()
    modular_pos_meta = None
    phase2_duration = 0

    if modular_basic.pos in ["noun", "verb", "adjective"]:
        try:
            modular_pos_meta = enrich_pos(
                modular_basic.lemma,
                modular_basic.pos,
                modular_basic.translation
            )
            phase2_duration = (datetime.now() - phase2_start).total_seconds()

            print(f"✓ Phase 2 completed in {phase2_duration:.2f}s")
            print()

            if modular_basic.pos == "noun":
                print("Noun Metadata:")
                print(format_metadata(modular_pos_meta.model_dump()))
            elif modular_basic.pos == "verb":
                print("Verb Metadata:")
                print(format_metadata(modular_pos_meta.model_dump()))
            elif modular_basic.pos == "adjective":
                print("Adjective Metadata:")
                print(format_metadata(modular_pos_meta.model_dump()))

        except Exception as e:
            print(f"✗ Phase 2 Error: {e}")
            import traceback
            traceback.print_exc()
            return
    else:
        print(f"  POS '{modular_basic.pos}' does not need Phase 2")

    modular_total_duration = phase1_duration + phase2_duration

    print()
    print()

    # ---- Comparison Summary ----
    print("=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print()

    # Timing
    print("TIMING:")
    print(f"  Monolithic: {monolithic_duration:.2f}s (1 API call)")
    print(f"  Modular:    {modular_total_duration:.2f}s (Phase 1: {phase1_duration:.2f}s + Phase 2: {phase2_duration:.2f}s)")
    print(f"  Difference: {modular_total_duration - monolithic_duration:+.2f}s")
    print()

    # Basic info comparison
    print("BASIC INFO COMPARISON:")
    print(f"  Lemma:       Mono: {monolithic_result.lemma:20s} | Modular: {modular_basic.lemma}")
    print(f"  POS:         Mono: {monolithic_result.pos:20s} | Modular: {modular_basic.pos}")
    print(f"  Translation: Mono: {monolithic_result.translation:20s} | Modular: {modular_basic.translation}")
    print(f"  Difficulty:  Mono: {monolithic_result.difficulty:20s} | Modular: {modular_basic.difficulty}")

    lemma_match = monolithic_result.lemma == modular_basic.lemma
    pos_match = monolithic_result.pos == modular_basic.pos
    trans_match = monolithic_result.translation == modular_basic.translation
    diff_match = monolithic_result.difficulty == modular_basic.difficulty

    print()
    print("CONSISTENCY:")
    print(f"  Lemma:       {'✓ Match' if lemma_match else '✗ Different'}")
    print(f"  POS:         {'✓ Match' if pos_match else '✗ Different'}")
    print(f"  Translation: {'✓ Match' if trans_match else '✗ Different'}")
    print(f"  Difficulty:  {'✓ Match' if diff_match else '✗ Different'}")
    print()

    # POS metadata comparison (if applicable)
    if monolithic_result.pos in ["noun", "verb", "adjective"]:
        print("POS METADATA:")
        print(f"  Both approaches produced {monolithic_result.pos} metadata")

        if monolithic_result.pos == "noun":
            mono_meta = monolithic_result.noun_meta
            mod_meta = modular_pos_meta
            print(f"  Article:    Mono: {mono_meta.article:10s} | Modular: {mod_meta.article}")
            print(f"  Plural:     Mono: {mono_meta.plural:10s} | Modular: {mod_meta.plural}")

        elif monolithic_result.pos == "verb":
            mono_meta = monolithic_result.verb_meta
            mod_meta = modular_pos_meta
            print(f"  Past:       Mono: {mono_meta.past_singular:10s} | Modular: {mod_meta.past_singular}")
            print(f"  Participle: Mono: {mono_meta.past_participle:10s} | Modular: {mod_meta.past_participle}")
            print(f"  Auxiliary:  Mono: {str(mono_meta.auxiliary):10s} | Modular: {mod_meta.auxiliary}")

        elif monolithic_result.pos == "adjective":
            mono_meta = monolithic_result.adjective_meta
            mod_meta = modular_pos_meta
            print(f"  Comparative: Mono: {mono_meta.comparative:10s} | Modular: {mod_meta.comparative}")
            print(f"  Superlative: Mono: {mono_meta.superlative:10s} | Modular: {mod_meta.superlative}")

        print()

    print("RECOMMENDATION:")
    if modular_total_duration < monolithic_duration * 1.5:
        print("  ✓ Modular approach is competitive on latency")
    else:
        print("  ⚠ Modular approach is significantly slower")

    if lemma_match and pos_match and trans_match:
        print("  ✓ Both approaches produce consistent basic info")
    else:
        print("  ⚠ Approaches produce different basic info - review carefully")

    print()
    print("For cost comparison, check OpenAI usage logs:")
    print("  - Monolithic uses 1 large call (~2500 input tokens)")
    print("  - Modular uses 2 smaller calls (~800 + ~1000 input tokens)")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.maintenance.compare_enrichment <dutch_word> [english_hint]")
        print("Example: python -m scripts.maintenance.compare_enrichment lopen 'to walk'")
        sys.exit(1)

    dutch = sys.argv[1]
    english = sys.argv[2] if len(sys.argv) > 2 else None

    compare_enrichment(dutch, english)


if __name__ == "__main__":
    main()
