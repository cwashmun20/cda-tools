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
