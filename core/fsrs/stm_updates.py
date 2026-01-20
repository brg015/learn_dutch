"""
Short-Term Memory (STM) Updates

Implements effective difficulty (D_eff) updates for STM practice.

STM exists to:
- Repair same-day failures
- Improve access and fluency
- Support later spaced learning

Key principle:
STM NEVER updates stability (S). It only modifies D_eff, which is used
at the next LTM update to scale stability gains.
"""

from __future__ import annotations
from core.fsrs.constants import FeedbackGrade


def apply_stm_success_update(
    d_eff: float,
    d_floor: float,
    stm_success_count: int
) -> float:
    """
    Update effective difficulty after STM success.

    Formula:
        D_eff = D_floor + (D_eff - D_floor) * (1 - lambda_m)

    With diminishing returns:
        lambda_m = 0.5 / (m + 1)

    Where m = number of STM successes today (before this one).

    Interpretation:
    - First STM success moves about 50% toward D_floor
    - Subsequent successes produce smaller gains
    - STM repairs fluency without overstating long-term mastery
    - D_eff cannot go below D_floor (counterfactual "Hard" difficulty)

    This encodes the rule:
    "STM can repair fluency up to 'Hard-correct', but cannot certify mastery."

    Args:
        d_eff: Current effective difficulty
        d_floor: Floor difficulty (from last LTM update)
        stm_success_count: Number of STM successes today (0-indexed, before this one)

    Returns:
        New D_eff value
    """
    # Diminishing returns factor
    # m=0 (first success): lambda = 0.5 / 1 = 0.5 (50% movement)
    # m=1 (second success): lambda = 0.5 / 2 = 0.25 (25% movement)
    # m=2 (third success): lambda = 0.5 / 3 = 0.167 (16.7% movement)
    lambda_m = 0.5 / (stm_success_count + 1)

    # Move toward D_floor with diminishing returns
    new_d_eff = d_floor + (d_eff - d_floor) * (1.0 - lambda_m)

    # Ensure we don't go below D_floor
    return max(d_floor, new_d_eff)


def should_update_d_eff(feedback_grade: FeedbackGrade) -> bool:
    """
    Determine if this STM feedback should update D_eff.

    Only successful retrievals (HARD, MEDIUM, EASY) update D_eff.
    Failures (AGAIN) are logged but do not modify state.

    Args:
        feedback_grade: User feedback

    Returns:
        True if D_eff should be updated, False otherwise
    """
    return feedback_grade != FeedbackGrade.AGAIN


def reset_stm_state() -> tuple[float, int]:
    """
    Reset STM state after an LTM event.

    After an LTM update:
    - D_eff is reset to D (the new long-term difficulty)
    - STM success count is reset to 0

    Returns:
        (d_eff_reset_value, stm_count_reset_value)
        These should be set based on the new D from LTM update
    """
    # D_eff will be set to new D by caller
    # STM count resets to 0
    return None, 0  # Caller must set d_eff = new_d


def get_stm_success_count_after_update(
    current_count: int,
    feedback_grade: FeedbackGrade
) -> int:
    """
    Get updated STM success count after a review.

    Args:
        current_count: Current STM success count
        feedback_grade: User feedback

    Returns:
        Updated count
    """
    if should_update_d_eff(feedback_grade):
        return current_count + 1
    else:
        # Failures don't increment count
        return current_count
