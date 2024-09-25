import dance
import partnership as partners

class Entry:
    """Representation of a competition entry."""

    dance_data = dance.Dance()
    partnership = partners.Partnership()
    event_name = None
    heat = None

    def __init__(self, dance_obj: dance.Dance, dancers: partners.Partnership, event_name, heat=None):
        self.dance_data = dance_obj
        self.partnership = dancers
        self.event_name = event_name
        self.heat = heat
        self.partnership.add(self)

    def __repr__(self):
        return str(self.dance_data)
