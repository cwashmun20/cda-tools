import datetime
from typing import Optional, TYPE_CHECKING

from utils.lib import constants
from utils.lib.api.client import DancerRecord, lookup_dancer
from utils.lib.constants import Style, SyllabusLevel
from utils.lib.models.dance import Dance
from utils.lib.models.entry import Entry
from utils.lib.points import Points

if TYPE_CHECKING:
    from utils.lib.models.partnership import Partnership


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

    def _is_registered_at_level(self, curr_style: Style, level: str) -> bool:
        """Returns True if the dancer is registered for an event at a
        specific level in the given style; otherwise, False.
        """
        for e in self.entries:
            if e.dance_data.style == curr_style and e.dance_data.level == level:
                return True
        return False

    def is_registered_newcomer(self, curr_style: Style) -> bool:
        return self._is_registered_at_level(curr_style, SyllabusLevel.NEWCOMER)

    def is_registered_bronze(self, curr_style: Style) -> bool:
        return self._is_registered_at_level(curr_style, SyllabusLevel.BRONZE)

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

    def _has_entry_in_level_range(
        self, style: Style, min_level_idx: int = 0, max_level_idx: Optional[int] = None
    ) -> bool:
        """Returns True if the dancer has an entry in a style whose level
        index (see constants.LEVELS) falls within [min_level_idx,
        max_level_idx] inclusive; max_level_idx of None means no upper bound.
        """
        for comp_entry in self.entries:
            if comp_entry.dance_data.style != style:
                continue
            level_idx = constants.LEVELS.index(comp_entry.dance_data.level)
            if level_idx < min_level_idx:
                continue
            if max_level_idx is not None and level_idx > max_level_idx:
                continue
            return True
        return False

    def has_vet_entries(self, style: Style) -> bool:
        """Returns True if the dancer has entries of Silver and above in a
        certain style; otherwise False. Having vet entries disqualifies a dancer
        from being a rookie.

        Args:
            style: the dance's style/category (e.g. "Smooth", "Latin").
        Returns:
            True if dancer has entries that would qualify them as a vet in a style;
            otherwise, False.
        """
        return self._has_entry_in_level_range(style, min_level_idx=2)

    def has_rookie_entries(self, style: Style) -> bool:
        """Returns True if the dancer has entries of Bronze or below in a
        certain style; otherwise False. Having rookie entries disqualifies a
        dancer from being a vet.

        Args:
            style: the dance's style/category (e.g. "Smooth", "Latin").
        Returns:
            True if dancer has entries that would qualify them as a rookie in a style;
            otherwise False.
        """
        return self._has_entry_in_level_range(style, max_level_idx=1)

    def has_entry_above(self, style: Style, dance: str, level_idx: int) -> bool:
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

    def has_entry_with_partnership(
        self, style: Style, dance: str, partnership_obj: "Partnership"
    ) -> bool:
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
        if target_dance.style not in Style.points_eligible_styles():
            raise ValueError(f"""'{target_dance}' is not eligible for points
                                 (e.g. nightclub dances).""")

        if target_dance.level in constants.SYLLABUS_LEVELS:
            row_idx = constants.SYLLABUS_LEVELS.index(target_dance.level)
            style_offset = constants.SYLLABUS_COLUMN_OFFSETS[target_dance.style]
            dance_idx = constants.DANCE_NAMES[target_dance.style].index(target_dance.dance)
            return self.points.syllabus_data[row_idx][style_offset + dance_idx]
        elif target_dance.level in constants.OPEN_LEVELS:
            row_idx = constants.OPEN_LEVELS.index(target_dance.level)
            col_idx = constants.STYLES.index(target_dance.style)
            return self.points.open_data[row_idx][col_idx]

        raise ValueError(
            f"'{target_dance}' has an unrecognized level and is not eligible for points."
        )
