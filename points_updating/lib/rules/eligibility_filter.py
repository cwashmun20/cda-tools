"""Points-eligibility filtering for points_updating.

Parsing raw competition results (out of scope for this package) may produce
a CompetitionResult for every dance danced at a competition, including ones
Fair Level Certification doesn't award points for: Nightclub (a non-points-
eligible style) and Rookie/Vet events (a non-points-eligible level, even
though they're danced in a points-eligible style like Smooth or Latin).
This is the boundary step between parsing and point calculation: it drops
those results before they ever reach PointsCalculator, which assumes every
result it's given is points-eligible.
"""

from cda_core.lib import constants
from cda_core.lib.constants import Style
from points_updating.lib.models.result import CompetitionResult


def filter_points_eligible(results: list[CompetitionResult]) -> list[CompetitionResult]:
    """Drops CompetitionResults not eligible for Fair Level Certification points.

    Args:
        results: CompetitionResults to filter - may include non-points-
            eligible styles (Nightclub) or levels (Rookie/Vet) if produced
            directly from raw competition results.
    Returns:
        Only the results whose dance is both a points-eligible style and a
        real syllabus/open level.
    """
    eligible_styles = Style.points_eligible_styles()
    return [
        result
        for result in results
        if result.dance.style in eligible_styles and result.dance.level in constants.LEVELS
    ]
