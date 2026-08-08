"""Per-result point scoring for points_updating.

Provides PointsCalculator, which scores one CompetitionResult against a
couple's current proficiency levels: detecting the Split-Level Exception
(which triples the award) and cascading the resulting award down through
lower levels via utils's award table and cascade logic.
"""

from dataclasses import dataclass

from points_updating.lib.models.result import CompetitionResult
from points_updating.lib.rules import award_table, cascade
from points_updating.lib.rules.cascade import PointDelta
from utils.lib import constants
from utils.lib.constants import Style
from utils.lib.models.dancer import Dancer
from utils.lib.proficiency_calculator import ProficiencyCalculator


@dataclass
class ResultAward:
    """Structured, non-printing result of scoring one CompetitionResult -
    mirrors the EligibilityResult/LevelViolation convention.
    """

    result: CompetitionResult
    is_split_level: bool
    delta: PointDelta  # identical amount applies to both lead and follow


class PointsCalculator:
    """Stateless calculator that scores a single CompetitionResult."""

    @staticmethod
    def compute(result: CompetitionResult, lead: Dancer, follow: Dancer) -> ResultAward:
        """Scores one CompetitionResult for a couple.

        Args:
            result: The CompetitionResult to score.
            lead: The lead's current Dancer - proficiency is read from
                their points as of immediately before this competition.
            follow: The follow's current Dancer, same caveat.
        Returns:
            A ResultAward with whether the Split-Level Exception applied
            and the resulting point delta (owed identically to both
            partners).
        Raises:
            ValueError: if result.dance's style isn't eligible for points
                (e.g. Nightclub).
        """
        dance = result.dance
        if dance.style not in Style.points_eligible_styles():
            raise ValueError(f"'{dance}' is not eligible for points.")

        danced, one_below, two_plus_below = award_table.compute_award(
            result.num_rounds, result.place
        )

        # A multi-dance event's dance set is fixed by the organizer, not
        # chosen per-dancer, so the couple's Split-Level Exception
        # eligibility is decided once for the whole combo - the higher of
        # each partner's proficiency across every dance in the combo, not
        # just the one dance this result happens to be keyed off of. For a
        # single-dance event this max() degenerates to today's behavior.
        lead_level = max(
            ProficiencyCalculator.compute_proficiency_level(lead, dance.style, d.dance)
            for d in result.event_dances
        )
        follow_level = max(
            ProficiencyCalculator.compute_proficiency_level(follow, dance.style, d.dance)
            for d in result.event_dances
        )
        # None if the couple doesn't qualify for the Split-Level Exception.
        combined_level = ProficiencyCalculator.compute_split_level_combined_level(
            lead_level, follow_level
        )
        event_level = constants.LEVELS.index(dance.level)
        # Only applies if they also danced at the exception's designated level.
        is_split_level = combined_level is not None and combined_level == event_level
        if is_split_level:
            danced, one_below, two_plus_below = danced * 3, one_below * 3, two_plus_below * 3

        delta = cascade.build_cascade_delta(dance, (danced, one_below, two_plus_below))
        return ResultAward(result=result, is_split_level=is_split_level, delta=delta)
