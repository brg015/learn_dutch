"""
Reset the learning database (FSRS).

DANGEROUS: This deletes all review history!
Only use when you want to start fresh for testing.

Usage:
    python -m scripts.maintenance.reset_learning_db
"""

from core import fsrs

def main():
    print("=" * 60)
    print("WARNING: Reset Learning Database")
    print("=" * 60)
    print()
    print("This will DELETE all review history:")
    print("  - All card states (stability, difficulty, etc.)")
    print("  - All review events (logs of past reviews)")
    print()

    response = input("Are you sure you want to reset? (type 'yes' to confirm): ")

    if response.lower() == "yes":
        print("\nResetting database...")
        fsrs.reset_db()
        print("✓ Database reset complete!")
        print("\nThe database now has empty tables ready for new reviews.")
    else:
        print("\nCancelled. No changes made.")


if __name__ == "__main__":
    main()
