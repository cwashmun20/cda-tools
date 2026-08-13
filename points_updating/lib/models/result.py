"""File-format-agnostic intermediate result model for points_updating.

Provides CompetitionResult/DancerRef, the shape every results parser
produces, so point-calculation logic never needs to know which results
source produced the raw strings.
"""

from dataclasses import dataclass
from datetime import date

from utils.lib.models.dance import Dance


@dataclass(frozen=True)
class DancerRef:
    """Identifies a dancer within a CompetitionResult by name alone.

    Deliberately not a Dancer: a Dancer can only be constructed from a
    DancerRecord fetched via the API (see Dancer.from_api), which isn't
    available until BackfillEngine looks this reference up. DancerRef is
    the raw identity that lookup takes as input, not a lighter Dancer.
    """

    first: str
    last: str

    def __post_init__(self) -> None:
        # A results source occasionally lists a name with a lowercase
        # first letter, so we normalize here before lookup.
        object.__setattr__(self, "first", _capitalize_first_letter(self.first))
        object.__setattr__(self, "last", _capitalize_first_letter(self.last))

    @property
    def full_name(self) -> str:
        return f"{self.first} {self.last}"


def _capitalize_first_letter(name: str) -> str:
    """Uppercases just a name's first character, leaving the rest as-is -
    unlike str.capitalize()/str.title(), this doesn't lowercase interior
    letters, so names with legitimate internal capitalization (e.g.
    "McDonald", "DiCaprio") aren't corrupted.
    """
    if not name:
        return name
    return name[0].upper() + name[1:]


@dataclass
class CompetitionResult:
    """A single couple/placement result from one competition event.

    One CompetitionResult per (couple, event) - a multi-dance event's one
    overall placement is carried once here, in event_dances, regardless of
    whether it's a syllabus or open level; cascade.build_cascade_delta()
    fans the resulting award out to every dance in event_dances (each
    dance's own column for syllabus, the whole style's columns for open).
    dance is the combo's first dance, a convenient single-dance handle for
    callers that don't need the full combo (e.g. event_dances == (dance,)
    for a single-dance event).
    """

    dance: Dance
    lead: DancerRef
    follow: DancerRef
    place: int
    num_rounds: int
    competition_name: str
    competition_date: date
    event_dances: tuple[Dance, ...]
