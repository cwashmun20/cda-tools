"""Violation types and structured results for rule checking.

Defines the data structures used to represent rule-checking results.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

from utils.lib.constants import Style


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
    NIGHTCLUB_CONSECUTIVE_LEVEL = "nightclub_consecutive_level"


class LevelViolationType(StrEnum):
    """Types of consecutive-level violations (see LevelViolation)."""

    TOO_MANY_LEVELS = "too_many_levels"
    NON_CONSECUTIVE = "non_consecutive"
    SPAN_TOO_WIDE = "span_too_wide"


@dataclass
class EligibilityResult:
    """Outcome of an eligibility check, consumable by both the CLI and a web UI."""

    eligible: bool
    violation_type: Optional[ViolationType] = None
    detail_message: Optional[str] = None
    is_split_level: bool = False
    split_level_info: Optional[str] = None
    # Whoever the violation is about, for grouping a report by dancer -
    # the partnership's combined name for couple-level violations, or an
    # individual dancer's name for DUPLICATE_ENTRY (which is checked per
    # dancer, not per couple).
    subject_name: Optional[str] = None


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
    style: Style
    violation_type: LevelViolationType
    levels: list[int] = field(default_factory=list)
    dance: Optional[str] = None
    detail_message: Optional[str] = None
