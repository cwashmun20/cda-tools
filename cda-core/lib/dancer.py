import dance
import dancer_points as pts
from datetime import date
import entry

class Dancer:
    """Abstract representation of a dancer for FLC entry checking and point updating purposes.
       All dates are handled using the datetime library's date object.
    """
    
    name = None
    id = 9999  # Dancer's CDA #
    first_comp_date = None
    points = None
    entries = set()

    def __init__(self, name: str, first_comp_date):  #TODO (CWA): Assess whether this is the best format for importing comp date data.
        """Parameterized constructor for adding a new dancer to the system (TODO: (CWA): check if this function is needed?).
        first_comp_date should be a tuple of 3 strings in ('MM', 'DD', 'YYYY') format.
        """
        self.name = name
        self.id = 9999  #TODO (CWA): Implement grabbing the next available CDA #.

        month, day, year = map(int, first_comp_date)
        self.first_comp_date = date(year, month, day)

        self.points = pts.DancerPoints()  #TODO (CWA): Construct this properly
        self.entries = []
    
    # TODO (CWA): Implement a new constructor for making a Dancer from existing database data.

    def newcomer(self) -> bool:
        """Returns True if a dancer would be considered a newcomer 
        (competing < 1 year); otherwise False.
        """
        return (date.today() - self.first_comp_date).days // 365 < 1
    
    def nc_beginner(self) -> bool:
        """Returns True if a dancer would be considered a beginner
            nightclub dancer (competing < 2 years); otherwise False.
        """
        return (date.today() - self.first_comp_date).days // 365 < 2
    
    def add(self, comp_entry: entry.Entry):
        """Adds a competition entry for a dancer. Should only be called from a partnership."""
        if comp_entry not in self.entries:
            self.entries.add(comp_entry)

    def drop(self, comp_entry: entry.Entry):
        """Drops a competition entry for a couple. Should only be called from a partnership"""
        self.entries.remove(comp_entry)

    def has_vet_entries(self, style: str) -> bool:
        """Returns True if the dancer has entries of Silver and above in a
        certain style; otherwise False. Having vet entries disqualifies a dancer
        from being a rookie.
        
        Args:
            style: the dance's style/category (e.g. "Smooth", "Latin").
        Returns:
            True if dancer has entries that would qualify them as a vet in a style;
            otherwise, False.
        Raises: None.
        """
        for comp_entry in self.entries:
            style_match = comp_entry.dance_data.style == style
            is_vet_entry = dance.FLC_LEVELS.index(comp_entry.dance_data.level) >= 2
            if style_match and is_vet_entry:
                return True
        return False
    
    def has_rookie_entries(self, style: str) -> bool:
        """Returns True if the dancer has entries of Bronze or below in a
        certain style; otherwise False. Having rookie entries disqualifies a
        dancer from being a vet.
        
        Args:
            style: the dance's style/category (e.g. "Smooth", "Latin").
        Returns:
            True if dancer has entries that would qualify them as a rookie in a style;
            otherwise False.
        Raises: None.
        """
        for comp_entry in self.entries:
            style_match = comp_entry.dance_data.style == style
            is_rookie_entry = dance.FLC_LEVELS.index(comp_entry.dance_data.level) <= 1
            if style_match and is_rookie_entry:
                return True
        return False