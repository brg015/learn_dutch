# FSRS Implementation Guide

## Overview

Your Dutch vocabulary trainer now uses **FSRS (Free Spaced Repetition Scheduler)** to optimize learning through forgetting curves and retrievability-based scheduling.

## What Changed

### 1. Graded Feedback System

**Before:** Binary feedback (I knew this / I didn't know)
**Now:** 4-level graded feedback:

- ❌ **Again** (1) - Completely forgot
- 😰 **Hard** (2) - Remembered with difficulty
- 👍 **Medium** (3) - Remembered normally
- ✨ **Easy** (4) - Remembered easily

### 2. Smart Scheduling

**Before:** Random word selection
**Now:** FSRS-based priority:

1. **Due cards first** - Words with retrievability < 70% (most urgent first)
2. **New cards** - Up to 10 new words per day
3. **Session complete** - When no due cards and new card limit reached

### 3. Database Schema

Two new components:

#### `card_state` table (current FSRS state)
```sql
lemma, pos, exercise_type → Primary key (one card per exercise type)
stability (S)              → Days until forgetting (higher = better learned)
difficulty (D)             → 1-10 scale (higher = harder for you)
last_review_timestamp      → When last reviewed
review_count               → Total reviews
```

#### `review_events` table (updated)
```sql
feedback_grade  → 1-4 (AGAIN/HARD/MEDIUM/EASY) instead of boolean
```

## How FSRS Works

### Memory State Per Card

Each card tracks:
- **Stability (S)** - How long before you forget (in days)
- **Difficulty (D)** - How hard this specific card is for you (0-10)

### Retrievability Calculation

At any moment, your probability of recalling a card is:

```
R = 0.9^(days_since_review / stability)
```

Example with S = 10 days:
- Day 0: R = 100% (just reviewed)
- Day 7: R = 93% (still strong)
- Day 14: R = 86% (starting to fade)
- Day 30: R = 73% (**due for review at 70% threshold**)

### State Updates After Review

Feedback affects future scheduling:

| Feedback | Stability Change | Difficulty Change | Meaning |
|----------|-----------------|-------------------|---------|
| **Again** | ×0.4 (drops) | +0.5 (harder) | You forgot - review sooner |
| **Hard** | ×1.2 (small gain) | +0.2 (slightly harder) | Struggled - needs work |
| **Medium** | ×2.5 (good gain) | -0.1 (slightly easier) | Normal recall |
| **Easy** | ×4.0 (large gain) | -0.3 (easier) | Solid recall - longer gap |

## Migration

If you have an existing database:

```bash
python migrate_to_fsrs.py
```

This will:
1. Backup your old `review_events` table
2. Convert binary feedback to graded (remembered=1 → MEDIUM, remembered=0 → AGAIN)
3. Create `card_state` table with initial values based on review history
4. Add proper indexes

## Configuration

### New Card Limit

Default: **10 new cards per day**

To change, edit `select_next_word()` in [core/scheduler.py:25](core/scheduler.py#L25):

```python
def select_next_word(
    ...
    max_new_cards: int = 10  # Change this
):
```

### Retrievability Threshold

Default: **70%** (cards reviewed when R drops below 0.70)

To change, edit `RETRIEVABILITY_THRESHOLD` in [core/log_repo.py:72](core/log_repo.py#L72):

```python
RETRIEVABILITY_THRESHOLD = 0.70  # Change this (0.0 to 1.0)
```

**Higher threshold (e.g., 0.80)** = Review cards more frequently (easier, safer)
**Lower threshold (e.g., 0.60)** = Review cards less frequently (harder, more efficient)

## FSRS Algorithm Parameters

Current weights in [core/log_repo.py:75-86](core/log_repo.py#L75-L86):

```python
W = {
    'stability_increase': {
        FeedbackGrade.AGAIN: 0.4,   # Failed: reduce to 40%
        FeedbackGrade.HARD: 1.2,    # Hard: +20%
        FeedbackGrade.MEDIUM: 2.5,  # Medium: 2.5x
        FeedbackGrade.EASY: 4.0,    # Easy: 4x
    },
    'difficulty_change': {
        FeedbackGrade.AGAIN: 0.5,   # Failure: +0.5 difficulty
        FeedbackGrade.HARD: 0.2,    # Hard: +0.2
        FeedbackGrade.MEDIUM: -0.1, # Medium: -0.1
        FeedbackGrade.EASY: -0.3,   # Easy: -0.3
    }
}
```

**Do NOT change these unless you understand FSRS optimization.**
They're based on research and large-scale data fitting.

## Testing Your Setup

Run the test script to verify everything works:

```bash
python test_fsrs.py
```

This creates a temporary database and demonstrates:
- Card state initialization
- Stability/difficulty updates
- Retrievability calculation over time
- Due card scheduling

## Analytics

### View Card States

```python
from core import log_repo

# Get all cards with current state
cards = log_repo.get_all_cards_with_state('word_translation')

for card in sorted(cards, key=lambda c: c['retrievability']):
    print(f"{card['lemma']:15} "
          f"R={card['retrievability']:.0%} "
          f"S={card['stability']:.1f}d "
          f"D={card['difficulty']:.1f}")
```

### View Due Cards

```python
from core import log_repo

due = log_repo.get_due_cards('word_translation', threshold=0.70)
print(f"{len(due)} cards due for review")

for card in due[:10]:  # Top 10 most urgent
    print(f"{card['lemma']} - {card['retrievability']:.0%}")
```

### Check Individual Card

```python
from core import log_repo

state = log_repo.get_card_state('huis', 'noun', 'word_translation')
print(f"Stability: {state['stability']:.2f} days")
print(f"Difficulty: {state['difficulty']:.1f}")
print(f"Retrievability: {state['retrievability']:.0%}")
print(f"Reviews: {state['review_count']}")
```

## Future Enhancements

Not yet implemented (from project_context.md):

1. **Multiple Exercise Types**
   - Current: Only `word_translation` (Dutch → English)
   - Future: Articles, verb conjugations, prepositions, etc.
   - Each exercise type gets independent card state

2. **Parameter Optimization**
   - Current: Fixed FSRS weights
   - Future: Optimize weights based on your review history

3. **Confidence Intervals**
   - Show uncertainty bounds on retrievability predictions

4. **Learning Curve Visualization**
   - Plot stability/difficulty over time
   - Identify problem words

## Troubleshooting

### "No cards due" immediately after starting

This is normal! If you just reviewed words, they all have R ≈ 100%.
Wait a day or increase `max_new_cards` to see new words.

### All cards showing R = 100%

You just reviewed them. Come back tomorrow to see retrievability decay.

### Session ends too quickly

Increase `max_new_cards` or lower `RETRIEVABILITY_THRESHOLD`.

### Too many due cards overwhelming

This happens if you skip several days. FSRS will catch up as you review.
Consider temporarily increasing threshold to reduce backlog.

## References

- [FSRS Algorithm Paper](https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-Algorithm)
- [FSRS-4.5 Implementation](https://github.com/open-spaced-repetition/fsrs-optimizer)
- Project context: [project_context.md](project_context.md)

---

**Ready to start?**

1. Migrate your database: `python migrate_to_fsrs.py`
2. Test the system: `python test_fsrs.py`
3. Run the app: `.\run_app.ps1`

Happy learning! 🇳🇱
