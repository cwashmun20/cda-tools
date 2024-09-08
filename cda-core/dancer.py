import dancer_points as pts
from datetime import date

class Dancer:
    """Abstract representation of a dancer for FLC entry checking and point updating purposes.
       All dates are handeled using the datetime library's date object.
    """
    
    name = None
    id = 9999  # Dancer's CDA #
    first_comp_date = None
    points = None

    def __init__(self, name: str, first_comp_date):  #TODO (CWA): Assess whether this is the best format for importing comp date data.
        """Parameterized constructor for adding a new dancer to the system (TODO: (CWA): check if this function is needed?).
        first_comp_date should be a tuple of 3 strings in ('MM', 'DD', 'YYYY') format.
        """
        self.name = name
        self.id = 9999  #TODO (CWA): Implement grabbing the next available CDA #.

        month, day, year = map(int, first_comp_date)
        self.first_comp_date = date(year, month, day)

        self.points = pts.DancerPoints()  #TODO (CWA): Construct this properly
    
    # TODO (CWA): Implement a new constructor for making a Dancer from existing database data.

    def newcomer(self) -> bool:
        """Returns true if a dancer would be considered a newcomer (competing < 1 year)."""
        return (date.today() - self.first_comp_date).days // 365 < 1
    
    def nc_beginner(self) -> bool:
        """Returns true if a dancer would be considered a beginner
            nightclub dancer (competing < 2 years).
        """
        return (date.today() - self.first_comp_date).days // 365 < 2