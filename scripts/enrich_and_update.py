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
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient

from scripts.enrich_lexicon import enrich_word

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
    query = {"enrichment.enriched": False}

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
        # Get import data (fallback to lemma/translations if no import_data)
        if doc.get("import_data"):
            dutch = doc["import_data"]["imported_word"]
            english = doc["import_data"]["imported_translation"]
        else:
            dutch = doc["lemma"]
            english = doc["translations"][0] if doc.get("translations") else ""

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

            # Enrich with AI
            print(f"  Enriching with AI...")
            enriched = enrich_word(dutch, english, model=model)
            print(f"  ✓ AI enriched - POS: {enriched.pos}, Difficulty: {enriched.difficulty}")

            # AFTER AI call: Also check if the resulting lemma+POS already exists
            # (handles case where different imports normalize to same lemma)
            existing_enriched_lemma = collection.find_one({
                "lemma": enriched.lemma,
                "pos": enriched.pos,
                "enrichment.enriched": True,
                "_id": {"$ne": doc["_id"]}  # Don't match self
            })

            if existing_enriched_lemma:
                skipped_count += 1
                print(f"  ⚠ Skipped - '{enriched.lemma}' ({enriched.pos}) already enriched in DB")
                continue

            # Determine if lemma was normalized
            lemma_normalized = enriched.lemma.lower() != dutch.lower()
            if lemma_normalized:
                print(f"  → Lemma normalized: '{dutch}' → '{enriched.lemma}'")

            # Prepare update
            update_doc = {
                "$set": {
                    # Update lexicon fields (may differ from import_data)
                    "lemma": enriched.lemma,
                    "pos": enriched.pos,
                    "translations": enriched.translations,
                    "difficulty": enriched.difficulty,
                    "tags": enriched.tags,

                    # POS-specific metadata
                    "noun_meta": enriched.noun_meta.model_dump() if enriched.noun_meta else None,
                    "verb_meta": enriched.verb_meta.model_dump() if enriched.verb_meta else None,
                    "adjective_meta": enriched.adjective_meta.model_dump() if enriched.adjective_meta else None,
                    "general_examples": [ex.model_dump() for ex in enriched.general_examples],

                    # Enrichment metadata
                    "enrichment.enriched": True,
                    "enrichment.enriched_at": datetime.now(datetime.timezone.utc),
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
