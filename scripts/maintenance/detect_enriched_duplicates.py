"""
Detect enriched entries that may be duplicates based on {lemma, pos, sense}.

This script finds cases where:
1. Multiple enriched entries exist with same {lemma, pos, sense}
2. An entry was recently enriched and matches an older enriched entry

Example use case:
- You import "liep" and "lopen" separately
- Both get enriched to lemma="lopen", pos="verb", sense=None
- This script detects the duplicate and lets you decide which to keep

Usage:
    python -m scripts.data.detect_enriched_duplicates
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment
load_dotenv()

# Configuration
DB_NAME = "dutch_trainer"
COLLECTION_NAME = "lexicon"


def detect_duplicates():
    """
    Find enriched entries with duplicate {lemma, pos, sense}.

    Returns a report of potential duplicates for manual review.
    """
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI not found in environment variables")

    client = MongoClient(mongo_uri)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print("Connecting to MongoDB...")
    client.admin.command("ping")
    print(f"Connected to MongoDB: {DB_NAME}.{COLLECTION_NAME}\n")

    # Find all enriched entries
    enriched_entries = list(collection.find({
        "word_enrichment.enriched": True
    }))

    if not enriched_entries:
        print("No enriched entries found in lexicon")
        return

    print(f"Found {len(enriched_entries)} enriched entries")
    print("Analyzing for duplicates...\n")

    # Group by {lemma, pos, sense}
    groups = defaultdict(list)
    for entry in enriched_entries:
        lemma = entry.get("lemma", "").lower()
        pos = entry.get("pos", "")
        sense = entry.get("sense")  # None for most entries

        # Create key
        key = (lemma, pos, sense)
        groups[key].append(entry)

    # Find duplicates (groups with >1 entry)
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        print("✓ No duplicate enriched entries found!")
        print("All enriched words have unique {lemma, pos, sense} combinations")
        return

    # Report duplicates
    print(f"{'='*80}")
    print(f"FOUND {len(duplicates)} DUPLICATE GROUPS")
    print(f"{'='*80}\n")

    for idx, ((lemma, pos, sense), entries) in enumerate(duplicates.items(), 1):
        sense_str = f"'{sense}'" if sense else "None"
        print(f"\n[{idx}] Duplicate: lemma='{lemma}', pos='{pos}', sense={sense_str}")
        print(f"    Found {len(entries)} entries:\n")

        for entry in sorted(entries, key=lambda e: e.get("import_data", {}).get("imported_at", datetime.min)):
            word_id = entry.get("word_id", "unknown")
            imported_word = entry.get("import_data", {}).get("imported_word", "N/A")
            imported_at = entry.get("import_data", {}).get("imported_at", "N/A")
            enriched_at = entry.get("word_enrichment", {}).get("enriched_at", "N/A")
            user_tags = entry.get("user_tags", [])

            # Format dates
            if isinstance(imported_at, datetime):
                imported_at = imported_at.strftime("%Y-%m-%d %H:%M")
            if isinstance(enriched_at, datetime):
                enriched_at = enriched_at.strftime("%Y-%m-%d %H:%M")

            print(f"    • word_id: {word_id}")
            print(f"      Imported as: '{imported_word}'")
            print(f"      Imported: {imported_at}")
            print(f"      Enriched: {enriched_at}")
            if user_tags:
                print(f"      User tags: {', '.join(user_tags)}")
            print()

        print(f"    RECOMMENDATION:")
        print(f"    - Keep the entry you want (usually the first imported)")
        print(f"    - Delete others using: collection.delete_one({{'word_id': 'xxx'}})")
        print(f"    - Or merge user_tags if both have useful tags")

    # Summary
    total_duplicates = sum(len(entries) - 1 for entries in duplicates.values())
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Duplicate groups: {len(duplicates)}")
    print(f"Extra entries (can be deleted): {total_duplicates}")
    print(f"\nNext steps:")
    print(f"  1. Review each duplicate group above")
    print(f"  2. Decide which entry to keep")
    print(f"  3. Use MongoDB or a cleanup script to delete unwanted entries")
    print(f"  4. Update Google Sheet to point to kept word_id if needed")


def main():
    detect_duplicates()


if __name__ == "__main__":
    main()
