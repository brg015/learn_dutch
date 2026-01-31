"""
Pydantic models for the Dutch vocabulary lexicon.

These models define the structure of MongoDB documents and support
AI-enrichment with structured outputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


# Configuration
MAX_EXAMPLES_PER_FORM = 5  # Maximum number of example sentences per form/tense


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

class FixedPreposition(BaseModel):
    """
    Fixed preposition for adjectives/nouns - conventional collocations.

    For adjectives/nouns where the preposition is selectionally preferred but not obligatory
    (e.g., 'bang voor', 'trots op', 'behoefte aan'). The preposition introduces a complement.
    """
    preposition: str = Field(..., description="The preposition (e.g., 'voor', 'op', 'aan')")
    usage_frequency: str = Field(
        ...,
        description="Frequency of this collocation: 'dominant' (80%+), 'common' (15-30%), 'rare' (<15%)"
    )
    meaning_context: Optional[str] = Field(
        default=None,
        description="Explanation of meaning or context (e.g., 'when expressing fear', 'in formal contexts')"
    )
    examples: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM, description="Example sentences showing usage")


# ---- POS-specific metadata ----

class NounMetadata(BaseModel):
    """Metadata specific to nouns."""
    article: Optional[Article] = None
    plural: Optional[str] = None
    diminutive: Optional[str] = None

    # Fixed prepositions (e.g., "angst voor", "behoefte aan")
    fixed_prepositions: Optional[list[FixedPreposition]] = Field(
        default=None,
        description="Fixed prepositions for this noun (if any). Max 2, ordered by frequency."
    )

    # Examples showing different forms
    examples_singular: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_plural: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)

    class Config:
        use_enum_values = True  # Store enum values as strings


class VerbPrepositionUsage(BaseModel):
    """
    Prepositional verb usage - the preposition is part of the verb phrase.

    For verbs where the preposition is valency-bound (e.g., 'denken aan', 'houden van').
    These are multi-word verbs where the preposition fundamentally changes the meaning.
    """
    preposition: str = Field(..., description="The preposition (e.g., 'aan', 'op', 'van')")
    meaning: str = Field(..., description="English translation of the phrasal verb (e.g., 'to think of', 'to love')")
    case_note: Optional[str] = Field(default=None, description="Grammatical notes about usage")
    examples: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM, description="Example sentences")


class VerbMetadata(BaseModel):
    """Metadata specific to verbs."""
    past_singular: Optional[str] = None  # ik liep
    past_plural: Optional[str] = None    # wij liepen
    past_participle: Optional[str] = None  # gelopen
    auxiliary: Optional[VerbAuxiliary] = None  # hebben or zijn
    separable: Optional[bool] = None
    separable_prefix: Optional[str] = None  # e.g., "op" in "opstaan"

    # Reflexive verbs (e.g., "zich schamen", "zich vergissen")
    is_reflexive: Optional[bool] = None  # True if verb requires "zich"

    # Irregularity flags (important for FSRS difficulty)
    is_irregular_past: Optional[bool] = None  # True if past tense is irregular
    is_irregular_participle: Optional[bool] = None  # True if past participle is irregular

    # Prepositional verb usage (phrasal verbs with fixed prepositions)
    preposition_usage: list[VerbPrepositionUsage] = Field(
        default_factory=list,
        description="List of prepositional verb uses (e.g., 'denken aan', 'wachten op'). Max 5-6."
    )

    # Examples for different tenses/forms (for verbs without prepositions, or general tense examples)
    examples_present: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_past: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_perfect: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)

    class Config:
        use_enum_values = True  # Store enum values as strings


class AdjectiveMetadata(BaseModel):
    """Metadata specific to adjectives."""
    comparative: Optional[str] = None  # groter, or "meer tevreden"
    superlative: Optional[str] = None  # grootst, or "meest tevreden"

    # Irregularity flags (important for FSRS difficulty and learner awareness)
    is_irregular_comparative: Optional[bool] = Field(
        default=False,
        description="True if comparative is irregular (different stem, uses 'meer', or unusual spelling)"
    )
    is_irregular_superlative: Optional[bool] = Field(
        default=False,
        description="True if superlative is irregular (different stem, uses 'meest', or unusual spelling)"
    )

    # Fixed prepositions (e.g., "bang voor", "trots op", "goed in")
    fixed_prepositions: Optional[list[FixedPreposition]] = Field(
        default=None,
        description="Fixed prepositions for this adjective (if any). Max 3, ordered by frequency."
    )

    # Examples showing different forms
    examples_base: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_comparative: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)
    examples_superlative: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM)

    class Config:
        use_enum_values = True  # Store enum values as strings


# ---- Import Data ----

class ImportData(BaseModel):
    """Preserves the original import data from CSV."""
    imported_word: str = Field(..., description="The Dutch word as imported (may not be lemma)")
    imported_translation: str = Field(..., description="The English translation as imported")
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When this was imported")


# ---- AI Enrichment Metadata ----

class WordEnrichment(BaseModel):
    """
    Phase 1 enrichment metadata - basic word info (lemma, POS, translation, etc.).

    Version History:
    - v1: Initial implementation
    - v2: Translation/definition guaranteed to be for lemma (not imported_word)
    """
    enriched: bool = False
    enriched_at: Optional[datetime] = None
    model_used: Optional[str] = None  # e.g., "gpt-4o-2024-08-06"
    version: int = 1  # version of enrichment prompt used (default: 1, set to 2 for new enrichments)
    lemma_normalized: bool = False  # did AI correct the lemma from imported_word?
    approved: bool = False  # manual approval of Phase 1 data


class PosEnrichment(BaseModel):
    """Phase 2 enrichment metadata - POS-specific metadata (conjugations, declensions, etc.)."""
    enriched: bool = False
    enriched_at: Optional[datetime] = None
    model_used: Optional[str] = None  # e.g., "gpt-4o-2024-08-06"
    version: int = 1  # increment if re-enriched
    approved: bool = False  # manual approval of Phase 2 data


# ---- Main Lexicon Entry ----

class LexiconEntry(BaseModel):
    """
    A single word entry in the MongoDB lexicon.

    Each entry has a unique word_id to handle homonyms (e.g., 'bank' as financial institution vs couch).
    """
    # Unique identifier (auto-generated if not provided)
    word_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this word entry (UUID). Auto-generated if not provided."
    )

    # Import tracking (preserves original data)
    import_data: Optional[ImportData] = None

    # Entry classification
    entry_type: EntryType = Field(default=EntryType.WORD, description="Type of entry (word vs phrase)")

    # Required fields
    lemma: str = Field(..., description="Dictionary form of the word (may be normalized from imported_word)")
    pos: PartOfSpeech = Field(default=PartOfSpeech.OTHER, description="Part of speech")

    # Optional sense disambiguator for homonyms
    sense: Optional[str] = Field(
        default=None,
        description="Disambiguates homonyms (e.g., 'bank (financial)' vs 'bank (couch)'). Usually None for unique lemma+pos."
    )

    # Translation and definition
    translation: str = Field(
        default="",
        description="The single best, most common English translation for flashcards"
    )
    definition: Optional[str] = Field(
        default=None,
        description="Clear explanation with context and nuance (1-2 sentences). Mentions alternative translations if relevant."
    )

    # Optional common fields
    difficulty: CEFRLevel = Field(default=CEFRLevel.UNKNOWN, description="CEFR difficulty level")
    tags: list[str] = Field(default_factory=list, description="AI-generated semantic tags (e.g., travel, finance, emotions)")
    user_tags: list[str] = Field(default_factory=list, description="User-defined tags (e.g., 'Chapter 10', 'work vocabulary')")

    # POS-specific metadata (only populated for relevant types)
    noun_meta: Optional[NounMetadata] = None
    verb_meta: Optional[VerbMetadata] = None
    adjective_meta: Optional[AdjectiveMetadata] = None

    # General examples (for POS types without specific metadata)
    general_examples: list[BilingualExample] = Field(default_factory=list, description="Examples for other POS types")

    # AI enrichment tracking (modular two-phase approach)
    word_enrichment: WordEnrichment = Field(default_factory=WordEnrichment, description="Phase 1 enrichment metadata")
    pos_enrichment: PosEnrichment = Field(default_factory=PosEnrichment, description="Phase 2 enrichment metadata")

    class Config:
        use_enum_values = True  # Store enum values as strings in MongoDB


# ---- AI Enrichment Response Models ----

class AIBasicEnrichment(BaseModel):
    """
    Phase 1 enrichment: Basic word information (modular approach).

    Returns lemma, POS, translation, definition, difficulty, tags, and general examples.
    Does NOT include POS-specific metadata (conjugations, declensions, etc.).

    Version History:
    - v1: Initial implementation
    - v2: Ensures translation and definition are based on the normalized lemma,
          not the imported_word. The AI should always provide translation/definition
          for the lemma form, even if the imported_word was inflected (e.g., "liep" -> "lopen").
    """
    lemma: str
    pos: PartOfSpeech
    sense: Optional[str] = Field(default=None, description="Sense disambiguator for homonyms (usually None)")
    translation: str = Field(..., description="The single best, most common English translation FOR THE LEMMA")
    definition: str = Field(..., description="Clear explanation with context and nuance (1-2 sentences) FOR THE LEMMA")
    difficulty: CEFRLevel = CEFRLevel.UNKNOWN
    tags: list[str] = Field(default_factory=list, max_length=5, description="Max 5 semantic tags")
    general_examples: list[BilingualExample] = Field(default_factory=list, max_length=MAX_EXAMPLES_PER_FORM, description="General examples")

    class Config:
        use_enum_values = True


class AINounEnrichment(BaseModel):
    """Phase 2 enrichment for nouns: declension and examples."""
    noun_meta: NounMetadata

    class Config:
        use_enum_values = True


class AIVerbEnrichment(BaseModel):
    """Phase 2 enrichment for verbs: conjugation, prepositions, and examples."""
    verb_meta: VerbMetadata

    class Config:
        use_enum_values = True


class AIAdjectiveEnrichment(BaseModel):
    """Phase 2 enrichment for adjectives: comparison and examples."""
    adjective_meta: AdjectiveMetadata

    class Config:
        use_enum_values = True
