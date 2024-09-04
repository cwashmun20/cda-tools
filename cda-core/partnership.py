import dancer
import dancer_points as pts

class Partnership:
    """Representation of a partnership."""

    name = ""
    lead = None
    follow = None
    couple_proficiencies = None


    def __init__(self, lead: dancer.Dancer, follow: dancer.Dancer):
        """Create a partnership from two dancers."""
        
        self.name = lead.name + " & " + follow.name
        self.lead = lead
        self.follow = follow
        self.couple_proficiencies = self.get_proficiencies()

    
    def get_proficiencies(self):
        """Calculates the proficiency levels of all dances for a couple, which
            corresponds to what level they can register for in each dance."""
        # TODO (CWA): Implement proper merging once the Points class is finished.
        return self.lead.points + self.follow.points



