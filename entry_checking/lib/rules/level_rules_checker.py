"""Consecutive level checking for CDA Fair Level Certification.

Provides the LevelRulesChecker for validating that dancers don't register
for too many or non-consecutive levels of any single dance, or too wide a
range of levels overall within a style.
"""

from entry_checking.lib.rules.violations import LevelViolation, LevelViolationType
from utils.lib import constants
from utils.lib.constants import Style
from utils.lib.models.dancer import Dancer


class LevelRulesChecker:
    """Checks a dancer's registered entries for consecutive level violations."""

    @staticmethod
    def check(dancer: Dancer, consecutive_level_limit: int = 2) -> list[LevelViolation]:
        """Check a dancer's entries for consecutive level violations.

        The CDA measures consecutive-level eligibility per dance, not per style:
        a dancer may be registered across more distinct levels within a
        style than consecutive_level_limit, as long as no single dance has
        more than consecutive_level_limit levels registered for it (and none
        of those levels skip one, for that dance). The one style-wide
        constraint is that the overall range of levels registered anywhere
        in the style can't exceed consecutive_level_limit + 1 distinct
        levels - e.g. with a limit of 2, a dancer could be registered for
        Silver+Gold Waltz and Bronze+Silver Tango (Bronze through Gold is
        exactly 3 levels, right at the limit), but not Newcomer Waltz and
        Gold Tango (Newcomer through Gold is a 4-level-wide range, even
        though neither dance individually has more than one level).

        Args:
            dancer: A Dancer object with entries to check.
            consecutive_level_limit: Maximum number of consecutive levels
                allowed per dance (default 2).
        Returns:
            A list of LevelViolation objects (empty if none found).
        """
        violations: list[LevelViolation] = []

        dance_levels: dict[Style, dict[str, set[int]]] = {
            style: {} for style in Style.points_eligible_styles()
        }

        for entry_obj in dancer.entries:
            style = entry_obj.dance_data.style
            level = entry_obj.dance_data.level
            dance = entry_obj.dance_data.dance
            if style in dance_levels and level in constants.LEVELS:
                dance_levels[style].setdefault(dance, set()).add(constants.LEVELS.index(level))

        for style, dances in dance_levels.items():
            if not dances:
                continue

            all_levels = {level_idx for levels in dances.values() for level_idx in levels}
            span = max(all_levels) - min(all_levels)
            if span > consecutive_level_limit:
                sorted_all = sorted(all_levels)
                violations.append(
                    LevelViolation(
                        dancer_name=dancer.name,
                        style=style,
                        violation_type=LevelViolationType.SPAN_TOO_WIDE,
                        levels=sorted_all,
                        detail_message=(
                            f"CONSECUTIVE LEVEL VIOLATION: {dancer.name} is registered "
                            f"across too wide a range of {style} levels (at most "
                            f"{consecutive_level_limit + 1} distinct levels allowed):\n"
                            + "\n".join(
                                f"\t{dancer.name} is registered for at least one dance "
                                f"in '{constants.LEVELS[i]} {style}'."
                                for i in sorted_all
                            )
                        ),
                    )
                )

            for dance, level_set in dances.items():
                sorted_levels = sorted(level_set)

                if len(level_set) > consecutive_level_limit:
                    violations.append(
                        LevelViolation(
                            dancer_name=dancer.name,
                            style=style,
                            violation_type=LevelViolationType.TOO_MANY_LEVELS,
                            levels=sorted_levels,
                            dance=dance,
                            detail_message=(
                                f"CONSECUTIVE LEVEL VIOLATION: {dancer.name} is registered "
                                f"for more than {consecutive_level_limit} level(s) of "
                                f"{style} {dance}:\n"
                                + "\n".join(
                                    f"\t{dancer.name} is registered for "
                                    f"'{constants.LEVELS[i]} {style} {dance}'."
                                    for i in sorted_levels
                                )
                            ),
                        )
                    )

                else:
                    curr_idx, next_idx = 0, 1
                    while next_idx < len(sorted_levels):
                        if sorted_levels[next_idx] - sorted_levels[curr_idx] != 1:
                            level_name_1 = constants.LEVELS[sorted_levels[curr_idx]]
                            level_name_2 = constants.LEVELS[sorted_levels[next_idx]]
                            violations.append(
                                LevelViolation(
                                    dancer_name=dancer.name,
                                    style=style,
                                    violation_type=LevelViolationType.NON_CONSECUTIVE,
                                    levels=[sorted_levels[curr_idx], sorted_levels[next_idx]],
                                    dance=dance,
                                    detail_message=(
                                        f"CONSECUTIVE LEVEL VIOLATION: {dancer.name} is "
                                        f"registered for at least one event in both "
                                        f"'{level_name_1} {style} {dance}' and "
                                        f"'{level_name_2} {style} {dance}'."
                                    ),
                                )
                            )
                        curr_idx += 1
                        next_idx += 1

        return violations
