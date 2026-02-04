"""
Typed pool models shared across session builders.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


PoolStatus = Literal["ltm", "stm", "new"]


@dataclass
class PoolItem:
    """
    Represents a word assigned to a pool status.
    """
    word: dict
    status: PoolStatus
