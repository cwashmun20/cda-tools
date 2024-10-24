import dance
import partnership as partners

class Entry:
    """Representation of a competition entry."""

    dance_data = dance.Dance()
    event_name = ""
    partnership = partners.Partnership()
    heat = ""

    def __init__(self, dance_obj: dance.Dance, dancers: partners.Partnership, heat=None):
        self.dance_data = dance_obj
        self.event_name = str(dance_obj)
        self.partnership = dancers
        self.heat = heat
        self.partnership.add(self)

    def __repr__(self):
        return str((self.partnership, self.dance_data))
