"""Proficiency level calculation for CDA Fair Level Certification.

Provides a stateless calculator for determining a dancer's proficiency
level for a given dance, following CDA's rules including point-out
detection, within-style, and cross-style proficiency.
"""

from cda_core.lib import constants
from cda_core.lib.models.dance import Dance


class ProficiencyCalculator:
    """Stateless calculator for dancer proficiency levels.

    All methods are static and operate on Dancer/Dance objects,
    making them testable without instantiating full Dancer objects.
    """

    @staticmethod
    def has_pointed_out(dancer, dance_obj: Dance) -> bool:
        """Returns True if a dancer has pointed out of a Dance (at a certain
        level); otherwise, False.

        Args:
            dancer: A Dancer object with get_points() method.
            dance_obj: The Dance to check.
        Returns:
            True if the dancer has >= 7 or < 0 points for the dance.
        """
        num_points = dancer.get_points(dance_obj)
        return num_points < 0 or num_points >= 7

    @staticmethod
    def compute_point_out_level(dancer, style: str, dance_name: str) -> int:
        """Returns an int representing how many levels a dancer has pointed out
        of for a given dance.

        Args:
            dancer: A Dancer object.
            style: The dance style (e.g. "Smooth", "Latin").
            dance_name: The dance name (e.g. "Tango", "Samba").
        Returns:
            An int representing the number of levels pointed out of.
        """
        point_out_level = 0
        for level in constants.LEVELS:
            curr_dance = Dance(level, style, dance_name)
            if ProficiencyCalculator.has_pointed_out(dancer, curr_dance):
                point_out_level += 1
            else:
                break
        return point_out_level

    @staticmethod
    def compute_proficiency_level(dancer, style: str, dance_name: str) -> int:
        """Returns an int representing a dancer's proficiency level for a given dance.

        Corresponds to the index of the level in constants.LEVELS:
        0 = Newcomer, 1 = Bronze, 2 = Silver, 3 = Gold, 4 = Novice,
        5 = Pre-Champ, 6 = Championship

        Args:
            dancer: A Dancer object.
            style: The dance style (e.g. "Smooth", "Latin").
            dance_name: The dance name (e.g. "Tango", "Samba").
        Returns:
            An int representing the lowest level a dancer may register for.
        Raises:
            ValueError: if style is not eligible for points.
        """
        newcomer_level = 0 if dancer.is_newcomer() else 1

        # Proficiency via Pointing Out
        point_out_level = ProficiencyCalculator.compute_point_out_level(dancer, style, dance_name)

        # Within-Style Proficiency: never less than two levels lower
        # than any other dance within the same style.
        within_style_level = 0
        for curr_dance_name in constants.DANCE_NAMES[style]:
            if curr_dance_name != dance_name:
                within_style_level = max(
                    within_style_level,
                    ProficiencyCalculator.compute_point_out_level(dancer, style, curr_dance_name)
                    - 2,
                )

        # Cross-Style Proficiency: never less than two levels lower than the
        # dancer's point-out level in the paired dance of the counterpart style
        # (e.g. Standard Waltz <-> Smooth Waltz, Latin Jive <-> Rhythm Swing).
        # Dances with no cross-style counterpart (Quickstep, Samba, Paso,
        # Bolero, Mambo) get no cross-style credit.
        other_style = constants.CROSS_STYLE.get(style)
        if other_style is None:
            raise ValueError(f"'{style}' is not eligible for points (e.g. nightclub dances).")

        cross_style_level = 0
        other_dance = constants.CROSS_STYLE_DANCE_PAIRS.get(dance_name)
        if other_dance is not None:
            cross_style_level = max(
                cross_style_level,
                ProficiencyCalculator.compute_point_out_level(dancer, other_style, other_dance) - 2,
            )

        return max(newcomer_level, point_out_level, within_style_level, cross_style_level)
