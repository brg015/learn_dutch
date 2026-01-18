"""
Pydantic models for the Dutch vocabulary lexicon.

These models define the structure of MongoDB documents and support
AI-enrichment with structured outputs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# Configuration
MAX_EXAMPLES_PER_FORM = 2  # Maximum number of example sentences per form/tense


class EntryType(str, Enum):
    """Type of lexicon entry."""
    WORD = "word"           # Single word
    PHRASE = "phrase"       # Multi-word expression
    IDIOM = "idiom"         # Idiomatic expression (future)
    COLLOCATION = "collocation"  # Common word pairing (future)


class PartOfSpeech(str, Enum):
    """Part of speech categories."""
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    INTERJECTION = "interjection"
    OTHER = "other"


class CEFRLevel(str, Enum):
    """Common European Framework of Reference for Languages levels."""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
    UNKNOWN = "unknown"


class Article(str, Enum):
    """Dutch articles for nouns."""
    DE = "de"
    HET = "het"
    BOTH = "de/het"  # some nouns can use either


class VerbAuxiliary(str, Enum):
    """Auxiliary verbs used for perfect tense."""
    HEBBEN = "hebben"
    ZIJN = "zijn"
    BOTH = "hebben/zijn"


# ---- Example Sentences ----

class BilingualExample(BaseModel):
    """A bilingual example sentence pair."""
    dutch: str = Field(..., description="Dutch sentence")
    english: str = Field(..., description="English translation")


# ---- POS-specific metadata ----

class NounMetadata(BaseModel):
    """Metadata specific to nouns."""
    article: Optional[Article] = None
    plural: Optional[str] = None
    diminutive: Optional[str] = None

    # Examples showing different forms
    examples_singular: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_plural: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)


class VerbMetadata(BaseModel):
    """Metadata specific to verbs."""
    past_singular: Optional[str] = None  # ik liep
    past_plural: Optional[str] = None    # wij liepen
    past_participle: Optional[str] = None  # gelopen
    auxiliary: Optional[VerbAuxiliary] = None  # hebben or zijn
    separable: Optional[bool] = None
    separable_prefix: Optional[str] = None  # e.g., "op" in "opstaan"

    # Common prepositions used with this verb
    common_prepositions: list[str] = Field(
        default_factory=list,
        description="All common prepositions used with this verb (e.g., 'aan', 'op', 'van')"
    )

    # Examples for different tenses/forms
    examples_present: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_past: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_perfect: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)


class AdjectiveMetadata(BaseModel):
    """Metadata specific to adjectives."""
    comparative: Optional[str] = None  # groter
    superlative: Optional[str] = None  # grootst

    # Examples showing different forms
    examples_base: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_comparative: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_superlative: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)


# ---- Import Data ----

class ImportData(BaseModel):
    """Preserves the original import data from CSV."""
    imported_word: str = Field(..., description="The Dutch word as imported (may not be lemma)")
    imported_translation: str = Field(..., description="The English translation as imported")
    imported_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc), description="When this was imported")


# ---- AI Enrichment Metadata ----

class EnrichmentMetadata(BaseModel):
    """Tracks AI enrichment status and provenance."""
    enriched: bool = False
    enriched_at: Optional[datetime] = None
    model_used: Optional[str] = None  # e.g., "gpt-4o-2024-08-06"
    version: int = 1  # increment if re-enriched
    approved: bool = False  # manual approval (future)
    lemma_normalized: bool = False  # did AI correct the lemma from imported_word?


# ---- Main Lexicon Entry ----

class LexiconEntry(BaseModel):
    """
    A single word entry in the MongoDB lexicon.

    One document per lemma + POS combination.
    """
    # Import tracking (preserves original data)
    import_data: Optional[ImportData] = None

    # Entry classification
    entry_type: EntryType = Field(default=EntryType.WORD, description="Type of entry (word vs phrase)")

    # Required fields
    lemma: str = Field(..., description="Dictionary form of the word (may be normalized from imported_word)")
    pos: PartOfSpeech = Field(default=PartOfSpeech.OTHER, description="Part of speech")
    translations: list[str] = Field(default_factory=list, description="English translations")

    # Optional common fields
    difficulty: CEFRLevel = Field(default=CEFRLevel.UNKNOWN, description="CEFR difficulty level")
    tags: list[str] = Field(default_factory=list, description="AI-generated semantic tags (e.g., travel, finance, emotions)")
    user_tags: list[str] = Field(default_factory=list, description="User-defined tags (e.g., 'Chapter 10', 'work vocabulary')")
    frequency_rank: Optional[int] = None  # lower = more common

    # POS-specific metadata (only populated for relevant types)
    noun_meta: Optional[NounMetadata] = None
    verb_meta: Optional[VerbMetadata] = None
    adjective_meta: Optional[AdjectiveMetadata] = None

    # General examples (for POS types without specific metadata)
    general_examples: list[BilingualExample] = Field(default_factory=list, description="Examples for other POS types")

    # AI enrichment tracking
    enrichment: EnrichmentMetadata = Field(default_factory=EnrichmentMetadata)

    class Config:
        use_enum_values = True  # Store enum values as strings in MongoDB


# ---- AI Enrichment Response Model ----

class AIEnrichedEntry(BaseModel):
    """
    Structured output from AI enrichment.

    This is what the LLM returns when enriching a word.
    You can then merge this into a LexiconEntry.
    """
    lemma: str
    pos: PartOfSpeech
    translations: list[str] = Field(..., min_length=1, description="At least one English translation")
    difficulty: CEFRLevel = CEFRLevel.UNKNOWN
    tags: list[str] = Field(default_factory=list, max_length=5, description="Max 5 semantic tags")

    # POS-specific (AI fills these based on pos)
    noun_meta: Optional[NounMetadata] = None
    verb_meta: Optional[VerbMetadata] = None
    adjective_meta: Optional[AdjectiveMetadata] = None

    # For other POS types
    general_examples: list[BilingualExample] = Field(default_factory=list, max_length=3)

    class Config:
        use_enum_values = True
