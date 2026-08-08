"""File-format-agnostic intermediate result model for points_updating.

Provides CompetitionResult/DancerRef, the shape every results parser
produces, so point-calculation logic never needs to know which results
source produced the raw strings.
"""

from dataclasses import dataclass
from datetime import date

from utils.lib import constants
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


def event_dances_to_score(level: str, dances: tuple[Dance, ...]) -> tuple[Dance, ...]:
    """Returns which dance(s) in a (possibly multi-dance) event should each
    get their own CompetitionResult.

    A syllabus multi-dance event's single placement applies the same award
    to each dance's own distinct point column (cascade.py's syllabus branch
    keys by the specific dance) - every dance gets its own result so that
    award reaches every column it's owed to. An open multi-dance event's
    placement earns points once per style+level (cascade.py's open branch
    keys only on style/level, never the specific dance) - scoring it once
    per dance would multi-count one placement N times, so exactly one
    CompetitionResult (keyed off the first dance) represents the whole
    combo.
    """
    if level in constants.SYLLABUS_LEVELS:
        return dances
    return dances[:1]
