"""
Migration Script: Add word_id to Existing Lexicon Entries

This script adds a unique word_id (UUID) to all existing words in MongoDB
that don't already have one.

Usage:
    py -m scripts.data.migrate_add_word_ids
"""

import uuid
from core.lexicon_repo import get_collection


def migrate_add_word_ids():
    """Add word_id to all entries that don't have one."""
    collection = get_collection()

    # Find all entries without word_id
    entries_without_id = list(collection.find({"word_id": {"$exists": False}}))

    print(f"Found {len(entries_without_id)} entries without word_id")

    if len(entries_without_id) == 0:
        print("No migration needed - all entries already have word_id")
        return

    # Add word_id to each entry
    updated_count = 0
    for entry in entries_without_id:
        word_id = str(uuid.uuid4())

        result = collection.update_one(
            {"_id": entry["_id"]},
            {"$set": {"word_id": word_id}}
        )

        if result.modified_count > 0:
            updated_count += 1
            lemma = entry.get("lemma", "unknown")
            pos = entry.get("pos", "unknown")
            print(f"  Added word_id to: {lemma} ({pos}) -> {word_id}")

    print(f"\n[OK] Migration complete: {updated_count} entries updated")

    # Verify
    remaining = collection.count_documents({"word_id": {"$exists": False}})
    if remaining > 0:
        print(f"[WARNING] {remaining} entries still missing word_id")
    else:
        print("[OK] All entries now have word_id")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add word_id to existing lexicon entries")
    print("=" * 60)
    print()

    migrate_add_word_ids()
