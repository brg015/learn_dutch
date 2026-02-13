"""
SQLAlchemy ORM Models for FSRS Database

Defines CardState and ReviewEvent models for Postgres persistence.
Maps to the previously SQLite-based schema.
"""

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CardState(Base):
    """
    Persistent memory state for a single card (word_id + exercise_type).
    
    Represents the FSRS state of a flashcard used in spaced repetition.
    """
    __tablename__ = 'card_state'

    # Primary key: composite of user_id, word_id, and exercise_type
    user_id = Column(String(255), primary_key=True, nullable=False)
    word_id = Column(String(255), primary_key=True, nullable=False)
    exercise_type = Column(String(50), primary_key=True, nullable=False)

    # Metadata for readability and backward compatibility
    lemma = Column(String(255), nullable=False)
    pos = Column(String(50), nullable=False)

    # Long-term memory parameters
    stability = Column(Float, nullable=False)  # How slowly the card is forgotten
    difficulty = Column(Float, nullable=False)  # How hard this card is for the user
    d_eff = Column(Float, nullable=False)  # Effective difficulty (for next LTM update)

    # Review tracking
    review_count = Column(Integer, nullable=False)
    last_review_timestamp = Column(DateTime(timezone=True), nullable=False)
    last_ltm_timestamp = Column(DateTime(timezone=True), nullable=True)
    ltm_review_date = Column(String(255), nullable=True)

    # Short-term memory tracking (reset after LTM)
    stm_success_count_today = Column(Integer, nullable=False, default=0)

    # Metadata
    d_floor = Column(Float, nullable=True)  # Floor difficulty from last LTM update

    def __repr__(self):
        return f"<CardState({self.user_id}, {self.word_id}, {self.exercise_type})>"


class ReviewEvent(Base):
    """
    Log entry for a single review attempt of a card.
    
    Captures all relevant state before/after a review, including feedback and timing.
    """
    __tablename__ = 'review_events'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # User scope and card identifiers
    user_id = Column(String(255), nullable=False)
    word_id = Column(String(255), nullable=False)
    exercise_type = Column(String(50), nullable=False)

    # Metadata for readability and analytics
    lemma = Column(String(255), nullable=False)
    pos = Column(String(50), nullable=False)

    # Timing and feedback
    timestamp = Column(DateTime(timezone=True), nullable=False)
    feedback_grade = Column(Integer, nullable=False)  # 1=AGAIN, 2=HARD, 3=MEDIUM, 4=EASY
    latency_ms = Column(Integer, nullable=True)  # Time taken to answer

    # State before review
    stability_before = Column(Float, nullable=True)
    difficulty_before = Column(Float, nullable=True)
    d_eff_before = Column(Float, nullable=True)
    retrievability_before = Column(Float, nullable=True)

    # State after review
    stability_after = Column(Float, nullable=False)
    difficulty_after = Column(Float, nullable=False)
    d_eff_after = Column(Float, nullable=False)

    # Event type
    is_ltm_event = Column(Integer, nullable=False)  # 1 for LTM, 0 for STM, 2 for KNOWN no-score fallback

    # Session context (optional, for analytics)
    session_id = Column(String(255), nullable=True)
    session_position = Column(Integer, nullable=True)
    presentation_mode = Column(String(50), nullable=True)  # "words", "sentences", etc.

    def __repr__(self):
        return f"<ReviewEvent(id={self.id}, {self.word_id}/{self.exercise_type}, feedback={self.feedback_grade})>"
