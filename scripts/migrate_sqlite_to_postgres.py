"""
SQLite to Postgres Migration Script

One-time script to migrate learning data from SQLite to Postgres.

Usage:
    python scripts/migrate_sqlite_to_postgres.py
    
This will:
1. Connect to both SQLite files (production and test) and Postgres databases
2. Read all card_state and review_events from SQLite
3. Insert them into Postgres
4. Validate row counts before and after
5. Report success/failure with timestamps
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from core.fsrs.models import Base, CardState as CardStateModel, ReviewEvent as ReviewEventModel
from core.fsrs.database import get_engine, get_session

MIGRATION_USER_ID = os.getenv("MIGRATION_USER_ID", "ben")


def migrate_database(sqlite_path: str, is_test: bool = False) -> Dict[str, Any]:
    """
    Migrate a single SQLite database to Postgres.
    
    Args:
        sqlite_path: Path to the SQLite .db file
        is_test: Whether this is the test database
    
    Returns:
        Dictionary with migration results
    """
    print(f"\n{'='*70}")
    print(f"Starting migration for: {Path(sqlite_path).name}")
    print(f"{'='*70}")
    
    # Check if SQLite file exists
    if not Path(sqlite_path).exists():
        print(f"⚠ SQLite file not found: {sqlite_path}")
        return {"status": "skipped", "reason": "file not found"}
    
    # Set TEST_MODE for Postgres connection
    if is_test:
        os.environ["TEST_MODE"] = "true"
    else:
        os.environ["TEST_MODE"] = "false"
    
    # Connect to SQLite
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
    except Exception as e:
        print(f"✗ Failed to connect to SQLite: {e}")
        return {"status": "failed", "error": str(e)}
    
    # Connect to Postgres
    try:
        pg_engine = get_engine()
        pg_session = get_session()
        print("✓ Connected to Postgres")
        
        # Initialize database tables (create if don't exist)
        from core.fsrs.database import init_db
        init_db()
        
    except Exception as e:
        print(f"✗ Failed to connect to Postgres: {e}")
        return {"status": "failed", "error": str(e)}
    
    try:
        # Get row counts before migration
        sqlite_cursor.execute("SELECT COUNT(*) as count FROM card_state")
        sqlite_card_count = sqlite_cursor.fetchone()["count"]
        
        sqlite_cursor.execute("SELECT COUNT(*) as count FROM review_events")
        sqlite_event_count = sqlite_cursor.fetchone()["count"]
        
        print(f"Source (SQLite): {sqlite_card_count} cards, {sqlite_event_count} events")
        
        # Migrate card_state
        print("\nMigrating card_state...")
        sqlite_cursor.execute("SELECT * FROM card_state")
        cards = sqlite_cursor.fetchall()
        
        for card in cards:
            db_card = CardStateModel(
                user_id=MIGRATION_USER_ID,
                word_id=card["word_id"],
                exercise_type=card["exercise_type"],
                lemma=card["lemma"],
                pos=card["pos"],
                stability=card["stability"],
                difficulty=card["difficulty"],
                d_eff=card["d_eff"],
                review_count=card["review_count"],
                last_review_timestamp=card["last_review_timestamp"],
                last_ltm_timestamp=card["last_ltm_timestamp"],
                ltm_review_date=card["ltm_review_date"],
                stm_success_count_today=card["stm_success_count_today"],
                d_floor=card["d_floor"] if card["d_floor"] is not None else None  # Optional field
            )
            pg_session.add(db_card)
        
        pg_session.commit()
        print(f"✓ Migrated {len(cards)} cards")
        
        # Migrate review_events
        print("Migrating review_events...")
        sqlite_cursor.execute("SELECT * FROM review_events")
        events = sqlite_cursor.fetchall()
        
        for event in events:
            db_event = ReviewEventModel(
                user_id=MIGRATION_USER_ID,
                word_id=event["word_id"],
                exercise_type=event["exercise_type"],
                lemma=event["lemma"],
                pos=event["pos"],
                timestamp=event["timestamp"],
                feedback_grade=event["feedback_grade"],
                latency_ms=event["latency_ms"],
                stability_before=event["stability_before"],
                difficulty_before=event["difficulty_before"],
                d_eff_before=event["d_eff_before"],
                retrievability_before=event["retrievability_before"],
                stability_after=event["stability_after"],
                difficulty_after=event["difficulty_after"],
                d_eff_after=event["d_eff_after"],
                is_ltm_event=event["is_ltm_event"],
                session_id=event["session_id"],
                session_position=event["session_position"],
                presentation_mode=event["presentation_mode"] if event["presentation_mode"] is not None else None
            )
            pg_session.add(db_event)
        
        pg_session.commit()
        print(f"✓ Migrated {len(events)} events")
        
        # Verify migration
        pg_card_count = pg_session.query(CardStateModel).count()
        pg_event_count = pg_session.query(ReviewEventModel).count()
        
        print(f"\nTarget (Postgres): {pg_card_count} cards, {pg_event_count} events")
        
        # Validate counts match
        cards_match = sqlite_card_count == pg_card_count
        events_match = sqlite_event_count == pg_event_count
        
        if cards_match and events_match:
            print("\n✓ Migration completed successfully!")
            print(f"  - All {sqlite_card_count} cards migrated ✓")
            print(f"  - All {sqlite_event_count} events migrated ✓")
            return {
                "status": "success",
                "cards_migrated": sqlite_card_count,
                "events_migrated": sqlite_event_count
            }
        else:
            print("\n✗ Migration validation failed!")
            if not cards_match:
                print(f"  - Card mismatch: SQLite={sqlite_card_count}, Postgres={pg_card_count}")
            if not events_match:
                print(f"  - Event mismatch: SQLite={sqlite_event_count}, Postgres={pg_event_count}")
            return {
                "status": "failed",
                "error": "Row count mismatch",
                "cards": {"sqlite": sqlite_card_count, "postgres": pg_card_count},
                "events": {"sqlite": sqlite_event_count, "postgres": pg_event_count}
            }
    
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}
    
    finally:
        sqlite_conn.close()
        pg_session.close()


def main():
    """Run migrations for both production and test databases."""
    print("\n" + "="*70)
    print("SQLite to Postgres Migration")
    print("="*70)
    
    # Check that DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("\n✗ ERROR: DATABASE_URL environment variable not set!")
        print("Please set it to your Postgres connection string before running this migration.")
        print("\nExample: postgresql://user:password@host:port/learning_db")
        sys.exit(1)
    
    backup_dir = Path(__file__).parent.parent / "backups"
    db_dir = Path(__file__).parent.parent / "logs"
    
    results = {}
    
    # Migrate production database
    prod_db_path = backup_dir / "learning.db.backup"
    if not prod_db_path.exists():
        prod_db_path = db_dir / "learning.db"
    results["production"] = migrate_database(str(prod_db_path), is_test=False)
    
    # Migrate test database
    test_db_path = backup_dir / "test_learning.db.backup"
    if not test_db_path.exists():
        test_db_path = db_dir / "test_learning.db"
    results["test"] = migrate_database(str(test_db_path), is_test=True)
    
    # Summary
    print("\n" + "="*70)
    print("MIGRATION SUMMARY")
    print("="*70)
    
    for db_name, result in results.items():
        status = result.get("status", "unknown").upper()
        if status == "SUCCESS":
            print(f"\n✓ {db_name.upper()}: {status}")
            print(f"  - Cards: {result.get('cards_migrated', 'N/A')}")
            print(f"  - Events: {result.get('events_migrated', 'N/A')}")
        elif status == "SKIPPED":
            print(f"\n⊘ {db_name.upper()}: {status}")
            print(f"  - Reason: {result.get('reason', 'Unknown')}")
        else:
            print(f"\n✗ {db_name.upper()}: {status}")
            print(f"  - Error: {result.get('error', 'Unknown')}")
    
    print("\n" + "="*70)
    print(f"Migration completed at: {datetime.now().isoformat()}")
    print("="*70 + "\n")
    
    # Exit with error code if any migration failed
    if any(r.get("status") == "failed" for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
