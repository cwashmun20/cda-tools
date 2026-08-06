"""Update report generation for points_updating.

Builds a human-inspectable audit trail from a set of scored results: every
result that contributed to each dancer's point change and why (reusing
ResultAward's own explainability), alongside their starting and final
totals. This is what lets an unexpected point total be traced back to the
exact result that produced it.
"""

from collections import defaultdict
from dataclasses import dataclass

from points_updating.lib.points_calculator import ResultAward
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
        date.
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
            awards=sorted(dancer_awards, key=lambda award: award.result.competition_date),
        )
        for name, dancer_awards in awards_by_dancer.items()
    ]
    return UpdateReport(dancer_reports=dancer_reports)


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
        f"Starting totals:\n{dancer_report.starting_points}",
    ]
    lines.extend(_render_award_line(award) for award in dancer_report.awards)
    lines.append(f"Final totals:\n{dancer_report.final_points}")
    return "\n".join(lines)


def _render_award_line(award: ResultAward) -> str:
    result = award.result
    total_points = int(award.delta.syllabus.sum() + award.delta.open.sum())
    split_level_note = " [SPLIT-LEVEL EXCEPTION]" if award.is_split_level else ""
    return (
        f"  {result.competition_date} {result.competition_name}: {result.dance} - "
        f"placed {result.place} of {result.num_rounds} round(s){split_level_note} "
        f"-> +{total_points} pts"
    )
