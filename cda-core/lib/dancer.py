import dance
import datetime
import entry
import inspect
import numpy as np
import os
import pytz
import requests
import sys

# Allow imports from parent directory.
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
cda_tools_dir = os.path.dirname(os.path.dirname(curr_dir))
sys.path.insert(0, cda_tools_dir)

import config

SYLLABUS_KEYS = ['newcomer_points', 'bronze_points', 'silver_points', 'gold_points']
OPEN_KEYS = ['novice_points', 'prechamp_points', 'champ_points']

def lookup_dancer(first: str, last: str) -> dict:
    """Fetches all relevant data from the CDA points database for a dancer.
    
    Args:
        first: The dancer's first name.
        last: The dancer's last name.
    Returns:
        A {str: any} dictionary where the keys are strings representing relevant
        info ('id', 'first', 'last', 'first_comp_date', 'created_date',
        'syllabus_pts', 'open_pts') and the values are strings, datetime objects,
        NumPy arrays, etc. corresponding to those pieces of information.
    Note:
        In the output dictionary, the keys 'id' and 'first_comp_date' will have 
        values of None if the dancer is not already in the points database.
    """
    HEADER = {"x-api-key": config.API_KEY}
    parameters = {"firstName": first,
                  "lastName": last}
    result = requests.get("https://collegiatedancesport.org/db/namematch.php", 
                          headers=HEADER, params=parameters).json()
    
    dancer_info = {'id': None,
                   'first': None,
                   'last': None,
                   'first_comp_date': None,
                   'created_date': None,
                   'syllabus_pts': None,
                   'open_pts': None}
    
    if not result['success']:
        dancer_info['first'] = first
        dancer_info['last'] = last

        utc_dt = datetime.datetime.now(pytz.utc)
        loc_dt = utc_dt.astimezone(pytz.timezone('US/Pacific'))
        created_dt = loc_dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        created_dt = created_dt[:-2] + ':' + created_dt[-2:]
        dancer_info['created_date'] = created_dt

        dancer_info['syllabus_pts'] = np.zeros((4, 19), dtype=int)
        dancer_info['open_pts'] = np.zeros((3, 4), dtype=int)
    else:
        profile = result['competitor']
        profile_points = profile['fairlevelPoints']

        dancer_info['id'] = profile['cdaId']
        dancer_info['first'] = profile['firstName']
        dancer_info['last'] = profile['lastName']

        yr, m, d = [int(x) for x in profile['firstCompetitionDate'].split('-')]
        dancer_info['first_comp_date'] = datetime.date(yr, m, d)

        dancer_info['created_date'] = profile['dateCreated']

        syllabus_pts = [[int(pt) for pt in profile_points[key][1:-1].split(',')] 
                for key in SYLLABUS_KEYS]
        dancer_info['syllabus_pts'] = np.array(syllabus_pts)

        open_pts = [[int(pt) for pt in profile_points[key][1:-1].split(',')] 
                    for key in OPEN_KEYS]
        dancer_info['open_pts'] = np.array(open_pts)

    return dancer_info

class Dancer:
    """Abstract representation of a dancer for FLC entry checking and point updating purposes.
       All dates are handled using the datetime library's date object.
    """
    name = None
    cda_id = None  # Dancer's CDA #
    first_comp_date = None
    curr_comp_date = None
    created_date = None
    points = None
    entries = set()

    def __init__(self, curr_comp_date: datetime.date, name: str = None, first: str = None, last: str = None):
        """Parameterized constructor for fetching a dancer's info from the CDA points database."""
        if name is None and (first is None or last is None):
            raise ValueError("Must provide a full name when constructing a Dancer")
        
        # Make sure first and last have values.
        if name is not None:
            first, last = name.split()
        
        dancer_info = lookup_dancer(first, last)

        self.name = ' '.join([dancer_info['first'], dancer_info['last']])
        self.curr_comp_date = curr_comp_date
        self.created_date = dancer_info['created_date']
        self.points = Points(dancer_info['syllabus_pts'], dancer_info['open_pts'])
        self.entries = set()

        # New Dancers
        if dancer_info['id'] is None:
            self.cda_id = None
            self.first_comp_date = curr_comp_date
            
        # Existing Dancers in the Database
        else:
            self.cda_id = dancer_info['id']
            self.first_comp_date = dancer_info['first_comp_date']

    def __repr__(self) -> str:
        return self.name

    def newcomer(self) -> bool:
        """Returns True if a dancer would be considered a newcomer 
        (competing < 1 year); otherwise False.
        """
        return (self.curr_comp_date - self.first_comp_date).days // 365 < 1
    
    def nc_beginner(self) -> bool:
        """Returns True if a dancer would be considered a beginner
            nightclub dancer (competing < 2 years); otherwise False.
        """
        return (self.curr_comp_date - self.first_comp_date).days // 365 < 2
    
    def add(self, comp_entry: entry.Entry):
        """Adds a competition entry for a dancer. Should only be called from a partnership."""
        # Grab nightclub-related info.
        entry_style = comp_entry.dance_data.style
        is_nightclub = False
        if entry_style == dance.STYLES[-1]:
            is_nightclub = True
            nc_dance = comp_entry.dance_data.dance
            nc_level = comp_entry.dance_data.level
            other_nc_level = dance.NC_LEVELS[0] if nc_level == dance.NC_LEVELS[1] else dance.NC_LEVELS[1]
            other_nc_dance = dance.Dance(other_nc_level, entry_style, nc_dance)
        
        # TODO(CWA): Fix duplicate entry checking:
        # # Check for duplicate entries (currently broken but not essential).
        # if comp_entry in self.entries:
        #     print(f"DUPLICATE ENTRY: '{self.name}' is registered for '{comp_entry.dance_data}' more than once:")
        #     print(f"As '{comp_entry}'")
        #     for existing_entry in self.entries:
        #         if existing_entry == comp_entry:
        #             print(f"As '{existing_entry}'")
        #     print()
        # # Check for registration in two levels of the same Nightclub dance.
        # elif is_nightclub and other_nc_dance in self.entries:

        # Check for registration in two levels of the same Nightclub dance.
        if is_nightclub and other_nc_dance in self.entries:
            print(f"CONSECUTIVE LEVEL VIOLATION: '{self.name}' is registered for both levels of '{nc_dance}'.")
        else:
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
        """
        for comp_entry in self.entries:
            style_match = comp_entry.dance_data.style == style
            is_rookie_entry = dance.FLC_LEVELS.index(comp_entry.dance_data.level) <= 1
            if style_match and is_rookie_entry:
                return True
        return False
    
    def get_points(self, target_dance: dance.Dance) -> int:
        """Retrieves the points earned for a given dance at a given level, returning an int.
        
        Args:
            target_dance: a Dance object used to search for the dancer's points.
        Returns:
            the number of points the dancer has in target_dance.
        Raises:
            ValueError: if target_dance is not eligible for FLC points (e.g. nightclub dances).
        """
        if target_dance.style not in dance.STYLES[:-1]:
            raise ValueError(f"""'{target_dance}' is not eligible for FLC points 
                                 (e.g. nightclub dances).""")

        if target_dance.level in dance.SYLLABUS_LEVELS:
            row_idx = dance.SYLLABUS_LEVELS.index(target_dance.level)
            col_idx = dance.DANCES[target_dance.style].index(target_dance.dance)
            if target_dance.style == "Smooth":
                col_idx += 5
            if target_dance.style == "Latin":
                col_idx += 9
            if target_dance.style == "Rhythm":
                col_idx += 14
            return self.points.syllabus_data[row_idx][col_idx]
        elif target_dance.level in dance.OPEN_LEVELS:
            row_idx = dance.OPEN_LEVELS.index(target_dance.level)
            col_idx = dance.STYLES.index(target_dance.style)
            return self.points.open_data[row_idx][col_idx]

    def pointed_out(self, dance_obj: dance.Dance) -> bool:
        """Returns True if a dancer has pointed out of a Dance (at a certain
        level); otherwise, False.
        """
        num_points = self.get_points(dance_obj)
        return num_points < 0 or num_points >= 7

    def point_out_level(self, *args) -> int:
        """Returns an int representing a dancer's proficiency level in a Dance 
        based only on pointing out. See proficiency_level() for correspondences 
        between the output int and FLC levels.

        Args:
            *args can be in one of two formats:
            dance_obj: a Dance object.
            OR
            style: the dance's style/category (e.g. "Smooth", "Latin").
            dance_name: the dance's name (e.g. "Tango", "Samba").
        Returns:
            an int representing the lowest level a dancer may register for in a dance.
        """
        if len(args) == 1:
            dance_obj = args[0]
            style, dance_name = dance_obj.style, dance_obj.dance
        elif len(args) == 2:
            style, dance_name = args

        point_out_level = 0
        for level in dance.FLC_LEVELS:
            curr_dance = dance.Dance(level, style, dance_name)
            if self.pointed_out(curr_dance):
                point_out_level += 1
            else:
                break
        return point_out_level

    def proficiency_level(self, *args) -> int:
        """Returns an int representing a dancer's proficiency level for a given dance, following
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

        Args:
            *args can be in one of two formats:
            dance_obj: a Dance object.
            OR 
            style: the dance's style/category (e.g. "Smooth", "Latin").
            dance_name: the dance's name (e.g. "Tango", "Samba").
        Returns:
            an int representing the lowest level a dancer may register for in a dance.
        Raises:
            ValueError: if style is not eligible for FLC points (e.g. nightclub dances).
        """
        if len(args) == 1:
            dance_obj = args[0]
            style, dance_name = dance_obj.style, dance_obj.dance
        elif len(args) == 2:
            style, dance_name = args

        newcomer_level = 0 if self.newcomer() else 1

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
            other_style = "Smooth"
        elif style == "Smooth":
            other_style = "Standard"
        elif style == "Latin":
            other_style = "Rhythm"
        elif style == "Rhythm":
            other_style = "Latin"
        else:
            raise ValueError(f"'{style}' is not eligible for FLC points (e.g. nightclub dances).")
        
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
    


class Points(Dancer):
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

    def standard(self) -> np.ndarray:
        """Returns the subarrays of points corresponding to syllabus and open Standard points."""
        return self.syllabus_data[:, :5], self.open_data[:, :1]
    
    def smooth(self) -> np.ndarray:
        """Returns the subarrays of points corresponding to syllabus and open Smooth points."""
        return self.syllabus_data[:, 5:9], self.open_data[:, 1:2]
    
    def latin(self) -> np.ndarray:
        """Returns the subarrays of points corresponding to syllabus and open Latin points."""
        return self.syllabus_data[:, 9:14], self.open_data[:, 2:3]
    
    def rhythm(self) -> np.ndarray:
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