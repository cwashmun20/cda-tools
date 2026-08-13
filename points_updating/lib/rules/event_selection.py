"""Open-level multi-event selection for points_updating.

CompetitionResult is one per (couple, event), carrying every danced Dance
in event_dances - true for syllabus and open levels alike. A multi-dance
event's one overall placement produces one award, which cascade.py then
fans out to every dance in event_dances (syllabus: each dance's own
column; open: the whole style's columns), rather than one CompetitionResult
per dance. When an open level was split across more than one event at a
competition (e.g. Novice Smooth run as a WTF event plus a separate V
event), CDA rules use only the event with the most dances to calculate
points at that level+style for every couple - including a couple who
finaled in the smaller event but not the larger one, who score zero at
that level+style rather than falling back to the smaller event's
placement. The points event is therefore a property of the competition
(determined from every couple's results at that level+style, not just one
couple's), not something decided independently per couple.
"""

from collections import defaultdict
from typing import Hashable

from points_updating.lib.models.result import CompetitionResult
from utils.lib import constants
from utils.lib.constants import DanceName
from utils.lib.models.dance import Dance

_TIEBREAK_DANCES = (DanceName.WALTZ, DanceName.CHA_CHA)


def select_points_event_results(results: list[CompetitionResult]) -> list[CompetitionResult]:
    """Drops CompetitionResults from events CDA rules don't use for points.

    Args:
        results: CompetitionResults to filter - may span multiple
            competitions, couples, styles, and levels.
    Returns:
        results with non-points-event CompetitionResults removed. Syllabus-
        level results always pass through unchanged, since this rule only
        applies to open levels.
    """
    event_dance_sets: dict[Hashable, set[tuple[Dance, ...]]] = defaultdict(set)
    passthrough: list[CompetitionResult] = []
    open_results: list[CompetitionResult] = []

    for result in results:
        if result.dance.level not in constants.OPEN_LEVELS:
            passthrough.append(result)
            continue
        open_results.append(result)
        event_dance_sets[_competition_level_key(result)].add(result.event_dances)

    points_events = {
        key: max(dance_sets, key=_event_rank) for key, dance_sets in event_dance_sets.items()
    }

    selected = passthrough
    selected.extend(
        result
        for result in open_results
        if result.event_dances == points_events[_competition_level_key(result)]
    )
    return selected


def _competition_level_key(result: CompetitionResult) -> Hashable:
    """Identifies one open level+style at one competition - the scope
    within which a single points event applies to every couple."""
    return (
        result.competition_name,
        result.competition_date,
        result.dance.style,
        result.dance.level,
    )


def _event_rank(event_dances: tuple[Dance, ...]) -> tuple[int, bool]:
    has_tiebreak_dance = any(d.dance in _TIEBREAK_DANCES for d in event_dances)
    return (len(event_dances), has_tiebreak_dance)
