"""
Review and remove duplicate entries detected during enrichment.

This script reads the duplicates log file (logs/duplicates_detected.json) and allows
you to review and delete redundant entries from the MongoDB lexicon.

Usage:
    # Review duplicates (interactive)
    python -m scripts.maintenance.remove_duplicates

    # Auto-delete all duplicates without confirmation (use with caution!)
    python -m scripts.maintenance.remove_duplicates --auto-delete

    # Dry run - show what would be deleted
    python -m scripts.maintenance.remove_duplicates --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment
load_dotenv()

# Configuration
DB_NAME = "dutch_trainer"
COLLECTION_NAME = "lexicon"
DUPLICATES_FILE = Path("logs") / "duplicates_detected.json"


def load_duplicates() -> list[dict]:
    """Load duplicates from JSON file."""
    if not DUPLICATES_FILE.exists():
        print(f"No duplicates file found at: {DUPLICATES_FILE}")
        print("Run enrichment script first to detect duplicates")
        return []

    with open(DUPLICATES_FILE, 'r', encoding='utf-8') as f:
        duplicates = json.load(f)

    return duplicates


def review_and_delete(
    duplicates: list[dict],
    auto_delete: bool = False,
    dry_run: bool = False
) -> None:
    """
    Review duplicates and delete redundant entries.

    Args:
        duplicates: List of duplicate info dicts
        auto_delete: If True, delete all without asking
        dry_run: If True, don't actually delete
    """
    if not duplicates:
        print("No duplicates to review")
        return

    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI not found in environment variables")

    client = MongoClient(mongo_uri)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Verify connection
    client.admin.command("ping")
    print(f"✓ Connected to MongoDB: {DB_NAME}.{COLLECTION_NAME}\n")

    print(f"{'='*80}")
    print(f"DUPLICATE REVIEW - {len(duplicates)} duplicates found")
    print(f"{'='*80}\n")

    deleted_count = 0
    skipped_count = 0

    for idx, dup in enumerate(duplicates, 1):
        redundant = dup["redundant_entry"]
        existing = dup["existing_entry"]
        detected_at = dup["detected_at"]

        print(f"\n[{idx}/{len(duplicates)}] Duplicate detected at {detected_at}")
        print(f"-" * 80)
        print(f"EXISTING ENTRY (keep this):")
        print(f"  word_id:            {existing['word_id']}")
        print(f"  lemma:              {existing['lemma']}")
        print(f"  pos:                {existing['pos']}")
        print(f"  pos_enriched_at:    {existing.get('pos_enriched_at', 'N/A')}")
        print()
        print(f"REDUNDANT ENTRY (will be deleted):")
        print(f"  word_id:       {redundant['word_id']}")
        print(f"  imported_word: {redundant['imported_word']}")
        print(f"  imported_at:   {redundant.get('imported_at', 'N/A')}")
        print()

        # Decide whether to delete
        should_delete = False

        if auto_delete:
            should_delete = True
            print("  → Auto-deleting (--auto-delete enabled)")
        elif dry_run:
            should_delete = False
            print("  → [DRY RUN] Would delete this entry")
        else:
            # Interactive confirmation
            response = input(f"  Delete redundant entry {redundant['word_id']}? [y/n/q] (y=yes, n=no, q=quit): ").lower().strip()

            if response == 'q':
                print("\n⚠ Quitting - remaining duplicates not processed")
                break
            elif response == 'y':
                should_delete = True
            else:
                print("  → Skipped")
                skipped_count += 1

        # Delete if confirmed
        if should_delete and not dry_run:
            result = collection.delete_one({"word_id": redundant['word_id']})
            if result.deleted_count > 0:
                print(f"  ✓ Deleted redundant entry: {redundant['word_id']}")
                deleted_count += 1
            else:
                print(f"  ✗ Failed to delete (entry not found in DB)")
                skipped_count += 1
        elif should_delete and dry_run:
            deleted_count += 1  # Count what would be deleted

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Deleted:  {deleted_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Total:    {len(duplicates)}")

    if dry_run:
        print("\n⚠ DRY RUN MODE - No entries were actually deleted")
    elif deleted_count > 0:
        # Clear the duplicates file (or remove processed entries)
        if deleted_count == len(duplicates):
            DUPLICATES_FILE.unlink()
            print(f"\n✓ All duplicates processed - cleared {DUPLICATES_FILE}")
        else:
            # Keep unprocessed duplicates in file
            remaining = duplicates[deleted_count + skipped_count:]
            with open(DUPLICATES_FILE, 'w', encoding='utf-8') as f:
                json.dump(remaining, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Processed {deleted_count + skipped_count}/{len(duplicates)} duplicates")
            print(f"  {len(remaining)} remaining in {DUPLICATES_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Review and remove duplicate lexicon entries")
    parser.add_argument(
        "--auto-delete",
        action="store_true",
        help="Automatically delete all duplicates without confirmation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    args = parser.parse_args()

    # Load duplicates
    duplicates = load_duplicates()

    if not duplicates:
        return

    # Review and delete
    review_and_delete(duplicates, auto_delete=args.auto_delete, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
