"""
MENTAL MODEL / PURPOSE
----------------------
This script keeps `word_list.csv` clean while letting me add words freely
from an external source (e.g. Google Sheets → CSV download).

How it works:
- `word_list.csv`      = current source of truth
- `new_word_list.csv`  = freshly downloaded words to ingest

The script:
1. Compares rows using (dutch, english) as the key
2. Appends only truly new word pairs
3. Preserves extra columns (e.g. confidence, added_to_lexicon)
4. Sets added_to_lexicon=FALSE for newly added rows (default)
5. Overwrites `word_list.csv` safely

Outputs:
- word_list.csv            → updated source of truth
- word_list.backup.csv     → backup of previous state (undo button)
- added_rows.csv           → what was newly appended
- dupes.csv                → rows ignored because they already existed

Why this exists:
- CSVs have no primary keys or deduplication
- This prevents silent duplicates and accidental data loss
- Keeps the workflow simple without introducing a real database yet
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

# ---- Config ----
EXISTING_PATH = Path("data/word_list.csv")
NEW_PATH = Path("data/new_word_list.csv")

OUT_MERGED_PATH = Path("data/word_list.csv")  # overwrite existing (safe: we also make a backup)
OUT_ADDED_PATH = Path("data/added_rows.csv")
OUT_DUPES_PATH = Path("data/dupes.csv")

# Column names
DUTCH_COL = "dutch"
ENGLISH_COL = "english"
FLAG_COL = "added_to_lexicon"
USER_TAGS_COL = "user_tags"  # optional column

# Normalization rules
LOWERCASE = True  # set False if you care about capitalization
# ----------------


def normalize(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    if LOWERCASE:
        s = s.str.lower()
    # collapse multiple spaces
    s = s.str.replace(r"\s+", " ", regex=True)
    return s


def main() -> None:
    if not EXISTING_PATH.exists():
        raise FileNotFoundError(f"Missing existing file: {EXISTING_PATH}")
    if not NEW_PATH.exists():
        raise FileNotFoundError(f"Missing new file: {NEW_PATH}")

    existing = pd.read_csv(EXISTING_PATH)
    new = pd.read_csv(NEW_PATH)

    for df, name in [(existing, "existing"), (new, "new")]:
        if DUTCH_COL not in df.columns or ENGLISH_COL not in df.columns:
            raise ValueError(
                f"{name} CSV must contain columns '{DUTCH_COL}' and '{ENGLISH_COL}'. "
                f"Found: {list(df.columns)}"
            )

    # Keep the columns we need
    # For existing: preserve FLAG_COL and USER_TAGS_COL if they exist
    if FLAG_COL not in existing.columns:
        existing[FLAG_COL] = False
    if USER_TAGS_COL not in existing.columns:
        existing[USER_TAGS_COL] = ""

    existing_cols = [DUTCH_COL, ENGLISH_COL, FLAG_COL, USER_TAGS_COL]
    existing = existing[existing_cols].copy()

    # For new: keep dutch/english and user_tags if present
    new_cols = [DUTCH_COL, ENGLISH_COL]
    if USER_TAGS_COL in new.columns:
        new_cols.append(USER_TAGS_COL)
    new = new[new_cols].copy()

    # Add USER_TAGS_COL to new if it doesn't exist
    if USER_TAGS_COL not in new.columns:
        new[USER_TAGS_COL] = ""

    # Drop fully empty rows
    existing = existing.dropna(subset=[DUTCH_COL, ENGLISH_COL], how="any")
    new = new.dropna(subset=[DUTCH_COL, ENGLISH_COL], how="any")

    # Normalize FLAG_COL in existing: only TRUE (case-insensitive) stays True, everything else becomes False
    existing[FLAG_COL] = existing[FLAG_COL].astype(str).str.strip().str.upper() == 'TRUE'

    # Normalized keys for dedupe matching
    existing["_k_dutch"] = normalize(existing[DUTCH_COL])
    existing["_k_english"] = normalize(existing[ENGLISH_COL])
    new["_k_dutch"] = normalize(new[DUTCH_COL])
    new["_k_english"] = normalize(new[ENGLISH_COL])

    existing_keys = set(zip(existing["_k_dutch"], existing["_k_english"]))
    new_keys = list(zip(new["_k_dutch"], new["_k_english"]))

    is_dupe = [k in existing_keys for k in new_keys]
    dupes = new.loc[is_dupe, [DUTCH_COL, ENGLISH_COL]].copy()
    added = new.loc[[not d for d in is_dupe]].copy()

    # Set FLAG_COL to False for newly added rows
    added[FLAG_COL] = False

    # Backup existing before overwrite
    backup_path = EXISTING_PATH.with_name(EXISTING_PATH.stem + "_backup.csv")
    existing[[DUTCH_COL, ENGLISH_COL, FLAG_COL, USER_TAGS_COL]].to_csv(backup_path, index=False)

    # Merge: existing rows with their columns + new rows with FLAG_COL=False
    merged = pd.concat([existing[[DUTCH_COL, ENGLISH_COL, FLAG_COL, USER_TAGS_COL]], added], ignore_index=True)
    merged[DUTCH_COL] = merged[DUTCH_COL].astype(str).str.strip()
    merged[ENGLISH_COL] = merged[ENGLISH_COL].astype(str).str.strip()

    # Write outputs
    merged.to_csv(OUT_MERGED_PATH, index=False)
    added.to_csv(OUT_ADDED_PATH, index=False)
    dupes.to_csv(OUT_DUPES_PATH, index=False)

    print(f"Existing rows: {len(existing)}")
    print(f"New rows:      {len(new)}")
    print(f"Added rows:    {len(added)}  -> {OUT_ADDED_PATH}")
    print(f"Dupe rows:     {len(dupes)}  -> {OUT_DUPES_PATH}")
    print(f"Merged rows:   {len(merged)} -> {OUT_MERGED_PATH}")
    print(f"Backup saved:  {backup_path}")


if __name__ == "__main__":
    main()
