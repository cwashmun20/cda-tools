"""Violation types and structured results for rule checking.

This module defines the data structures used to represent rule-checking
results, replacing direct print() calls with structured dataclasses.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class ViolationType(StrEnum):
    """Types of rule violations."""

    NEWCOMER = "newcomer"
    NIGHTCLUB_BEGINNER = "nightclub_beginner"
    ROOKIE_LEAD = "rookie_lead"
    ROOKIE_FOLLOW = "rookie_follow"
    POINTED_OUT = "pointed_out"
    CONSECUTIVE_LEVEL = "consecutive_level"
    SPLIT_LEVEL = "split_level"
    DUPLICATE_ENTRY = "duplicate_entry"


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
    """A consecutive-level-limit violation for a dancer.

    CDA measures consecutive-level eligibility per dance: a dancer may be
    registered across more distinct levels within a style than the allowed
    limit, as long as no single dance exceeds that limit. "too_many_levels"
    and "non_consecutive" are reported per dance (dance is set); the one
    style-wide check is "span_too_wide", reported when the overall range of
    levels registered anywhere in the style is too broad (dance is None).
    """

    dancer_name: str
    style: str
    violation_type: str  # "too_many_levels", "non_consecutive", or "span_too_wide"
    levels: list[int] = field(default_factory=list)
    dance: Optional[str] = None
    detail_message: Optional[str] = None
