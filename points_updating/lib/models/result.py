"""File-format-agnostic intermediate result model for points_updating.

Provides CompetitionResult/DancerRef, the shape any future results parser
is expected to produce one of per dance (post multi-dance expansion), so
point-calculation logic never needs to know which results source produced
the raw strings.
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

    @property
    def full_name(self) -> str:
        return f"{self.first} {self.last}"


@dataclass
class CompetitionResult:
    """A single dance/couple/placement result from one competition."""

    dance: Dance
    lead: DancerRef
    follow: DancerRef
    place: int
    num_rounds: int
    competition_name: str
    competition_date: date
    event_dances: tuple[Dance, ...]
