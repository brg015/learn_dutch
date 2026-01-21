# Notebooks Changelog

## 2026-01-20 - Major Update

### Changes
1. **Moved notebooks to dedicated directory**: All `.ipynb` files moved from root to `notebooks/`
2. **Updated analytics.ipynb** to match current FSRS schema:
   - Fixed database path: `learning.db` → `logs/learning.db`
   - Updated schema to use new FSRS fields:
     - Added `word_id` (UUID-based identification)
     - Added `d_eff` (effective difficulty)
     - Added `last_ltm_timestamp` (last long-term memory event)
     - Added `stm_success_count_today` (short-term memory tracking)
     - Added `is_ltm_event` to review events (distinguishes LTM vs STM)
   - Fixed retrievability calculation to use LTM timestamps
   - Added new visualization: LTM vs STM event breakdown
   - Fixed f-string formatting error in summary cell
3. **Rewrote build_lexicon.ipynb** to use current workflow:
   - Removed outdated CSV-based enrichment code
   - Now connects to MongoDB to inspect lexicon state
   - Shows enriched/unenriched word counts
   - Provides guidance to use CLI scripts for production
4. **Added notebooks/README.md** with comprehensive documentation

### Database Schema Reference

#### card_state table
- `word_id` (TEXT): Unique word identifier (UUID)
- `exercise_type` (TEXT): Type of exercise
- `lemma` (TEXT): Word lemma
- `pos` (TEXT): Part of speech
- `stability` (REAL): Long-term memory stability (days)
- `difficulty` (REAL): Difficulty rating (1-10)
- `d_eff` (REAL): Effective difficulty (for next LTM update)
- `review_count` (INTEGER): Total reviews
- `last_review_timestamp` (TEXT): Last review time
- `last_ltm_timestamp` (TEXT): Last LTM event time (NULL for new cards)
- `ltm_review_date` (TEXT): Date string for LTM scheduling
- `stm_success_count_today` (INTEGER): STM successes today

#### review_events table
- `word_id` (TEXT): Unique word identifier
- `exercise_type` (TEXT): Type of exercise
- `lemma` (TEXT): Word lemma (for analytics)
- `pos` (TEXT): Part of speech (for analytics)
- `timestamp` (TEXT): Review timestamp
- `feedback_grade` (INTEGER): User feedback (1-4)
- `latency_ms` (INTEGER): Response time
- `stability_before/after` (REAL): Stability changes
- `difficulty_before/after` (REAL): Difficulty changes
- `d_eff_before/after` (REAL): Effective difficulty changes
- `retrievability_before` (REAL): Retrievability at review time
- `is_ltm_event` (INTEGER): 1 for LTM, 0 for STM
- `session_id` (TEXT): Optional session tracking
- `session_position` (INTEGER): Position in session

### Migration Notes

If you have old analytics data:
- The notebook will fail if using the old schema
- You can reset the database by deleting `logs/learning.db`
- The app will recreate it with the new schema on next run
- No migration script needed (learning data is disposable for testing)
