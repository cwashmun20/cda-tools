import dance
import numpy as np

class Points:
    """Representation of a Dancer's point totals."""

    syllabus_data = None
    open_data = None

    def __init__(self):
        """Default constructor to create a blank table of points."""
        self.syllabus_data = np.zeros((4, 19))
        self.open_data = np.zeros((3, 4))
    

    def linearize(self):
        """Returns a linear representation of a dancer's point totals in this order:
            Newcomer -> Bronze -> Silver -> Gold -> Novice -> Prechamp -> Champ.
        Within each level, the order is:
            Standard -> Smooth -> Latin -> Rhythm
        (Matches CDA point database website.)"""
        return np.reshape(self.syllabus_data, -1) + np.reshape(self.open_data, -1)
