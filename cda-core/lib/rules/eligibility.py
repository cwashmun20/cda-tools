"""Partnership eligibility checking for CDA Fair Level Certification.

Provides the EligibilityChecker class for validating whether a partnership
is eligible to compete in a given dance at a given level, returning
structured EligibilityResult objects.
"""

import constants
from models.dance import Dance
from rules.violations import EligibilityResult, ViolationType
from rules.proficiency import ProficiencyCalculator


class EligibilityChecker:
    """Checks whether a partnership is eligible for a dance at a given level.

    Returns structured EligibilityResult objects instead of printing directly.
    All violation messages are captured in the result for downstream formatting.
    """

    def __init__(self, rv_ruleset: str = "newcomer"):
        """Create an EligibilityChecker.

        Args:
            rv_ruleset: Either "newcomer" or "level", determining how rookie/vet
                        eligibility is evaluated.
        Raises:
            ValueError: if rv_ruleset is not recognized.
        """
        if rv_ruleset not in ("newcomer", "level"):
            raise ValueError(f"'{rv_ruleset}' is an invalid Rookie/Vet ruleset.")
        self.rv_ruleset = rv_ruleset

    def check(self, partnership, dance_obj: Dance) -> EligibilityResult:
        """Check whether a partnership is eligible for a dance.

        Args:
            partnership: A Partnership object containing lead and follow dancers.
            dance_obj: The Dance being checked.
        Returns:
            An EligibilityResult with the outcome and any violation details.
        """
        # Everyone is always eligible for int./adv. Nightclub and Championship
        if dance_obj.level == constants.NC_LEVELS[-1] or dance_obj.level == constants.OPEN_LEVELS[-1]:
            return EligibilityResult(eligible=True)

        # Check eligibility for Beginner Nightclub
        if dance_obj.level == constants.NC_LEVELS[0]:
            if partnership.nc_beginners:
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.NIGHTCLUB_BEGINNER,
                detail_message=(
                    f"NIGHTCLUB BEGINNER VIOLATION: '{partnership.names}' "
                    f"are ineligible for '{dance_obj}'."
                ),
            )

        # Check eligibility for Newcomer
        if dance_obj.level == constants.SYLLABUS_LEVELS[0]:
            if partnership.newcomers:
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.NEWCOMER,
                detail_message=(
                    f"NEWCOMER VIOLATION: '{partnership.names}' "
                    f"ineligible for '{dance_obj}'."
                ),
            )

        # Check eligibility for Rookie/Vet
        if self.rv_ruleset == "newcomer":
            result = self._check_rookie_vet_newcomer(partnership, dance_obj)
            if result is not None:
                return result
        elif self.rv_ruleset == "level":
            result = self._check_rookie_vet_level(partnership, dance_obj)
            if result is not None:
                return result

        # Check proficiency (Split-Level Exception and Pointing Out)
        lead_level = ProficiencyCalculator.compute_proficiency_level(
            partnership.lead, dance_obj.style, dance_obj.dance)
        follow_level = ProficiencyCalculator.compute_proficiency_level(
            partnership.follow, dance_obj.style, dance_obj.dance)
        event_level = constants.FLC_LEVELS.index(dance_obj.level)

        # Check for Split-Level Exception
        if abs(lead_level - follow_level) >= 2:
            combined_level = max(lead_level, follow_level) - 1
            if combined_level == event_level:
                return EligibilityResult(
                    eligible=True,
                    is_split_level=True,
                    split_level_info=(
                        f"SPLIT-LEVEL EXCEPTION: '{partnership.names}' are competing "
                        f"'{dance_obj}' under the Split-Level Exception. Be sure to "
                        f"award 3x points if points are awarded to this couple."
                    ),
                )
        else:
            combined_level = max(lead_level, follow_level)

        if combined_level <= event_level:
            return EligibilityResult(eligible=True)

        # Pointed out violation
        lead_eligibility = constants.FLC_LEVELS[lead_level]
        follow_eligibility = constants.FLC_LEVELS[follow_level]
        return EligibilityResult(
            eligible=False,
            violation_type=ViolationType.POINTED_OUT,
            detail_message=(
                f"POINTED OUT VIOLATION: '{partnership.names}' are ineligible "
                f"for '{dance_obj}'\n"
                f"\t{partnership.lead} lowest allowed level is {lead_eligibility}.\n"
                f"\t{partnership.follow} lowest allowed level is {follow_eligibility}."
            ),
        )

    def _check_rookie_vet_newcomer(self, partnership, dance_obj: Dance) -> EligibilityResult | None:
        """Check rookie/vet eligibility under the 'newcomer' ruleset."""
        curr_style = dance_obj.style

        if dance_obj.level == constants.RookieVetLevel.ROOKIE_LEAD:
            if (partnership.lead.is_newcomer()
                    and not partnership.follow.is_registered_newcomer(curr_style)
                    and not partnership.follow.is_registered_bronze(curr_style)):
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.ROOKIE_LEAD,
                detail_message=(
                    f"ROOKIE-LEAD VIOLATION: '{partnership.names}' ineligible "
                    f"for '{dance_obj}'.\n"
                    f"\tLead ({partnership.lead}) is rookie: "
                    f"{partnership.lead.is_newcomer()}."
                ),
            )

        if dance_obj.level == constants.RookieVetLevel.ROOKIE_FOLLOW:
            if (partnership.follow.is_newcomer()
                    and not partnership.lead.is_registered_newcomer(curr_style)
                    and not partnership.lead.is_registered_bronze(curr_style)):
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.ROOKIE_FOLLOW,
                detail_message=(
                    f"ROOKIE-FOLLOW VIOLATION: '{partnership.names}' ineligible "
                    f"for '{dance_obj}'.\n"
                    f"\tFollow ({partnership.follow}) is rookie: "
                    f"{partnership.follow.is_newcomer()}."
                ),
            )

        return None

    def _check_rookie_vet_level(self, partnership, dance_obj: Dance) -> EligibilityResult | None:
        """Check rookie/vet eligibility under the 'level' ruleset."""
        if dance_obj.level == constants.RookieVetLevel.ROOKIE_LEAD:
            rookie_lead = not partnership.lead.has_vet_entries(dance_obj.style)
            vet_follow = not partnership.follow.has_rookie_entries(dance_obj.style)
            if rookie_lead and vet_follow:
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.ROOKIE_LEAD,
                detail_message=(
                    f"ROOKIE-LEAD VIOLATION: '{partnership.names}' ineligible "
                    f"for '{dance_obj}'.\n"
                    f"\tLead ({partnership.lead}) is rookie: {rookie_lead}.\n"
                    f"\tFollow ({partnership.follow}) is vet: {vet_follow}."
                ),
            )

        if dance_obj.level == constants.RookieVetLevel.ROOKIE_FOLLOW:
            rookie_follow = not partnership.follow.has_vet_entries(dance_obj.style)
            vet_lead = not partnership.lead.has_rookie_entries(dance_obj.style)
            if rookie_follow and vet_lead:
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.ROOKIE_FOLLOW,
                detail_message=(
                    f"ROOKIE-FOLLOW VIOLATION: '{partnership.names}' ineligible "
                    f"for '{dance_obj}'.\n"
                    f"\tLead ({partnership.lead}) is vet: {vet_lead}.\n"
                    f"\tFollow ({partnership.follow}) is rookie: {rookie_follow}."
                ),
            )

        return None