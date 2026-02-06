"""
MongoDB repository for lexicon access.

Provides functions to query and retrieve words from the lexicon.
"""

from __future__ import annotations

import os
from typing import Optional, Sequence

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection


# Load environment
load_dotenv()

# Configuration
DB_NAME = "dutch_trainer"
COLLECTION_NAME = "lexicon"
ONLY_ENRICHED = True # If True, enriched_only is always enforced

# Global connection pool (reused across requests)
_client: Optional[MongoClient] = None
_collection: Optional[Collection] = None


# ---- Connection Management ----

def get_collection() -> Collection:
    """
    Get a connection to the MongoDB lexicon collection.

    Uses a persistent connection pool that's reused across requests
    to avoid the 5-second cold start on every query.

    Returns:
        MongoDB collection object
    """
    global _client, _collection

    # Return cached collection if it exists
    if _collection is not None:
        return _collection

    # Create new connection
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI not found in environment variables")

    _client = MongoClient(
        mongo_uri,
        maxPoolSize=10,  # Connection pool size
        minPoolSize=1,   # Keep at least 1 connection alive
        maxIdleTimeMS=60000  # Keep connections alive for 60 seconds
    )
    db = _client[DB_NAME]
    _collection = db[COLLECTION_NAME]

    return _collection


# ---- Query Functions ----

def _should_filter_enriched(enriched_only: bool) -> bool:
    """
    Determine whether to enforce enriched-only filtering.

    If ONLY_ENRICHED is enabled, always filter to enriched words.
    """
    if ONLY_ENRICHED:
        return True
    return bool(enriched_only)


def get_all_words(
    enriched_only: bool = False,
    user_tags: Optional[Sequence[str]] = None,
    pos: Optional[Sequence[str]] = None,
    require_verb_meta: bool = False
) -> list[dict]:
    """
    Get all words from the lexicon.

    Args:
        enriched_only: If True, only return enriched words
        user_tags: If provided, filter by these user_tags (OR semantics)
        pos: Optional part of speech filters (e.g., ["verb"])
        require_verb_meta: If True, only include verbs with verb_meta populated
    
    Notes:
        If ONLY_ENRICHED is True, enriched_only is forced regardless of input.

    Returns:
        List of lexicon entry dictionaries
    """
    collection = get_collection()

    query = {}

    if _should_filter_enriched(enriched_only):
        query["word_enrichment.enriched"] = True

    if user_tags:
        # NOTE: For now, only user_tags are used. We'll merge tags later.
        query["user_tags"] = {"$in": list(user_tags)}

    if pos:
        query["pos"] = {"$in": list(pos)}

    if require_verb_meta:
        query["verb_meta"] = {"$ne": None}

    return list(collection.find(query))


def get_enriched_verbs(
    user_tags: Optional[Sequence[str]] = None
) -> list[dict]:
    """
    Get all verbs with Phase 2 enrichment (verb_meta populated).
    """
    return get_all_words(
        enriched_only=True,
        user_tags=user_tags,
        pos=["verb"],
        require_verb_meta=True
    )


def get_user_tag_counts(min_count: int = 20) -> list[dict]:
    """
    Return user tag counts for UI selection.

    Args:
        min_count: Minimum number of matches to include a tag.
    """
    collection = get_collection()
    pipeline = [
        {"$unwind": "$user_tags"},
        {"$group": {"_id": "$user_tags", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": min_count}}},
        {"$sort": {"count": -1}},
    ]
    return [
        {"tag": item["_id"], "count": item["count"]}
        for item in collection.aggregate(pipeline)
    ]


def get_word_by_id(word_id: str) -> Optional[dict]:
    """
    Get a word by its unique word_id.

    Args:
        word_id: The unique word identifier

    Returns:
        Lexicon entry dictionary, or None if not found
    """
    collection = get_collection()
    query = {"word_id": word_id}
    if ONLY_ENRICHED:
        query["word_enrichment.enriched"] = True
    return collection.find_one(query)
