import dance

class Entry:
    """Representation of a competition entry."""

    dance_data = dance.Dance()
    event_name = ""
    partnership = None
    heat = ""

    from partnership import Partnership
    def __init__(self, dance_obj: dance.Dance, partnership_obj: Partnership, heat=None):
        self.dance_data = dance_obj
        self.event_name = str(dance_obj)
        self.partnership = partnership_obj
        self.heat = heat
        self.partnership.add(self)

    def __repr__(self):
        return str((self.partnership, self.dance_data))
