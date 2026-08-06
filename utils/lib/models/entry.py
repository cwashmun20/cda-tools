from typing import Optional, TYPE_CHECKING
from utils.lib.models.dance import Dance

if TYPE_CHECKING:
    from utils.lib.models.partnership import Partnership


class Entry:
    """Representation of a competition entry."""

    def __init__(
        self, dance_obj: Dance, partnership_obj: "Partnership", heat: Optional[str] = None
    ):
        self.dance_data: Dance = dance_obj
        self.event_name: str = str(dance_obj)
        self.partnership: "Partnership" = partnership_obj
        self.heat: Optional[str] = heat
        self.partnership.add(self)

    def __repr__(self):
        return str((self.partnership, self.dance_data))

    def __eq__(self, other) -> bool:
        """Two entries are considered equal if they are for the same dance at the
        same level. NOTE: Equivalent entries do not have to have the same partnership.
        This is to aid in checking each dancer for duplicate entries, regardless of
        who they're dancing with."""
        if isinstance(other, Entry):
            return self.dance_data == other.dance_data
        # You can also check equality between Entries and Dances.
        elif isinstance(other, Dance):
            return self.dance_data == other
        return False

    def __hash__(self):
        """Hashing is based only on the entry's dance (not its partnership)."""
        return hash(self.dance_data)
