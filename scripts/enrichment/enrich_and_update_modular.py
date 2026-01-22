"""
Enrich existing MongoDB lexicon entries with AI-generated metadata (modular approach).

This script uses a two-phase enrichment process:
1. Phase 1: Basic word info (lemma, POS, translation, definition, etc.)
2. Phase 2: POS-specific metadata (only for nouns, verbs, adjectives)

Advantages over monolithic approach:
- More cost-efficient (words without POS metadata skip Phase 2)
- Selective re-enrichment (re-run only Phase 2 for specific POS)
- Cleaner, more focused prompts

Usage:
    # Enrich all unenriched words (both phases)
    python -m scripts.enrichment.enrich_and_update_modular [--batch-size N] [--dry-run]

    # Only run Phase 1 (basic enrichment)
    python -m scripts.enrichment.enrich_and_update_modular --phase 1

    # Only run Phase 2 for words that have Phase 1 but not Phase 2
    python -m scripts.enrichment.enrich_and_update_modular --phase 2

    # Enrich only words with specific tag
    python -m scripts.enrichment.enrich_and_update_modular --user-tag "Chapter 10"
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Optional, Literal

from dotenv import load_dotenv
from pymongo import MongoClient

from scripts.enrichment.enrich_modular import enrich_basic, enrich_pos
from core.schemas import PartOfSpeech

# Load environment
load_dotenv()

# Configuration
DB_NAME = "dutch_trainer"
COLLECTION_NAME = "lexicon"


def enrich_and_update_modular(
    user_tag_filter: Optional[str] = None,
    batch_size: Optional[int] = None,
    dry_run: bool = False,
    model: str = "gpt-4o-2024-08-06",
    phase: Optional[Literal[1, 2]] = None
) -> None:
    """
    Enrich existing MongoDB entries with AI metadata (modular approach).

    Args:
        user_tag_filter: Only enrich words with this user_tag (None = all)
        batch_size: Maximum number of words to enrich (None = all)
        dry_run: If True, don't actually update MongoDB
        model: OpenAI model to use for enrichment
        phase: If specified, only run Phase 1 or Phase 2 (None = both)
    """

    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI not found in environment variables")

    print(f"Connecting to MongoDB...")
    client = MongoClient(mongo_uri)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Verify connection
    client.admin.command("ping")
    print(f"✓ Connected to MongoDB: {DB_NAME}.{COLLECTION_NAME}\n")

    # Determine which phase(s) to run
    run_phase1 = phase is None or phase == 1
    run_phase2 = phase is None or phase == 2

    # Track statistics
    stats = {
        "phase1_success": 0,
        "phase1_error": 0,
        "phase1_skipped": 0,
        "phase2_success": 0,
        "phase2_error": 0,
        "phase2_skipped": 0,
    }

    # ---- PHASE 1: Basic Enrichment ----
    if run_phase1:
        print(f"{'='*60}")
        print("PHASE 1: Basic Enrichment")
        print(f"{'='*60}\n")

        # Build query for Phase 1 (unenriched words)
        query = {
            "enrichment.word_enriched": False,
            "$or": [
                {"entry_type": {"$exists": False}},
                {"entry_type": "word"}
            ]
        }

        if user_tag_filter:
            query["user_tags"] = user_tag_filter
            print(f"Filter: user_tag = '{user_tag_filter}'")

        cursor = collection.find(query)
        if batch_size:
            cursor = cursor.limit(batch_size)
            print(f"Batch size limit: {batch_size}")

        words = list(cursor)

        if len(words) == 0:
            print("No words need Phase 1 enrichment\n")
        else:
            print(f"Found {len(words)} words needing Phase 1 enrichment\n")

            for idx, doc in enumerate(words, 1):
                # Get import data (fallback to lemma/translation)
                if doc.get("import_data"):
                    dutch = doc["import_data"]["imported_word"]
                    english = doc["import_data"]["imported_translation"]
                else:
                    dutch = doc.get("lemma", "")
                    english = doc.get("translation", "")

                print(f"\n[{idx}/{len(words)}] Phase 1: {dutch} ({english})")

                try:
                    # Check if already enriched (shouldn't happen, but safety check)
                    if doc.get("enrichment", {}).get("word_enriched"):
                        stats["phase1_skipped"] += 1
                        print(f"  ⚠ Skipped - already has Phase 1 enrichment")
                        continue

                    # Enrich with AI (Phase 1)
                    print(f"  Enriching with AI...")
                    basic = enrich_basic(dutch, english, model=model)
                    print(f"  ✓ AI enriched - POS: {basic.pos}, Difficulty: {basic.difficulty}")

                    # Check if lemma was normalized
                    lemma_normalized = basic.lemma.lower() != dutch.lower()
                    if lemma_normalized:
                        print(f"  → Lemma normalized: '{dutch}' → '{basic.lemma}'")

                    # Prepare update
                    update_doc = {
                        "$set": {
                            "lemma": basic.lemma,
                            "pos": basic.pos,
                            "sense": basic.sense,
                            "translation": basic.translation,
                            "definition": basic.definition,
                            "difficulty": basic.difficulty,
                            "tags": basic.tags,
                            "general_examples": [ex.model_dump() for ex in basic.general_examples],

                            # Phase 1 enrichment metadata
                            "enrichment.word_enriched": True,
                            "enrichment.word_enriched_at": datetime.now(timezone.utc),
                            "enrichment.word_model": model,
                            "enrichment.word_version": doc.get("enrichment", {}).get("word_version", 1),
                            "enrichment.lemma_normalized": lemma_normalized,
                        }
                    }

                    if not dry_run:
                        collection.update_one({"_id": doc["_id"]}, update_doc)

                    stats["phase1_success"] += 1
                    print(f"  ✓ {'[DRY RUN] Would update' if dry_run else 'Updated'} Phase 1 in MongoDB")

                except Exception as e:
                    stats["phase1_error"] += 1
                    print(f"  ✗ Error: {e}")

        print(f"\nPhase 1 Summary:")
        print(f"  Success: {stats['phase1_success']}")
        print(f"  Skipped: {stats['phase1_skipped']}")
        print(f"  Errors:  {stats['phase1_error']}")
        print()

    # ---- PHASE 2: POS-Specific Enrichment ----
    if run_phase2:
        print(f"{'='*60}")
        print("PHASE 2: POS-Specific Enrichment")
        print(f"{'='*60}\n")

        # Build query for Phase 2 (words with Phase 1 but not Phase 2)
        query = {
            "enrichment.word_enriched": True,
            "enrichment.pos_enriched": False,
            "pos": {"$in": ["noun", "verb", "adjective"]},
            "$or": [
                {"entry_type": {"$exists": False}},
                {"entry_type": "word"}
            ]
        }

        if user_tag_filter:
            query["user_tags"] = user_tag_filter

        cursor = collection.find(query)
        if batch_size and run_phase1:
            # If we ran Phase 1, respect the same batch size
            cursor = cursor.limit(batch_size)

        words = list(cursor)

        if len(words) == 0:
            print("No words need Phase 2 enrichment\n")
        else:
            print(f"Found {len(words)} words needing Phase 2 enrichment\n")

            for idx, doc in enumerate(words, 1):
                lemma = doc["lemma"]
                pos = doc["pos"]
                translation = doc["translation"]

                print(f"\n[{idx}/{len(words)}] Phase 2: {lemma} ({pos})")

                try:
                    # Enrich with AI (Phase 2)
                    print(f"  Enriching {pos} metadata...")
                    pos_meta = enrich_pos(lemma, PartOfSpeech(pos), translation, model=model)

                    if pos_meta is None:
                        stats["phase2_skipped"] += 1
                        print(f"  ⚠ POS '{pos}' doesn't need Phase 2")
                        continue

                    print(f"  ✓ AI enriched {pos} metadata")

                    # Prepare update
                    update_doc = {
                        "$set": {
                            # Phase 2 enrichment metadata
                            "enrichment.pos_enriched": True,
                            "enrichment.pos_enriched_at": datetime.now(timezone.utc),
                            "enrichment.pos_model": model,
                            "enrichment.pos_version": doc.get("enrichment", {}).get("pos_version", 1),
                        }
                    }

                    # Add POS-specific metadata
                    if pos == "noun":
                        update_doc["$set"]["noun_meta"] = pos_meta.model_dump()
                    elif pos == "verb":
                        update_doc["$set"]["verb_meta"] = pos_meta.model_dump()
                    elif pos == "adjective":
                        update_doc["$set"]["adjective_meta"] = pos_meta.model_dump()

                    if not dry_run:
                        collection.update_one({"_id": doc["_id"]}, update_doc)

                    stats["phase2_success"] += 1
                    print(f"  ✓ {'[DRY RUN] Would update' if dry_run else 'Updated'} Phase 2 in MongoDB")

                except Exception as e:
                    stats["phase2_error"] += 1
                    print(f"  ✗ Error: {e}")

        print(f"\nPhase 2 Summary:")
        print(f"  Success: {stats['phase2_success']}")
        print(f"  Skipped: {stats['phase2_skipped']}")
        print(f"  Errors:  {stats['phase2_error']}")
        print()

    # Overall summary
    print(f"{'='*60}")
    print("Overall Summary")
    print(f"{'='*60}")
    print(f"Phase 1 - Success: {stats['phase1_success']}, Skipped: {stats['phase1_skipped']}, Errors: {stats['phase1_error']}")
    print(f"Phase 2 - Success: {stats['phase2_success']}, Skipped: {stats['phase2_skipped']}, Errors: {stats['phase2_error']}")
    print(f"Total   - Success: {stats['phase1_success'] + stats['phase2_success']}, Errors: {stats['phase1_error'] + stats['phase2_error']}")

    if dry_run:
        print("\n⚠ DRY RUN MODE - No changes were made to MongoDB")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich existing MongoDB entries with AI metadata (modular approach)"
    )
    parser.add_argument(
        "--user-tag",
        help="Only enrich words with this user_tag"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Maximum number of words to enrich (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually update MongoDB"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-2024-08-06",
        help="OpenAI model to use for enrichment"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2],
        help="Only run Phase 1 or Phase 2 (default: both)"
    )

    args = parser.parse_args()

    enrich_and_update_modular(
        user_tag_filter=args.user_tag,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        model=args.model,
        phase=args.phase
    )


if __name__ == "__main__":
    main()
