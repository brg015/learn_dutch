"""
FSRS Constants and Parameters

All configurable parameters for the FSRS algorithm in one place.
These values are based on the design specification in FSRS_IMPLEMENTATION.md.
"""

from enum import IntEnum


# ---- Feedback Grades ----

class FeedbackGrade(IntEnum):
    """User feedback on retrieval attempt."""
    AGAIN = 1   # Retrieval failed
    HARD = 2    # Retrieved with high effort
    MEDIUM = 3  # Retrieved normally
    EASY = 4    # Retrieved fluently


# ---- Global Constants ----

R_TARGET = 0.70  # Target retrievability threshold for "due" cards
S_MIN = 0.5      # Minimum stability (days)
D_MIN = 1.0      # Minimum difficulty
D_MAX = 10.0     # Maximum difficulty


# ---- Learning Parameters ----

K = 1.2          # Stability learning rate
K_FAIL = 0.6     # Stability penalty rate on failure
ALPHA = 0.15     # Difficulty penalty factor (higher = slower learning for hard cards)
ETA = 0.8        # Difficulty adaptation rate (higher = faster difficulty changes)


# ---- Base Learning Gain by Rating ----
# Multiplier for stability increase on successful retrieval

BASE_GAIN = {
    FeedbackGrade.HARD: 0.5,
    FeedbackGrade.MEDIUM: 1.0,
    FeedbackGrade.EASY: 1.8,
}


# ---- Difficulty Update Direction by Rating ----
# Direction and magnitude of difficulty change

U_RATING = {
    FeedbackGrade.AGAIN: +1.0,   # Failure increases difficulty
    FeedbackGrade.HARD: +0.35,   # Hard success slightly increases difficulty
    FeedbackGrade.MEDIUM: -0.20, # Medium success slightly decreases difficulty
    FeedbackGrade.EASY: -0.60,   # Easy success significantly decreases difficulty
}
