import constants
from models.dance import Dance
from models.dancer import Dancer
from rules.eligibility import EligibilityChecker


class Partnership:
    """Representation of a partnership."""

    names = ""
    lead = None
    follow = None
    newcomers = None
    nc_beginners = None
    entries = []

    def __init__(self, leader: Dancer, follower: Dancer):
        """Create a partnership from two dancers."""

        self.names = leader.name + " & " + follower.name
        self.lead = leader
        self.follow = follower
        self.newcomers = leader.is_newcomer() and follower.is_newcomer()
        self.nc_beginners = leader.nc_beginner() and follower.nc_beginner()
        self.entries = set()

    def __repr__(self) -> str:
        """String representation of a partnership with registration-relevant
        information.
        """
        return self.names

    # TODO (CWA): Future feature: add recommended levels for each syllabus style,
    #             AKA the lowest common level where neither dancer has pointed
    #             out of any dances, plus the level above that. Will need to
    #             ignore Newcomer if dancers are ineligible.

    def eligible(self, dance_obj: Dance, rv_ruleset: str = "newcomer") -> bool:
        """Returns a boolean corresponding to whether a couple is eligible for
        a certain dance at a certain level. Delegates to EligibilityChecker.

        Args:
            dance_obj: a Dance object used to determine eligibility for that dance.
            rv_ruleset: a string, either "newcomer" or "level", based on which
                        ruleset a competition uses for rookie-vet eligibility.
        Returns:
            True if a couple is eligible for the dance; otherwise False.
        Prints:
            Violation messages if not eligible.
        """
        checker = EligibilityChecker(rv_ruleset)
        result = checker.check(self, dance_obj)

        if result.is_split_level and result.split_level_info:
            print(result.split_level_info)
            print()

        if not result.eligible and result.detail_message:
            print(result.detail_message)
            if result.violation_type is not None:
                print()

        return result.eligible

    def add(self, entry_obj):
        """Adds a competition entry for a couple. Should only be called within the Entry constructor."""
        self.entries.add(entry_obj)
        self.lead.add(entry_obj)
        self.follow.add(entry_obj)

    def drop(self, entry_obj):
        """Drops a competition entry for a couple."""
        self.entries.remove(entry_obj)
        self.lead.drop(entry_obj)
        self.follow.drop(entry_obj)