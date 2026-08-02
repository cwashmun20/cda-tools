"""Partnership eligibility checking for CDA Fair Level Certification.

Provides the EligibilityChecker class for validating whether a partnership
is eligible to compete in a given dance at a given level, returning
structured EligibilityResult objects.
"""

from typing import cast

from cda_core.lib import constants
from cda_core.lib.constants import NightclubLevel, OpenLevel, RookieVetLevel, Style, SyllabusLevel
from cda_core.lib.models.dance import Dance
from cda_core.lib.models.dancer import Dancer
from cda_core.lib.models.partnership import Partnership
from entry_checking.lib.rules.violations import EligibilityResult, ViolationType
from entry_checking.lib.rules.proficiency import ProficiencyCalculator
from entry_checking.lib.rules.recommended_levels import RecommendedLevelsCalculator


class EligibilityChecker:
    """Checks whether a partnership is eligible for a dance at a given level.

    Returns structured EligibilityResult objects instead of printing directly.
    All violation messages are captured in the result for downstream formatting.
    """

    def __init__(self, rv_ruleset: str = "newcomer", rookie_max_level: str = "Bronze"):
        """Create an EligibilityChecker.

        Args:
            rv_ruleset: Either "newcomer" or "level", determining how rookie/vet
                        eligibility is evaluated.
            rookie_max_level: Either "Bronze" or "Silver" - the highest level
                        a Rookie may also compete at in regular (non
                        Rookie/Vet) events in that style, under the
                        "newcomer" ruleset. Competitions vary on whether
                        they allow Rookies up to Silver, so this is
                        configurable. Unused under the "level" ruleset.
        Raises:
            ValueError: if rv_ruleset or rookie_max_level is not recognized.
        """
        if rv_ruleset not in ("newcomer", "level"):
            raise ValueError(f"'{rv_ruleset}' is an invalid Rookie/Vet ruleset.")
        if rookie_max_level not in ("Bronze", "Silver"):
            raise ValueError(f"'{rookie_max_level}' is an invalid Rookie max level.")
        # Narrowed via cast(), not an annotation alone - mypy doesn't narrow a
        # plain `str` to a Literal from an `in (...)` runtime check above, so
        # this documents (and enforces, via the checks above it) the actual
        # guarantee: rv_ruleset/rookie_max_level are real str input until
        # this exact point.
        self.rv_ruleset = cast(constants.RvRuleset, rv_ruleset)
        self.rookie_max_level = cast(constants.RookieMaxLevel, rookie_max_level)

    def check(self, partnership: Partnership, dance_obj: Dance) -> EligibilityResult:
        """Check whether a partnership is eligible for a dance.

        Args:
            partnership: A Partnership object containing lead and follow dancers.
            dance_obj: The Dance being checked.
        Returns:
            An EligibilityResult with the outcome and any violation details.
        """
        # A dancer already registered for this exact dance (regardless of
        # partner) is a duplicate entry - checked first since it should be
        # flagged even at levels that are otherwise always eligible.
        for dancer_obj in (partnership.lead, partnership.follow):
            if dance_obj in dancer_obj.entries:
                return EligibilityResult(
                    eligible=False,
                    violation_type=ViolationType.DUPLICATE_ENTRY,
                    detail_message=(
                        f"DUPLICATE ENTRY: '{dancer_obj.name}' is already "
                        f"registered for '{dance_obj}'."
                    ),
                    subject_name=dancer_obj.name,
                )

        # A dancer already registered for the OTHER level of this same
        # Nightclub dance is a consecutive-level violation - checked before
        # the int./adv. shortcut below since it should override it too.
        if dance_obj.style == Style.NIGHTCLUB:
            other_nc_level = (
                NightclubLevel.BEGINNER
                if dance_obj.level == NightclubLevel.INT_ADV
                else NightclubLevel.INT_ADV
            )
            other_dance = Dance(other_nc_level, dance_obj.style, dance_obj.dance)
            for dancer_obj in (partnership.lead, partnership.follow):
                if other_dance in dancer_obj.entries:
                    return EligibilityResult(
                        eligible=False,
                        violation_type=ViolationType.NIGHTCLUB_CONSECUTIVE_LEVEL,
                        detail_message=(
                            f"CONSECUTIVE LEVEL VIOLATION: '{dancer_obj.name}' is "
                            f"already registered for both levels of '{dance_obj.dance}'."
                        ),
                        subject_name=dancer_obj.name,
                    )

        # Everyone is always eligible for int./adv. Nightclub and Championship
        if dance_obj.level == NightclubLevel.INT_ADV or dance_obj.level == OpenLevel.CHAMP:
            return EligibilityResult(eligible=True)

        # Check eligibility for Beginner Nightclub
        if dance_obj.level == NightclubLevel.BEGINNER:
            if partnership.nc_beginners:
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.NIGHTCLUB_BEGINNER,
                detail_message=(
                    f"NIGHTCLUB BEGINNER VIOLATION: '{partnership.names}' "
                    f"are ineligible for '{dance_obj}'."
                ),
                subject_name=partnership.names,
            )

        # Check eligibility for Newcomer
        if dance_obj.level == SyllabusLevel.NEWCOMER:
            if partnership.newcomers:
                return EligibilityResult(eligible=True)
            return EligibilityResult(
                eligible=False,
                violation_type=ViolationType.NEWCOMER,
                detail_message=(
                    f"NEWCOMER VIOLATION: '{partnership.names}' " f"ineligible for '{dance_obj}'."
                ),
                subject_name=partnership.names,
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
            partnership.lead, dance_obj.style, dance_obj.dance
        )
        follow_level = ProficiencyCalculator.compute_proficiency_level(
            partnership.follow, dance_obj.style, dance_obj.dance
        )
        event_level = constants.LEVELS.index(dance_obj.level)

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
        lead_eligibility = constants.LEVELS[lead_level]
        follow_eligibility = constants.LEVELS[follow_level]
        recommended_levels = RecommendedLevelsCalculator.compute(partnership, dance_obj.style)
        return EligibilityResult(
            eligible=False,
            violation_type=ViolationType.POINTED_OUT,
            detail_message=(
                f"POINTED OUT VIOLATION: '{partnership.names}' are ineligible "
                f"for '{dance_obj}'\n"
                f"\t{partnership.lead} lowest allowed level is {lead_eligibility}.\n"
                f"\t{partnership.follow} lowest allowed level is {follow_eligibility}.\n"
                f"\tRecommended {dance_obj.style} level(s) for this partnership: "
                f"{' and '.join(recommended_levels)}."
            ),
            subject_name=partnership.names,
        )

    def _check_rookie_vet_newcomer(
        self, partnership: Partnership, dance_obj: Dance
    ) -> EligibilityResult | None:
        """Check rookie/vet eligibility under the 'newcomer' ruleset.

        The Rookie partner must (1) be a time-based newcomer and not have
        pointed out of Newcomer in this specific dance, and (2) if they also
        have a regular-level entry for this specific dance in this style, it
        must be at or below rookie_max_level and not with the same partner
        as this Rookie/Vet entry. The Veteran partner must not be registered
        for a Newcomer or Bronze event anywhere in this style (checked
        style-wide, unlike the Rookie's own-entry checks, since the Veteran's
        floor isn't tied to one specific dance).
        """
        if dance_obj.level == RookieVetLevel.ROOKIE_LEAD:
            return self._check_rookie_vet_newcomer_role(
                partnership,
                dance_obj,
                rookie=partnership.lead,
                rookie_role="Lead",
                vet=partnership.follow,
                vet_role="Follow",
                violation_type=ViolationType.ROOKIE_LEAD,
            )

        if dance_obj.level == RookieVetLevel.ROOKIE_FOLLOW:
            return self._check_rookie_vet_newcomer_role(
                partnership,
                dance_obj,
                rookie=partnership.follow,
                rookie_role="Follow",
                vet=partnership.lead,
                vet_role="Lead",
                violation_type=ViolationType.ROOKIE_FOLLOW,
            )

        return None

    def _check_rookie_vet_newcomer_role(
        self,
        partnership: Partnership,
        dance_obj: Dance,
        rookie: Dancer,
        rookie_role: str,
        vet: Dancer,
        vet_role: str,
        violation_type: ViolationType,
    ) -> EligibilityResult:
        """Shared 'newcomer'-ruleset Rookie/Vet check for one role assignment.

        Called once with (rookie=lead, vet=follow) and once with the roles
        swapped, since _check_rookie_vet_newcomer's Lead and Follow checks
        are otherwise identical.
        """
        curr_style = dance_obj.style
        disqualifying_level_idx = constants.SYLLABUS_LEVELS.index(self.rookie_max_level) + 1

        rookie_is_newcomer = rookie.is_newcomer()
        rookie_pointed_out_of_newcomer = ProficiencyCalculator.has_pointed_out(
            rookie, Dance(SyllabusLevel.NEWCOMER, curr_style, dance_obj.dance)
        )
        rookie_above_own_cap = rookie.has_entry_above(
            curr_style, dance_obj.dance, disqualifying_level_idx
        )
        rookie_same_partner_entry = rookie.has_entry_with_partnership(
            curr_style, dance_obj.dance, partnership
        )
        vet_registered_newcomer = vet.is_registered_newcomer(curr_style)
        vet_registered_bronze = vet.is_registered_bronze(curr_style)
        if (
            rookie_is_newcomer
            and not rookie_pointed_out_of_newcomer
            and not rookie_above_own_cap
            and not rookie_same_partner_entry
            and not vet_registered_newcomer
            and not vet_registered_bronze
        ):
            return EligibilityResult(eligible=True)

        reasons = []
        if not rookie_is_newcomer:
            reasons.append(
                f"{rookie_role} ({rookie}) is not a newcomer, so is ineligible "
                f"for the Rookie {rookie_role} designation."
            )
        if rookie_pointed_out_of_newcomer:
            reasons.append(
                f"{rookie_role} ({rookie}) has pointed out of Newcomer "
                f"{curr_style} {dance_obj.dance}, so is ineligible for the "
                f"Rookie {rookie_role} designation."
            )
        if rookie_above_own_cap:
            reasons.append(
                f"{rookie_role} ({rookie}) is registered above "
                f"{self.rookie_max_level} in {curr_style} {dance_obj.dance}, "
                f"exceeding the level a Rookie may also compete at."
            )
        if rookie_same_partner_entry:
            reasons.append(
                f"{rookie_role} ({rookie}) is also registered for "
                f"{curr_style} {dance_obj.dance} with the same partner "
                f"({vet}) outside the Rookie {rookie_role} designation."
            )
        if vet_registered_newcomer:
            reasons.append(
                f"{vet_role} ({vet}) is already registered for a "
                f"Newcomer {curr_style} event, so can't act as the vet partner."
            )
        if vet_registered_bronze:
            reasons.append(
                f"{vet_role} ({vet}) is already registered for a "
                f"Bronze {curr_style} event, so can't act as the vet partner."
            )
        return EligibilityResult(
            eligible=False,
            violation_type=violation_type,
            detail_message=(
                f"ROOKIE-{rookie_role.upper()} VIOLATION: '{partnership.names}' ineligible "
                f"for '{dance_obj}'.\n" + "\n".join(f"\t{reason}" for reason in reasons)
            ),
            subject_name=partnership.names,
        )

    def _check_rookie_vet_level(
        self, partnership: Partnership, dance_obj: Dance
    ) -> EligibilityResult | None:
        """Check rookie/vet eligibility under the 'level' ruleset."""
        if dance_obj.level == RookieVetLevel.ROOKIE_LEAD:
            return self._check_rookie_vet_level_role(
                partnership,
                dance_obj,
                rookie=partnership.lead,
                rookie_role="Lead",
                vet=partnership.follow,
                vet_role="Follow",
                violation_type=ViolationType.ROOKIE_LEAD,
            )

        if dance_obj.level == RookieVetLevel.ROOKIE_FOLLOW:
            return self._check_rookie_vet_level_role(
                partnership,
                dance_obj,
                rookie=partnership.follow,
                rookie_role="Follow",
                vet=partnership.lead,
                vet_role="Lead",
                violation_type=ViolationType.ROOKIE_FOLLOW,
            )

        return None

    def _check_rookie_vet_level_role(
        self,
        partnership: Partnership,
        dance_obj: Dance,
        rookie: Dancer,
        rookie_role: str,
        vet: Dancer,
        vet_role: str,
        violation_type: ViolationType,
    ) -> EligibilityResult:
        """Shared 'level'-ruleset Rookie/Vet check for one role assignment -
        see _check_rookie_vet_newcomer_role for why this is split out from
        the Lead/Follow dispatch above.
        """
        rookie_has_vet_entries = rookie.has_vet_entries(dance_obj.style)
        vet_has_rookie_entries = vet.has_rookie_entries(dance_obj.style)
        if not rookie_has_vet_entries and not vet_has_rookie_entries:
            return EligibilityResult(eligible=True)

        reasons = []
        if rookie_has_vet_entries:
            reasons.append(
                f"{rookie_role} ({rookie}) already has Silver-or-above "
                f"{dance_obj.style} entries, so is ineligible for the Rookie "
                f"{rookie_role} designation."
            )
        if vet_has_rookie_entries:
            reasons.append(
                f"{vet_role} ({vet}) already has Bronze-or-below "
                f"{dance_obj.style} entries, so can't act as the vet partner."
            )
        return EligibilityResult(
            eligible=False,
            violation_type=violation_type,
            detail_message=(
                f"ROOKIE-{rookie_role.upper()} VIOLATION: '{partnership.names}' ineligible "
                f"for '{dance_obj}'.\n" + "\n".join(f"\t{reason}" for reason in reasons)
            ),
            subject_name=partnership.names,
        )
