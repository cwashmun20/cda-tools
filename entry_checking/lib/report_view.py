"""Presentation-agnostic report data for entry-checking results.

Extracts the grouping/sorting logic entry_checker._report() prints directly
into a plain data structure, so the same grouping can be rendered by both the
CLI and a web UI without duplicating the algorithm.
"""

from dataclasses import dataclass, field

from entry_checking.lib.rules.violations import EligibilityResult, LevelViolation


@dataclass
class ReportView:
    """A presentation-agnostic view of eligibility/level-rule check results.

    split_level_notes are eligible entries that just need a 3x-points note -
    kept separate from groups since they aren't violations. groups pairs each
    subject (a partnership's combined name, or an individual dancer's name)
    with their violation messages, sorted by subject name.
    """

    split_level_notes: list[str] = field(default_factory=list)
    groups: list[tuple[str, list[str]]] = field(default_factory=list)


def build_report_view(
    eligibility_results: list[EligibilityResult], level_violations: list[LevelViolation]
) -> ReportView:
    """Build a ReportView from eligibility/level-rule check results."""
    split_level_notes = [
        result.split_level_info
        for result in eligibility_results
        if result.is_split_level and result.split_level_info
    ]

    grouped: dict[str, list[str]] = {}
    for result in eligibility_results:
        if not result.eligible and result.detail_message and result.subject_name:
            grouped.setdefault(result.subject_name, []).append(result.detail_message)
    for violation in level_violations:
        if violation.detail_message:
            grouped.setdefault(violation.dancer_name, []).append(violation.detail_message)

    groups = [(subject_name, grouped[subject_name]) for subject_name in sorted(grouped)]

    return ReportView(split_level_notes=split_level_notes, groups=groups)
