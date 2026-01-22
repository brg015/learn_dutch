"""
Enrich existing MongoDB lexicon entries with AI-generated metadata.

This script updates words that are already in MongoDB but not yet enriched.
It can enrich all unenriched words or filter by user_tags.

Usage:
    # Enrich all unenriched words
    python -m scripts.enrich_and_update [--batch-size N] [--dry-run]

    # Enrich only words with specific tag
    python -m scripts.enrich_and_update --user-tag "Chapter 10"
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient

from scripts.enrichment.enrich_modular import enrich_basic, enrich_pos

# Load environment
load_dotenv()

# Configuration
DB_NAME = "dutch_trainer"
COLLECTION_NAME = "lexicon"


def enrich_and_update(
    user_tag_filter: Optional[str] = None,
    batch_size: Optional[int] = None,
    dry_run: bool = False,
    model: str = "gpt-4o-2024-08-06"
) -> None:
    """
    Enrich existing MongoDB entries with AI metadata.

    Args:
        user_tag_filter: Only enrich words with this user_tag (None = all)
        batch_size: Maximum number of words to enrich (None = all)
        dry_run: If True, don't actually update MongoDB
        model: OpenAI model to use for enrichment
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

    # Build query for unenriched words
    # Exclude phrases - they don't need AI enrichment
    query = {
        "enrichment.enriched": False,
        "$or": [
            {"entry_type": {"$exists": False}},  # Old entries without entry_type
            {"entry_type": "word"}  # Only enrich words, not phrases
        ]
    }

    if user_tag_filter:
        query["user_tags"] = user_tag_filter
        print(f"Filter: user_tag = '{user_tag_filter}'")

    # Find unenriched words
    cursor = collection.find(query)

    if batch_size:
        cursor = cursor.limit(batch_size)
        print(f"Batch size limit: {batch_size}")

    words = list(cursor)

    if len(words) == 0:
        print("No unenriched words found matching criteria")
        return

    print(f"Found {len(words)} unenriched words\n")
    print(f"{'='*60}")
    print("Starting enrichment...")
    print(f"{'='*60}\n")

    # Process each word
    success_count = 0
    error_count = 0
    skipped_count = 0

    for idx, doc in enumerate(words, 1):
        # Get import data (fallback to lemma/translation if no import_data)
        if doc.get("import_data"):
            dutch = doc["import_data"]["imported_word"]
            english = doc["import_data"]["imported_translation"]
        else:
            dutch = doc["lemma"]
            # Handle both old (translations list) and new (translation string) schema
            if doc.get("translation"):
                english = doc["translation"]
            else:
                english = ""

        print(f"\n[{idx}/{len(words)}] Processing: {dutch} ({english})")

        try:
            # BEFORE AI call: Check if this imported_word already has an enriched entry
            # (avoids AI call if "liep" was already enriched and normalized to "lopen")
            existing_with_import = collection.find_one({
                "import_data.imported_word": dutch,
                "enrichment.enriched": True,
                "_id": {"$ne": doc["_id"]}  # Don't match self
            })

            if existing_with_import:
                skipped_count += 1
                lemma = existing_with_import.get("lemma", dutch)
                print(f"  ⚠ Skipped - '{dutch}' already enriched as '{lemma}'")
                continue

            # Phase 1: Basic enrichment (lemma, POS, translation, etc.)
            print(f"  Phase 1: Basic enrichment...")
            basic_enriched = enrich_basic(dutch, english, model=model)
            print(f"  ✓ Phase 1 complete - Lemma: {basic_enriched.lemma}, POS: {basic_enriched.pos}")

            # AFTER Phase 1: Check if the resulting lemma+POS already exists
            # This saves Phase 2 cost if we find a match
            existing_enriched_lemma = collection.find_one({
                "lemma": basic_enriched.lemma,
                "pos": basic_enriched.pos,
                "enrichment.enriched": True,
                "_id": {"$ne": doc["_id"]}  # Don't match self
            })

            if existing_enriched_lemma:
                skipped_count += 1
                print(f"  ⚠ Skipped Phase 2 - '{basic_enriched.lemma}' ({basic_enriched.pos}) already enriched in DB")
                continue

            # Phase 2: POS-specific enrichment (if needed)
            from core.schemas import PartOfSpeech, AIEnrichedEntry

            noun_meta = None
            verb_meta = None
            adjective_meta = None

            if basic_enriched.pos in [PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE]:
                print(f"  Phase 2: {basic_enriched.pos} enrichment...")
                pos_metadata = enrich_pos(basic_enriched.lemma, basic_enriched.pos, basic_enriched.translation, model=model)

                # Assign to correct field
                if basic_enriched.pos == PartOfSpeech.NOUN:
                    noun_meta = pos_metadata
                elif basic_enriched.pos == PartOfSpeech.VERB:
                    verb_meta = pos_metadata
                elif basic_enriched.pos == PartOfSpeech.ADJECTIVE:
                    adjective_meta = pos_metadata

                print(f"  ✓ Phase 2 complete")
            else:
                print(f"  → Phase 2 skipped (POS '{basic_enriched.pos}' doesn't need it)")

            # Convert Phase 1 + Phase 2 results into AIEnrichedEntry format
            # (needed because update code expects noun_meta/verb_meta/adjective_meta fields)
            enriched = AIEnrichedEntry(
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

            print(f"  ✓ Enrichment complete - Difficulty: {enriched.difficulty}")

            # Determine if lemma was normalized
            lemma_normalized = enriched.lemma.lower() != dutch.lower()
            if lemma_normalized:
                print(f"  → Lemma normalized: '{dutch}' → '{enriched.lemma}'")

            # Prepare general_examples: copy from present examples if available
            general_examples = []

            # Check if AI provided general_examples
            if enriched.general_examples:
                general_examples = enriched.general_examples
            else:
                # Auto-populate from POS-specific examples
                # For verbs, copy from examples_present
                if enriched.verb_meta and enriched.verb_meta.examples_present:
                    general_examples = enriched.verb_meta.examples_present[:2]  # Take first 2
                # For nouns, copy from examples_singular
                elif enriched.noun_meta and enriched.noun_meta.examples_singular:
                    general_examples = enriched.noun_meta.examples_singular[:2]
                # For adjectives, copy from examples_base
                elif enriched.adjective_meta and enriched.adjective_meta.examples_base:
                    general_examples = enriched.adjective_meta.examples_base[:2]

            # Prepare update
            update_doc = {
                "$set": {
                    # Update lexicon fields (may differ from import_data)
                    "lemma": enriched.lemma,
                    "pos": enriched.pos,
                    "translation": enriched.translation,
                    "definition": enriched.definition,
                    "difficulty": enriched.difficulty,
                    "tags": enriched.tags,

                    # POS-specific metadata
                    "noun_meta": enriched.noun_meta.model_dump() if enriched.noun_meta else None,
                    "verb_meta": enriched.verb_meta.model_dump() if enriched.verb_meta else None,
                    "adjective_meta": enriched.adjective_meta.model_dump() if enriched.adjective_meta else None,
                    "general_examples": [ex.model_dump() for ex in general_examples] if general_examples else [],

                    # Enrichment metadata
                    "enrichment.enriched": True,
                    "enrichment.enriched_at": datetime.now(timezone.utc),
                    "enrichment.model_used": model,
                    "enrichment.version": doc.get("enrichment", {}).get("version", 1),
                    "enrichment.lemma_normalized": lemma_normalized,
                }
            }

            if not dry_run:
                # Update in MongoDB
                collection.update_one({"_id": doc["_id"]}, update_doc)

            success_count += 1
            print(f"  ✓ {'[DRY RUN] Would update' if dry_run else 'Updated'} in MongoDB")

        except Exception as e:
            error_count += 1
            print(f"  ✗ Error: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("Enrichment complete!")
    print(f"{'='*60}")
    print(f"Successfully enriched: {success_count}")
    print(f"Skipped (already enriched): {skipped_count}")
    print(f"Errors:                {error_count}")
    print(f"Total:                 {len(words)}")

    if dry_run:
        print("\n⚠ DRY RUN MODE - No changes were made to MongoDB")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich existing MongoDB entries with AI metadata"
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

    args = parser.parse_args()

    enrich_and_update(
        user_tag_filter=args.user_tag,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        model=args.model
    )


if __name__ == "__main__":
    main()
