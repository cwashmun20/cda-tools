import dance
import numpy as np

class Points:
    """Representation of a Dancer's point totals."""

    syllabus_data = None
    open_data = None

    def __init__(self):
        """Default constructor to create a blank table of points."""
        self.syllabus_data = np.zeros((4, 19), dtype=int)
        self.open_data = np.zeros((3, 4), dtype=int)

    def __init__(self, syllabus_pts: np.ndarray, open_pts: np.ndarray):
        """Create a table of points from existing arrays of data."""
        self.syllabus_data = syllabus_pts
        self.open_data = open_pts

    def __repr__(self):
        """String representation of points; modeled after CDA points database UI."""


        string = f"""\
                     Standard      |  Smooth     |  Latin         |  Rhythm        |
                     W  T  V  F  Q |  W  T  F  V |  C  S  R  P  J |  C  R  S  B  M |
          Newcomer  34  3 11  0 37 | 21
            Bronze  s
            Silver  s
              Gold  s
            Novice        s
          Prechamp        s
             Champ        s
        """

        return string

    def linear_data(self) -> np.ndarray:
        """Returns a linear representation of a dancer's point totals in this order:
            Newcomer -> Bronze -> Silver -> Gold -> Novice -> Prechamp -> Champ.
        Within each level, the order is:
            Standard -> Smooth -> Latin -> Rhythm
        (Matches CDA point database website.)"""
        return np.reshape(self.syllabus_data, -1) + np.reshape(self.open_data, -1)
    
    def get_points(self, dance: dance.Dance) -> int:
        """Retrieves the points earned for a given dance at a given level."""

    def standard(self):
        """Returns the subarrays of points corresponding to syllabus and open Standard points."""
        return self.syllabus_data[:, :5], self.open_data[:, :1]
    
    def smooth(self):
        """Returns the subarrays of points corresponding to syllabus and open Smooth points."""
        return self.syllabus_data[:, 5:9], self.open_data[:, 1:2]
    
    def latin(self):
        """Returns the subarrays of points corresponding to syllabus and open Latin points."""
        return self.syllabus_data[:, 9:14], self.open_data[:, 2:3]
    
    def rhythm(self):
        """Returns the subarrays of points corresponding to syllabus and open Rhythm points."""
        return self.syllabus_data[:, 14:19], self.open_data[:, 3:4]
