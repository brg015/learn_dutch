"""
Typed pool models shared across session builders.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


PoolStatus = Literal["ltm", "stm", "new", "known"]


@dataclass
class PoolState:
    """
    Launch-scoped pool state for an activity.
    """
    word_map: dict[str, dict]
    ltm: set[str]
    stm: set[str]
    new: set[str]
    known: set[str]
    ltm_scores: dict[str, float]

    def move_to(self, word_id: str, target: PoolStatus) -> None:
        """
        Move a word_id to the target pool, removing it from others.
        """
        self.ltm.discard(word_id)
        self.stm.discard(word_id)
        self.new.discard(word_id)
        self.known.discard(word_id)

        if target == "ltm":
            self.ltm.add(word_id)
        elif target == "stm":
            self.stm.add(word_id)
        elif target == "new":
            self.new.add(word_id)
        elif target == "known":
            self.known.add(word_id)
