"""
MongoDB repository for lexicon access.

Provides functions to query and retrieve words from the lexicon.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

from core.schemas import LexiconEntry

# Load environment
load_dotenv()

# Configuration
DB_NAME = "dutch_trainer"
COLLECTION_NAME = "lexicon"
ONLY_ENRICHED = True # If True, only use enriched words

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
    tag: Optional[str] = None
) -> list[dict]:
    """
    Get all words from the lexicon.

    Args:
        enriched_only: If True, only return enriched words
        tag: If provided, filter by this tag (checks both user_tags and tags)

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

    return list(collection.find(query))


def get_word_by_lemma_pos(lemma: str, pos: str) -> Optional[dict]:
    """
    Get a specific word by lemma and part of speech.

    Note: This returns the first match. For homonyms with different senses,
    use get_word_by_id() or specify the sense.

    Args:
        lemma: The word lemma
        pos: Part of speech (e.g., "verb", "noun")

    Returns:
        Lexicon entry dictionary, or None if not found
    """
    collection = get_collection()

    query = {
        "lemma": lemma,
        "pos": pos
    }
    if ONLY_ENRICHED:
        query["word_enrichment.enriched"] = True
    return collection.find_one(query)


# Backward compatibility alias
get_word = get_word_by_lemma_pos


def get_random_word(
    enriched_only: bool = True,
    tag: Optional[str] = None,
    exclude_lemmas: Optional[set[tuple[str, str]]] = None
) -> Optional[dict]:
    """
    Get a random word from the lexicon.

    Args:
        enriched_only: If True, only select from enriched words
        tag: If provided, filter by this tag (checks both user_tags and tags)
        exclude_lemmas: Optional set of (lemma, pos) tuples to exclude

    Returns:
        Random lexicon entry dictionary, or None if no words match
    """
    collection = get_collection()

    # Build query
    query = {}

    if _should_filter_enriched(enriched_only):
        query["word_enrichment.enriched"] = True

    if tag:
        # Match tag in either user_tags OR AI-generated tags
        query["$or"] = [
            {"user_tags": tag},
            {"tags": tag}
        ]

    if exclude_lemmas:
        # Exclude specific lemma+pos combinations
        exclude_conditions = [
            {"lemma": lemma, "pos": pos}
            for lemma, pos in exclude_lemmas
        ]
        if exclude_conditions:
            query["$nor"] = exclude_conditions

    # Use MongoDB's $sample aggregation for random selection
    pipeline = [
        {"$match": query},
        {"$sample": {"size": 1}}
    ]

    results = list(collection.aggregate(pipeline))

    if results:
        return results[0]
    return None


def get_words_by_tag(tag: str, enriched_only: bool = True) -> list[dict]:
    """
    Get all words with a specific tag.

    Args:
        tag: The tag to filter by (checks both user_tags and tags)
        enriched_only: If True, only return enriched words

    Returns:
        List of lexicon entry dictionaries
    """
    collection = get_collection()

    query = {
        "$or": [
            {"user_tags": tag},
            {"tags": tag}
        ]
    }

    if _should_filter_enriched(enriched_only):
        query["word_enrichment.enriched"] = True

    return list(collection.find(query))


def count_words(enriched_only: bool = False) -> int:
    """
    Count total words in the lexicon.

    Args:
        enriched_only: If True, only count enriched words

    Returns:
        Total number of words
    """
    collection = get_collection()

    query = {}
    if _should_filter_enriched(enriched_only):
        query["word_enrichment.enriched"] = True

    return collection.count_documents(query)


def get_all_tags() -> list[str]:
    """
    Get all unique tags (both user_tags and AI-generated tags) in the lexicon.

    Returns the union of both tag types.

    Useful for UI filters.

    Returns:
        Sorted list of unique tags
    """
    collection = get_collection()

    # Get all user_tags
    user_tags_pipeline = [
        {"$unwind": "$user_tags"},
        {"$group": {"_id": "$user_tags"}}
    ]

    # Get all AI-generated tags
    ai_tags_pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags"}}
    ]

    user_tags = {doc["_id"] for doc in collection.aggregate(user_tags_pipeline)}
    ai_tags = {doc["_id"] for doc in collection.aggregate(ai_tags_pipeline)}

    # Return sorted union
    all_tags = user_tags | ai_tags
    return sorted(all_tags)


# ---- Utility Functions ----

def word_exists(lemma: str, pos: str) -> bool:
    """
    Check if a word exists in the lexicon.

    Args:
        lemma: The word lemma
        pos: Part of speech

    Returns:
        True if the word exists, False otherwise
    """
    return get_word(lemma, pos) is not None


def generate_word_id() -> str:
    """
    Generate a unique word ID (UUID).

    Returns:
        UUID string
    """
    return str(uuid.uuid4())


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
