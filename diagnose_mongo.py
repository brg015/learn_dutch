"""
Diagnose MongoDB Atlas performance issues.
"""

import time
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
print("=" * 60)
print("MongoDB Atlas Diagnostics")
print("=" * 60)

# Parse connection details
if "mongodb.net" in mongo_uri:
    print("\nConnection: MongoDB Atlas (Cloud)")
    # Extract cluster region if possible
    if "cluster0" in mongo_uri.lower():
        print("Cluster: Free tier (M0)")
else:
    print(f"\nConnection: {mongo_uri[:50]}...")

print("\n--- Test 1: Connection Time ---")
start = time.time()
client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = client["dutch_trainer"]
collection = db["lexicon"]

# Force connection
try:
    client.admin.command("ping")
    connection_time = time.time() - start
    print(f"Connection established: {connection_time*1000:.2f}ms")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

print("\n--- Test 2: Simple Queries ---")

# Test count without filter
start = time.time()
count = collection.count_documents({})
elapsed = time.time() - start
print(f"count_documents({{}}): {elapsed*1000:.2f}ms (found {count} documents)")

# Test count with filter
start = time.time()
count_enriched = collection.count_documents({"enrichment.enriched": True})
elapsed = time.time() - start
print(f"count_documents({{enriched: True}}): {elapsed*1000:.2f}ms (found {count_enriched} documents)")

# Test find_one
start = time.time()
doc = collection.find_one({})
elapsed = time.time() - start
print(f"find_one({{}}): {elapsed*1000:.2f}ms")

# Test aggregation (like get_all_tags)
start = time.time()
pipeline = [
    {"$unwind": "$user_tags"},
    {"$group": {"_id": "$user_tags"}},
    {"$sort": {"_id": 1}}
]
tags = list(collection.aggregate(pipeline))
elapsed = time.time() - start
print(f"aggregate(user_tags): {elapsed*1000:.2f}ms (found {len(tags)} tags)")

# Test $sample (random)
start = time.time()
results = list(collection.aggregate([{"$sample": {"size": 1}}]))
elapsed = time.time() - start
print(f"aggregate({{$sample: 1}}): {elapsed*1000:.2f}ms")

print("\n--- Test 3: Index Analysis ---")
indexes = list(collection.list_indexes())
print(f"Number of indexes: {len(indexes)}")
for idx in indexes:
    print(f"  - {idx['name']}: {idx.get('key', {})}")

print("\n--- Test 4: Connection Pooling ---")
# Test if reusing connection is faster
start = time.time()
for i in range(5):
    collection.count_documents({})
elapsed = time.time() - start
avg = (elapsed / 5) * 1000
print(f"5x count_documents (reused connection): avg {avg:.2f}ms per query")

print("\n--- Test 5: Network Latency Estimate ---")
# Ping test
pings = []
for i in range(3):
    start = time.time()
    client.admin.command("ping")
    pings.append((time.time() - start) * 1000)
avg_ping = sum(pings) / len(pings)
print(f"Average ping to Atlas: {avg_ping:.2f}ms")

print("\n" + "=" * 60)
print("Analysis & Recommendations")
print("=" * 60)

if avg_ping > 200:
    print("\n⚠️  HIGH LATENCY: Network ping > 200ms")
    print("   Likely cause: Atlas cluster in a different region")
    print("   Solution: Create cluster in your region (e.g., US-East if you're in US)")
elif avg_ping > 50:
    print("\n⚠️  MODERATE LATENCY: Network ping 50-200ms")
    print("   This is normal for cloud databases")
    print("   Solution: Aggressive caching recommended")
else:
    print(f"\n✓ Network latency looks good ({avg_ping:.2f}ms)")

if avg > 100:
    print("\n⚠️  SLOW QUERIES: Queries taking >100ms each")
    print("   Possible causes:")
    print("   1. Cold start (first query after idle)")
    print("   2. Missing indexes")
    print("   3. Free tier throttling")
    print("\n   Solutions:")
    print("   - Add index on 'enrichment.enriched'")
    print("   - Use connection pooling")
    print("   - Cache query results aggressively")

# Check for missing indexes
has_enriched_index = any("enrichment.enriched" in str(idx.get("key", {})) for idx in indexes)
has_lemma_pos_index = any("lemma" in str(idx.get("key", {})) and "pos" in str(idx.get("key", {})) for idx in indexes)

print("\n--- Index Recommendations ---")
if not has_enriched_index:
    print("⚠️  MISSING: Index on 'enrichment.enriched'")
    print("   Run: collection.create_index([('enrichment.enriched', 1)])")
else:
    print("✓ Index exists: enrichment.enriched")

if not has_lemma_pos_index:
    print("⚠️  MISSING: Compound index on 'lemma' + 'pos'")
    print("   Run: collection.create_index([('lemma', 1), ('pos', 1)], unique=True)")
else:
    print("✓ Index exists: lemma + pos")

client.close()
