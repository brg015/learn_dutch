"""
Database - FSRS Database I/O Operations

Handles all database operations for card state and review events.
Uses SQLAlchemy ORM with Postgres backend.

This module handles ONLY database I/O.
Algorithm logic is handled by the scheduler module.
"""

from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from core.fsrs.models import Base, CardState as CardStateModel, ReviewEvent as ReviewEventModel
from core.fsrs.memory_state import CardState, CardStateSnapshot
from core.fsrs.constants import FeedbackGrade


# Database configuration
def get_database_url() -> str:
    """
    Get the database URL from environment variables.
    
    Uses TEST_MODE env var to determine which database to connect to.
    Assumes DATABASE_URL contains a connection string with the prod database name.
    For test mode, replaces 'learning_db' with 'test_learning_db' in the connection string.
    
    Returns:
        Database URL (Postgres connection string)
    """
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Please set it to a Postgres connection string (e.g., "
            "postgresql://user:password@host:port/learning_db)"
        )
    
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    if test_mode:
        # Replace production db name with test db name
        url = base_url.replace("learning_db", "test_learning_db")
        return url
    
    return base_url


def get_engine():
    """
    Get SQLAlchemy engine for database connection.
    
    Uses connection pooling for better performance.
    
    Returns:
        SQLAlchemy Engine instance
    """
    db_url = get_database_url()
    return create_engine(
        db_url,
        pool_size=5,           # Keep 5 connections open
        max_overflow=10,       # Allow up to 10 extra connections
        pool_pre_ping=True,    # Verify connections before use
        echo=False
    )


def get_session() -> Session:
    """
    Get a SQLAlchemy session for database operations.
    
    Returns:
        SQLAlchemy Session instance
    """
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()


def is_test_mode() -> bool:
    """Check if running in test mode."""
    return os.getenv("TEST_MODE", "false").lower() == "true"


def get_default_user_id() -> str:
    """Get default user id for scoping review data."""
    return os.getenv("DEFAULT_USER_ID", "ben")


def init_db():
    """
    Initialize database schema if tables don't exist.
    
    Creates all tables defined in SQLAlchemy models.
    Safe to call multiple times - only creates tables if they don't exist.
    """
    engine = get_engine()
    
    # Check if tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Create all tables if they don't exist
    if 'card_state' not in existing_tables or 'review_events' not in existing_tables:
        Base.metadata.create_all(engine)
        # Silent initialization - no spam on every rerun
        return

    # If tables exist, ensure schema includes user_id
    card_columns = {col["name"] for col in inspector.get_columns("card_state")}
    event_columns = {col["name"] for col in inspector.get_columns("review_events")}
    if "user_id" not in card_columns or "user_id" not in event_columns:
        raise RuntimeError(
            "FSRS schema missing user_id column. "
            "Please reset or migrate the database to the new per-user schema."
        )


def reset_db():
    """
    DANGEROUS: Delete all data and recreate tables.
    
    Only use this for testing or when you want to start fresh.
    All review history will be lost!
    """
    engine = get_engine()
    Base.metadata.drop_all(engine)
    print("All tables dropped")
    
    # Recreate tables
    init_db()




def load_card_state(
    user_id: str,
    word_id: str,
    exercise_type: str
) -> Optional[CardState]:
    """
    Load card state from database.
    
    Args:
        user_id: User identifier for scoping review data
        word_id: Unique word identifier
        exercise_type: Type of exercise
    
    Returns:
        CardState if found, None if new card
    """
    session = get_session()
    try:
        db_card = session.query(CardStateModel).filter(
            CardStateModel.user_id == user_id,
            CardStateModel.word_id == word_id,
            CardStateModel.exercise_type == exercise_type
        ).first()
        
        if db_card is None:
            return None
        
        # Parse timestamps
        last_review_ts = datetime.fromisoformat(db_card.last_review_timestamp)
        last_ltm_ts = (
            datetime.fromisoformat(db_card.last_ltm_timestamp)
            if db_card.last_ltm_timestamp
            else None
        )
        
        return CardState(
            user_id=db_card.user_id,
            word_id=db_card.word_id,
            exercise_type=db_card.exercise_type,
            lemma=db_card.lemma,
            pos=db_card.pos,
            stability=db_card.stability,
            difficulty=db_card.difficulty,
            d_eff=db_card.d_eff,
            review_count=db_card.review_count,
            last_review_timestamp=last_review_ts,
            last_ltm_timestamp=last_ltm_ts,
            ltm_review_date=db_card.ltm_review_date,
            stm_success_count_today=db_card.stm_success_count_today
        )
    finally:
        session.close()


def save_card_state(card: CardState):
    """
    Save card state to database (insert or update).
    
    Args:
        card: CardState to save
    """
    session = get_session()
    try:
        # Try to find existing card
        db_card = session.query(CardStateModel).filter(
            CardStateModel.user_id == card.user_id,
            CardStateModel.word_id == card.word_id,
            CardStateModel.exercise_type == card.exercise_type
        ).first()
        
        if db_card is None:
            # Create new card
            db_card = CardStateModel(
                user_id=card.user_id,
                word_id=card.word_id,
                exercise_type=card.exercise_type,
                lemma=card.lemma,
                pos=card.pos,
                stability=card.stability,
                difficulty=card.difficulty,
                d_eff=card.d_eff,
                review_count=card.review_count,
                last_review_timestamp=card.last_review_timestamp.isoformat(),
                last_ltm_timestamp=card.last_ltm_timestamp.isoformat() if card.last_ltm_timestamp else None,
                ltm_review_date=card.ltm_review_date,
                stm_success_count_today=card.stm_success_count_today
            )
            session.add(db_card)
        else:
            # Update existing card
            db_card.lemma = card.lemma
            db_card.pos = card.pos
            db_card.stability = card.stability
            db_card.difficulty = card.difficulty
            db_card.d_eff = card.d_eff
            db_card.review_count = card.review_count
            db_card.last_review_timestamp = card.last_review_timestamp.isoformat()
            db_card.last_ltm_timestamp = card.last_ltm_timestamp.isoformat() if card.last_ltm_timestamp else None
            db_card.ltm_review_date = card.ltm_review_date
            db_card.stm_success_count_today = card.stm_success_count_today
        
        session.commit()
    finally:
        session.close()


def batch_save_card_states(cards: list[CardState]):
    """
    Save multiple card states in a single database transaction (much faster).
    
    Args:
        cards: List of CardState objects to save
    """
    if not cards:
        return
    
    session = get_session()
    try:
        for card in cards:
            # Try to find existing card
            db_card = session.query(CardStateModel).filter(
                CardStateModel.user_id == card.user_id,
                CardStateModel.word_id == card.word_id,
                CardStateModel.exercise_type == card.exercise_type
            ).first()
            
            if db_card is None:
                # Create new card
                db_card = CardStateModel(
                    user_id=card.user_id,
                    word_id=card.word_id,
                    exercise_type=card.exercise_type,
                    lemma=card.lemma,
                    pos=card.pos,
                    stability=card.stability,
                    difficulty=card.difficulty,
                    d_eff=card.d_eff,
                    review_count=card.review_count,
                    last_review_timestamp=card.last_review_timestamp.isoformat(),
                    last_ltm_timestamp=card.last_ltm_timestamp.isoformat() if card.last_ltm_timestamp else None,
                    ltm_review_date=card.ltm_review_date,
                    stm_success_count_today=card.stm_success_count_today
                )
                session.add(db_card)
            else:
                # Update existing card
                db_card.lemma = card.lemma
                db_card.pos = card.pos
                db_card.stability = card.stability
                db_card.difficulty = card.difficulty
                db_card.d_eff = card.d_eff
                db_card.review_count = card.review_count
                db_card.last_review_timestamp = card.last_review_timestamp.isoformat()
                db_card.last_ltm_timestamp = card.last_ltm_timestamp.isoformat() if card.last_ltm_timestamp else None
                db_card.ltm_review_date = card.ltm_review_date
                db_card.stm_success_count_today = card.stm_success_count_today
        
        session.commit()
    finally:
        session.close()


def batch_log_review_events(events: list[dict]):
    """
    Log multiple review events in a single database transaction (much faster).
    
    Args:
        events: List of event dicts with keys:
            - word_id, lemma, pos, exercise_type, timestamp, feedback_grade
            - latency_ms, stability_before, difficulty_before, d_eff_before
            - retrievability_before, stability_after, difficulty_after, d_eff_after
            - is_ltm_event, session_id, session_position, presentation_mode
    """
    if not events:
        return
    
    session = get_session()
    try:
        for event in events:
            review_event = ReviewEventModel(
                user_id=event['user_id'],
                word_id=event['word_id'],
                exercise_type=event['exercise_type'],
                lemma=event['lemma'],
                pos=event['pos'],
                timestamp=event['timestamp'].isoformat() if isinstance(event['timestamp'], datetime) else event['timestamp'],
                feedback_grade=int(event['feedback_grade']),
                latency_ms=event.get('latency_ms'),
                stability_before=event.get('stability_before'),
                difficulty_before=event.get('difficulty_before'),
                d_eff_before=event.get('d_eff_before'),
                retrievability_before=event.get('retrievability_before'),
                stability_after=event['stability_after'],
                difficulty_after=event['difficulty_after'],
                d_eff_after=event['d_eff_after'],
                is_ltm_event=1 if event['is_ltm_event'] else 0,
                session_id=event.get('session_id'),
                session_position=event.get('session_position'),
                presentation_mode=event.get('presentation_mode')
            )
            session.add(review_event)
        session.commit()
    finally:
        session.close()


def get_all_cards_with_state(exercise_type: str, user_id: str) -> list[CardStateSnapshot]:
    """
    Get all cards with their current retrievability snapshot.
    
    Args:
        exercise_type: Type of exercise to filter by
        user_id: User identifier for scoping review data
    
    Returns:
        List of CardStateSnapshot values with computed retrievability
    """
    from core.fsrs.memory_state import (
        calculate_retrievability,
        get_days_since_ltm_review,
        CardStateSnapshot,
    )
    
    session = get_session()
    try:
        db_cards = session.query(CardStateModel).filter(
            CardStateModel.user_id == user_id,
            CardStateModel.exercise_type == exercise_type
        ).order_by(CardStateModel.last_review_timestamp.desc()).all()
        
        result: list[CardStateSnapshot] = []
        for db_card in db_cards:
            last_ltm_ts = (
                datetime.fromisoformat(db_card.last_ltm_timestamp)
                if db_card.last_ltm_timestamp
                else None
            )
            
            days_since = get_days_since_ltm_review(last_ltm_ts)
            retrievability = calculate_retrievability(db_card.stability, days_since)
            
            result.append(
                CardStateSnapshot(
                    word_id=db_card.word_id,
                    exercise_type=db_card.exercise_type,
                    retrievability=retrievability
                )
            )
        
        return result
    finally:
        session.close()


def get_due_cards(exercise_type: str, user_id: str, r_threshold: float = 0.70) -> list[CardStateSnapshot]:
    """
    Get cards with retrievability below threshold (due for review).
    
    Args:
        exercise_type: Type of exercise to filter by
        user_id: User identifier for scoping review data
        r_threshold: Retrievability threshold (default: 0.70)
    
    Returns:
        List of CardStateSnapshot values, sorted by retrievability (most urgent first)
    """
    all_cards = get_all_cards_with_state(exercise_type, user_id)
    
    # Filter by threshold
    due_cards = [c for c in all_cards if c.retrievability < r_threshold]
    
    # Sort by retrievability (lowest first = most urgent)
    due_cards.sort(key=lambda c: c.retrievability)
    
    return due_cards


def get_recent_events(user_id: str, limit: int = 10) -> list[dict]:
    """
    Get recent review events.
    
    Args:
        user_id: User identifier for scoping review data
        limit: Maximum number of events to return
    
    Returns:
        List of recent events (newest first)
    """
    session = get_session()
    try:
        events = session.query(ReviewEventModel).filter(
            ReviewEventModel.user_id == user_id
        ).order_by(
            ReviewEventModel.timestamp.desc()
        ).limit(limit).all()
        
        result = []
        for event in events:
            result.append({
                "id": event.id,
                "user_id": event.user_id,
                "word_id": event.word_id,
                "exercise_type": event.exercise_type,
                "lemma": event.lemma,
                "pos": event.pos,
                "timestamp": event.timestamp,
                "feedback_grade": event.feedback_grade,
                "latency_ms": event.latency_ms,
                "stability_before": event.stability_before,
                "difficulty_before": event.difficulty_before,
                "d_eff_before": event.d_eff_before,
                "retrievability_before": event.retrievability_before,
                "stability_after": event.stability_after,
                "difficulty_after": event.difficulty_after,
                "d_eff_after": event.d_eff_after,
                "is_ltm_event": event.is_ltm_event,
                "session_id": event.session_id,
                "session_position": event.session_position,
                "presentation_mode": event.presentation_mode
            })
        
        return result
    finally:
        session.close()


