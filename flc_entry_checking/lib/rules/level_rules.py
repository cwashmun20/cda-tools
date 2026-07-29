"""Consecutive level checking for CDA Fair Level Certification.

Provides the LevelRulesChecker for validating that dancers don't register
for too many or non-consecutive levels within the same style.
"""

from cda_core.lib import constants
from flc_entry_checking.lib.rules.violations import LevelViolation


class LevelRulesChecker:
    """Checks a dancer's registered entries for consecutive level violations."""

    @staticmethod
    def check(dancer, flc_level_limit: int = 2) -> list[LevelViolation]:
        """Check a dancer's entries for consecutive level violations.

        Args:
            dancer: A Dancer object with entries to check.
            flc_level_limit: Maximum number of consecutive levels allowed (default 2).
        Returns:
            A list of LevelViolation objects (empty if none found).
        """
        violations: list[LevelViolation] = []

        level_log = {
            "Smooth": set(),
            "Standard": set(),
            "Rhythm": set(),
            "Latin": set(),
        }

        for entry_obj in dancer.entries:
            style = entry_obj.dance_data.style
            level = entry_obj.dance_data.level
            if style in constants.STYLES and level in constants.FLC_LEVELS:
                level_log[style].add(constants.FLC_LEVELS.index(level))

        for style, level_set in level_log.items():
            if not level_set:
                continue

            sorted_levels = sorted(level_set)

            # Check for too many levels registered
            if len(level_set) > flc_level_limit:
                violations.append(
                    LevelViolation(
                        dancer_name=dancer.name,
                        style=style,
                        violation_type="too_many_levels",
                        levels=sorted_levels,
                        detail_message=(
                            f"CONSECUTIVE LEVEL VIOLATION: {dancer.name} is registered "
                            f"for more than {flc_level_limit} level(s) of {style}:\n"
                            + "\n".join(
                                f"\t{dancer.name} is registered for at least one dance "
                                f"in '{constants.FLC_LEVELS[i]} {style}'."
                                for i in sorted_levels
                            )
                        ),
                    )
                )

            # Check for non-consecutive levels registered
            else:
                curr_idx, next_idx = 0, 1
                while next_idx < len(sorted_levels):
                    if sorted_levels[next_idx] - sorted_levels[curr_idx] != 1:
                        level_name_1 = constants.FLC_LEVELS[sorted_levels[curr_idx]]
                        level_name_2 = constants.FLC_LEVELS[sorted_levels[next_idx]]
                        violations.append(
                            LevelViolation(
                                dancer_name=dancer.name,
                                style=style,
                                violation_type="non_consecutive",
                                levels=[sorted_levels[curr_idx], sorted_levels[next_idx]],
                                detail_message=(
                                    f"CONSECUTIVE LEVEL VIOLATION: {dancer.name} is "
                                    f"registered for at least one event in both "
                                    f"'{level_name_1} {style}' and "
                                    f"'{level_name_2} {style}'."
                                ),
                            )
                        )
                    curr_idx += 1
                    next_idx += 1

        return violations
