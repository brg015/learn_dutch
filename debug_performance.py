"""
Debug script to measure performance of different operations.
"""

import time
from core import lexicon_repo, scheduler, log_repo

def time_operation(name, func, *args, **kwargs):
    """Time a function call and print results."""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    print(f"{name}: {elapsed*1000:.2f}ms")
    return result, elapsed

print("=" * 60)
print("Performance Diagnostics")
print("=" * 60)

# Test 1: MongoDB connection
print("\n1. MongoDB Operations:")
time_operation("  count_words(enriched_only=False)", lexicon_repo.count_words, enriched_only=False)
time_operation("  count_words(enriched_only=True)", lexicon_repo.count_words, enriched_only=True)
time_operation("  get_random_word(enriched_only=False)", lexicon_repo.get_random_word, enriched_only=False)
time_operation("  get_all_tags()", lexicon_repo.get_all_tags)

# Test 2: Scheduler (includes MongoDB + SQLite)
print("\n2. Scheduler Operations:")
time_operation("  select_next_word(exclude_recent=False)", scheduler.select_next_word, enriched_only=False, exclude_recent=False)
time_operation("  select_next_word(exclude_recent=True)", scheduler.select_next_word, enriched_only=False, exclude_recent=True)

# Test 3: SQLite operations
print("\n3. SQLite Operations:")
time_operation("  get_recent_events(limit=1)", log_repo.get_recent_events, limit=1)
time_operation("  get_review_count('test', 'verb')", log_repo.get_review_count, "test", "verb")

# Test 4: Multiple operations (simulating app flow)
print("\n4. Simulating App Flow:")
start = time.time()
# What happens when you click a button
counts = {"total": lexicon_repo.count_words(enriched_only=False), "enriched": lexicon_repo.count_words(enriched_only=True)}
word = scheduler.select_next_word(enriched_only=False, exclude_recent=True)
tags = lexicon_repo.get_all_tags()
elapsed = time.time() - start
print(f"  Full app flow: {elapsed*1000:.2f}ms")

print("\n" + "=" * 60)
print("Analysis:")
print("=" * 60)

# Identify slow operations
if elapsed > 1.0:
    print("⚠️  SLOW: Full app flow takes > 1 second")
    print("    This will make the UI feel sluggish")
    print("\nLikely causes:")
    print("  1. MongoDB on Atlas (network latency)")
    print("  2. get_all_tags() with aggregation pipeline")
    print("  3. Multiple count_words() calls")
    print("\nSolutions to try:")
    print("  - Cache get_all_tags() (rarely changes)")
    print("  - Use local MongoDB instead of Atlas")
    print("  - Reduce MongoDB queries per page load")
else:
    print("✓ Performance looks good!")

print("\nMongoDB Details:")
import os
from dotenv import load_dotenv
load_dotenv()
mongo_uri = os.getenv("MONGO_URI", "")
if "mongodb.net" in mongo_uri or "cloud" in mongo_uri:
    print("  Using: MongoDB Atlas (cloud)")
    print("  → Network latency expected (50-200ms per query)")
elif "localhost" in mongo_uri or "127.0.0.1" in mongo_uri:
    print("  Using: Local MongoDB")
    print("  → Should be fast (<10ms per query)")
else:
    print(f"  Using: {mongo_uri[:30]}...")
