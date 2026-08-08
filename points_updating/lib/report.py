"""Update report generation for points_updating.

Builds a human-inspectable audit trail from a set of scored results: every
result that contributed to each dancer's point change and why (reusing
ResultAward's own explainability), alongside their starting and final
totals. This is what lets an unexpected point total be traced back to the
exact result that produced it.
"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import groupby

from points_updating.lib.points_calculator import ResultAward
from points_updating.lib.rules.cascade import PointDelta
from utils.lib import constants
from utils.lib.points import Points


@dataclass
class DancerReport:
    """One dancer's full audit trail across a set of scored results."""

    dancer_name: str
    starting_points: Points
    final_points: Points
    awards: list[ResultAward]  # every result they earned points from, chronological


@dataclass
class UpdateReport:
    """The full audit trail for a set of scored results."""

    dancer_reports: list[DancerReport]


def build_report(
    awards: list[ResultAward],
    starting_totals: dict[str, Points],
    final_totals: dict[str, Points],
) -> UpdateReport:
    """Groups awards by dancer (both lead and follow of each result),
    pairing each with their starting and final totals.

    Args:
        awards: Every ResultAward to include - from one
            UpdateEngine.process_competition() call, or every competition
            in an UpdateEngine.run_backfill() run flattened together.
        starting_totals: Each processed dancer's totals from before these
            awards were applied (UpdateEngine.starting_totals()).
        final_totals: Each processed dancer's totals from after these
            awards were applied (UpdateEngine.final_totals(), with .points
            taken from each Dancer).
    Returns:
        An UpdateReport with one DancerReport per dancer appearing in
        awards, each dancer's awards sorted chronologically by competition
        (date, then name - a compound key so two competitions sharing one
        date still sort/group into separate blocks, not just tie-broken
        arbitrarily).
    """
    awards_by_dancer: dict[str, list[ResultAward]] = defaultdict(list)
    for award in awards:
        awards_by_dancer[award.result.lead.full_name].append(award)
        awards_by_dancer[award.result.follow.full_name].append(award)

    dancer_reports = [
        DancerReport(
            dancer_name=name,
            starting_points=starting_totals[name],
            final_points=final_totals[name],
            awards=sorted(dancer_awards, key=_competition_key),
        )
        for name, dancer_awards in awards_by_dancer.items()
    ]
    return UpdateReport(dancer_reports=dancer_reports)


def _competition_key(award: ResultAward) -> tuple:
    return (award.result.competition_date, award.result.competition_name)


def render_report(report: UpdateReport) -> str:
    """Renders an UpdateReport as human-readable text: one section per
    dancer, listing every result that contributed to their point change
    between their starting and final totals.
    """
    sections = [_render_dancer_report(dancer_report) for dancer_report in report.dancer_reports]
    return "\n\n".join(sections)


def _render_dancer_report(dancer_report: DancerReport) -> str:
    lines = [
        f"=== {dancer_report.dancer_name} ===",
        _render_totals(dancer_report.starting_points, dancer_report.final_points),
        "",
    ]
    for (comp_date, comp_name), comp_awards in groupby(dancer_report.awards, key=_competition_key):
        lines.append(f"{comp_date} {comp_name}:")
        lines.extend(_render_award_line(award) for award in comp_awards)
    return "\n".join(lines)


def _render_totals(starting: Points, final: Points) -> str:
    """Renders starting and final point totals stacked vertically, grouped
    together ahead of the award lines for easy before/after comparison.
    """
    return f"Starting:\n{starting}\nFinal:\n{final}"


def _render_award_line(award: ResultAward) -> str:
    result = award.result
    split_level_note = " [SPLIT-LEVEL EXCEPTION]" if award.is_split_level else ""
    breakdown = _level_breakdown(award.delta)
    points_str = ", ".join(f"{level} +{pts}" for level, pts in breakdown) if breakdown else "+0 pts"
    return (
        f"  {_render_dance(result)} - Placed {_ordinal(result.place)} from {result.num_rounds} "
        f"round(s){split_level_note} -> {points_str}"
    )


def _render_dance(result) -> str:
    """Renders a result's dance(s): just the single dance for a
    single-dance event (unchanged from before), or the shared level/style
    prefix once followed by every dance name in the combo joined by "/" for
    a multi-dance event - now that an open combo collapses to one award
    line, that line should still show everything that was danced rather
    than only the one dance the award was keyed off.
    """
    if len(result.event_dances) <= 1:
        return str(result.dance)
    first = result.event_dances[0]
    designation = ""
    if first.style in constants.AM_STYLES:
        designation = "Am. "
    elif first.style in constants.INTL_STYLES:
        designation = "Intl. "
    dance_names = "/".join(dance.dance for dance in result.event_dances)
    return f"{first.level} {designation}{dance_names}"


def _level_breakdown(delta: PointDelta) -> list[tuple[str, int]]:
    """Returns (level, points) for every level this delta actually awarded
    points to, ordered from the danced level down through each cascaded
    level below it - what a dancer actually cares about, rather than one
    opaque combined total.

    Each affected row's cells share one point value (either a single
    (style, dance) cell for a syllabus event, or every cell in that style
    for an open event's cascade into syllabus levels) - max() reads that
    shared value directly, where sum() would overcount an open cascade's
    multi-cell row.
    """
    breakdown = [
        (level, int(row.max()))
        for level, row in zip(constants.SYLLABUS_LEVELS, delta.syllabus)
        if row.max()
    ]
    breakdown += [
        (level, int(row.max()))
        for level, row in zip(constants.OPEN_LEVELS, delta.open)
        if row.max()
    ]
    return list(reversed(breakdown))


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
