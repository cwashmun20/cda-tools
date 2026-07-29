from cda_core.lib.models.dancer import Dancer


class Partnership:
    """Representation of a partnership."""

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

    def add(self, entry_obj):
        """Adds a competition entry for a couple.

        Should only be called within the Entry constructor.
        """
        self.entries.add(entry_obj)
        self.lead.add(entry_obj)
        self.follow.add(entry_obj)

    def drop(self, entry_obj):
        """Drops a competition entry for a couple."""
        self.entries.remove(entry_obj)
        self.lead.drop(entry_obj)
        self.follow.drop(entry_obj)
