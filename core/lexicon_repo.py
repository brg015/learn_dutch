"""
MongoDB repository for lexicon access.

Provides functions to query and retrieve words from the lexicon.
"""

from __future__ import annotations

import os
from typing import Optional

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
    tag: Optional[str] = None,
    pos: Optional[str] = None,
    require_verb_meta: bool = False
) -> list[dict]:
    """
    Get all words from the lexicon.

    Args:
        enriched_only: If True, only return enriched words
        tag: If provided, filter by this tag (checks both user_tags and tags)
        pos: Optional part of speech filter (e.g., "verb")
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

    if tag:
        # Match tag in either user_tags OR AI-generated tags
        query["$or"] = [
            {"user_tags": tag},
            {"tags": tag}
        ]

    if pos:
        query["pos"] = pos

    if require_verb_meta:
        query["verb_meta"] = {"$ne": None}

    return list(collection.find(query))


def get_enriched_verbs() -> list[dict]:
    """
    Get all verbs with Phase 2 enrichment (verb_meta populated).
    """
    return get_all_words(pos="verb", require_verb_meta=True)


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
