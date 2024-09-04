import dancer_points as pts

class Dancer:
    """Abstract representation of a dancer for FLC entry checking and point updating purposes."""
    
    name = ""
    id = 9999  # Dancer's CDA #
    first_comp_date = ("mm", "dd", "yyyy")
    points = None

    def __init__(self, name: str, first_comp_date: tuple[str, str, str]):
        """Parameterized constructor for adding a new dancer to the system"""
        self.name = name
        self.id = 9999  #TODO (CWA): Implement grabbing the next available CDA #.
        self.first_comp_date = first_comp_date
        self.points = pts.DancerPoints()  #TODO (CWA): Construct this properly