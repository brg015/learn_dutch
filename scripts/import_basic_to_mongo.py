"""
Import basic word pairs from CSV to MongoDB (no AI enrichment).

This script performs a quick import of Dutch-English word pairs without
calling any AI APIs. Words can be enriched later with enrich_and_update.py.

Usage:
    python -m scripts.import_basic_to_mongo [--batch-size N] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from core.schemas import LexiconEntry, EnrichmentMetadata, ImportData, PartOfSpeech

# Load environment
load_dotenv()

# Configuration
CSV_PATH = Path("data/word_list.csv")
DB_NAME = "dutch_trainer"
COLLECTION_NAME = "lexicon"


def parse_user_tags(tags_str: str) -> list[str]:
    """Parse comma-separated user tags from CSV."""
    if pd.isna(tags_str) or not tags_str or str(tags_str).strip() == "":
        return []

    tags = [tag.strip() for tag in str(tags_str).split(",")]
    return [tag for tag in tags if tag]


def import_basic_words(
    batch_size: int | None = None,
    dry_run: bool = False
) -> None:
    """
    Import basic word pairs from CSV to MongoDB without AI enrichment.

    Args:
        batch_size: Maximum number of words to process (None = all)
        dry_run: If True, don't actually insert to MongoDB or update CSV
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

    # Create unique index on lemma + pos if it doesn't exist
    collection.create_index([("lemma", 1), ("pos", 1)], unique=True)

    # Load CSV
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} words from CSV")

    # Filter to words not yet added
    if "added_to_lexicon" in df.columns:
        to_process = df[df["added_to_lexicon"] == False].copy()
    else:
        print("Warning: 'added_to_lexicon' column not found, processing all words")
        to_process = df.copy()

    if len(to_process) == 0:
        print("No words to process (all already added to lexicon)")
        return

    print(f"Words to process: {len(to_process)}")

    # Apply batch size limit
    if batch_size:
        to_process = to_process.head(batch_size)
        print(f"Limited to batch size: {batch_size}")

    print(f"\n{'='*60}")
    print("Starting basic import (no AI enrichment)...")
    print(f"{'='*60}\n")

    # Process each word
    success_count = 0
    error_count = 0
    duplicate_count = 0

    for idx, row in to_process.iterrows():
        dutch = row["dutch"]
        english = row["english"]
        user_tags_str = row.get("user_tags", "")

        print(f"\n[{idx+1}/{len(to_process)}] Importing: {dutch} ({english})")

        try:
            # Parse user tags
            user_tags = parse_user_tags(user_tags_str)
            if user_tags:
                print(f"  User tags: {', '.join(user_tags)}")

            # Create basic lexicon entry (no AI enrichment)
            entry = LexiconEntry(
                import_data=ImportData(
                    imported_word=dutch,
                    imported_translation=english,
                    imported_at=datetime.utcnow()
                ),
                lemma=dutch,  # Use imported word as lemma for now
                pos=PartOfSpeech.OTHER,  # Unknown until enriched
                translations=[english],
                user_tags=user_tags,
                enrichment=EnrichmentMetadata(
                    enriched=False,
                    lemma_normalized=False
                )
            )

            if not dry_run:
                # Insert to MongoDB
                collection.insert_one(entry.model_dump())

                # Update CSV to mark as added
                df.loc[idx, "added_to_lexicon"] = True

            success_count += 1
            print(f"  ✓ {'[DRY RUN] Would insert' if dry_run else 'Inserted'} to MongoDB")

        except DuplicateKeyError:
            duplicate_count += 1
            print(f"  ⚠ Duplicate (lemma + POS already exists in DB)")
            # Still mark as added in CSV
            if not dry_run:
                df.loc[idx, "added_to_lexicon"] = True

        except Exception as e:
            error_count += 1
            print(f"  ✗ Error: {e}")

    # Save updated CSV
    if not dry_run and success_count > 0:
        df.to_csv(CSV_PATH, index=False)
        print(f"\n✓ Updated {CSV_PATH}")

    # Summary
    print(f"\n{'='*60}")
    print("Import complete!")
    print(f"{'='*60}")
    print(f"Successfully imported: {success_count}")
    print(f"Duplicates skipped:    {duplicate_count}")
    print(f"Errors:                {error_count}")
    print(f"Total:                 {len(to_process)}")

    if dry_run:
        print("\n⚠ DRY RUN MODE - No changes were made to MongoDB or CSV")
    else:
        print("\n💡 Tip: Use `enrich_and_update.py` to add AI enrichment later")


def main():
    parser = argparse.ArgumentParser(
        description="Import basic word pairs to MongoDB (no AI enrichment)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Maximum number of words to process (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually insert to MongoDB or update CSV"
    )

    args = parser.parse_args()

    import_basic_words(
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
