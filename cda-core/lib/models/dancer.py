import datetime
from typing import Optional

import constants
from api.client import DancerRecord, lookup_dancer
from models.dance import Dance
from models.entry import Entry
from points import Points


class Dancer:
    """Abstract representation of a dancer for FLC entry checking and point updating purposes.
       All dates are handled using the datetime library's date object.
    """
    name: Optional[str] = None
    cda_id: Optional[int] = None  # Dancer's CDA #
    first_comp_date: Optional[datetime.date] = None
    curr_comp_date: Optional[datetime.date] = None
    created_date: Optional[str] = None
    points: Optional[Points] = None
    entries: set = set()

    def __init__(self, curr_comp_date: datetime.date, dancer_record: DancerRecord):
        """Construct a Dancer from a DancerRecord (typed API response).

        Args:
            curr_comp_date: The date of the current competition.
            dancer_record: A DancerRecord from the API client.
        """
        self.name = ' '.join([dancer_record.first, dancer_record.last])
        self.curr_comp_date = curr_comp_date
        self.created_date = dancer_record.created_date
        self.cda_id = dancer_record.cda_id
        self.points = Points(dancer_record.syllabus_pts, dancer_record.open_pts)
        self.entries = set()

        # New Dancers (not yet in database)
        if dancer_record.cda_id is None:
            self.first_comp_date = curr_comp_date
        # Existing Dancers in the Database
        else:
            self.first_comp_date = dancer_record.first_comp_date

    @classmethod
    def from_api(cls, curr_comp_date: datetime.date, first: str, last: str) -> "Dancer":
        """Fetch a dancer from the CDA API and construct a Dancer object.

        Args:
            curr_comp_date: The date of the current competition.
            first: The dancer's first name.
            last: The dancer's last name.
        Returns:
            A Dancer constructed from the API response.
        """
        record = lookup_dancer(first, last)
        return cls(curr_comp_date, record)

    @classmethod
    def from_data(cls, curr_comp_date: datetime.date, dancer_record: DancerRecord) -> "Dancer":
        """Construct a Dancer from an existing DancerRecord (no API call).

        Args:
            curr_comp_date: The date of the current competition.
            dancer_record: A DancerRecord, possibly from test/mock data.
        Returns:
            A Dancer constructed from the provided data.
        """
        return cls(curr_comp_date, dancer_record)

    def __repr__(self) -> str:
        return self.name

    def is_newcomer(self) -> bool:
        """Returns True if a dancer would be considered a newcomer
        (competing < 1 year); otherwise False.
        """
        return (self.curr_comp_date - self.first_comp_date).days // 365 < 1

    def is_registered_newcomer(self, curr_style: str) -> bool:
        # Returns True if the dancer is registered for a Newcomer event in the current style; otherwise, False.
        for e in self.entries:
            entry_style = e.dance_data.style
            entry_level = e.dance_data.level
            if curr_style == entry_style and entry_level == constants.SYLLABUS_LEVELS[0]:
                print(f"{self.name} is registered for at least one Newcomer event in {curr_style}.")
                return True
        return False

    def is_registered_bronze(self, curr_style: str) -> bool:
        # Returns True if the dancer is registered for a Bronze event in the current style; otherwise, False.
        for e in self.entries:
            entry_style = e.dance_data.style
            entry_level = e.dance_data.level
            if curr_style == entry_style and entry_level == constants.SYLLABUS_LEVELS[1]:
                print(f"{self.name} is registered for at least one Bronze event in {curr_style}.")
                return True
        return False

    def nc_beginner(self) -> bool:
        """Returns True if a dancer would be considered a beginner
            nightclub dancer (competing < 2 years); otherwise False.
        """
        return (self.curr_comp_date - self.first_comp_date).days // 365 < 2

    def add(self, comp_entry: 'Entry'):
        """Adds a competition entry for a dancer. Should only be called from a partnership."""
        # Grab nightclub-related info.
        entry_style = comp_entry.dance_data.style
        is_nightclub = False
        if entry_style == constants.Style.NIGHTCLUB:
            is_nightclub = True
            nc_dance = comp_entry.dance_data.dance
            nc_level = comp_entry.dance_data.level
            other_nc_level = constants.NC_LEVELS[0] if nc_level == constants.NC_LEVELS[1] else constants.NC_LEVELS[1]
            other_nc_dance = Dance(other_nc_level, entry_style, nc_dance)

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

    def drop(self, comp_entry: 'Entry'):
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
            is_vet_entry = constants.FLC_LEVELS.index(comp_entry.dance_data.level) >= 2
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
            is_rookie_entry = constants.FLC_LEVELS.index(comp_entry.dance_data.level) <= 1
            if style_match and is_rookie_entry:
                return True
        return False

    def get_points(self, target_dance: Dance) -> int:
        """Retrieves the points earned for a given dance at a given level,
           returning an int.

        Args:
            target_dance: a Dance object used to search for the dancer's points.
        Returns:
            the number of points the dancer has in target_dance.
        Raises:
            ValueError: if target_dance is not eligible for FLC points
                        (e.g. nightclub dances).
        """
        if target_dance.style not in constants.STYLES[:-1]:
            raise ValueError(f"""'{target_dance}' is not eligible for FLC points
                                 (e.g. nightclub dances).""")

        if target_dance.level in constants.SYLLABUS_LEVELS:
            row_idx = constants.SYLLABUS_LEVELS.index(target_dance.level)
            col_idx = constants.DANCE_NAMES[target_dance.style].index(target_dance.dance)
            if target_dance.style == constants.Style.SMOOTH:
                col_idx += 5
            if target_dance.style == constants.Style.LATIN:
                col_idx += 9
            if target_dance.style == constants.Style.RHYTHM:
                col_idx += 14
            return self.points.syllabus_data[row_idx][col_idx]
        elif target_dance.level in constants.OPEN_LEVELS:
            row_idx = constants.OPEN_LEVELS.index(target_dance.level)
            col_idx = constants.STYLES.index(target_dance.style)
            return self.points.open_data[row_idx][col_idx]

    def pointed_out(self, dance_obj: Dance) -> bool:
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
        for level in constants.FLC_LEVELS:
            curr_dance = Dance(level, style, dance_name)
            if self.pointed_out(curr_dance):
                point_out_level += 1
            else:
                break
        return point_out_level

    def proficiency_level(self, *args) -> int:
        """Returns an int representing a dancer's proficiency level for a given dance, following
        CDA Fair Level Certification rules: https://collegiatedancesport.org/fairlevel/
        Proficiency level integer represents the lowest level a dancer *is* eligible
        to register for and corresponds to the index of the level in constants.FLC_LEVELS:
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

        newcomer_level = 0 if self.is_newcomer() else 1

        # Proficiency via Pointing Out
        point_out_level = self.point_out_level(style, dance_name)

        # Within-Style Proficiency: never less than two levels lower
        # than any other dance within the same style.
        within_style_level = 0
        for curr_dance_name in constants.DANCE_NAMES[style]:
            if curr_dance_name != dance_name:
                within_style_level = max(within_style_level,
                                         self.point_out_level(style, curr_dance_name) - 2)

        # Cross-Style Proficiency
        cross_style_level = 0
        if style == constants.Style.STANDARD:
            other_style = constants.Style.SMOOTH
        elif style == constants.Style.SMOOTH:
            other_style = constants.Style.STANDARD
        elif style == constants.Style.LATIN:
            other_style = constants.Style.RHYTHM
        elif style == constants.Style.RHYTHM:
            other_style = constants.Style.LATIN
        else:
            raise ValueError(f"'{style}' is not eligible for FLC points (e.g. nightclub dances).")

        # Cross-Style: Dances where their corresponding dance has the same name.
        if (style in [constants.Style.STANDARD, constants.Style.SMOOTH]
                or dance_name in ["ChaCha", "Rumba"]) and dance_name != "Quickstep":
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