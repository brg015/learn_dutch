# Architecture Overview

This document describes the current runtime flow, data stores, and module responsibilities. It is intended as a reference before adding new activities.

## High-Level Flow

1. The Streamlit app (`app/streamlit_app.py`) initializes session state and the SQL schema.
2. On session start, the app builds a base pool snapshot (per activity) and a launch-scoped STM set.
3. A session builder selects a batch of words from pools (LTM, STM, NEW).
4. The active activity renders a card (front/back) and collects feedback.
5. Feedback updates in-memory STM, buffers card updates/events, and advances the session.
6. On session completion (or explicit quit), buffered changes are flushed to SQL.

## Data Stores

### MongoDB (lexicon)
Source of truth for words and enrichment data.

- Accessed via `core/lexicon_repo.py`.
- `get_all_words(...)` is the primary entry point and applies filters (enriched, tag, pos, verb_meta).
- `get_enriched_verbs()` is a wrapper for verbs with Phase 2 enrichment.

### SQL (FSRS)
Persistent spaced-repetition state and review history.

- `card_state` table: per-user, per-word, per-exercise memory state.
- `review_events` table: event log for each review attempt.

Key modules:
- `core/fsrs/models.py`: ORM schema.
- `core/fsrs/database.py`: read/write IO.
- `core/fsrs/scheduler.py`: pure algorithm updates (no DB).
- `core/fsrs/memory_state.py`: dataclasses and retrievability math.

## FSRS Data Types

- `CardState` (dataclass, mutable): used by the scheduler and stored in SQL.
- `CardStateSnapshot` (dataclass, minimal): `{word_id, exercise_type, retrievability}` used for pool building.

Snapshots are computed in `get_all_cards_with_state(...)` and are intended to be short-lived.

## Pools and Session Builders

### STM
STM is a launch-scoped dynamic set of `(word_id, exercise_type)` keys:

- Built from recent AGAIN events: `build_stm_set(...)`.
- Updated after each review: `update_stm_set(...)`.
- Converted to word dicts when building pools: `build_stm_words(...)`.

### Pools
Pools use a fixed schema:

```
PoolItem = { word: dict, status: "ltm" | "stm" | "new" }
```

Pools are built in the activity-specific builders:

- `core/session_builders/word_builder.py`
- `core/session_builders/verb_builder.py`

Both use `fill_in_order(...)` to assemble sessions (priority: LTM -> STM -> NEW).

### Base Pool Caching
The Streamlit app caches base pools in `st.session_state`:

- `word_pool_cache` for word/sentence sessions
- `verb_pool_cache` for verb sessions

This reduces DB calls but means pool snapshots are stale within a long-running app. STM remains dynamic.

## Activities and UI

- Activity classes render card fronts/backs:
  - `WordActivity`
  - `SentenceActivity`
  - `VerbTenseActivity`
- UI components live in `app/ui` (flashcards, feedback buttons, session stats, word details).

`app/streamlit_app.py` orchestrates:

- Session state setup
- Session start and batch creation
- Activity rendering
- Feedback processing
- Buffer flush to SQL

## Configuration

Important constants live in:

- `core/fsrs/constants.py` (retrievability thresholds, session sizes)

Environment variables:

- `DATABASE_URL`, `TEST_MODE`, `DEFAULT_USER_ID`
- `MONGO_URI`

Migration helper:

- `scripts/migrate_timestamps_to_datetime.py` converts timestamp columns to `timestamptz`.

## Adding a New Activity (Checklist)

1. Create an activity class in `app/activities/`.
2. Add a session builder or reuse an existing one in `core/session_builders/`.
3. Decide which exercise_type(s) to use in SQL.
4. Wire the activity into `streamlit_app.py` (session start + rendering).
5. Ensure feedback updates STM if you want STM behavior.

## Current Tradeoffs / Known Constraints

- Pool snapshots are cached per launch and do not auto-refresh. Retrievability can drift over time.
- `get_session()` creates a new SQLAlchemy engine per call (no global engine cache).
- SQL timestamps use native DateTime columns.
- No automated tests yet; changes are validated manually.
