"""Violation types and structured results for FLC rule checking.

This module defines the data structures used to represent rule-checking
results, replacing direct print() calls with structured dataclasses.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class ViolationType(StrEnum):
    """Types of FLC rule violations."""

    NEWCOMER = "newcomer"
    NIGHTCLUB_BEGINNER = "nightclub_beginner"
    ROOKIE_LEAD = "rookie_lead"
    ROOKIE_FOLLOW = "rookie_follow"
    POINTED_OUT = "pointed_out"
    CONSECUTIVE_LEVEL = "consecutive_level"
    SPLIT_LEVEL = "split_level"


@dataclass
class EligibilityResult:
    """Structured result from an eligibility check.

    This replaces print() side effects in the eligibility logic with a
    dataclass that can be consumed programmatically (e.g., by a web UI).
    """

    eligible: bool
    violation_type: Optional[ViolationType] = None
    detail_message: Optional[str] = None
    is_split_level: bool = False
    split_level_info: Optional[str] = None


@dataclass
class LevelViolation:
    """A consecutive level violation for a dancer.

    Used to report when a dancer registers for too many levels or
    non-consecutive levels within the same style.
    """

    dancer_name: str
    style: str
    violation_type: str  # "too_many_levels" or "non_consecutive"
    levels: list[int] = field(default_factory=list)
    detail_message: Optional[str] = None
