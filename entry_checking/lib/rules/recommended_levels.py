"""Recommended syllabus level calculation for CDA Fair Level Certification.

Provides a calculator for the level(s) a partnership should be recommended
to register at for a given style, based on both dancers' proficiency across
every dance in that style.
"""

from cda_core.lib import constants
from cda_core.lib.constants import Style
from cda_core.lib.models.partnership import Partnership
from cda_core.lib.rules.proficiency import ProficiencyCalculator


class RecommendedLevelsCalculator:
    """Computes recommended registration level(s) for a partnership."""

    @staticmethod
    def compute(partnership: Partnership, style: Style) -> list[str]:
        """Computes the level(s) a partnership should be recommended to
        register at in a given style.

        The recommendation is the lowest level where neither dancer has
        pointed out of any dance in the style, plus the level above that -
        mirroring CDA's consecutive-level allowance. Newcomer eligibility is
        already handled by ProficiencyCalculator itself (a non-newcomer
        dancer's per-dance proficiency floor is never 0), so no separate
        adjustment is needed here.

        Args:
            partnership: A Partnership object.
            style: The dance style/category (e.g. "Smooth", "Latin").
        Returns:
            A list of one or two level names from constants.LEVELS - two,
            unless the lowest eligible level is already the last defined
            level (Champ), in which case just that one.
        Raises:
            ValueError: if style is not eligible for points (e.g. Nightclub).
        """
        level_idx = max(
            ProficiencyCalculator.compute_proficiency_level(dancer, style, dance_name)
            for dancer in (partnership.lead, partnership.follow)
            for dance_name in constants.DANCE_NAMES[style]
        )

        if level_idx + 1 < len(constants.LEVELS):
            return [constants.LEVELS[level_idx], constants.LEVELS[level_idx + 1]]
        return [constants.LEVELS[level_idx]]
