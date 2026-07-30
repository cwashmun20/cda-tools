import datetime
from typing import Optional

from cda_core.lib import constants
from cda_core.lib.api.client import DancerRecord, lookup_dancer
from cda_core.lib.models.dance import Dance
from cda_core.lib.models.entry import Entry
from cda_core.lib.points import Points


class Dancer:
    """Abstract representation of a dancer for entry checking and points-updating purposes.
    All dates are handled using the datetime library's date object.
    """

    def __init__(self, curr_comp_date: datetime.date, dancer_record: DancerRecord):
        """Construct a Dancer from a DancerRecord (typed API response).

        Args:
            curr_comp_date: The date of the current competition.
            dancer_record: A DancerRecord from the API client.
        """
        self.name: str = " ".join([dancer_record.first, dancer_record.last])
        self.curr_comp_date: datetime.date = curr_comp_date
        self.created_date: str = dancer_record.created_date
        self.cda_id: Optional[int] = dancer_record.cda_id
        self.points: Points = Points(dancer_record.syllabus_pts, dancer_record.open_pts)
        self.entries: set["Entry"] = set()

        self.first_comp_date: datetime.date
        # New Dancers (not yet in database)
        if dancer_record.cda_id is None:
            self.first_comp_date = curr_comp_date
        # Existing Dancers in the Database - the API always populates
        # first_comp_date alongside cda_id, so this is never None here.
        else:
            assert dancer_record.first_comp_date is not None
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
        # Returns True if the dancer is registered for a Newcomer event in the
        # current style; otherwise, False.
        for e in self.entries:
            entry_style = e.dance_data.style
            entry_level = e.dance_data.level
            if curr_style == entry_style and entry_level == constants.SYLLABUS_LEVELS[0]:
                return True
        return False

    def is_registered_bronze(self, curr_style: str) -> bool:
        # Returns True if the dancer is registered for a Bronze event in the
        # current style; otherwise, False.
        for e in self.entries:
            entry_style = e.dance_data.style
            entry_level = e.dance_data.level
            if curr_style == entry_style and entry_level == constants.SYLLABUS_LEVELS[1]:
                return True
        return False

    def nc_beginner(self) -> bool:
        """Returns True if a dancer would be considered a beginner
        nightclub dancer (competing < 2 years); otherwise False.
        """
        return (self.curr_comp_date - self.first_comp_date).days // 365 < 2

    def add(self, comp_entry: "Entry"):
        """Adds a competition entry for a dancer. Should only be called from a partnership."""
        self.entries.add(comp_entry)

    def drop(self, comp_entry: "Entry"):
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
            is_vet_entry = constants.LEVELS.index(comp_entry.dance_data.level) >= 2
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
            is_rookie_entry = constants.LEVELS.index(comp_entry.dance_data.level) <= 1
            if style_match and is_rookie_entry:
                return True
        return False

    def has_entry_above(self, style: str, dance: str, level_idx: int) -> bool:
        """Returns True if the dancer has an entry for a specific dance in a
        style at or above a given level index (see constants.LEVELS).

        Args:
            style: the dance's style/category (e.g. "Smooth", "Latin").
            dance: the specific dance name (e.g. "Waltz").
            level_idx: the minimum constants.LEVELS index that counts.
        Returns:
            True if a matching entry exists at or above level_idx.
        """
        for e in self.entries:
            entry = e.dance_data
            if (
                entry.style == style
                and entry.dance == dance
                and entry.level in constants.LEVELS
                and constants.LEVELS.index(entry.level) >= level_idx
            ):
                return True
        return False

    def has_entry_with_partnership(self, style: str, dance: str, partnership_obj) -> bool:
        """Returns True if the dancer has a regular (non Rookie/Vet) entry
        for a specific dance in a style registered with a given partnership.

        Args:
            style: the dance's style/category (e.g. "Smooth", "Latin").
            dance: the specific dance name (e.g. "Waltz").
            partnership_obj: the Partnership to match against.
        Returns:
            True if a matching entry exists with that partnership.
        """
        for e in self.entries:
            entry = e.dance_data
            if (
                entry.style == style
                and entry.dance == dance
                and entry.level in constants.LEVELS
                and e.partnership is partnership_obj
            ):
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
            ValueError: if target_dance is not eligible for points
                        (e.g. nightclub dances).
        """
        if target_dance.style not in constants.STYLES[:-1]:
            raise ValueError(f"""'{target_dance}' is not eligible for points
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

        raise ValueError(
            f"'{target_dance}' has an unrecognized level and is not eligible for points."
        )
