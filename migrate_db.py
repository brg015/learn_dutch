"""
Migration script to recreate SQLite database with correct schema.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("logs/reviews.sqlite")
BACKUP_PATH = Path("logs/reviews_backup.sqlite")

# Backup existing database
if DB_PATH.exists():
    print(f"Backing up existing database to {BACKUP_PATH}")
    import shutil
    shutil.copy(DB_PATH, BACKUP_PATH)
    DB_PATH.unlink()

# Create new database with correct schema
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        lemma TEXT NOT NULL,
        pos TEXT NOT NULL,
        exercise_type TEXT NOT NULL,
        remembered INTEGER NOT NULL,
        latency_ms INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create indexes
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_lemma_pos
    ON review_events(lemma, pos)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_timestamp
    ON review_events(timestamp DESC)
""")

conn.commit()
conn.close()

print(f"✓ Database recreated successfully at {DB_PATH}")
print("Note: Old database was backed up to", BACKUP_PATH)
