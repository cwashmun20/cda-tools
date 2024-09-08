import dance
import partnership as partners

class Entry:
    """Representation of a competition entry; holds all the info obtainable from
    an o2cm entry.
    """

    dance_info = None
    dancers = None
    event_name = None
    heat = None
    multi_dance = False

    def __init__(self, style, dance, skill, lead_first, lead_last, follow_first, follow_last, event_name, heat=None):
        if dance.isupper():
            multi_dance = True
            raise ValueError("""Attempted to construct an Entry from a multi-dance event. 
                                Please handle multi-dance events in the entry checker.""")
            for symbol in dance.ABBREVIATION_MAPS[style].keys():
                if symbol in dance:
                    continue
            # TODO (CWA): Figure out *where* and how to handle multi-dance events.        
        else:
            self.dance_info = dance.Dance(style, dance, skill)
        
        # TODO (CWA): Implement way to grab first comp date from database.
        # TODO (CWA): Implement way to make a Dancer object with their points data if they
        #               already exist in the system.
        lead = dance.Dancer(f"{lead_first} {lead_last}", get_first_comp())
        follow = dance.Dancer(f"{follow_first} {follow_last}", get_first_comp())
        self.dancers = partners.Partnership(lead, follow)
        self.event_name = event_name
        self.heat = heat
