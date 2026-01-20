"""
Long-Term Memory (LTM) Updates

Implements stability and difficulty updates for LTM events.

LTM events occur once per day per card (first meaningful retrieval attempt).
These updates drive long-term scheduling.

Key principles:
- Spaced, effortful success produces largest stability gains
- Failures are penalized more when recall was expected (high R)
- Difficulty reflects learning efficiency, not forgetting speed
"""

from __future__ import annotations
import math

from core.fsrs.constants import (
    FeedbackGrade,
    R_TARGET,
    S_MIN,
    D_MIN,
    D_MAX,
    K,
    K_FAIL,
    ALPHA,
    ETA,
    BASE_GAIN,
    U_RATING
)


def update_stability_on_success(
    stability: float,
    retrievability: float,
    difficulty_used: float,
    feedback_grade: FeedbackGrade,
    is_new_card: bool = False
) -> float:
    """
    Update stability after successful retrieval (Hard/Medium/Easy).

    Formula:
        ΔS = k * S * base_gain(rating) * (1 - R) * f(D_used)
        S_new = S + ΔS

    Where:
        - (1 - R) rewards risky (well-spaced) success
        - f(D) reduces learning gains for difficult items
        - f(D) = 1 / (1 + alpha * (D - 1))

    Special case for new cards:
        When R = 1.0 (first review), (1-R) = 0, so we use a special formula:
        S_new = S_MIN * base_gain(rating)

    Key principle:
    Spaced, effortful success produces the largest stability gains.

    Args:
        stability: Current stability (S)
        retrievability: Current retrievability (R)
        difficulty_used: Difficulty used for this update (D or D_eff)
        feedback_grade: User feedback (HARD, MEDIUM, or EASY)
        is_new_card: True if this is the first review

    Returns:
        New stability value
    """
    if feedback_grade == FeedbackGrade.AGAIN:
        raise ValueError("Use update_stability_on_failure for AGAIN feedback")

    # Base gain from rating
    base_gain = BASE_GAIN[feedback_grade]

    # Special case for new cards (R = 1.0)
    if is_new_card or retrievability >= 0.99:
        # First review: set initial stability based on rating
        new_stability = S_MIN * base_gain * 2.0  # Scale up from minimum
        return max(S_MIN, new_stability)

    # Difficulty penalty: f(D) = 1 / (1 + alpha * (D - 1))
    # Higher difficulty -> smaller f(D) -> slower learning
    f_d = 1.0 / (1.0 + ALPHA * (difficulty_used - 1.0))

    # Stability increase
    delta_s = K * stability * base_gain * (1.0 - retrievability) * f_d

    new_stability = stability + delta_s

    return max(S_MIN, new_stability)


def update_stability_on_failure(
    stability: float,
    retrievability: float
) -> float:
    """
    Update stability after failed retrieval (Again).

    Formula:
        S_new = max(S_min, S * (1 - k_fail * R))

    Failures are penalized more strongly when recall was expected (high R).

    Args:
        stability: Current stability
        retrievability: Current retrievability

    Returns:
        New stability value (reduced)
    """
    # Reduce stability proportional to how much we expected success
    new_stability = stability * (1.0 - K_FAIL * retrievability)

    return max(S_MIN, new_stability)


def update_difficulty(
    difficulty: float,
    retrievability: float,
    feedback_grade: FeedbackGrade
) -> float:
    """
    Update difficulty based on retrieval outcome.

    Formula:
        D_new = clip(
            D + eta * surprise * u(rating),
            min=1,
            max=10
        )

    Where:
        - surprise = R on failure, (1-R) on success
        - u(rating) = direction of difficulty change

    Conceptually:
    - Failure increases difficulty
    - Easy success decreases difficulty
    - Changes are larger when outcome was surprising given R

    Difficulty updates happen ONLY during LTM events.

    Args:
        difficulty: Current difficulty
        retrievability: Current retrievability
        feedback_grade: User feedback

    Returns:
        New difficulty value (clipped to [1, 10])
    """
    # Surprise: how unexpected was this outcome?
    if feedback_grade == FeedbackGrade.AGAIN:
        # Failure was more surprising if R was high
        surprise = retrievability
    else:
        # Success was more surprising if R was low
        surprise = 1.0 - retrievability

    # Direction of difficulty change
    u = U_RATING[feedback_grade]

    # Update difficulty
    delta_d = ETA * surprise * u
    new_difficulty = difficulty + delta_d

    # Clip to valid range
    return max(D_MIN, min(D_MAX, new_difficulty))


def compute_d_floor(
    difficulty: float,
    retrievability: float
) -> float:
    """
    Compute D_floor: the counterfactual difficulty if user had answered "Hard".

    D_floor is used by STM to constrain how much fluency repair can occur.
    STM can move D_eff toward D_floor, but never below it.

    This encodes the rule:
    "STM can repair fluency up to 'Hard-correct', but cannot certify mastery."

    Args:
        difficulty: Current difficulty (D)
        retrievability: Current retrievability (R)

    Returns:
        D_floor value
    """
    # Simulate "Hard" update from current D
    surprise = 1.0 - retrievability  # Success surprise
    u_hard = U_RATING[FeedbackGrade.HARD]

    delta_d = ETA * surprise * u_hard
    d_floor = difficulty + delta_d

    # Clip to valid range
    return max(D_MIN, min(D_MAX, d_floor))


def apply_ltm_update(
    stability: float,
    difficulty: float,
    d_eff: float,
    retrievability: float,
    feedback_grade: FeedbackGrade,
    is_new_card: bool = False
) -> tuple[float, float, float]:
    """
    Apply LTM update rules to get new S, D, and D_floor.

    This is the main entry point for LTM updates.

    Args:
        stability: Current stability
        difficulty: Current difficulty
        d_eff: Current effective difficulty
        retrievability: Current retrievability
        feedback_grade: User feedback
        is_new_card: True if this is the first review

    Returns:
        (new_stability, new_difficulty, d_floor)
    """
    # Update stability
    if feedback_grade == FeedbackGrade.AGAIN:
        new_stability = update_stability_on_failure(stability, retrievability)
    else:
        # Use D_eff for stability update (accounts for STM practice)
        new_stability = update_stability_on_success(
            stability, retrievability, d_eff, feedback_grade, is_new_card
        )

    # Update difficulty (always uses current D, not D_eff)
    new_difficulty = update_difficulty(difficulty, retrievability, feedback_grade)

    # Compute D_floor for STM constraint
    d_floor = compute_d_floor(new_difficulty, retrievability)

    return new_stability, new_difficulty, d_floor
