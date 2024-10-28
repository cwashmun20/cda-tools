from typing import TYPE_CHECKING
import dance

if TYPE_CHECKING:
    from partnership import Partnership

class Entry:
    """Representation of a competition entry."""

    dance_data = None
    event_name = ""
    partnership = None
    heat = ""

    def __init__(self, dance_obj: dance.Dance, partnership_obj: 'Partnership', heat=None):
        self.dance_data = dance_obj
        self.event_name = str(dance_obj)
        self.partnership = partnership_obj
        self.heat = heat
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
        elif isinstance(other, dance.Dance):
            return self.dance_data == other
    
    def __hash__(self):
        """Hashing is based only on the entry's dance (not its partnership)."""
        return hash(self.dance_data)
