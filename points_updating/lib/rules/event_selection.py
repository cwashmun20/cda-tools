"""Open-level multi-event selection for points_updating.

CompetitionResult is one per (couple, dance, event), so a multi-dance event
produces one result per dance. When an open level was split across more
than one event at a competition (e.g. Novice Smooth run as a WTF event plus
a separate V event), couples placed in all of them - but CDA rules use only
the event with the most dances to calculate points at that level+style; the
other event's results are dropped, not because the placements didn't
happen, but because they don't count toward points.
"""

from collections import defaultdict
from typing import Hashable

from cda_core.lib import constants
from cda_core.lib.constants import DanceName
from cda_core.lib.models.dance import Dance
from points_updating.lib.models.result import CompetitionResult

_TIEBREAK_DANCES = (DanceName.WALTZ, DanceName.CHA_CHA)


def select_points_event_results(results: list[CompetitionResult]) -> list[CompetitionResult]:
    """Drops CompetitionResults from events CDA rules don't use for points.

    Groups results by (competition, lead, follow, style, open level) and
    keeps only the points-event results within each group (see
    _filter_group_to_points_event). Syllabus-level results always pass
    through unchanged, since this rule only applies to open levels.

    Args:
        results: CompetitionResults to filter - may span multiple
            competitions, couples, styles, and levels.
    Returns:
        results with non-points-event CompetitionResults removed.
    """
    groups: dict[Hashable, list[CompetitionResult]] = defaultdict(list)
    passthrough: list[CompetitionResult] = []

    for result in results:
        if result.dance.level not in constants.OPEN_LEVELS:
            passthrough.append(result)
            continue
        key = (
            result.competition_name,
            result.competition_date,
            result.lead,
            result.follow,
            result.dance.style,
            result.dance.level,
        )
        groups[key].append(result)

    selected = list(passthrough)
    for group in groups.values():
        selected.extend(_filter_group_to_points_event(group))
    return selected


def _filter_group_to_points_event(group: list[CompetitionResult]) -> list[CompetitionResult]:
    """Keeps only one couple's results from the event CDA rules use for points.

    Args:
        group: Every CompetitionResult one couple earned at one open
            level+style at one competition - may span more than one event.
    Returns:
        Only the results from the event with the most dances, breaking ties
        by whether the event includes Waltz or Cha Cha. Unchanged if the
        group is already a single event.
    """
    event_dance_sets = {result.event_dances for result in group}
    if len(event_dance_sets) <= 1:
        return group

    points_event = max(event_dance_sets, key=_event_rank)
    return [result for result in group if result.event_dances == points_event]


def _event_rank(event_dances: tuple[Dance, ...]) -> tuple[int, bool]:
    has_tiebreak_dance = any(d.dance in _TIEBREAK_DANCES for d in event_dances)
    return (len(event_dances), has_tiebreak_dance)
