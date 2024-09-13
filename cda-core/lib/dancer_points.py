import dance
import dancer
import numpy as np

class Points(dancer.Dancer):
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

    def __repr__(self) -> str:
        """String representation of points modeled after CDA points database UI.
        Should only need updating if point totals regularly exceed 100 or more
        point-eligible dances or levels are added.
        """
        strs = []
        lin_data = self.linear_data()
        for offset in [0, 19, 38, 57, 76, 80, 84]:
            # Format Syllabus points 
            # (this is not very nice because Smooth doesn't have a 5th dance, so
            # let's add Peabody, Polka, or Quickstep so I can write prettier code :).
            if offset < 76:
                for start, end in [(0, 5), (5, 9), (9, 14), (14, 19)]:
                    pt_line = str(lin_data[offset + start:offset + end])[1:-1]
                    # Format segments of all single-digit numbers
                    condensed_line = ''.join(pt_line.split())
                    singledigit_smooth = start == 5 and len(condensed_line) == 4
                    singledigit_non_smooth = start != 5 and len(condensed_line) == 5
                    if singledigit_smooth or singledigit_non_smooth:
                        pt_line = " " + "  ".join(pt_line.split())
                    strs.append(pt_line)
            # Format Open points.
            else:
                for i in range(4):
                    open_pt = str(lin_data[offset + i:offset + i + 1])[1:-1]
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
    
    def linear_data(self) -> np.ndarray:
        """Returns a linear representation of a dancer's point totals in this order:
            Newcomer -> Bronze -> Silver -> Gold -> Novice -> Prechamp -> Champ.
        Within each level, the order is:
            Standard -> Smooth -> Latin -> Rhythm
        (Matches CDA point database format.)
        """
        temp_list = list(np.reshape(self.syllabus_data, -1)) + list(np.reshape(self.open_data, -1))
        return np.array(temp_list)
    
    def get_points(self, target_dance: dance.Dance) -> int:
        """Retrieves the points earned for a given dance at a given level."""
        if target_dance.style not in dance.STYLES[:-1]:
            raise ValueError(f"""{target_dance} is not eligible for FLC points 
                                 (e.g. nightclub dances).""")

        if target_dance.level in dance.SYLLABUS_LEVELS:
            row_idx = dance.SYLLABUS_LEVELS.index(target_dance.level)
            col_idx = dance.DANCES[target_dance.style].index(target_dance.dance)
            return self.syllabus_data[row_idx][col_idx]
        elif target_dance.level in dance.OPEN_LEVELS:
            row_idx = dance.OPEN_LEVELS.index(target_dance.level)
            col_idx = dance.STYLES.index(target_dance.style)
            return self.open_data[row_idx][col_idx]
        else:
            raise ValueError("Invalid dance level.")

    def pointed_out(self, dance_obj: dance.Dance) -> bool:
        """Returns True if a dancer has pointed out of a Dance (at a certain
        level); otherwise, False.
        """
        return self.get_points(dance_obj) >= 7

    def point_out_level(self, style: str, dance_name: str) -> int:
        """Returns a dancer's proficiency level in a Dance based only on pointing
        out. See proficiency_level() for correspondences between the output int
        and FLC levels.
        """
        point_out_level = 0
        for level in dance.FLC_LEVELS:
            curr_dance = dance.Dance(level, style, dance_name)
            if self.pointed_out(curr_dance):
                point_out_level += 1
            else:
                break
        return point_out_level
    
    def point_out_level(self, dance_obj: dance.Dance) -> int:
        """Returns a dancer's proficiency level in a Dance based only on pointing
        out. See proficiency_level() for correspondences between the output int
        and FLC levels.
        """
        return self.point_out_level(dance_obj.style, dance_obj.dance)

    def proficiency_level(self, style: str, dance_name: str) -> int:
        """Calculates a dancer's proficiency level for a given dance, following
        CDA Fair Level Certification rules: https://collegiatedancesport.org/fairlevel/
        Proficiency level integer represents the lowest level a dancer *is* eligible
        to register for and corresponds to the index of the level in dance.FLC_LEVELS:
        0 = Newcomer
        1 = Bronze
        2 = Silver
        3 = Gold
        4 = Novice
        5 = Pre-Champ
        6 = Championship
        """
        newcomer_level = 0 if super().newcomer() else 1

        # Proficiency via Pointing Out
        point_out_level = self.point_out_level(style, dance_name)
        
        # Within-Style Proficiency: never less than two levels two levels lower
        # than any other dance within the same style.
        within_style_level = 0
        for curr_dance_name in dance.DANCES[style]:
            if curr_dance_name != dance_name:
                within_style_level = max(within_style_level, 
                                         self.point_out_level(style, curr_dance_name) - 2)

        # Cross-Style Proficiency
        cross_style_level = 0
        if style == "Standard":
            other_style == "Smooth"
        elif style == "Smooth":
            other_style = "Standard"
        elif style == "Latin":
            other_style = "Rhythm"
        elif style == "Rhythm":
            other_style = "Latin"
        else:
            raise ValueError(f"{style} is not eligible for FLC points (e.g. nightclub dances).")
        
        # Cross-Style: Dances where their corresponding dance has the same name.
        if (style in ["Standard", "Smooth"] or dance_name in ["ChaCha", "Rumba"]) and dance_name != "Quickstep":
            cross_style_level = max(cross_style_level, 
                                    self.point_out_level(other_style, dance_name) - 2)
        # Cross-Style: Swing and Jive Handling
        elif dance_name == "Jive":
            other_dance = "Swing"
        elif dance_name == "Swing":
            other_dance = "Jive"
            cross_style_level = max(cross_style_level,
                                    self.point_out_level(other_style, other_dance) - 2)

        return max(newcomer_level, point_out_level, within_style_level, cross_style_level)
    
    def proficiency_level(self, dance_obj: dance.Dance) -> int:
        """Calculates a dancer's proficiency level for a given dance, following
        CDA Fair Level Certification rules: https://collegiatedancesport.org/fairlevel/
        Can calculate by passing in a Dance object, which will ignore the level.
        """
        return self.proficiency_level(dance_obj.style, dance_obj.dance)
