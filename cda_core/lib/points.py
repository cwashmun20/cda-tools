"""Points representation for CDA Fair Level Certification.

This module provides the Points class for storing and displaying
a dancer's FLC point totals across all syllabus and open levels.
"""

import numpy as np


class Points:
    """Representation of a Dancer's point totals."""

    def __init__(self, syllabus_pts: np.ndarray, open_pts: np.ndarray):
        """Create a table of points from existing arrays of data.

        Args:
            syllabus_pts: 4x19 numpy array of syllabus points (Newcomer through Gold)
            open_pts: 3x4 numpy array of open points (Novice through Champ)
        """
        self.syllabus_data: np.ndarray = syllabus_pts
        self.open_data: np.ndarray = open_pts

    def __repr__(self) -> str:
        """String representation of points modeled after CDA points database UI.
        Should only need updating if point totals regularly exceed 100 or more
        point-eligible dances or levels are added.
        """
        strs = []
        lin_data = self.linear_data()
        for offset in [0, 19, 38, 57, 76, 80, 84]:
            # Format Syllabus points
            if offset < 76:
                for start, end in [(0, 5), (5, 9), (9, 14), (14, 19)]:
                    pt_line = str(lin_data[offset + start : offset + end])[1:-1]
                    # Format segments of all single-digit numbers
                    condensed_line = "".join(pt_line.split())
                    singledigit_smooth = start == 5 and len(condensed_line) == 4
                    singledigit_non_smooth = start != 5 and len(condensed_line) == 5
                    if singledigit_smooth or singledigit_non_smooth:
                        pt_line = " " + "  ".join(pt_line.split())
                    strs.append(pt_line)
            # Format Open points.
            else:
                for i in range(4):
                    open_pt = str(lin_data[offset + i : offset + i + 1])[1:-1]
                    if len(open_pt) == 1:
                        open_pt = " " + open_pt
                    strs.append(open_pt)

        string = f"""\
                     Standard      |  Smooth     |  Latin         |  Rhythm        |
                     W  T  V  F  Q |  W  T  F  V |  C  S  R  P  J |  C  R  S  B  M |
          Newcomer  {strs[0]} | {strs[1]} | {strs[2]} | {strs[3]} |
            Bronze  {strs[4]} | {strs[5]} | {strs[6]} | {strs[7]} |
            Silver  {strs[8]} | {strs[9]} | {strs[10]} | {strs[11]} |
              Gold  {strs[12]} | {strs[13]} | {strs[14]} | {strs[15]} |
            Novice        {strs[16]}       |      {strs[17]}     |       {strs[18]}       |       {strs[19]}       |
          Prechamp        {strs[20]}       |      {strs[21]}     |       {strs[22]}       |       {strs[23]}       |
             Champ        {strs[24]}       |      {strs[25]}     |       {strs[26]}       |       {strs[27]}       |
        """
        return string

    def standard(self) -> tuple:
        """Returns the subarrays of points corresponding to syllabus and open Standard points."""
        return self.syllabus_data[:, :5], self.open_data[:, :1]

    def smooth(self) -> tuple:
        """Returns the subarrays of points corresponding to syllabus and open Smooth points."""
        return self.syllabus_data[:, 5:9], self.open_data[:, 1:2]

    def latin(self) -> tuple:
        """Returns the subarrays of points corresponding to syllabus and open Latin points."""
        return self.syllabus_data[:, 9:14], self.open_data[:, 2:3]

    def rhythm(self) -> tuple:
        """Returns the subarrays of points corresponding to syllabus and open Rhythm points."""
        return self.syllabus_data[:, 14:19], self.open_data[:, 3:4]

    def linear_data(self) -> np.ndarray:
        """Returns a linear representation of a dancer's point totals in this order:
            Newcomer -> Bronze -> Silver -> Gold -> Novice -> Prechamp -> Champ.
        Within each level, the order is:
            Standard -> Smooth -> Latin -> Rhythm
        (Matches CDA point database format.)
        """
        temp_list = list(np.reshape(self.syllabus_data, -1)) + list(np.reshape(self.open_data, -1))
        return np.array(temp_list)
